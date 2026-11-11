"""Kakuro board: the grid as the player sees it (black cells, clue cells, white cells).

The board knows nothing about search. It only parses the puzzle file, finds the *runs*
(maximal horizontal/vertical blocks of white cells, each owned by one clue) and checks
whether a filled grid obeys the rules.
"""

import os

ACROSS = "across"
DOWN = "down"


class Cell:
    """One square of the grid. Subclasses tell the three kinds apart."""

    is_white = False

    def __init__(self, row, col):
        self.row = row
        self.col = col

    @property
    def pos(self):
        return (self.row, self.col)


class BlackCell(Cell):
    """Black square without any clue."""


class ClueCell(Cell):
    """Black square holding a down clue (lower-left) and/or an across clue (upper-right)."""

    def __init__(self, row, col, down=None, across=None):
        super().__init__(row, col)
        self.down = down
        self.across = across


class WhiteCell(Cell):
    """Square the player must fill with a digit 1..9."""

    is_white = True


class Run:
    """A block of white cells whose digits must be distinct and add up to `total`."""

    def __init__(self, run_id, direction, total, clue_pos, cells):
        self.id = run_id
        self.direction = direction
        self.total = total
        self.clue_pos = clue_pos
        self.cells = tuple(cells)

    @property
    def name(self):
        arrow = "→" if self.direction == ACROSS else "↓"
        return "{}{}@{},{}".format(self.total, arrow, self.clue_pos[0], self.clue_pos[1])

    def __len__(self):
        return len(self.cells)

    def __repr__(self):
        return "Run({}, cells={})".format(self.name, list(self.cells))


class PuzzleFormatError(ValueError):
    pass


class KakuroBoard:
    """Parsed puzzle: `grid[r][c]` holds a Cell, `runs` lists every clue's block of cells."""

    def __init__(self, grid, name="puzzle"):
        self.grid = grid
        self.name = name
        self.rows = len(grid)
        self.cols = len(grid[0]) if grid else 0
        self.runs = self._find_runs()
        self.white_cells = [cell.pos for line in grid for cell in line if cell.is_white]
        # cell -> the runs containing it (normally one across and one down)
        self.runs_of = {pos: [] for pos in self.white_cells}
        for run in self.runs:
            for pos in run.cells:
                self.runs_of[pos].append(run)
        self._validate()

    # ------------------------------------------------------------------ parsing
    @classmethod
    def from_text(cls, text, name="puzzle"):
        grid = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            r = len(grid)
            grid.append([cls._parse_token(tok, r, c) for c, tok in enumerate(line.split())])
        if not grid:
            raise PuzzleFormatError("empty puzzle")
        width = len(grid[0])
        if any(len(line) != width for line in grid):
            raise PuzzleFormatError("all rows must have the same number of cells")
        return cls(grid, name)

    @classmethod
    def from_file(cls, path):
        with open(path, encoding="utf-8") as f:
            return cls.from_text(f.read(), os.path.splitext(os.path.basename(path))[0])

    @staticmethod
    def _parse_token(token, r, c):
        if token == ".":
            return WhiteCell(r, c)
        if token == "#":
            return BlackCell(r, c)
        if "\\" in token:
            down, across = token.split("\\", 1)
            try:
                return ClueCell(r, c, int(down) if down else None, int(across) if across else None)
            except ValueError:
                pass
        raise PuzzleFormatError("bad token {!r} at row {}, col {}".format(token, r, c))

    # ------------------------------------------------------------------ structure
    def cell(self, r, c):
        return self.grid[r][c]

    def _white(self, r, c):
        return 0 <= r < self.rows and 0 <= c < self.cols and self.grid[r][c].is_white

    def _find_runs(self):
        runs = []
        for line in self.grid:
            for cell in line:
                if not isinstance(cell, ClueCell):
                    continue
                for direction, total, (dr, dc) in ((ACROSS, cell.across, (0, 1)), (DOWN, cell.down, (1, 0))):
                    if total is None:
                        continue
                    cells = []
                    r, c = cell.row + dr, cell.col + dc
                    while self._white(r, c):
                        cells.append((r, c))
                        r, c = r + dr, c + dc
                    runs.append(Run(len(runs), direction, total, cell.pos, cells))
        return runs

    def _validate(self):
        for run in self.runs:
            if not run.cells:
                raise PuzzleFormatError("clue {} has no white cells after it".format(run.name))
            if len(run) > 9:
                raise PuzzleFormatError("run {} is longer than 9 cells".format(run.name))
        for pos, runs in self.runs_of.items():
            if not runs:
                raise PuzzleFormatError("white cell {} belongs to no clue".format(pos))

    # ------------------------------------------------------------------ checking
    def violations(self, values):
        """Return the runs broken by `values` (dict pos -> digit). Empty list means solved."""
        bad = []
        for run in self.runs:
            digits = [values.get(pos) for pos in run.cells]
            if (None in digits or any(not 1 <= d <= 9 for d in digits)
                    or len(set(digits)) != len(digits) or sum(digits) != run.total):
                bad.append(run)
        return bad

    def is_solution(self, values):
        return set(values) == set(self.white_cells) and not self.violations(values)

    def format_solution(self, values):
        """Grid as text: digits for white cells, '#' for black/clue cells."""
        lines = []
        for line in self.grid:
            lines.append(" ".join(str(values.get(cell.pos, ".")) if cell.is_white else "#" for cell in line))
        return "\n".join(lines)
