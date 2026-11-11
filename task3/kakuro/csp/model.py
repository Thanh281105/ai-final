"""Kakuro written as a CSP <X, D, C> (see docs/formulation.md)."""

from .constraint import DIGITS, SumAllDiffConstraint


class KakuroCSP:
    """X = white cells, D(x) = {1..9}, C = one SumAllDiffConstraint per run.

    Also builds the constraint graph: two variables are neighbours if they share a run.
    """

    def __init__(self, board):
        self.board = board
        self.variables = list(board.white_cells)  # row-major order, used by the static ordering
        self.constraints = [SumAllDiffConstraint(run) for run in board.runs]
        self.constraints_of = {v: [] for v in self.variables}
        for c in self.constraints:
            for v in c.variables:
                self.constraints_of[v].append(c)
        self.neighbors = {v: set() for v in self.variables}
        for c in self.constraints:
            for v in c.variables:
                self.neighbors[v].update(x for x in c.variables if x != v)

    def initial_domains(self):
        return {v: set(DIGITS) for v in self.variables}

    def is_consistent(self, var, value, assignment, counter=None):
        """Would var=value break any constraint, given the current partial assignment?

        `counter` (a one-element list) counts the constraint checks: one per constraint tested.
        """
        assignment[var] = value
        try:
            for c in self.constraints_of[var]:
                if counter is not None:
                    counter[0] += 1
                if not c.is_consistent(assignment):
                    return False
            return True
        finally:
            del assignment[var]

    def summary(self):
        arities = [len(c.variables) for c in self.constraints]
        edges = sum(len(n) for n in self.neighbors.values()) // 2
        return {
            "variables": len(self.variables),
            "constraints": len(self.constraints),
            "min_arity": min(arities),
            "max_arity": max(arities),
            "graph_edges": edges,
            "search_space": "9^{}".format(len(self.variables)),
        }
