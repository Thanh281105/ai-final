"""The only kind of constraint in Kakuro: a run's digits are all different and add up to its clue.

We keep it as ONE n-ary constraint per run instead of splitting it into binary `≠` constraints
plus a sum, because the sum and the all-different parts are much stronger together: e.g. a
2-cell run with clue 3 forces the set {1, 2}, which neither part can deduce alone.

The key tool is the table of digit *combinations*: for a run of k cells and sum s, the sets of
k distinct digits from 1..9 adding up to s. There are at most 12 such sets for any (k, s), so
checking a value against the table is cheap.
"""

from functools import lru_cache
from itertools import combinations

DIGITS = frozenset(range(1, 10))


@lru_cache(maxsize=None)
def digit_combinations(k, total):
    """All sets of k distinct digits 1..9 with the given sum, e.g. (2, 4) -> [{1, 3}]."""
    return tuple(frozenset(c) for c in combinations(range(1, 10), k) if sum(c) == total)


class SumAllDiffConstraint:
    """Constraint over the variables of one run: AllDifferent(vars) and Sum(vars) == total."""

    def __init__(self, run):
        self.run = run
        self.id = run.id
        self.name = run.name
        self.variables = run.cells
        self.total = run.total
        self.combos = digit_combinations(len(run.cells), run.total)

    def __repr__(self):
        return "Constraint({})".format(self.name)

    # ------------------------------------------------------------------ plain consistency check
    def is_consistent(self, assignment):
        """Can the *assigned* variables of this run still be part of a solution of this run alone?

        Used by plain backtracking: assigned digits must be distinct, and their sum must be exactly
        the clue when the run is full, or smaller than it otherwise (every empty cell adds >= 1).
        """
        values = [assignment[v] for v in self.variables if v in assignment]
        if len(set(values)) != len(values):
            return False
        partial = sum(values)
        if len(values) == len(self.variables):
            return partial == self.total
        return partial < self.total

    # ------------------------------------------------------------------ generalized arc consistency
    def supported_values(self, var, domains, counter=None):
        """Values of `var` that have a *support*: a full tuple of the run that satisfies the
        constraint, uses var's value, and takes every other cell's value from that cell's domain.

        A value v is supported iff some combination C contains v and the remaining digits C - {v}
        can be given one-to-one to the other cells (a bipartite matching, checked by `_matchable`).
        `counter` (a one-element list) counts the support checks, for the statistics.
        """
        others = [x for x in self.variables if x != var]
        supported = set()
        for combo in self.combos:
            for value in (combo & domains[var]) - supported:
                if counter is not None:
                    counter[0] += 1
                if _matchable(others, combo - {value}, domains):
                    supported.add(value)
        return supported


def _matchable(variables, digits, domains):
    """True if each variable can take a different digit from `digits` within its own domain.

    Augmenting-path bipartite matching (Kuhn's algorithm); runs have at most 9 cells, so it is tiny.
    """
    owner = {}  # digit -> variable currently matched to it

    def try_assign(var, seen):
        for d in domains[var]:
            if d in digits and d not in seen:
                seen.add(d)
                if d not in owner or try_assign(owner[d], seen):
                    owner[d] = var
                    return True
        return False

    return all(try_assign(var, set()) for var in variables)
