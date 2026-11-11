"""Kakuro GUI (Requirement 3): visualizes domains, constraint propagation and backtracking search.

    python main.py                                   # complex 9x9, full solver
    python main.py --puzzle example_5x5 --inference FC --var-order Static --value-order Ascending --no-preprocess
"""

import argparse

from kakuro.csp import INFERENCES, VALUE_ORDERINGS, VARIABLE_ORDERINGS, SolverConfig


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--puzzle", default="complex_9x9")
    p.add_argument("--inference", default="MAC", choices=list(INFERENCES))
    p.add_argument("--var-order", default="MRV+Degree", choices=list(VARIABLE_ORDERINGS))
    p.add_argument("--value-order", default="LCV", choices=list(VALUE_ORDERINGS))
    p.add_argument("--no-preprocess", action="store_true")
    args = p.parse_args()
    from kakuro.gui import App   # imported here so `--help` works without pygame
    config = SolverConfig(args.var_order, args.value_order, args.inference, not args.no_preprocess)
    App(args.puzzle, config).run()


if __name__ == "__main__":
    main()
