import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kakuro.core import KakuroBoard, PuzzleFormatError, load_puzzle  # noqa: E402
from kakuro.core.generator import generate  # noqa: E402
from kakuro.csp import (INFERENCES, VALUE_ORDERINGS, VARIABLE_ORDERINGS, KakuroCSP, SolverConfig,  # noqa: E402
                        digit_combinations, solve)
from kakuro.csp.solver import BacktrackingSolver  # noqa: E402
from kakuro.csp.inference import AC3  # noqa: E402

EXAMPLE_SOLUTION = """# # # # #
# # 8 4 #
# 9 3 1 8
# 5 1 2 3
# # 9 7 #"""


class TestBoard(unittest.TestCase):
    def test_parse_example(self):
        board = load_puzzle("example_5x5")
        self.assertEqual((board.rows, board.cols), (5, 5))
        self.assertEqual(len(board.white_cells), 12)
        self.assertEqual(sorted(r.total for r in board.runs), sorted([21, 14, 14, 11, 12, 21, 11, 16]))
        for pos in board.white_cells:            # every white cell lies in one across and one down run
            self.assertEqual(sorted(r.direction for r in board.runs_of[pos]), ["across", "down"])

    def test_parse_complex(self):
        board = load_puzzle("complex_9x9")
        self.assertEqual(len(board.white_cells), 48)
        self.assertEqual(len(board.runs), 28)
        across = sum(r.total for r in board.runs if r.direction == "across")
        down = sum(r.total for r in board.runs if r.direction == "down")
        self.assertEqual(across, down)           # both add up to the sum of all digits

    def test_bad_puzzles(self):
        with self.assertRaises(PuzzleFormatError):
            KakuroBoard.from_text("# x\n# .")
        with self.assertRaises(PuzzleFormatError):
            KakuroBoard.from_text("#  \\3\n#  #")      # clue with no cells after it
        with self.assertRaises(PuzzleFormatError):
            KakuroBoard.from_text("# #\n# .")          # white cell without a clue


class TestConstraint(unittest.TestCase):
    def test_combinations(self):
        self.assertEqual(digit_combinations(2, 3), (frozenset({1, 2}),))
        self.assertEqual(digit_combinations(2, 17), (frozenset({8, 9}),))
        self.assertEqual(len(digit_combinations(9, 45)), 1)
        self.assertEqual(digit_combinations(2, 2), ())

    def test_supported_values(self):
        board = KakuroBoard.from_text("#   3\\  4\\\n\\3  .   .\n\\4  .   .")
        csp = KakuroCSP(board)
        c = next(c for c in csp.constraints if c.total == 3 and c.run.direction == "across")
        domains = csp.initial_domains()
        self.assertEqual(c.supported_values((1, 1), domains), {1, 2})
        domains[(1, 2)] = {2}
        self.assertEqual(c.supported_values((1, 1), domains), {1})

    def test_consistency_check(self):
        csp = KakuroCSP(load_puzzle("example_5x5"))
        row4 = next(c for c in csp.constraints if c.total == 16)   # (4,2) + (4,3) = 16
        self.assertTrue(row4.is_consistent({(4, 2): 7}))
        self.assertFalse(row4.is_consistent({(4, 2): 7, (4, 3): 7}))
        self.assertFalse(row4.is_consistent({(4, 2): 7, (4, 3): 8}))
        self.assertTrue(row4.is_consistent({(4, 2): 7, (4, 3): 9}))


class TestSolver(unittest.TestCase):
    def test_example_solution_and_uniqueness(self):
        board = load_puzzle("example_5x5")
        result = solve(board, SolverConfig(max_solutions=2))
        self.assertEqual(len(result.solutions), 1)
        self.assertEqual(board.format_solution(result.solution), EXAMPLE_SOLUTION)

    def test_complex_unique(self):
        board = load_puzzle("complex_9x9")
        result = solve(board, SolverConfig(max_solutions=2))
        self.assertEqual(result.status, "solved")
        self.assertEqual(len(result.solutions), 1)
        self.assertTrue(board.is_solution(result.solution))

    def test_every_configuration_on_example(self):
        board = load_puzzle("example_5x5")
        for inf in INFERENCES:
            for var in VARIABLE_ORDERINGS:
                for val in VALUE_ORDERINGS:
                    for pre in (True, False):
                        r = solve(board, SolverConfig(var, val, inf, pre))
                        self.assertTrue(board.is_solution(r.solution), (inf, var, val, pre))

    def test_domains_restored_after_search(self):
        """Undoing must put back exactly what was pruned: after exploring the whole tree the
        domains equal those right after preprocessing."""
        board = load_puzzle("complex_9x9")
        s = BacktrackingSolver(board, SolverConfig("Static", "Ascending", "FC", False, max_solutions=99))
        s.solve()
        self.assertEqual(s.domains, s.csp.initial_domains())
        self.assertEqual(s.assignment, {})

    def test_preprocess_gac(self):
        s = BacktrackingSolver(load_puzzle("example_5x5"))
        self.assertTrue(AC3(s).run(AC3(s).all_arcs()))
        self.assertEqual(s.domains[(4, 2)], {9})        # forced by 16 = 7 + 9 and 21 down
        self.assertEqual(s.domains[(4, 3)], {7})

    def test_unsatisfiable(self):
        board = KakuroBoard.from_text("#   3\\  3\\\n\\3  .   .\n\\4  .   .")
        for pre in (True, False):
            r = solve(board, SolverConfig(preprocess=pre))
            self.assertEqual(r.status, "unsatisfiable")

    def test_random_boards(self):
        for seed in range(4):
            text, _ = generate(8, 8, seed)
            board = KakuroBoard.from_text(text)
            r = solve(board, SolverConfig(seed=seed))
            self.assertTrue(board.is_solution(r.solution))

    def test_node_limit(self):
        r = solve(load_puzzle("complex_9x9"), SolverConfig("Static", "Ascending", "None", False, node_limit=50))
        self.assertEqual(r.status, "limit reached")


class TestReplay(unittest.TestCase):
    def test_seek_matches_sequential(self):
        from kakuro.gui.replay import TraceReplay
        board = load_puzzle("example_5x5")
        rep = TraceReplay(board, SolverConfig("Static", "Ascending", "FC", False))
        snapshots = []
        while not rep.done:
            snapshots.append((rep.index, {v: set(d) for v, d in rep.state.domains.items()},
                              dict(rep.state.assignment)))
            rep.step(37)
        self.assertTrue(rep.state.solved)
        self.assertTrue(board.is_solution(rep.state.assignment))
        for index, domains, assignment in reversed(snapshots):
            rep.seek(index)
            self.assertEqual(rep.state.domains, domains)
            self.assertEqual(rep.state.assignment, assignment)


if __name__ == "__main__":
    unittest.main()
