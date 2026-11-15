"""Chạy:  python -m unittest discover -s tests -v"""
import sys
import unittest
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nqueens_solver.core import (  # noqa: E402
    Board,
    ConflictState,
    ConstraintDiscoverer,
    MinConflictsSolver,
    NQueensCNF,
)

try:
    import pysat  # noqa: F401

    HAS_PYSAT = True
except ImportError:
    HAS_PYSAT = False


class BoardTests(unittest.TestCase):
    def test_valid_solution_n4(self):
        self.assertTrue(Board.from_columns([1, 3, 0, 2]).is_solution())

    def test_detects_attacks(self):
        b = Board.from_columns([0, 1, 2, 3])  # cùng đường chéo chính
        self.assertEqual(b.attacking_pairs(), 6)
        self.assertFalse(b.is_solution())

    def test_decode_model(self):
        # N=4: biến v = r*4 + c + 1
        model = [-1, 2, -3, -4, -5, -6, -7, 8, 9, -10, -11, -12, -13, -14, 15, -16]
        self.assertEqual(Board.from_model(4, model).queens, {(0, 1), (1, 3), (2, 0), (3, 2)})


class CNFTests(unittest.TestCase):
    def test_clause_count_matches_closed_form(self):
        for n in range(1, 13):
            self.assertEqual(NQueensCNF(n).num_clauses, NQueensCNF.expected_clause_count(n), n)

    def test_constraints_equal_brute_force_attack_relation(self):
        for n in range(2, 8):
            cells = [(r, c) for r in range(n) for c in range(n)]
            expected = {frozenset(p) for p in combinations(cells, 2) if ConstraintDiscoverer.attacks(*p)}
            cnf = NQueensCNF(n)
            produced = set()
            for g in cnf.groups[1:]:  # bỏ nhóm "ít nhất một"
                for a, b in g.clauses:
                    self.assertTrue(a < 0 and b < 0)
                    produced.add(frozenset((cnf.vars.cell(-a), cnf.vars.cell(-b))))
            self.assertEqual(produced, expected, n)

    def test_each_attacking_pair_appears_once(self):
        cnf = NQueensCNF(6)
        seen = [frozenset(c) for g in cnf.groups[1:] for c in g.clauses]
        self.assertEqual(len(seen), len(set(seen)))

    def test_column_alo_adds_exactly_n_clauses(self):
        for n in range(1, 10):
            cnf = NQueensCNF(n, column_alo=True)
            self.assertEqual(cnf.num_clauses, NQueensCNF(n).num_clauses + n)
            self.assertEqual(cnf.num_clauses, NQueensCNF.expected_clause_count(n, column_alo=True))
            self.assertEqual(cnf.groups[-1].key, "col_alo")

    def test_variable_mapping_roundtrip(self):
        cnf = NQueensCNF(5)
        for r in range(5):
            for c in range(5):
                self.assertEqual(cnf.vars.cell(cnf.vars.var(r, c)), (r, c))


class ConflictStateTests(unittest.TestCase):
    def test_incremental_total_matches_board(self):
        cols = [2, 0, 3, 3, 1, 5, 4, 4]
        state = ConflictState(len(cols))
        for r, c in enumerate(cols):
            state.place(r, c)
        self.assertEqual(state.total, Board.from_columns(cols).attacking_pairs())
        state.remove(3)
        state.place(3, 6)
        cols[3] = 6
        self.assertEqual(state.total, Board.from_columns(cols).attacking_pairs())


