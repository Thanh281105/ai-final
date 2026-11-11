"""Create extra random (always solvable) boards in puzzles/, e.g. for the stability experiments.

    python generate.py --rows 10 --cols 10 --seed 1
"""

import argparse
import os

from kakuro.core import PUZZLE_DIR
from kakuro.core.generator import generate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--rows", type=int, default=10, help="including the clue row")
    p.add_argument("--cols", type=int, default=10, help="including the clue column")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--black-ratio", type=float, default=0.18)
    args = p.parse_args()
    text, _ = generate(args.rows, args.cols, args.seed, args.black_ratio)
    path = os.path.join(PUZZLE_DIR, "random_{}x{}_s{}.txt".format(args.rows, args.cols, args.seed))
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print("Saved", path)
    print(text)


if __name__ == "__main__":
    main()
