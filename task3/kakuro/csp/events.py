"""Search events. The solver reports every step it takes; the GUI replays them one by one.

Only ASSIGN / UNASSIGN / PRUNE / RESTORE change the state (assignment and domains); the other
kinds are there to highlight what the solver is looking at.
"""

PREPROCESS = "PREPROCESS"   # initial AC-3 over all arcs starts
SELECT = "SELECT"           # variable chosen by the variable-ordering heuristic
REJECT = "REJECT"           # value fails the consistency check, not assigned
ASSIGN = "ASSIGN"           # var = value
REVISE = "REVISE"           # constraint propagation revises arc (var, constraint)
PRUNE = "PRUNE"             # value removed from var's domain
WIPEOUT = "WIPEOUT"         # var's domain became empty -> failure
RESTORE = "RESTORE"         # values put back into var's domain when undoing
UNASSIGN = "UNASSIGN"       # var = value is undone
DEADEND = "DEADEND"         # every value of var failed, backtrack to the previous variable
SOLUTION = "SOLUTION"
FINISH = "FINISH"


class Event:
    __slots__ = ("kind", "var", "value", "values", "constraint", "depth", "info")

    def __init__(self, kind, var=None, value=None, values=None, constraint=None, depth=0, info=""):
        self.kind = kind
        self.var = var
        self.value = value
        self.values = values
        self.constraint = constraint  # SumAllDiffConstraint or None
        self.depth = depth
        self.info = info

    def describe(self):
        var = "({},{})".format(*self.var) if self.var else ""
        con = self.constraint.name if self.constraint else ""
        text = {
            PREPROCESS: "Initial AC-3 on all arcs",
            SELECT: "Select {} {}".format(var, self.info),
            REJECT: "{} = {} inconsistent".format(var, self.value),
            ASSIGN: "Assign {} = {}".format(var, self.value),
            REVISE: "Revise {} w.r.t. {}".format(var, con),
            PRUNE: "Prune {} from {} ({})".format(self.value, var, con or self.info),
            WIPEOUT: "Domain of {} empty ({})".format(var, con),
            RESTORE: "Restore {} to {}".format(sorted(self.values or ()), var),
            UNASSIGN: "Undo {} = {}".format(var, self.value),
            DEADEND: "Dead end at {} -> backtrack".format(var),
            SOLUTION: "Solution found",
            FINISH: "Finished: {}".format(self.info),
        }.get(self.kind, self.kind)
        return text


class TraceLimitReached(Exception):
    pass


class Tracer:
    """Collects events. Stops the solver (by raising) if the trace grows past `max_events`."""

    def __init__(self, max_events=300000):
        self.events = []
        self.max_events = max_events

    def emit(self, event):
        if len(self.events) >= self.max_events:
            raise TraceLimitReached()
        self.events.append(event)