class MinConflictsTests(unittest.TestCase):
    def test_both_variants_return_valid_solutions(self):
        for factory in (MinConflictsSolver.standard, MinConflictsSolver.heuristic):
            for n in (4, 5, 32, 50, 100):
                res = factory(50_000).solve(n, seed=7)
                self.assertTrue(res.solved, (res.algorithm, n))
                self.assertTrue(res.board.is_solution(), (res.algorithm, n))

    def test_heuristic_differs_from_standard_only_in_variable_selection(self):
        from nqueens_solver.core.min_conflicts import (
            MinConflictsValue, MostConflictedTabuSelector, RandomConflictedSelector, RandomInitializer,
        )

        std, heu = MinConflictsSolver.standard(), MinConflictsSolver.heuristic()
        self.assertIsInstance(std.var_selector, RandomConflictedSelector)
        self.assertIsInstance(heu.var_selector, MostConflictedTabuSelector)
        for solver in (std, heu):
            self.assertIsInstance(solver.initializer, RandomInitializer)
            self.assertIsInstance(solver.value_selector, MinConflictsValue)
            self.assertIsNone(solver.stall_factor)      # không khởi động lại
        # Cùng seed -> cùng phép gán ban đầu, nên phép so sánh là công bằng.
        for seed in range(5):
            self.assertEqual(std.solve(40, seed=seed).init_cols, heu.solve(40, seed=seed).init_cols)

    def test_proposed_selector_picks_most_conflicted_and_respects_tabu(self):
        import random

        from nqueens_solver.core.min_conflicts import MostConflictedTabuSelector

        state = ConflictState(6)
        for r, c in enumerate([0, 0, 0, 3, 5, 1]):   # hàng 0,1,2 cùng cột; hàng 1 còn dính đường chéo
            state.place(r, c)
        counts = state.all_queen_conflicts()
        top = max(counts)
        selector = MostConflictedTabuSelector(tenure=2)
        selector.reset(6)
        rng = random.Random(0)
        first = selector.select(state, rng)
        self.assertEqual(counts[first], top)
        second = selector.select(state, rng)
        self.assertNotEqual(second, first, "biến vừa chọn phải bị cấm trong tenure bước")
        self.assertGreater(counts[second], 0)

    def test_enhanced_variant_solves(self):
        for n in (4, 8, 16, 50):
            res = MinConflictsSolver.enhanced(50_000).solve(n, seed=7)
            self.assertTrue(res.solved and res.board.is_solution(), n)

    def test_reproducible_with_seed(self):
        a = MinConflictsSolver.heuristic().solve(30, seed=3)
        b = MinConflictsSolver.heuristic().solve(30, seed=3)
        self.assertEqual((a.steps, a.board.queens), (b.steps, b.board.queens))

    def test_recorded_events_replay_to_final_board(self):
        res = MinConflictsSolver.standard().solve(20, seed=5, record=True)
        cols = list(res.init_cols)
        for e in res.events:
            if e[0] == "move":
                cols[e[1]] = e[3]
            else:
                cols = list(e[1])
        self.assertEqual(cols, res.board.to_columns())

    def test_n2_n3_rejected(self):
        with self.assertRaises(ValueError):
            MinConflictsSolver.standard().solve(3)


@unittest.skipUnless(HAS_PYSAT, "cần cài python-sat")
class SATTests(unittest.TestCase):
    def test_glucose3_solutions_are_valid(self):
        from nqueens_solver.core import GlucoseQueensSolver

        solver = GlucoseQueensSolver()
        for n in (4, 5, 6, 8, 10, 12):
            res = solver.solve(n)
            self.assertTrue(res.satisfiable and res.valid, n)
            self.assertEqual(res.num_clauses, NQueensCNF.expected_clause_count(n))
            self.assertEqual(res.num_clauses, (5 * n ** 3 - 6 * n ** 2 + 4 * n) // 3)   # dạng rút gọn
            self.assertGreater(res.propagations, 0)

    def test_unsat_for_n2_n3(self):
        from nqueens_solver.core import GlucoseQueensSolver

        for n in (2, 3):
            self.assertFalse(GlucoseQueensSolver().solve(n).satisfiable)

    def _models(self, n, column_alo):
        from pysat.solvers import Glucose3

        cnf = NQueensCNF(n, column_alo=column_alo)
        solver = Glucose3(bootstrap_with=cnf.iter_clauses())
        try:
            return {frozenset(v for v in model if v > 0) for model in solver.enum_models()}
        finally:
            solver.delete()

    def test_models_are_exactly_the_n_queens_solutions(self):
        """Mỗi mô hình của KB là một lời giải N-Queens và ngược lại (số lời giải đã biết)."""
        known = {1: 1, 2: 0, 3: 0, 4: 2, 5: 10, 6: 4, 7: 40, 8: 92}
        for n, count in known.items():
            models = self._models(n, column_alo=False)
            self.assertEqual(len(models), count, n)
            for model in models:
                self.assertTrue(Board.from_model(n, model).is_solution(), n)

    def test_column_alo_is_entailed_by_the_kb(self):
        """Thêm "mỗi cột ít nhất một hậu" không đổi tập mô hình (KB ⊨ mệnh đề đó)."""
        for n in range(1, 9):
            self.assertEqual(self._models(n, column_alo=False), self._models(n, column_alo=True), n)

    def test_column_alo_solutions_are_valid(self):
        from nqueens_solver.core import GlucoseQueensSolver

        for n in (4, 8, 16, 30):
            res = GlucoseQueensSolver().solve(n, column_alo=True)
            self.assertTrue(res.satisfiable and res.valid, n)
            self.assertEqual(res.num_clauses, (5 * n ** 3 - 6 * n ** 2 + 7 * n) // 3)


if __name__ == "__main__":
    unittest.main()
