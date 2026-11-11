"""Ordering heuristics from Lecture 08 (Strategy pattern: the solver only calls `select` / `order`).

Variable ordering:  StaticOrder, MRV, MRVDegree (MRV with the degree heuristic as tie-breaker)
Value ordering:     AscendingValues, LeastConstrainingValue (LCV)
"""


class VariableOrdering:
    name = "?"

    def select(self, solver):
        """Return the next unassigned variable."""
        raise NotImplementedError


class StaticOrder(VariableOrdering):
    """Row-major order of the board: the first unassigned cell."""

    name = "Static"

    def select(self, solver):
        for var in solver.csp.variables:
            if var not in solver.assignment:
                return var
        return None


class MRV(VariableOrdering):
    """Minimum Remaining Values: the variable with the fewest legal values left ("fail first")."""

    name = "MRV"

    def key(self, solver, var):
        return (solver.legal_value_count(var),)

    def select(self, solver):
        best, best_key = [], None
        for var in solver.csp.variables:
            if var in solver.assignment:
                continue
            key = self.key(solver, var)
            if best_key is None or key < best_key:
                best, best_key = [var], key
            elif key == best_key:
                best.append(var)
        if not best:
            return None
        return solver.rng.choice(best) if solver.rng else best[0]


class MRVDegree(MRV):
    """MRV, ties broken by the degree heuristic: most constraints with *unassigned* variables."""

    name = "MRV+Degree"

    def key(self, solver, var):
        degree = sum(1 for n in solver.csp.neighbors[var] if n not in solver.assignment)
        return (solver.legal_value_count(var), -degree)


class ValueOrdering:
    name = "?"

    def order(self, solver, var):
        """Return the values of var's current domain in the order to try them."""
        raise NotImplementedError


class AscendingValues(ValueOrdering):
    name = "Ascending"

    def order(self, solver, var):
        return sorted(solver.domains[var])


class LeastConstrainingValue(ValueOrdering):
    """LCV: try first the value that rules out the fewest values in the neighbours' domains.

    For each candidate v we pretend var = v and revise every unassigned neighbour against the
    runs of var (one step of forward checking), counting how many values that removes. A value
    that empties a neighbour's domain is tried last.
    """

    name = "LCV"

    def order(self, solver, var):
        scores = []
        for value in solver.domains[var]:
            ruled_out = solver.count_ruled_out(var, value)
            tie = solver.rng.random() if solver.rng else 0
            scores.append((ruled_out, tie, value))
        scores.sort()
        return [value for _, _, value in scores]


VARIABLE_ORDERINGS = {cls.name: cls for cls in (StaticOrder, MRV, MRVDegree)}
VALUE_ORDERINGS = {cls.name: cls for cls in (AscendingValues, LeastConstrainingValue)}
