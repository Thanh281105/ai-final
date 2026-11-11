"""Find and load the puzzle files stored in `task3/puzzles/`."""

import glob
import os

from .board import KakuroBoard

PUZZLE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "puzzles")


def list_puzzles():
    """Puzzle names (file names without .txt), the two assignment boards first."""
    names = [os.path.splitext(os.path.basename(p))[0] for p in glob.glob(os.path.join(PUZZLE_DIR, "*.txt"))]
    first = ["example_5x5", "complex_9x9"]
    return [n for n in first if n in names] + sorted(n for n in names if n not in first)


def load_puzzle(name_or_path):
    """Accept either a name from `list_puzzles()` or a path to any puzzle file."""
    path = name_or_path
    if not os.path.exists(path):
        path = os.path.join(PUZZLE_DIR, name_or_path if name_or_path.endswith(".txt") else name_or_path + ".txt")
    return KakuroBoard.from_file(path)
