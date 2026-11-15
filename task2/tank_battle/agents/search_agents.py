"""Minimax family of adversarial search agents (Lecture 07).

One game cycle = two plies: our tank (MAX) chooses an action, then the opponent (MIN) chooses its
action knowing ours, and only then the cycle is resolved with `GameState.next_state`. Treating the
opponent as if it could react to our move is the pessimistic (safe) way to turn a simultaneous game
into an alternating zero-sum game tree.

    MAX node  : state at the start of a cycle, we pick a_me
    MIN node  : (state, a_me), the opponent picks a_opp -> child = RESULT(state, a_me, a_opp)

The four required configurations are the same engine with two switches:

    configuration                    use_alpha_beta    evaluator
    Minimax Search                   False             None  (utility only)
    Alpha-Beta Search                True              None
    Heuristic Minimax Search         False             HeuristicEvaluator (cutoff + EVAL)
    Heuristic Alpha-Beta Search      True              HeuristicEvaluator

`depth` is the cutoff depth d of CUTOFF-TEST(s, d), measured in game cycles (d cycles = 2d plies).

depth=None is the search of the lecture for Minimax / Alpha-Beta: no cutoff, the tree is explored
down to the TERMINAL states and leaves are scored with UTILITY. The tree is finite because of the
turn limit, but m = 2 * (remaining cycles) plies, so this is only feasible near the end of a game.

Minimax / Alpha-Beta with a depth are a compromise needed to let them play a whole game in real
time: they have no EVAL, so a non-terminal state at the cutoff is scored 0 (as a draw). That is
H-Minimax with EVAL(s) = 0, and is reported as "cutoff, EVAL = 0" in the experiments.

Optimizations of Heuristic Alpha-Beta (none of them changes the minimax value, only the order in
which the tree is explored, so more of it is pruned):
    * move ordering: TT move -> killer moves -> history heuristic -> tactical ordering of EVAL
    * transposition table keyed by the complete state: tanks, bases, bullets, the Zobrist hash of the
      walls and the turn (so an entry is only reused for the same node reached by another move order)
    * iterative deepening under a time budget; a new depth is not started when it cannot finish
Root tie-break: when several root moves have exactly the best minimax value, the agent picks the
one that improves its own side of EVAL most if the opponent stays put. Without it, on a symmetric map
every move is worth 0 (the opponent can mirror any move) and the agent turns on the spot forever.
The move played always has the best minimax value, so the tie-break never costs minimax value.
Optional randomized variant (off by default, tie_random > 0): with probability tie_random the agent
plays a random root move whose minimax value is within tie_margin of the best one. It makes games
between two copies of the same agent differ from each other, but it gives up minimax value and loses
more games (experiment D), so no experiment about the four configurations uses it. The root window is
lowered by tie_margin so these moves get exact values; the reported value is still the best one.
"""

import gc
import math
import random
import time

from ..core.constants import Action
from .base_agent import BaseAgent, SearchStats
from .heuristics import HeuristicEvaluator

WIN_SCORE = 1_000_000.0
TIE_EPS = 1e-6               # root moves within this of the best value are ties
TT_MAX_ENTRIES = 200_000     # the table is cleared every move; this only guards very long searches
ID_START_FRACTION = 0.4      # do not start depth d+1 after this fraction of the time budget
TIME_MARGIN = 0.003          # seconds kept free at the end of the time budget
# Randomized variant only (tie_random > 0; the default agents are deterministic):
RANDOM_TIE_PROBABILITY = 0.2 # probability of playing a random near-best root move
NEAR_TIE_MARGIN = 15.0       # root moves this close to the best minimax value count as "near-best"
PROGRESS_MARGIN = 10.0       # random choices stay within this much progress of the best candidate

TT_EXACT = 0
TT_LOWER = 1
TT_UPPER = 2


class SearchTimeout(Exception):
    pass


