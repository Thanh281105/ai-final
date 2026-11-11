"""Draws the board: clues, assigned digits, and every variable's current domain as small candidates.

Look: a sheet of squared paper. Clue cells are printed in navy ink, the solver's work is "pencilled"
on top: grey candidates, red strikes for pruned values, green for values put back on backtracking.
"""

import pygame

from ..core import ClueCell

# Paper and ink
BG = (233, 238, 243)
SHEET = (252, 253, 254)
TEXT = (27, 36, 58)
MUTED = (104, 114, 134)
RULE = (196, 204, 216)
GRID = (150, 160, 178)
BLACK_CELL = (38, 48, 74)
CLUE_CELL = (58, 70, 102)
CLUE_ACTIVE = (58, 110, 214)
CLUE_TEXT = (236, 240, 248)
WHITE = SHEET

# Solver marks
SELECTED = (255, 233, 138)
REVISE_RUN = (221, 232, 252)
HOVER_RUN = (240, 236, 252)
FAILED = (252, 214, 210)
SOLVED = (221, 243, 228)
ASSIGNED = (27, 36, 58)
CANDIDATE = (118, 128, 148)
PRUNED = (208, 56, 56)
RESTORED = (28, 140, 88)
REJECTED = (218, 128, 20)
ORANGE = (230, 156, 16)
BLUE = (58, 110, 214)


def font(size, role="text", bold=False):
    """role: "text" (interface), "digit" (numbers on the board and counters), "mono" (event log)."""
    names = {"text": "avenir,helveticaneue,arial,dejavusans",
             "digit": "dinalternate,avenirnextcondensed,arialnarrow,arial,dejavusans",
             "mono": "menlo,monaco,couriernew,dejavusansmono"}[role]
    return pygame.font.SysFont(names, size, bold=bold)


class BoardView:
    def __init__(self, rect):
        self.rect = pygame.Rect(rect)
        self.board = None

    def set_board(self, board):
        self.board = board
        self.size = min(self.rect.w // board.cols, self.rect.h // board.rows, 136)
        self.origin = (self.rect.x + (self.rect.w - self.size * board.cols) // 2,
                       self.rect.y + (self.rect.h - self.size * board.rows) // 2)
        s = self.size
        self.f_value = font(int(s * 0.60), "digit")
        self.f_cand = font(max(9, int(s * 0.23)), "digit")
        self.f_clue = font(max(10, int(s * 0.27)), "digit")

    def cell_rect(self, r, c):
        return pygame.Rect(self.origin[0] + c * self.size, self.origin[1] + r * self.size, self.size, self.size)

    def cell_at(self, pos):
        x, y = pos[0] - self.origin[0], pos[1] - self.origin[1]
        if x < 0 or y < 0:
            return None
        r, c = y // self.size, x // self.size
        return (r, c) if r < self.board.rows and c < self.board.cols else None

    def draw(self, surface, state, hover=None, hover_cells=()):
        """hover: the white cell under the mouse; hover_cells: the cells of its two runs."""
        revise_cells, revise_clue = set(), None
        if state.revising:
            revise_cells = set(state.revising[1].variables)
            revise_clue = state.revising[1].run.clue_pos
        for line in self.board.grid:
            for cell in line:
                rect = self.cell_rect(cell.row, cell.col)
                if cell.is_white:
                    self._draw_white(surface, rect, cell.pos, state, cell.pos in revise_cells,
                                     cell.pos in hover_cells)
                    pygame.draw.rect(surface, GRID, rect, 1)
                else:
                    is_clue = isinstance(cell, ClueCell)
                    color = CLUE_ACTIVE if cell.pos == revise_clue else (CLUE_CELL if is_clue else BLACK_CELL)
                    pygame.draw.rect(surface, color, rect)
                    if is_clue:
                        self._draw_clue(surface, rect, cell)
                    pygame.draw.rect(surface, BLACK_CELL, rect, 1)
        board = pygame.Rect(self.origin, (self.size * self.board.cols, self.size * self.board.rows))
        pygame.draw.rect(surface, BLACK_CELL, board, 2)
        # outlines on top so neighbours do not cover them
        if hover:
            pygame.draw.rect(surface, MUTED, self.cell_rect(*hover).inflate(-2, -2), 2)
        if state.revising:
            pygame.draw.rect(surface, BLUE, self.cell_rect(*state.revising[0]).inflate(-2, -2), 3)
        if state.selected and state.selected not in state.assignment:
            pygame.draw.rect(surface, ORANGE, self.cell_rect(*state.selected).inflate(-2, -2), 4)
        if state.failed_var:
            pygame.draw.rect(surface, PRUNED, self.cell_rect(*state.failed_var).inflate(-2, -2), 4)

    def _draw_clue(self, surface, rect, cell):
        pygame.draw.line(surface, GRID, rect.topleft, rect.bottomright, 1)
        pad = max(3, self.size // 11)
        if cell.down is not None:
            img = self.f_clue.render(str(cell.down), True, CLUE_TEXT)
            surface.blit(img, (rect.x + pad, rect.bottom - img.get_height() - pad // 2))
        if cell.across is not None:
            img = self.f_clue.render(str(cell.across), True, CLUE_TEXT)
            surface.blit(img, (rect.right - img.get_width() - pad, rect.y + pad // 2))

    def _draw_white(self, surface, rect, pos, state, in_revised_run, in_hover_run):
        if state.solved:
            bg = SOLVED
        elif pos == state.failed_var:
            bg = FAILED
        elif pos == state.selected and pos not in state.assignment:
            bg = SELECTED
        elif in_revised_run:
            bg = REVISE_RUN
        elif in_hover_run:
            bg = HOVER_RUN
        else:
            bg = SHEET
        pygame.draw.rect(surface, bg, rect)
        if pos in state.assignment:
            img = self.f_value.render(str(state.assignment[pos]), True, ASSIGNED)
            surface.blit(img, img.get_rect(center=rect.center))
            return
        domain = state.domains[pos]
        third = (self.size - 6) / 3.0
        for d in range(1, 10):
            cx = rect.x + 3 + third * ((d - 1) % 3) + third / 2
            cy = rect.y + 3 + third * ((d - 1) // 3) + third / 2
            if d in domain:
                color = RESTORED if (pos, d) in state.recent_restored else CANDIDATE
                if (pos, d) in state.rejected:
                    color = REJECTED
            elif (pos, d) in state.recent_pruned:
                color = PRUNED
            else:
                continue
            img = self.f_cand.render(str(d), True, color)
            r = img.get_rect(center=(int(cx), int(cy)))
            surface.blit(img, r)
            if color in (PRUNED, REJECTED):
                pygame.draw.line(surface, color, (r.left - 2, r.bottom - 3), (r.right + 2, r.top + 3), 2)
