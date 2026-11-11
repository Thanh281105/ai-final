"""Replays a recorded solver trace step by step (no pygame here, so it can be unit-tested).

The solver is run once with a Tracer; the GUI then moves a cursor over the event list.
Going forward applies events; going backward reloads the nearest keyframe (a snapshot taken
every KEYFRAME_EVERY events) and re-applies events up to the target index.
"""

from ..csp import Tracer
from ..csp.events import (ASSIGN, DEADEND, PRUNE, REJECT, RESTORE, REVISE, SELECT, SOLUTION, UNASSIGN,
                          WIPEOUT)
from ..csp.solver import BacktrackingSolver

KEYFRAME_EVERY = 250
MAX_EVENTS = 300000


class ReplayState:
    """Everything the GUI draws for one moment of the search."""

    def __init__(self, domains):
        self.domains = {v: set(d) for v, d in domains.items()}
        self.assignment = {}
        self.path = []                    # [(var, value)] in assignment order = current search branch
        self.selected = None              # variable chosen by the last SELECT
        self.revising = None              # (var, constraint) of the last REVISE
        self.recent_pruned = set()        # (var, value) removed since the last decision -> drawn red
        self.recent_restored = set()      # (var, value) put back by the last undo -> drawn green
        self.rejected = set()             # (var, value) refused by the consistency check
        self.failed_var = None            # wipe-out / dead-end cell
        self.solved = False
        self.counters = {"nodes": 0, "backtracks": 0, "prunings": 0, "revisions": 0, "rejected": 0}

    def copy(self):
        c = ReplayState({})
        c.domains = {v: set(d) for v, d in self.domains.items()}
        c.assignment = dict(self.assignment)
        c.path = list(self.path)
        c.selected = self.selected
        c.revising = self.revising
        c.recent_pruned = set(self.recent_pruned)
        c.recent_restored = set(self.recent_restored)
        c.rejected = set(self.rejected)
        c.failed_var = self.failed_var
        c.solved = self.solved
        c.counters = dict(self.counters)
        return c

    def apply(self, e):
        k = e.kind
        if k == SELECT:
            self.selected = e.var
            self.revising = None
            self.recent_pruned.clear()
            self.recent_restored.clear()
            self.rejected.clear()
            self.failed_var = None
        elif k == ASSIGN:
            self.assignment[e.var] = e.value
            self.domains[e.var] = {e.value}     # the solver does the same (its removals go on the trail)
            self.path.append((e.var, e.value))
            self.counters["nodes"] += 1
            self.recent_pruned.clear()
            self.recent_restored.clear()
            self.failed_var = None
        elif k == REJECT:
            self.rejected.add((e.var, e.value))
            self.counters["rejected"] += 1
        elif k == REVISE:
            self.revising = (e.var, e.constraint)
            self.counters["revisions"] += 1
        elif k == PRUNE:
            self.domains[e.var].discard(e.value)
            self.recent_pruned.add((e.var, e.value))
            self.counters["prunings"] += 1
        elif k == WIPEOUT:
            self.failed_var = e.var
        elif k == RESTORE:
            self.domains[e.var] |= e.values
            self.recent_restored |= {(e.var, v) for v in e.values}
            self.recent_pruned -= {(e.var, v) for v in e.values}
        elif k == UNASSIGN:
            self.assignment.pop(e.var, None)
            if self.path and self.path[-1][0] == e.var:
                self.path.pop()
            self.counters["backtracks"] += 1
            self.revising = None
        elif k == DEADEND:
            self.failed_var = e.var
            self.selected = e.var
        elif k == SOLUTION:
            self.solved = True
            self.revising = None


class TraceReplay:
    def __init__(self, board, config, max_events=MAX_EVENTS):
        self.board = board
        self.config = config
        tracer = Tracer(max_events)
        solver = BacktrackingSolver(board, config, tracer)
        self.result = solver.solve()
        self.csp = solver.csp
        self.events = tracer.events
        self.truncated = self.result.status == "limit reached"
        self.depths = [e.depth for e in self.events]
        self.keyframes = {}
        self.index = 0                                        # number of events applied
        self.state = ReplayState(self.csp.initial_domains())
        self.keyframes[0] = self.state.copy()

    def __len__(self):
        return len(self.events)

    @property
    def current_event(self):
        return self.events[self.index - 1] if self.index > 0 else None

    @property
    def done(self):
        return self.index >= len(self.events)

    def step(self, n=1):
        while n > 0 and self.index < len(self.events):
            self.state.apply(self.events[self.index])
            self.index += 1
            if self.index % KEYFRAME_EVERY == 0 and self.index not in self.keyframes:
                self.keyframes[self.index] = self.state.copy()
            n -= 1

    def step_until(self, kinds):
        """Advance until an event of one of `kinds` has been applied (e.g. the next decision)."""
        while self.index < len(self.events):
            kind = self.events[self.index].kind
            self.step()
            if kind in kinds:
                return

    def seek(self, target):
        target = max(0, min(len(self.events), target))
        if target < self.index:
            base = (target // KEYFRAME_EVERY) * KEYFRAME_EVERY
            while base not in self.keyframes:
                base -= KEYFRAME_EVERY
            self.state = self.keyframes[base].copy()
            self.index = base
        self.step(target - self.index)

    def back(self, n=1):
        self.seek(self.index - n)
