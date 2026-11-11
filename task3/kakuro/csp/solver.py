"""Backtracking Search combined with constraint propagation (AIMA Fig. 6.5 structure).

    BACKTRACK(assignment):
        if assignment is complete: return assignment
        var <- SELECT-UNASSIGNED-VARIABLE()            # Static / MRV / MRV+Degree
        for value in ORDER-DOMAIN-VALUES(var):          # Ascending / LCV
            if value is consistent with assignment:
                add var = value; domain(var) <- {value}
                if INFERENCE(var) does not empty a domain: # None / FC / MAC
                    result <- BACKTRACK(assignment)
                    if result != failure: return result
                undo var = value and every pruning made since    # trail
        return failure

Domains are mutated in place; every removed value is pushed on a *trail* so that undoing a
choice is just popping the trail back to a mark (cheaper than copying all domains per node).
"""

import random
import time

from .events import (ASSIGN, DEADEND, FINISH, PREPROCESS, PRUNE, REJECT, RESTORE, SELECT, SOLUTION,
                     UNASSIGN, Event, TraceLimitReached)
from .heuristics import VALUE_ORDERINGS, VARIABLE_ORDERINGS
from .inference import AC3, INFERENCES, NoInference
from .model import KakuroCSP

SOLVED = "solved"
UNSATISFIABLE = "unsatisfiable"
LIMIT = "limit reached"


class SolverConfig:
    """Which techniques to switch on. Names match the keys of VARIABLE_ORDERINGS etc."""

    def __init__(self, variable_order="MRV+Degree", value_order="LCV", inference="MAC", preprocess=True,
                 seed=None, max_solutions=1, node_limit=None, time_limit=None):
        self.variable_order = variable_order
        self.value_order = value_order
        self.inference = inference
        self.preprocess = preprocess          # run AC-3 on every arc before searching
        self.seed = seed                      # None = deterministic ties; int = random tie-breaking
        self.max_solutions = max_solutions    # 2 is enough to prove uniqueness
        self.node_limit = node_limit
        self.time_limit = time_limit

    @property
    def label(self):
        parts = ["BT", self.inference if self.inference != "None" else None, self.variable_order,
                 self.value_order if self.value_order != "Ascending" else None,
                 "AC3-pre" if self.preprocess else None]
        return " + ".join(p for p in parts if p and p != "Static")

    def copy(self, **changes):
        c = SolverConfig(**self.__dict__)
        c.__dict__.update(changes)
        return c


class SolverStats:
    def __init__(self):
        self.nodes = 0          # assignments made (search tree nodes)
        self.rejected = 0       # values refused by the consistency check
        self.backtracks = 0     # assignments undone because the subtree failed
        self.revisions = 0      # REVISE(arc) calls
        self.checks = 0         # constraint checks: consistency checks + support checks in REVISE / LCV
        self.prunings = 0       # values deleted from domains
        self.max_depth = 0      # deepest level of the search tree reached (space: O(n))
        self.max_trail = 0      # largest number of removed values remembered at once (space: O(n*d))
        self.preprocess_prunings = 0
        self.time = 0.0

    def as_dict(self):
        return dict(self.__dict__)


class SolveResult:
    def __init__(self, status, solutions, stats, config):
        self.status = status
        self.solutions = solutions
        self.stats = stats
        self.config = config

    @property
    def solution(self):
        return self.solutions[0] if self.solutions else None


class _Stop(Exception):
    pass


