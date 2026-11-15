"""Unit tests for the game rules and the search algorithms.  Run:  python -m unittest discover tests"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tank_battle.core import Action, DRAW, parse_map, load_map  # noqa: E402
from tank_battle.core.constants import DOWN, LEFT, RIGHT  # noqa: E402
from tank_battle.core.entities import Bullet  # noqa: E402
from tank_battle.core.game_state import GameState  # noqa: E402
from tank_battle.agents import (  # noqa: E402
    CUTOFF_ALPHA_BETA, CUTOFF_MINIMAX, AlphaBetaAgent, HeuristicAlphaBetaAgent, HeuristicMinimaxAgent,
    MinimaxAgent, build_registry,
)
from tank_battle.agents.plugin_loader import discover_plugins  # noqa: E402

S = Action.STAY


def make(text, max_turns=50):
    return parse_map(text, max_turns=max_turns)


class RuleTests(unittest.TestCase):
    def test_move_and_turn(self):
        s = make("2.B\n...\n...\nA.1")
        n = s.next_state(Action.MOVE_LEFT, S)
        self.assertEqual(n.tanks[0].pos, (3, 1))
        self.assertEqual(n.tanks[0].direction, LEFT)
        self.assertEqual(s.tanks[0].pos, (3, 2), "next_state must not modify the original state")
        # Blocked by the map border: only turns.
        n = s.next_state(Action.MOVE_RIGHT, S)
        self.assertEqual(n.tanks[0].pos, (3, 2))
        self.assertEqual(n.tanks[0].direction, RIGHT)

    def test_same_target_cell_nobody_moves(self):
        s = make("B.2\n...\n1..\n..A")
        s.tanks[0].row, s.tanks[0].col = 1, 0
        s.tanks[1].row, s.tanks[1].col = 0, 1
        n = s.next_state(Action.MOVE_RIGHT, Action.MOVE_DOWN)   # both want (1, 1)
        self.assertEqual(n.tanks[0].pos, (1, 0))
        self.assertEqual(n.tanks[1].pos, (0, 1))

    def test_bullet_speed_three_cells(self):
        s = make("...B...2\n........\n........\n........\n........\n........\n1......A")
        n = s.next_state(Action.FIRE, S)        # P1 faces up from (6, 0)
        self.assertEqual(len(n.bullets), 1)
        self.assertEqual(n.bullets[0].pos, (3, 0))
        n = n.next_state(S, S)
        self.assertEqual(n.bullets[0].pos, (0, 0))
        n = n.next_state(S, S)                  # leaves the map
        self.assertEqual(n.bullets, [])

    def test_bullet_hits_tank_and_stops(self):
        s = make("2......B\n........\n........\n........\n........\n........\n1......A")
        n = s.next_state(Action.FIRE, S).next_state(S, S)
        # The P2 tank is at (0,0): the 2nd cycle moves the bullet (3,0)->(2,0)->(1,0)->(0,0) = hit
        self.assertEqual(n.tanks[1].hp, 5)
        self.assertEqual(n.bullets, [])

    def test_wall_absorbs_hits(self):
        s = make("B..2\n.W..\n....\n.1.A")
        s.tanks[0].row, s.tanks[0].col = 3, 1
        n = s
        for expected in (2, 1):
            n = n.next_state(Action.FIRE, S)
            self.assertEqual(n.walls[(1, 1)], expected)
        n = n.next_state(Action.FIRE, S)
        self.assertNotIn((1, 1), n.walls)
        self.assertIn((1, 1), s.walls, "copy-on-write must protect the parent's walls")

    def test_bullets_do_not_stop_each_other(self):
        # The assignment only lets a bullet collide with a wall, a tank or a base.
        s = make("B..2\n....\n....\n....\n....\n....\n....\nA..1")
        n = s.next_state(Action.FIRE, Action.FIRE)   # bullets at (4,3) and (3,3)
        n = n.next_state(S, S)                       # they pass each other: now at (1,3) and (6,3)
        self.assertEqual(sorted(b.pos for b in n.bullets), [(1, 3), (6, 3)])
        n = n.next_state(S, S)                       # and each one hits the tank it was aimed at
        self.assertEqual(n.bullets, [])
        self.assertEqual(n.tanks[0].hp, 5)
        self.assertEqual(n.tanks[1].hp, 5)

    def test_tanks_facing_each_other_do_not_stall(self):
        # Two tanks trading shots at close range must end the game, not stand still until the turn limit.
        s = make("B..2\n....\n....\nA..1", max_turns=50)
        while not s.is_terminal():
            s = s.next_state(Action.FIRE, Action.FIRE)
        self.assertLess(s.turn, 10)
        self.assertEqual(s.winner(), DRAW)           # both tanks destroyed in the same cycle

    def test_one_bullet_per_tank(self):
        s = make("2......B\n........\n........\n........\n........\n........\n........\n"
                 "........\n........\n........\n1......A")
        n = s.next_state(Action.FIRE, S)
        self.assertNotIn(Action.FIRE, n.legal_actions(0))
        self.assertEqual(len(n.next_state(Action.FIRE, S).bullets), 1)

    def test_terminal_and_winner(self):
        s = make("2..B\n....\n1..A")
        s.bases[1].hp = 0
        self.assertTrue(s.is_terminal())
        self.assertEqual(s.winner(), 0)
        self.assertEqual(s.utility(0), 1)
        self.assertEqual(s.utility(1), -1)
        s.tanks[0].hp = 0
        self.assertEqual(s.winner(), DRAW)
        t = make("2..B\n....\n1..A", max_turns=0)
        self.assertEqual(t.winner(), DRAW)

    def test_fire_is_decided_at_the_start_of_the_cycle(self):
        """A tank with a bullet in flight cannot fire in this cycle, even when the opponent drives onto
        that bullet during the movement phase. So FIRE with a bullet in flight is exactly STAY."""
        s = make(".2.B\n1...\n....\n.A..")
        s.tanks[0].direction = RIGHT
        s.bullets.append(Bullet(1, 1, 1, DOWN))                 # P2's bullet, next to P1's tank
        fired = s.next_state(Action.MOVE_RIGHT, Action.FIRE)    # P1 drives onto the bullet, P2 "fires"
        stayed = s.next_state(Action.MOVE_RIGHT, S)
        self.assertEqual(fired.tanks[0].hp, s.tanks[0].hp - 1)  # hit once, by the bullet it drove onto
        self.assertEqual(fired.bullets, [])
        self.assertEqual(fired.key(), stayed.key())

    def test_bullets_entering_the_same_cell_hit_together(self):
        """Two bullets reach a 1-HP wall in the same step: both are absorbed, whatever their order."""
        s = make("A.....B\n1..W..2\n.......")
        s.walls[(1, 3)] = 1
        s.wall_hash = s.compute_wall_hash()
        s.tanks[0].direction, s.tanks[1].direction = RIGHT, LEFT
        s = s.next_state(Action.FIRE, Action.FIRE)
        self.assertNotIn((1, 3), s.walls)
        self.assertEqual(s.bullets, [])
        self.assertEqual([t.hp for t in s.tanks], [6, 6])
        self.assertEqual(s.wall_hash, s.compute_wall_hash())

    def test_legal_actions_drop_duplicates_of_stay(self):
        s = make("2..B\n....\n1..A")
        s.tanks[0].direction = LEFT
        legal = s.legal_actions(0)
        self.assertNotIn(Action.MOVE_LEFT, legal)   # facing the border: same as STAY
        self.assertIn(Action.MOVE_DOWN, legal)      # blocked, but it turns the tank
        self.assertIn(Action.FIRE, legal)


class SearchTests(unittest.TestCase):
    def random_states(self, n=6):
        rng = random.Random(3)
        states = []
        for name in ("duel", "open"):
            s = load_map(name)
            for _ in range(n):
                for _ in range(rng.randint(0, 6)):
                    s = s.next_state(rng.choice(s.legal_actions(0)), rng.choice(s.legal_actions(1)))
                states.append(s)
        return states

    def test_alpha_beta_value_equals_minimax(self):
        for s in self.random_states():
            for player in (0, 1):
                mm = HeuristicMinimaxAgent(player, depth=2)
                ab = HeuristicAlphaBetaAgent(player, depth=2)
                mm.choose_action(s)
                ab.choose_action(s)
                self.assertAlmostEqual(mm.last_stats.value, ab.last_stats.value, places=6)
                self.assertLessEqual(ab.last_stats.nodes, mm.last_stats.nodes)
                um, ua = MinimaxAgent(player, depth=2), AlphaBetaAgent(player, depth=2)
                um.choose_action(s)
                ua.choose_action(s)
                self.assertEqual(um.last_stats.value, ua.last_stats.value)

    def test_alpha_beta_equals_minimax_to_terminal_states(self):
        """Exact search (no cutoff): pruning must not change the minimax value of the root."""
        rng = random.Random(11)
        for name in ("duel", "open"):
            for _ in range(4):
                s = load_map(name)
                for _ in range(rng.randint(2, 10)):
                    s = s.next_state(rng.choice(s.legal_actions(0)), rng.choice(s.legal_actions(1)))
                s.tanks[0].hp, s.tanks[1].hp = rng.randint(1, 2), rng.randint(1, 2)
                s.max_turns = s.turn + 3          # game tree of m = 6 plies
                for player in (0, 1):
                    mm, ab = MinimaxAgent(player), AlphaBetaAgent(player)
                    mm.choose_action(s)
                    ab.choose_action(s)
                    self.assertEqual(mm.last_stats.value, ab.last_stats.value)
                    self.assertLessEqual(ab.last_stats.nodes, mm.last_stats.nodes)
                    self.assertEqual(mm.last_stats.max_ply, 6)

    def test_full_depth_finds_forced_win(self):
        # P2's base has 1 HP, P1 is facing it on the same column: FIRE wins immediately.
        s = make("2.B\n...\n...\nA.1", max_turns=4)
        s.bases[1].hp = 1
        for cls in (MinimaxAgent, AlphaBetaAgent):
            agent = cls(0, depth=None)
            self.assertEqual(agent.choose_action(s), Action.FIRE)
            self.assertGreater(agent.last_stats.value, 0)

    def test_iterative_deepening_respects_time(self):
        agent = HeuristicAlphaBetaAgent(0, depth=20, time_limit=0.2, iterative_deepening=True)
        agent.choose_action(load_map("classic"))
        self.assertLess(agent.last_stats.time, 0.6)
        self.assertGreaterEqual(agent.last_stats.depth, 1)

    def test_wall_hash_is_updated_incrementally(self):
        """The Zobrist wall hash kept by apply_cycle must equal the hash recomputed from scratch."""
        rng = random.Random(5)
        for name in ("classic", "duel", "open"):
            s = load_map(name)
            for _ in range(80):
                if s.is_terminal():
                    break
                s = s.next_state(rng.choice(s.legal_actions(0)), rng.choice(s.legal_actions(1)))
                self.assertEqual(s.wall_hash, s.compute_wall_hash())

    def test_tt_key_tells_base_hp_and_walls_apart(self):
        agent = HeuristicAlphaBetaAgent(0, depth=2)
        s = load_map("duel")
        hurt = s.deep_copy()
        hurt.bases[1].hp -= 1
        self.assertNotEqual(agent._state_key(s), agent._state_key(hurt))
        hit = s.next_state(Action.FIRE, S)       # P1 faces the wall above it on the duel map
        broken = hit.deep_copy()
        broken.tanks[0].direction = s.tanks[0].direction
        if broken.walls != s.walls:
            self.assertNotEqual(agent._state_key(s), agent._state_key(broken))

    def test_all_optimizations_keep_the_minimax_value(self):
        """TT + killer moves + history heuristic + move ordering only change the order of the search."""
        for s in self.random_states(4):
            for depth in (2, 3):
                mm = HeuristicMinimaxAgent(0, depth=depth)
                mm.choose_action(s)
                for kwargs in ({}, {"use_tt": False}, {"use_killers": False, "use_history": False}):
                    ab = HeuristicAlphaBetaAgent(0, depth=depth, **kwargs)
                    ab.choose_action(s)
                    self.assertAlmostEqual(mm.last_stats.value, ab.last_stats.value, places=6, msg=str(kwargs))

    def test_transposition_table_keeps_the_minimax_value_at_depth_4(self):
        """Regression: a table keyed without the turn reused, at a node with less depth left, a value
        searched deeper. On this position (open map, turn 26) it returned 120.17 / MOVE_UP at depth 4
        instead of the H-Minimax value 119.63 / MOVE_RIGHT. With the turn in the key the table only
        merges true transpositions, so the value and the move are those of plain alpha-beta."""
        s = load_map("open")
        s.turn = 26
        del s.walls[(0, 5)]
        s.wall_hash = s.compute_wall_hash()
        s.bases[1].hp = 7
        (s.tanks[0].row, s.tanks[0].col, s.tanks[0].direction) = (4, 0, LEFT)
        (s.tanks[1].row, s.tanks[1].col, s.tanks[1].direction) = (2, 6, LEFT)
        for player, expected in ((0, 119.6258), (1, -122.5508)):
            plain = HeuristicAlphaBetaAgent(player, depth=4, use_tt=False)
            plain.choose_action(s)
            exact = plain.root_action_values(s, 4)
            for kwargs in ({}, {"iterative_deepening": True}, {"move_ordering": False}):
                agent = HeuristicAlphaBetaAgent(player, depth=4, **kwargs)
                action = agent.choose_action(s)
                self.assertAlmostEqual(agent.last_stats.value, plain.last_stats.value, places=6, msg=str(kwargs))
                self.assertAlmostEqual(agent.last_stats.value, expected, places=3)
                self.assertAlmostEqual(exact[action], max(exact.values()), places=6, msg=str(kwargs))

    def test_tt_key_is_the_complete_state_including_the_turn(self):
        agent = HeuristicAlphaBetaAgent(0, depth=3)
        s = load_map("duel")
        later = s.next_state(S, S)             # nothing moved: same position, one turn later
        self.assertEqual(later.key()[:-1], s.key()[:-1])
        self.assertNotEqual(agent._state_key(s), agent._state_key(later))

    def test_action_pruning_keeps_the_exact_minimax_value(self):
        """legal_actions drops moves that equal STAY; the exact value must be the same with all six."""
        trap = make(".2.B\n1...\n....\n.A..", max_turns=1)   # P1 can drive onto P2's bullet
        trap.tanks[0].hp, trap.tanks[0].direction, trap.tanks[1].direction = 2, RIGHT, DOWN
        trap.bases[0].hp = 1
        trap.bullets.append(Bullet(1, 1, 1, DOWN))
        states = [trap]
        rng = random.Random(7)
        for name in ("duel", "open"):
            for _ in range(5):
                s = load_map(name)
                for _ in range(rng.randint(4, 20)):
                    if s.is_terminal():
                        break
                    s = s.next_state(rng.choice(s.legal_actions(0)), rng.choice(s.legal_actions(1)))
                if not s.is_terminal():
                    s.max_turns = s.turn + 2
                    states.append(s)
        pruned = GameState.legal_actions
        for s in states:
            for player in (0, 1):
                values = []
                for all_six in (False, True):
                    if all_six:
                        GameState.legal_actions = lambda self, p: list(Action)
                    try:
                        agent = AlphaBetaAgent(player, depth=None)
                        agent.choose_action(s)
                        values.append(agent.last_stats.value)
                    finally:
                        GameState.legal_actions = pruned
                self.assertEqual(values[0], values[1])

    def test_default_agents_play_a_move_of_best_minimax_value(self):
        """The root tie-break only chooses among moves of best minimax value (no randomization by default)."""
        for s in self.random_states(3):
            for cls in (HeuristicMinimaxAgent, HeuristicAlphaBetaAgent):
                agent = cls(0, depth=2)
                action = agent.choose_action(s)
                exact = HeuristicMinimaxAgent(0, depth=2, tie_break=False).root_action_values(s)
                self.assertAlmostEqual(exact[action], max(exact.values()), places=6)
                self.assertAlmostEqual(agent.last_stats.value, max(exact.values()), places=6)
                self.assertEqual(action, cls(0, depth=2, seed=5).choose_action(s))   # deterministic

    def test_peak_memory_is_linear_in_depth(self):
        """Depth-first search keeps O(b*m) nodes: the path plus the untried siblings of each node."""
        for depth in (2, 3, 4):
            agent = HeuristicAlphaBetaAgent(0, depth=depth, use_tt=False)
            agent.choose_action(load_map("classic"))
            st = agent.last_stats
            self.assertGreater(st.peak_memory, 2 * depth)
            self.assertLessEqual(st.peak_memory, 1 + 2 * depth * 6)

    def test_root_tie_break_does_not_stall_on_symmetric_map(self):
        """On the point-symmetric classic map every root move has minimax value 0; the agents must
        still make progress instead of turning on the spot (regression for the 'stalling' bug)."""
        s = load_map("classic")
        agents = [HeuristicAlphaBetaAgent(p, depth=3, iterative_deepening=True, seed=p) for p in (0, 1)]
        fired, cells = 0, set()
        for _ in range(60):
            if s.is_terminal():
                break
            a0, a1 = agents[0].choose_action(s), agents[1].choose_action(s)
            fired += (a0 == Action.FIRE) + (a1 == Action.FIRE)
            s = s.next_state(a0, a1)
            cells.add(s.tanks[0].pos)
        self.assertGreater(fired, 0)
        self.assertGreater(len(cells), 6)

    def test_defender_contests_a_siege_lane(self):
        """P1 sits on a clean firing lane to P2's base; P2's tank stands next to that lane. P2 must move
        to block / contest the lane (f6 siege term) instead of firing into the void or walking away."""
        from tank_battle.core.constants import UP
        s = make("...B...\n.......\n..2....\n.......\n...1...\n.......\n...A...", max_turns=100)
        s.tanks[0].direction = s.tanks[1].direction = UP
        for depth in (2, 3):
            agent = HeuristicAlphaBetaAgent(1, depth=depth)
            self.assertIn(agent.choose_action(s), (Action.MOVE_UP, Action.MOVE_RIGHT))

    def test_near_tie_choice_stays_close_to_the_minimax_value(self):
        """Optional randomized variant: a random choice among near-best root moves may lose at most
        tie_margin of minimax value."""
        s = load_map("classic")
        for seed in range(5):
            agent = HeuristicAlphaBetaAgent(0, depth=2, seed=seed, tie_margin=15.0, tie_random=1.0)
            action = agent.choose_action(s)
            values = HeuristicAlphaBetaAgent(0, depth=2, tie_break=False).root_action_values(s)
            self.assertGreaterEqual(values[action], max(values.values()) - 15.0)


class PluginTests(unittest.TestCase):
    def test_cutoff_agents_without_heuristic_are_labelled(self):
        """Minimax / Alpha-Beta with a depth cutoff and no EVAL must not be listed as plain Minimax."""
        entries, _ = build_registry(include_plugins=False)
        names = [e.name for e in entries]
        self.assertIn(CUTOFF_MINIMAX, names)
        self.assertIn(CUTOFF_ALPHA_BETA, names)
        self.assertNotIn("Minimax", names)
        self.assertNotIn("Alpha-Beta", names)
        for name in (CUTOFF_MINIMAX, CUTOFF_ALPHA_BETA):
            self.assertIn("EVAL = 0", name)

    def test_example_plugins_load(self):
        entries, errors = discover_plugins()
        self.assertEqual(errors, [])
        names = [e.name for e in entries]
        self.assertTrue(len(names) >= 2)
        s = load_map("duel")
        for e in entries:
            agent = e.create(1)
            self.assertIn(Action.parse(agent.choose_action(s.deep_copy())), list(Action))


if __name__ == "__main__":
    unittest.main()
