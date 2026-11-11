"""PyGame application: pick a puzzle and solver settings, then watch the search step by step.

The solver runs once and records a trace (kakuro/gui/replay.py); playback just moves a cursor over
it, so the user can pause, step forward/backward, jump to the next decision or click the timeline.
"""

import math

import pygame

from ..core import list_puzzles, load_puzzle
from ..csp import INFERENCES, VALUE_ORDERINGS, VARIABLE_ORDERINGS, SolverConfig
from ..csp.events import (ASSIGN, DEADEND, PRUNE, REJECT, RESTORE, REVISE, SELECT, SOLUTION, UNASSIGN,
                          WIPEOUT)
from .renderer import (ASSIGNED, BG, BLACK_CELL, BLUE, CANDIDATE, MUTED, ORANGE, PRUNED, REJECTED, RESTORED,
                       RULE, SHEET, TEXT, BoardView, font)
from .replay import TraceReplay

# Fits a 1280x800 laptop screen (the evaluation machine is a MacBook).
WINDOW = (1240, 760)
BOARD_RECT = (20, 14, 680, 680)
PANEL_X = 728
PANEL_W = WINDOW[0] - PANEL_X - 20
SPEEDS = [1, 2, 5, 10, 25, 60, 150, 400, 1000, 5000]   # events per second
SEEDS = [None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
EVENT_COLORS = {ASSIGN: ASSIGNED, UNASSIGN: PRUNED, PRUNE: PRUNED, WIPEOUT: PRUNED, DEADEND: PRUNED,
                RESTORE: RESTORED, REVISE: BLUE, SELECT: ORANGE, REJECT: REJECTED, SOLUTION: RESTORED}
HOVER = (238, 242, 248)
ACTIVE = (214, 226, 250)


def plain(text):
    """Run names use arrows (28→@5,1); spell them out so every font can draw them."""
    return text.replace("→@", " across from ").replace("↓@", " down from ")


class Button:
    def __init__(self, rect, label, action, hint=""):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action        # callable(direction): +1 for left click, -1 for right click
        self.hint = hint

    def draw(self, surface, f, active=False):
        hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        color = ACTIVE if active else (HOVER if hovered else SHEET)
        pygame.draw.rect(surface, color, self.rect, border_radius=4)
        pygame.draw.rect(surface, BLUE if active else RULE, self.rect, 1, border_radius=4)
        label = self.label() if callable(self.label) else self.label
        img = f.render(label, True, TEXT)
        surface.blit(img, img.get_rect(center=self.rect.center))


class SettingRow(Button):
    """One solver option: name on the left, current choice on the right. Click = next, right-click = previous."""

    def __init__(self, rect, setting, action):
        super().__init__(rect, setting.title, action)
        self.setting = setting

    def draw(self, surface, f, active=False):
        if self.rect.collidepoint(pygame.mouse.get_pos()):
            pygame.draw.rect(surface, HOVER, self.rect)
        surface.blit(f.render(self.setting.title, True, MUTED), (self.rect.x + 10, self.rect.y + 4))
        img = f.render(self.setting.fmt(self.setting.value), True, TEXT)
        surface.blit(img, (self.rect.right - img.get_width() - 26, self.rect.y + 4))
        cx, cy = self.rect.right - 13, self.rect.centery
        pygame.draw.polygon(surface, MUTED, [(cx - 3, cy - 5), (cx + 3, cy), (cx - 3, cy + 5)])


class Setting:
    """A named option with a list of choices, cycled by clicking."""

    def __init__(self, title, choices, index=0, fmt=str):
        self.title = title
        self.choices = choices
        self.index = index
        self.fmt = fmt

    @property
    def value(self):
        return self.choices[self.index]

    def cycle(self, direction):
        self.index = (self.index + direction) % len(self.choices)

    def label(self):
        return "{}:  {}".format(self.title, self.fmt(self.value))


class App:
    def __init__(self, puzzle=None, config=None):
        pygame.init()
        pygame.display.set_caption("Kakuro — CSP: Backtracking + Constraint Propagation")
        self.screen = pygame.display.set_mode(WINDOW)
        self.clock = pygame.time.Clock()
        self.f_title = font(24, bold=True)
        self.f = font(15)
        self.f_small = font(13)
        self.f_mono = font(12, "mono")
        self.f_event = font(18, bold=True)
        self.f_num = font(22, "digit")
        config = config or SolverConfig()
        puzzles = list_puzzles()
        self.s_puzzle = Setting("Puzzle", puzzles, puzzles.index(puzzle) if puzzle in puzzles else
                                (puzzles.index("complex_9x9") if "complex_9x9" in puzzles else 0))
        self.s_inference = Setting("Inference", list(INFERENCES), list(INFERENCES).index(config.inference))
        self.s_var = Setting("Variable order", list(VARIABLE_ORDERINGS),
                             list(VARIABLE_ORDERINGS).index(config.variable_order))
        self.s_val = Setting("Value order", list(VALUE_ORDERINGS), list(VALUE_ORDERINGS).index(config.value_order))
        self.s_pre = Setting("Initial AC-3", [True, False], 0 if config.preprocess else 1,
                             lambda v: "On" if v else "Off")
        self.s_seed = Setting("Tie-break seed", SEEDS, 0, lambda v: "deterministic" if v is None else str(v))
        self.settings = [self.s_puzzle, self.s_inference, self.s_var, self.s_val, self.s_pre, self.s_seed]
        self.view = BoardView(BOARD_RECT)
        self.playing = False
        self.speed_index = 3
        self.accumulator = 0.0
        self._build_buttons()
        self.rebuild()

    # ------------------------------------------------------------------ setup
    def _build_buttons(self):
        self.buttons = []
        y = 58
        self.settings_box = pygame.Rect(PANEL_X, y, PANEL_W, len(self.settings) * 25)
        for s in self.settings:
            self.buttons.append(SettingRow((PANEL_X, y, PANEL_W, 25), s, self._setting_action(s)))
            y += 25
        y += 8
        w = (PANEL_W - 5 * 6) // 6
        row = [("Restart", lambda d: self.reset(), "R"), ("Back", lambda d: self.replay.back(), "Left"),
               (lambda: "Pause" if self.playing else "Play", lambda d: self.toggle_play(), "Space"),
               ("Step", lambda d: self.replay.step(), "Right"),
               ("Next choice", lambda d: self.replay.step_until({ASSIGN, UNASSIGN, SOLUTION}), "N"),
               ("To end", lambda d: self.replay.seek(len(self.replay)), "E")]
        for i, (label, action, hint) in enumerate(row):
            self.buttons.append(Button((PANEL_X + i * (w + 6), y, w, 30), label, action, hint))
        self.play_button = self.buttons[-4]
        y += 36
        self.buttons.append(Button((PANEL_X, y, 30, 24), "−", lambda d: self.change_speed(-1)))
        self.buttons.append(Button((PANEL_X + 34, y, 30, 24), "+", lambda d: self.change_speed(+1)))
        self.speed_y = y
        self.timeline = pygame.Rect(PANEL_X, y + 30, PANEL_W, 56)

    def _setting_action(self, setting):
        def action(direction):
            setting.cycle(direction)
            self.rebuild()
        return action

    def config(self):
        return SolverConfig(self.s_var.value, self.s_val.value, self.s_inference.value, self.s_pre.value,
                            seed=self.s_seed.value)

    def rebuild(self):
        """Run the solver for the current settings and restart playback."""
        self.playing = False
        self.screen.fill(BG)
        img = self.f_title.render("Solving and recording the search", True, TEXT)
        self.screen.blit(img, (40, 40))
        pygame.display.flip()
        self.board = load_puzzle(self.s_puzzle.value)
        self.view.set_board(self.board)
        self.replay = TraceReplay(self.board, self.config())
        self.depth_points = self._depth_profile()
        # index of the first search event: everything before it is the initial AC-3
        self.search_start = next((i for i, ev in enumerate(self.replay.events) if ev.kind == SELECT), 0)

    def reset(self):
        self.playing = False
        self.replay.seek(0)

    def toggle_play(self):
        if self.replay.done:
            self.replay.seek(0)
        self.playing = not self.playing

    def change_speed(self, d):
        self.speed_index = max(0, min(len(SPEEDS) - 1, self.speed_index + d))

    def _depth_profile(self):
        """Max depth per pixel column of the timeline (the search tree's 'saw-tooth')."""
        n, width = len(self.replay.depths), self.timeline.w
        if n == 0:
            return []
        cols = []
        for x in range(width):
            a, b = x * n // width, max(x * n // width + 1, (x + 1) * n // width)
            cols.append(max(self.replay.depths[a:b]))
        return cols

    # ------------------------------------------------------------------ loop
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    running = self.on_key(event.key)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button in (1, 3):
                    self.on_click(event.pos, 1 if event.button == 1 else -1)
                elif event.type == pygame.MOUSEMOTION and event.buttons[0] and self.timeline.collidepoint(event.pos):
                    self.seek_timeline(event.pos[0])
            if self.playing:
                self.accumulator += dt * SPEEDS[self.speed_index]
                steps = int(self.accumulator)
                self.accumulator -= steps
                self.replay.step(steps)
                if self.replay.done:
                    self.playing = False
            self.draw()
        pygame.quit()

    def on_key(self, key):
        r = self.replay
        if key in (pygame.K_ESCAPE, pygame.K_q):
            return False
        actions = {pygame.K_SPACE: self.toggle_play, pygame.K_RIGHT: r.step, pygame.K_LEFT: r.back,
                   pygame.K_n: lambda: r.step_until({ASSIGN, UNASSIGN, SOLUTION}),
                   pygame.K_b: lambda: r.step_until({UNASSIGN, DEADEND}),
                   pygame.K_e: lambda: r.seek(len(r)), pygame.K_r: self.reset,
                   pygame.K_UP: lambda: self.change_speed(1), pygame.K_DOWN: lambda: self.change_speed(-1)}
        if key in actions:
            actions[key]()
        return True

    def on_click(self, pos, direction):
        for b in self.buttons:
            if b.rect.collidepoint(pos):
                b.action(direction)
                return
        if self.timeline.collidepoint(pos):
            self.seek_timeline(pos[0])

    def seek_timeline(self, x):
        frac = (x - self.timeline.x) / float(self.timeline.w)
        self.replay.seek(int(round(frac * len(self.replay))))

    # ------------------------------------------------------------------ drawing
    def _text(self, f, text, pos, color=TEXT, right=False):
        img = f.render(text, True, color)
        self.screen.blit(img, (pos[0] - img.get_width(), pos[1]) if right else pos)
        return img.get_width()

    def _hovered_cell(self):
        pos = self.view.cell_at(pygame.mouse.get_pos())
        return pos if pos in self.replay.state.domains else None

    def draw(self):
        self.screen.fill(BG)
        state = self.replay.state
        hover = self._hovered_cell()
        hover_cells = set()
        if hover:
            for c in self.replay.csp.constraints_of[hover]:
                hover_cells.update(c.variables)
        self.view.draw(self.screen, state, hover, hover_cells)
        self._draw_legend(BOARD_RECT[0], BOARD_RECT[1] + BOARD_RECT[3] + 7)
        self._text(self.f_small, "Space play or pause    Left / Right step    N next choice    B next backtrack    "
                   "Up / Down speed    R restart    E end", (BOARD_RECT[0], WINDOW[1] - 21), MUTED)

        self._text(self.f_title, "Kakuro as a CSP", (PANEL_X, 12))
        summary = self.replay.csp.summary()
        self._text(self.f_small, "{} variables, {} constraints".format(summary["variables"], summary["constraints"]),
                   (PANEL_X + PANEL_W, 22), MUTED, right=True)
        pygame.draw.rect(self.screen, SHEET, self.settings_box)
        for b in self.buttons:
            b.draw(self.screen, self.f, active=(b is self.play_button and self.playing))
        for i in range(1, len(self.settings)):
            y = self.settings_box.y + i * 25
            pygame.draw.line(self.screen, RULE, (PANEL_X, y), (PANEL_X + PANEL_W, y))
        pygame.draw.rect(self.screen, RULE, self.settings_box, 1)
        self._text(self.f_small, "{} events per second".format(SPEEDS[self.speed_index]),
                   (PANEL_X + 74, self.speed_y + 4), MUTED)
        r = self.replay
        self._text(self.f_small, "Step {:,} of {:,}".format(r.index, len(r)),
                   (PANEL_X + PANEL_W, self.speed_y + 4), MUTED, right=True)
        self._draw_timeline()
        y = self._draw_search_space(self.timeline.bottom + 10)
        y = self._draw_stats(y + 8)
        y = self._draw_inspector(y, hover)
        self._draw_event_log(y + 2, WINDOW[1] - 14)
        pygame.display.flip()

    def _draw_timeline(self):
        t = self.timeline
        pygame.draw.rect(self.screen, SHEET, t)
        n = len(self.replay)
        if self.search_start and n:      # shade the part spent in the initial AC-3
            w = int(t.w * self.search_start / n)
            pygame.draw.rect(self.screen, (232, 240, 253), (t.x, t.y, w, t.h))
        if self.depth_points:
            top = max(self.depth_points) or 1
            base = t.bottom - 2
            pts = [(t.x + x, base - int((t.h - 20) * d / top)) for x, d in enumerate(self.depth_points)]
            if len(pts) > 1:
                pygame.draw.polygon(self.screen, (214, 222, 236), [(t.x, base)] + pts + [(t.right - 1, base)])
                pygame.draw.lines(self.screen, BLACK_CELL, False, pts, 1)
        cx = t.x + (int(t.w * self.replay.index / n) if n else 0)
        pygame.draw.line(self.screen, PRUNED, (cx, t.y), (cx, t.bottom), 2)
        pygame.draw.rect(self.screen, RULE, t, 1)
        label = "Depth of the search tree over time. Click or drag to jump."
        if self.search_start:
            label = "Shaded: initial AC-3. Then the depth of the search tree."
        self._text(self.f_small, label, (t.x + 6, t.y + 2), MUTED)

    def _draw_search_space(self, y):
        """The product of the domain sizes: what constraint propagation shrinks."""
        now = sum(math.log10(len(d)) for d in self.replay.state.domains.values() if d)
        full = len(self.replay.state.domains) * math.log10(9)
        self._text(self.f_small, "Search space left, product of domain sizes", (PANEL_X, y), MUTED)
        self._text(self.f_num, "10^{:.1f}".format(now), (PANEL_X + PANEL_W, y - 5), TEXT, right=True)
        bar = pygame.Rect(PANEL_X, y + 22, PANEL_W, 8)
        pygame.draw.rect(self.screen, SHEET, bar)
        fill = bar.copy()
        fill.w = int(bar.w * now / full) if full else 0
        pygame.draw.rect(self.screen, BLUE, fill)
        pygame.draw.rect(self.screen, RULE, bar, 1)
        return bar.bottom

    def _draw_stats(self, y):
        r, s, c = self.replay, self.replay.state, self.replay.state.counters
        ev = r.current_event
        res = r.result
        text = plain(ev.describe()) if ev else "Press Space to play, or Right to take one step"
        color = EVENT_COLORS.get(ev.kind, TEXT) if ev else MUTED
        self._text(self.f_event, text, (PANEL_X, y), color)
        y += 30
        cells = [("Nodes", c["nodes"]), ("Backtracks", c["backtracks"]),
                 ("Depth", "{} / {}".format(len(s.path), len(s.domains))),
                 ("Revisions", c["revisions"]), ("Values pruned", c["prunings"]), ("Values rejected", c["rejected"])]
        col = PANEL_W // 3
        for i, (name, value) in enumerate(cells):
            x, yy = PANEL_X + (i % 3) * col, y + (i // 3) * 42
            self._text(self.f_num, "{:,}".format(value) if isinstance(value, int) else value, (x, yy))
            self._text(self.f_small, name, (x, yy + 22), MUTED)
        y += 88
        status = "Solved" if s.solved else ("Finished: " + res.status if r.done else "Searching")
        if r.truncated:
            status += " (trace stopped at {:,} events)".format(len(r))
        self._text(self.f_small, "{}. Whole run: {:,} nodes, {:,} backtracks, {:,} constraint checks".format(
            status, res.stats.nodes, res.stats.backtracks, res.stats.checks), (PANEL_X, y), MUTED)
        y += 18
        path = "  ".join("({},{})={}".format(v[0], v[1], val) for v, val in s.path[-6:])
        if len(s.path) > 6:
            path = "...  " + path
        self._text(self.f_small, "Branch: " + (path or "empty assignment"), (PANEL_X, y), TEXT)
        return y + 20

    def _draw_inspector(self, y, hover):
        """Domain and constraints of the cell under the mouse."""
        if not hover:
            self._text(self.f_small, "Point at a white cell to read its domain and its two constraints.",
                       (PANEL_X, y), MUTED)
            return y + 22
        s = self.replay.state
        domain = "{" + ", ".join(str(v) for v in sorted(s.domains[hover])) + "}"
        if hover in s.assignment:
            head = "x({},{}) = {}".format(hover[0], hover[1], s.assignment[hover])
        else:
            head = "x({},{})   D = {}".format(hover[0], hover[1], domain)
        parts = ["{} cells sum to {}".format(len(c.variables), c.total) for c in self.replay.csp.constraints_of[hover]]
        w = self._text(self.f_small, head, (PANEL_X, y), TEXT)
        self._text(self.f_small, "all different; " + ", ".join(parts), (PANEL_X + w + 14, y), MUTED)
        return y + 22

    def _draw_event_log(self, y, bottom):
        r = self.replay
        rows = max(3, (bottom - y - 8) // 16)
        box = pygame.Rect(PANEL_X, y, PANEL_W, rows * 16 + 8)
        pygame.draw.rect(self.screen, SHEET, box)
        pygame.draw.rect(self.screen, RULE, box, 1)
        start = max(0, r.index - rows)
        for i in range(start, r.index):
            e = r.events[i]
            text = "{:>7}  depth {:<3} {}".format(i + 1, e.depth, plain(e.describe()))
            img = self.f_mono.render(text[:66], True, EVENT_COLORS.get(e.kind, TEXT))
            self.screen.blit(img, (box.x + 6, box.y + 4 + (i - start) * 16))
        return box.bottom

    def _draw_legend(self, x0, y):
        items = [(CANDIDATE, "value in the domain"), (PRUNED, "pruned by propagation"),
                 (RESTORED, "restored on backtrack"), (REJECTED, "rejected as inconsistent"),
                 (ORANGE, "variable selected"), (BLUE, "arc being revised"),
                 (PRUNED, "domain wiped out"), (ASSIGNED, "assigned value")]
        for i, (color, text) in enumerate(items):
            x = x0 + (i % 4) * (BOARD_RECT[2] // 4)
            yy = y + (i // 4) * 18
            pygame.draw.rect(self.screen, color, (x, yy + 4, 10, 10))
            self._text(self.f_small, text, (x + 16, yy), TEXT)
