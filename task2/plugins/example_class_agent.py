"""Example plugin, style (a): subclass BaseAgent.

Copy this file, rename it (e.g. group07_agent.py) and put it in plugins/.
The game discovers every BaseAgent subclass defined in the file.
"""

from tank_battle.agents import BaseAgent
from tank_battle.core import Action


class SniperAgent(BaseAgent):
    name = "Example: Sniper"
    description = "Fires when lined up with the enemy, otherwise walks toward the enemy base"

    def choose_action(self, state):
        me = state.tanks[self.player]
        enemy = state.tanks[self.opponent]
        base = state.bases[self.opponent]
        legal = state.legal_actions(self.player)

        for target in (enemy, base):
            if target.row == me.row or target.col == me.col:
                facing = self._direction_to(me, target)
                if facing == me.direction and Action.FIRE in legal:
                    return Action.FIRE
                turn = {"UP": Action.MOVE_UP, "DOWN": Action.MOVE_DOWN,
                        "LEFT": Action.MOVE_LEFT, "RIGHT": Action.MOVE_RIGHT}[facing]
                if turn in legal:
                    return turn

        # Walk toward the enemy base: horizontal first, vertical if blocked, else shoot through the wall.
        steps = []
        if base.col != me.col:
            steps.append((Action.MOVE_RIGHT, 0, 1) if base.col > me.col else (Action.MOVE_LEFT, 0, -1))
        if base.row != me.row:
            steps.append((Action.MOVE_DOWN, 1, 0) if base.row > me.row else (Action.MOVE_UP, -1, 0))
        for action, dr, dc in steps:
            if state.is_free_for_tank(me.row + dr, me.col + dc):
                return action
        return Action.FIRE if Action.FIRE in legal else Action.STAY

    @staticmethod
    def _direction_to(me, target):
        if target.row == me.row:
            return "RIGHT" if target.col > me.col else "LEFT"
        return "DOWN" if target.row > me.row else "UP"
