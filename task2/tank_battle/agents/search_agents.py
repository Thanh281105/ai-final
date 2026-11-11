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
"""

import math
import random
import time

from .base_agent import BaseAgent, SearchStats
from .heuristics import HeuristicEvaluator

WIN_SCORE = 1_000_000.0


class SearchTimeout(Exception):
    pass


class AdversarialSearchAgent(BaseAgent):
    name = "Adversarial Search"

    def __init__(self, player, depth=2, use_alpha_beta=False, evaluator=None, move_ordering=None,
                 time_limit=None, iterative_deepening=False, seed=0, **kwargs):
        super().__init__(player)
        self.depth = depth
        self.use_alpha_beta = use_alpha_beta
        self.evaluator = evaluator
        # Move ordering only helps when pruning and needs domain knowledge, so by default it is enabled
        # for heuristic alpha-beta only (plain alpha-beta stays knowledge-free for a fair comparison).
        if move_ordering is None:
            move_ordering = use_alpha_beta and evaluator is not None
        self.move_ordering = move_ordering
        self._orderer = evaluator if evaluator is not None else HeuristicEvaluator()
        self.time_limit = time_limit
        self.iterative_deepening = iterative_deepening
        self.seed = seed
        self.rng = random.Random(seed)
        self._deadline = None
        self._root_turn = 0
        self._partial = None
        self._stats = SearchStats()

    def reset(self):
        super().reset()
        self.rng = random.Random(self.seed)

    # ------------------------------------------------------------------ entry point
    def choose_action(self, state):
        stats = self._stats = SearchStats()
        start = time.perf_counter()
        self._deadline = start + self.time_limit if self.time_limit else None
        self._root_turn = state.turn

        root_actions = state.legal_actions(self.player)
        self.rng.shuffle(root_actions)   # random tie-breaking among equally good moves
        best_action, best_value = root_actions[0], None

        if self.iterative_deepening:
            depths = range(1, (self.depth or 10 ** 6) + 1)
        else:
            depths = [self.depth]

        pv_action = None
        for d in depths:
            try:
                action, value = self._search_root(state, d, root_actions, pv_action)
            except SearchTimeout:
                stats.timed_out = True
                if best_value is None and self._partial is not None:
                    best_action, best_value = self._partial   # fixed-depth search ran out of time
                break
            best_action, best_value, pv_action = action, value, action
            stats.depth = d if d is not None else stats.max_ply // 2
            if abs(value) >= WIN_SCORE / 2 or d is None:
                break    # a forced win/loss was proven, deeper search cannot change it

        stats.time = time.perf_counter() - start
        stats.value = best_value
        self.last_stats = stats
        return best_action

    # ------------------------------------------------------------------ minimax / alpha-beta
    def _search_root(self, state, depth, root_actions, pv_action):
        actions = self._order(state, self.player, list(root_actions))
        if pv_action in actions:      # best move of the previous iteration first
            actions.remove(pv_action)
            actions.insert(0, pv_action)
        self._partial = None
        self._stats.nodes += 1
        alpha, beta = -math.inf, math.inf
        best_action, best_value = actions[0], -math.inf
        for action in actions:
            value = self._min_value(state, action, depth, alpha, beta, 1)
            if value > best_value:
                best_action, best_value = action, value
                self._partial = (best_action, best_value)
            if self.use_alpha_beta:
                alpha = max(alpha, value)
        return best_action, best_value

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
            return self.evaluator.evaluate(state, self.player) if self.evaluator else 0.0

        value = -math.inf
        for action in self._order(state, self.player, state.legal_actions(self.player)):
            value = max(value, self._min_value(state, action, depth, alpha, beta, ply + 1))
            if self.use_alpha_beta:
                if value >= beta:
                    stats.cutoffs += 1
                    return value
                alpha = max(alpha, value)
        return value

    def _min_value(self, state, my_action, depth, alpha, beta, ply):
        stats = self._stats
        stats.nodes += 1
        if ply > stats.max_ply:
            stats.max_ply = ply
        next_depth = None if depth is None else depth - 1

        value = math.inf
        for opp_action in self._order(state, self.opponent, state.legal_actions(self.opponent)):
            if self.player == 0:
                child = state.next_state(my_action, opp_action)
            else:
                child = state.next_state(opp_action, my_action)
            stats.states += 1
            value = min(value, self._max_value(child, next_depth, alpha, beta, ply + 1))
            if self.use_alpha_beta:
                if value <= alpha:
                    stats.cutoffs += 1
                    return value
                beta = min(beta, value)
        return value

    # ------------------------------------------------------------------ helpers
    def _utility(self, state):
        self._stats.evaluations += 1
        u = state.utility(self.player)
        if u == 0:
            return 0.0
        # Prefer faster wins and slower losses.
        return u * (WIN_SCORE - (state.turn - self._root_turn))

    def _order(self, state, player, actions):
        if self.move_ordering:
            return self._orderer.order_actions(state, player, actions)
        return actions

    def _check_time(self):
        if self._deadline is not None and (self._stats.nodes & 127) == 0:
            if time.perf_counter() > self._deadline:
                raise SearchTimeout()

    def root_action_values(self, state, depth=None):
        """Exact backed-up value of every root action (full window, no pruning at the root).
        Used by the experiments to check whether a decision is optimal."""
        self._stats = SearchStats()
        self._deadline = None
        self._root_turn = state.turn
        d = self.depth if depth is None else depth
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
    description = "H-Minimax + alpha-beta pruning + move ordering"

    def __init__(self, player, depth=2, evaluator=None, **kwargs):
        super().__init__(player, depth=depth, use_alpha_beta=True,
                         evaluator=evaluator or HeuristicEvaluator(), **kwargs)