class AdversarialSearchAgent(BaseAgent):
    name = "Adversarial Search"

    def __init__(self, player, depth=2, use_alpha_beta=False, evaluator=None, move_ordering=None,
                 time_limit=None, iterative_deepening=False, seed=0, use_tt=False, use_killers=None,
                 use_history=None, tie_break=None, tie_random=0.0, tie_margin=TIE_EPS, **kwargs):
        super().__init__(player)
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.evaluator = evaluator
        # Move ordering only helps when pruning and needs domain knowledge, so by default it is enabled
        # for heuristic alpha-beta only (plain alpha-beta stays knowledge-free for a fair comparison).
        if move_ordering is None:
            move_ordering = use_alpha_beta and evaluator is not None
        self.move_ordering = move_ordering
        self.use_killers = move_ordering and use_alpha_beta if use_killers is None else use_killers
        self.use_history = move_ordering and use_alpha_beta if use_history is None else use_history
        self.tie_break = evaluator is not None if tie_break is None else tie_break
        # Default: deterministic. Among the root moves of best minimax value the one with most progress
        # is played. tie_random > 0 switches on the randomized variant described in the module docstring.
        self.tie_random = tie_random
        self.tie_margin = tie_margin
        self._orderer = evaluator if evaluator is not None else HeuristicEvaluator()
        self.time_limit = time_limit
        self.iterative_deepening = iterative_deepening
        self.seed = seed
        self.rng = random.Random(seed)
        self.use_tt = use_tt
        self._tt = {}
        self._eval_cache = {}        # EVAL of cutoff states (only with the transposition table)
        self._killers = {}           # ply -> [most recent, older] moves that caused a cutoff
        self._history = {}           # (player, row, col, action) -> sum of depth^2 over cutoffs
        self._deadline = None
        self._root_turn = 0
        self._partial = None
        self._live = 0
        self._ticks = 0
        self._stats = SearchStats()

    def reset(self):
        super().reset()
        self.rng = random.Random(self.seed)
        self._tt.clear()

    def _state_key(self, state):
        """Transposition-table key: the complete game state s = (tanks, bases, bullets, walls, turn).

        The turn is part of the key on purpose. In a search to depth d from the root, a state at turn t
        has d - (t - root turn) cycles left, so two nodes with the same key are the same state with the
        same remaining depth (a transposition: the same node reached by a different move order). The
        stored value is then exactly the value H-Minimax computes at that node, and a win keeps its
        distance in cycles. Without the turn, a state met again later (both tanks waiting, for example)
        would reuse a value searched deeper than its own cutoff allows, which changes the minimax value."""
        t0, t1 = state.tanks
        return (t0.row, t0.col, t0.direction, t0.hp, t1.row, t1.col, t1.direction, t1.hp,
                state.bases[0].hp, state.bases[1].hp,
                tuple([(b.owner, b.row, b.col, b.direction) for b in state.bullets]),
                state.wall_hash, state.turn)

    # ------------------------------------------------------------------ entry point
    def choose_action(self, state):
        # The search creates no reference cycles, so the cyclic garbage collector is paused while it
        # runs: a full collection over the caches can take 10+ ms and would break the time budget.
        gc_was_enabled = gc.isenabled()
        gc.disable()
        try:
            return self._choose_action(state)
        finally:
            if gc_was_enabled:
                gc.enable()

    def _choose_action(self, state):
        stats = self._stats = SearchStats()
        start = time.perf_counter()
        # The deadline keeps a small margin for unwinding the recursion and returning the move.
        self._deadline = start + max(0.5 * self.time_limit, self.time_limit - TIME_MARGIN) if self.time_limit else None
        self._ticks = 0
        self._root_turn = state.turn
        self._tt.clear()
        self._eval_cache.clear()
        self._killers.clear()
        self._history.clear()

        root_actions = state.legal_actions(self.player)
        self.rng.shuffle(root_actions)   # random tie-breaking among equally good moves
        best_action, best_value = root_actions[0], None

        if self.iterative_deepening:
            depths = range(1, (self.depth or 10 ** 6) + 1)
        else:
            depths = [self.depth]

        pv_action = best_values = None
        for d in depths:
            if (best_value is not None and self._deadline is not None
                    and time.perf_counter() - start > ID_START_FRACTION * self.time_limit):
                break    # depth d would cost ~b* times the previous one: it cannot finish in time
            try:
                action, value, values = self._search_root(state, d, root_actions, pv_action)
            except SearchTimeout:
                stats.timed_out = True
                # The previous best move is searched first, so any move recorded after it in the
                # unfinished iteration is better at the deeper level and can be used.
                if self._partial is not None and (best_value is None or self._partial[2]):
                    best_action, best_value = self._partial[0], self._partial[1]
                    best_values = None    # values of an unfinished iteration are not comparable
                break
            best_action, best_value, pv_action, best_values = action, value, action, values
            stats.depth = d if d is not None else stats.max_ply // 2
            if abs(value) >= WIN_SCORE / 2 or d is None:
                break    # a forced win/loss was proven, deeper search cannot change it

        if self.tie_break and best_values:
            # Done once, on the deepest completed iteration (the PV above stays the true best move).
            near = [a for a in best_values if best_values[a] > best_value - self.tie_margin]
            ties = [a for a in near if best_values[a] > best_value - TIE_EPS]
            if len(near) > 1:
                best_action = self._break_tie(state, ties, near)

        stats.time = time.perf_counter() - start
        stats.value = best_value
        stats.tt_entries = len(self._tt) + len(self._eval_cache)
        self.last_stats = stats
        return best_action

    # ------------------------------------------------------------------ minimax / alpha-beta
    def _search_root(self, state, depth, root_actions, pv_action):
        actions = self._order(state, self.player, list(root_actions))
        if pv_action in actions:      # best move of the previous iteration first
            actions.remove(pv_action)
            actions.insert(0, pv_action)
        self._partial = None
        stats = self._stats
        stats.nodes += 1
        self._live = 1 + len(actions)
        stats.peak_memory = max(stats.peak_memory, self._live)
        # With tie-breaking, the window is lowered by tie_margin so that a move as good (or nearly as good)
        # as the best one gets its exact value instead of an upper bound (pruning still applies to worse moves).
        margin = self.tie_margin if (self.tie_break and self.use_alpha_beta) else 0.0
        alpha, beta = -math.inf, math.inf
        best_action, best_value = actions[0], -math.inf
        values = {}
        for i, action in enumerate(actions):
            value = self._min_value(state, action, depth, alpha - margin, beta, 1)
            self._live -= 1
            values[action] = value
            if value > best_value:
                best_action, best_value = action, value
                self._partial = (best_action, best_value, i > 0)
            if self.use_alpha_beta:
                alpha = max(alpha, value)
        return best_action, best_value, values

    def _break_tie(self, state, ties, near=None):
        """Among moves with the same minimax value, prefer the one that improves our own side of EVAL
        most after one cycle in which the opponent does nothing. The zero-sum EVAL cannot be used here:
        stepping out of cover helps our attack but also opens lines for the opponent, so the
        difference always favours hiding, and the agent would turn on the spot forever."""
        def score(action):
            if self.player == 0:
                child = state.next_state(action, Action.STAY)
            else:
                child = state.next_state(Action.STAY, action)
            if child.is_terminal():
                return self._utility(child)
            return self.evaluator.progress(child, self.player)
        near = near or ties
        scores = {a: score(a) for a in near}
        if self.tie_random and self.rng.random() < self.tie_random:
            # Randomized variant: a random move among the near-best ones (within tie_margin of the
            # minimax value), restricted to moves making about as much progress, so a pure rotation
            # that achieves nothing is never picked at random.
            top = max(scores.values())
            return self.rng.choice([a for a in near if scores[a] >= top - PROGRESS_MARGIN])
        return max(ties, key=scores.get)

    def _max_value(self, state, depth, alpha, beta, ply):
        stats = self._stats
        stats.nodes += 1
        if ply > stats.max_ply:
            stats.max_ply = ply
        self._check_time()
        if state.is_terminal():
            return self._utility(state)
        if depth is not None and depth <= 0:          # CUTOFF-TEST
            stats.evaluations += 1
            if self.evaluator is None:
                return 0.0
            if not self.use_tt:
                return self.evaluator.evaluate(state, self.player)
            # The same cutoff state is reached through different move orders (transpositions):
            # EVAL is computed once per state and move.
            key = self._state_key(state)
            v = self._eval_cache.get(key)
            if v is None:
                v = self._eval_cache[key] = self.evaluator.evaluate(state, self.player)
            else:
                stats.tt_hits += 1
            return v

        key = None
        tt_move = None
        if self.use_tt:
            key = self._state_key(state)
            tt_entry = self._tt.get(key)
            if tt_entry is not None:
                tt_depth, tt_flag, tt_val, tt_move = tt_entry
                if tt_depth >= (depth if depth is not None else 999):
                    stats.tt_hits += 1
                    if tt_flag == TT_EXACT:
                        return tt_val
                    elif tt_flag == TT_LOWER and tt_val >= beta:
                        stats.cutoffs += 1
                        return tt_val
                    elif tt_flag == TT_UPPER and tt_val <= alpha:
                        return tt_val

        actions = self._order_node(state, self.player, state.legal_actions(self.player), ply, tt_move)
        n = len(actions)
        self._live += n
        if self._live > stats.peak_memory:
            stats.peak_memory = self._live

        orig_alpha = alpha
        value = -math.inf
        best_act = actions[0]
        done = 0
        for action in actions:
            v = self._min_value(state, action, depth, alpha, beta, ply + 1)
            done += 1
            self._live -= 1
            if v > value:
                value = v
                best_act = action
            if self.use_alpha_beta:
                if value >= beta:
                    stats.cutoffs += 1
                    self._live -= n - done
                    self._record_cutoff(state, self.player, action, ply, depth)
                    if key is not None:
                        self._store(key, depth, TT_LOWER, value, best_act)
                    return value
                alpha = max(alpha, value)

        if key is not None:
            flag = TT_EXACT if orig_alpha < value < beta else (TT_UPPER if value <= orig_alpha else TT_LOWER)
            self._store(key, depth, flag, value, best_act)
        return value

    def _min_value(self, state, my_action, depth, alpha, beta, ply):
        stats = self._stats
        stats.nodes += 1
        if ply > stats.max_ply:
            stats.max_ply = ply
        next_depth = None if depth is None else depth - 1

        actions = self._order_node(state, self.opponent, state.legal_actions(self.opponent), ply)
        n = len(actions)
        self._live += n
        if self._live > stats.peak_memory:
            stats.peak_memory = self._live

        value = math.inf
        done = 0
        for opp_action in actions:
            if self.player == 0:
                child = state.next_state(my_action, opp_action)
            else:
                child = state.next_state(opp_action, my_action)
            stats.states += 1
            value = min(value, self._max_value(child, next_depth, alpha, beta, ply + 1))
            done += 1
            self._live -= 1
            if self.use_alpha_beta:
                if value <= alpha:
                    stats.cutoffs += 1
                    self._live -= n - done
                    self._record_cutoff(state, self.opponent, opp_action, ply, depth)
                    return value
                beta = min(beta, value)
        return value

    # ------------------------------------------------------------------ move ordering
    def _order_node(self, state, player, actions, ply, tt_move=None):
        """TT move, then killer moves of this ply, then the rest by history score / tactical order."""
        actions = self._order(state, player, actions)
        if self.use_history and self._history:
            tank = state.tanks[player]
            h = self._history
            r, c = tank.row, tank.col
            # Stable sort: the tactical order of EVAL is kept among moves with the same history score.
            actions.sort(key=lambda a: -h.get((player, r, c, a), 0))
        if self.use_killers:
            for k in reversed(self._killers.get(ply, ())):
                if k in actions:
                    actions.remove(k)
                    actions.insert(0, k)
        if tt_move is not None and tt_move in actions:
            actions.remove(tt_move)
            actions.insert(0, tt_move)
        return actions

    def _record_cutoff(self, state, player, action, ply, depth):
        if self.use_killers:
            slot = self._killers.setdefault(ply, [])
            if action not in slot:
                slot.insert(0, action)
                del slot[2:]
        if self.use_history:
            tank = state.tanks[player]
            k = (player, tank.row, tank.col, action)
            d = depth if depth is not None else 1
            self._history[k] = self._history.get(k, 0) + d * d

    def _order(self, state, player, actions):
        if self.move_ordering:
            return self._orderer.order_actions(state, player, actions)
        return actions

    # ------------------------------------------------------------------ helpers
    def _store(self, key, depth, flag, value, move):
        if len(self._tt) >= TT_MAX_ENTRIES:
            self._tt.clear()
        self._tt[key] = (depth if depth is not None else 999, flag, value, move)

    def _utility(self, state):
        self._stats.evaluations += 1
        u = state.utility(self.player)
        if u == 0:
            return 0.0
        # Prefer faster wins and slower losses.
        return u * (WIN_SCORE - (state.turn - self._root_turn))

    def _check_time(self):
        if self._deadline is not None:
            self._ticks += 1
            if (self._ticks & 3) == 0 and time.perf_counter() > self._deadline:
                raise SearchTimeout()

    def root_action_values(self, state, depth=None):
        """Exact backed-up value of every root action (full window, no pruning at the root).
        Used by the experiments to check whether a decision is optimal."""
        self._stats = SearchStats()
        self._deadline = None
        self._root_turn = state.turn
        d = self.depth if depth is None else depth
        self._tt.clear()
        self._eval_cache.clear()
        self._killers.clear()
        self._history.clear()
        return {a: self._min_value(state, a, d, -math.inf, math.inf, 1)
                for a in state.legal_actions(self.player)}


