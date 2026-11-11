"""Unit tests for the game rules and the search algorithms.  Run:  python -m unittest discover tests"""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tank_battle.core import Action, DRAW, parse_map, load_map  # noqa: E402
from tank_battle.core.constants import LEFT, RIGHT  # noqa: E402
from tank_battle.agents import (  # noqa: E402
    AlphaBetaAgent, HeuristicAlphaBetaAgent, HeuristicMinimaxAgent, MinimaxAgent,
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


class PluginTests(unittest.TestCase):
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