class BacktrackingSolver:
    def __init__(self, board, config=None, tracer=None):
        self.board = board
        self.csp = KakuroCSP(board)
        self.config = config or SolverConfig()
        self.tracer = tracer
        self.variable_order = VARIABLE_ORDERINGS[self.config.variable_order]()
        self.value_order = VALUE_ORDERINGS[self.config.value_order]()
        self.inference = INFERENCES[self.config.inference]()
        self.rng = random.Random(self.config.seed) if self.config.seed is not None else None
        self.domains = self.csp.initial_domains()
        self.assignment = {}
        self.trail = []                 # (var, removed value) in the order they were pruned
        self.stats = SolverStats()
        self.check_counter = [0]
        self.solutions = []
        self._depth = 0
        self._deadline = None

    # ------------------------------------------------------------------ public API
    def solve(self):
        start = time.perf_counter()
        if self.config.time_limit:
            self._deadline = start + self.config.time_limit
        status = None
        try:
            if self.config.preprocess:
                self.emit(PREPROCESS)
                ac3 = AC3(self)
                ok = ac3.run(ac3.all_arcs())
                self.stats.preprocess_prunings = self.stats.prunings
                if not ok:
                    status = UNSATISFIABLE
            if status is None:
                self._backtrack()
                status = SOLVED if self.solutions else UNSATISFIABLE
        except (_Stop, TraceLimitReached):
            status = LIMIT
        self.stats.time = time.perf_counter() - start
        self.stats.checks = self.check_counter[0]
        if self.tracer is not None:
            self.tracer.events.append(Event(FINISH, info="{} ({} solution(s))".format(status, len(self.solutions))))
        return SolveResult(status, list(self.solutions), self.stats, self.config)

    # ------------------------------------------------------------------ search
    def _backtrack(self):
        if len(self.assignment) == len(self.csp.variables):
            self.solutions.append(dict(self.assignment))
            self.emit(SOLUTION)
            return len(self.solutions) >= self.config.max_solutions
        self._check_limits()
        var = self.variable_order.select(self)
        self.emit(SELECT, var=var, info="(|D| = {})".format(len(self.domains[var])))
        for value in self.value_order.order(self, var):
            if not self.csp.is_consistent(var, value, self.assignment, self.check_counter):
                self.stats.rejected += 1
                self.emit(REJECT, var=var, value=value)
                continue
            mark = len(self.trail)
            self._assign(var, value)
            if self.inference.infer(self, var) and self._recurse():
                return True
            self._undo(var, value, mark)
        self.emit(DEADEND, var=var)
        return False

    def _recurse(self):
        self._depth += 1
        self.stats.max_depth = max(self.stats.max_depth, self._depth)
        try:
            return self._backtrack()
        finally:
            self._depth -= 1

    def _assign(self, var, value):
        self.stats.nodes += 1
        self.assignment[var] = value
        self.emit(ASSIGN, var=var, value=value)
        for other in sorted(self.domains[var] - {value}):  # D(var) <- {value}, kept on the trail for undo
            self.domains[var].discard(other)
            self.trail.append((var, other))
        if len(self.trail) > self.stats.max_trail:
            self.stats.max_trail = len(self.trail)

    def _undo(self, var, value, mark):
        self.stats.backtracks += 1
        restored = {}
        while len(self.trail) > mark:
            v, val = self.trail.pop()
            self.domains[v].add(val)
            restored.setdefault(v, set()).add(val)
        for v, vals in restored.items():
            self.emit(RESTORE, var=v, values=frozenset(vals))
        del self.assignment[var]
        self.emit(UNASSIGN, var=var, value=value)

    def _check_limits(self):
        if self.config.node_limit and self.stats.nodes >= self.config.node_limit:
            raise _Stop()
        if self._deadline and time.perf_counter() > self._deadline:
            raise _Stop()

    # ------------------------------------------------------------------ helpers used by heuristics/inference
    def prune(self, var, value, constraint=None, info=""):
        self.domains[var].discard(value)
        self.trail.append((var, value))
        if len(self.trail) > self.stats.max_trail:
            self.stats.max_trail = len(self.trail)
        self.stats.prunings += 1
        self.emit(PRUNE, var=var, value=value, constraint=constraint, info=info)

    def emit(self, kind, **fields):
        if self.tracer is not None:
            self.tracer.emit(Event(kind, depth=self._depth, **fields))

    def legal_value_count(self, var):
        """Number of values of var still possible. With propagation the domain is already
        filtered; without it we count the values passing the consistency check (AIMA's MRV)."""
        if isinstance(self.inference, NoInference):
            return sum(1 for v in self.domains[var]
                       if self.csp.is_consistent(var, v, self.assignment, self.check_counter))
        return len(self.domains[var])

    def count_ruled_out(self, var, value):
        """For LCV: how many neighbour values disappear if var = value (one forward-checking step)."""
        saved = self.domains[var]
        self.domains[var] = {value}
        self.assignment[var] = value
        try:
            ruled_out = 0
            for c in self.csp.constraints_of[var]:
                for y in c.variables:
                    if y == var or y in self.assignment:
                        continue
                    left = len(c.supported_values(y, self.domains, self.check_counter))
                    if left == 0:
                        return float("inf")
                    ruled_out += len(self.domains[y]) - left
            return ruled_out
        finally:
            self.domains[var] = saved
            del self.assignment[var]


def solve(board, config=None, tracer=None):
    return BacktrackingSolver(board, config, tracer).solve()
