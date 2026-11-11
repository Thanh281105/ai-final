"""Command-line solver.

    python solve.py complex_9x9
    python solve.py example_5x5 --inference FC --var-order Static --value-order Ascending --no-preprocess
    python solve.py complex_9x9 --all          # look for a 2nd solution to prove uniqueness
"""

import argparse

from kakuro.core import list_puzzles, load_puzzle
from kakuro.csp import INFERENCES, VALUE_ORDERINGS, VARIABLE_ORDERINGS, KakuroCSP, SolverConfig, solve


def main():
    p = argparse.ArgumentParser(description="Solve a Kakuro puzzle with backtracking + constraint propagation")
    p.add_argument("puzzle", nargs="?", default="complex_9x9", help="name in puzzles/ or a file path")
    p.add_argument("--inference", default="MAC", choices=list(INFERENCES))
    p.add_argument("--var-order", default="MRV+Degree", choices=list(VARIABLE_ORDERINGS))
    p.add_argument("--value-order", default="LCV", choices=list(VALUE_ORDERINGS))
    p.add_argument("--no-preprocess", action="store_true", help="skip the initial AC-3")
    p.add_argument("--seed", type=int, default=None, help="random tie-breaking")
    p.add_argument("--all", action="store_true", help="keep searching for a second solution")
    p.add_argument("--time-limit", type=float, default=None)
    p.add_argument("--list", action="store_true", help="list available puzzles")
    args = p.parse_args()

    if args.list:
        print("\n".join(list_puzzles()))
        return
    board = load_puzzle(args.puzzle)
    config = SolverConfig(args.var_order, args.value_order, args.inference, not args.no_preprocess,
                          seed=args.seed, max_solutions=2 if args.all else 1, time_limit=args.time_limit)
    print("Puzzle:", board.name, "| CSP:", KakuroCSP(board).summary())
    print("Solver:", config.label)
    result = solve(board, config)
    print("Status:", result.status, "| solutions found:", len(result.solutions))
    for i, sol in enumerate(result.solutions, 1):
        print("\nSolution {} (valid: {}):".format(i, board.is_solution(sol)))
        print(board.format_solution(sol))
    if args.all and result.status != "limit reached":
        print("\nUnique solution." if len(result.solutions) == 1 else "\nThe puzzle has several solutions.")
    s = result.stats
    print("\nnodes={} backtracks={} rejected={} revisions={} checks={} prunings={} (preprocess {}) "
          "max_depth={} time={:.4f}s".format(s.nodes, s.backtracks, s.rejected, s.revisions, s.checks,
                                             s.prunings, s.preprocess_prunings, s.max_depth, s.time))


if __name__ == "__main__":
    main()