class MinimaxAgent(AdversarialSearchAgent):
    name = "Minimax"
    description = "Minimax to terminal states (depth=None), or cutoff with EVAL = 0"

    def __init__(self, player, depth=None, **kwargs):
        super().__init__(player, depth=depth, use_alpha_beta=False, evaluator=None, **kwargs)


class AlphaBetaAgent(AdversarialSearchAgent):
    name = "Alpha-Beta"
    description = "Alpha-beta to terminal states (depth=None), or cutoff with EVAL = 0"

    def __init__(self, player, depth=None, **kwargs):
        super().__init__(player, depth=depth, use_alpha_beta=True, evaluator=None, **kwargs)


class HeuristicMinimaxAgent(AdversarialSearchAgent):
    name = "Heuristic Minimax"
    description = "H-Minimax: depth cutoff + heuristic EVAL"

    def __init__(self, player, depth=2, evaluator=None, **kwargs):
        super().__init__(player, depth=depth, use_alpha_beta=False,
                         evaluator=evaluator or HeuristicEvaluator(), **kwargs)


class HeuristicAlphaBetaAgent(AdversarialSearchAgent):
    name = "Heuristic Alpha-Beta"
    description = "H-Minimax + alpha-beta + move ordering (TT move, killers, history) + transposition table"

    def __init__(self, player, depth=2, evaluator=None, use_tt=True, **kwargs):
        super().__init__(player, depth=depth, use_alpha_beta=True,
                         evaluator=evaluator or HeuristicEvaluator(), use_tt=use_tt, **kwargs)
