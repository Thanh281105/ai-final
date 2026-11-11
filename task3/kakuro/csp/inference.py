"""Constraint propagation (Lecture 08).

All three strategies share the same REVISE step (`AC3.revise`): remove the values of a variable
that have no support in one constraint. They differ in which arcs get revised:

- NoInference:     nothing; plain backtracking only checks the assigned cells.
- ForwardChecking: after X = v, revise each unassigned neighbour once against X's constraints.
                   No further propagation.
- MAC:             Maintaining Arc Consistency: after X = v, run AC-3 starting from the arcs of
                   X's neighbours and keep propagating until nothing changes.

Because the constraints are n-ary, an "arc" is a pair (variable Y, constraint C) and consistency
is *generalized* arc consistency (GAC): every value of Y has a support tuple in C.
"""

from collections import deque

from .events import REVISE, WIPEOUT


class AC3:
    """AC-3 generalized to n-ary constraints. Works on the solver's current domains."""

    def __init__(self, solver):
        self.solver = solver

    def revise(self, var, constraint):
        """Remove unsupported values of var w.r.t. constraint. Returns (changed, still_ok)."""
        s = self.solver
        s.stats.revisions += 1
        s.emit(REVISE, var=var, constraint=constraint)
        supported = constraint.supported_values(var, s.domains, s.check_counter)
        removed = s.domains[var] - supported
        for value in sorted(removed):
            s.prune(var, value, constraint)
        if not s.domains[var]:
            s.emit(WIPEOUT, var=var, constraint=constraint)
            return bool(removed), False
        return bool(removed), True

    def run(self, queue):
        """Standard AC-3 loop. `queue` holds arcs (Y, C). Returns False on a domain wipe-out."""
        s = self.solver
        queue = deque(queue)
        in_queue = set(queue)
        while queue:
            var, constraint = queue.popleft()
            in_queue.discard((var, constraint))
            changed, ok = self.revise(var, constraint)
            if not ok:
                return False
            if changed:
                # var lost values: every other variable sharing another constraint with it must be rechecked
                for other_c in s.csp.constraints_of[var]:
                    if other_c is constraint:
                        continue
                    for z in other_c.variables:
                        if z != var and z not in s.assignment and (z, other_c) not in in_queue:
                            queue.append((z, other_c))
                            in_queue.add((z, other_c))
        return True

    def all_arcs(self):
        s = self.solver
        return [(v, c) for c in s.csp.constraints for v in c.variables if v not in s.assignment]

    def arcs_towards(self, var):
        """Arcs (Y, C) for every constraint C of var and every unassigned Y in C."""
        s = self.solver
        return [(y, c) for c in s.csp.constraints_of[var] for y in c.variables
                if y != var and y not in s.assignment]


class Inference:
    name = "?"

    def infer(self, solver, var):
        """Called right after var is assigned. Returns False if a domain became empty."""
        raise NotImplementedError


class NoInference(Inference):
    name = "None"

    def infer(self, solver, var):
        return True


class ForwardChecking(Inference):
    name = "FC"

    def infer(self, solver, var):
        ac3 = AC3(solver)
        for y, c in ac3.arcs_towards(var):
            _, ok = ac3.revise(y, c)
            if not ok:
                return False
        return True


class MAC(Inference):
    name = "MAC"

    def infer(self, solver, var):
        ac3 = AC3(solver)
        return ac3.run(ac3.arcs_towards(var))


INFERENCES = {cls.name: cls for cls in (NoInference, ForwardChecking, MAC)}
