"""Baseline agents: random play and keyboard-controlled human play."""

import random

from ..core.constants import Action
from .base_agent import BaseAgent


class RandomAgent(BaseAgent):
    name = "Random"
    description = "Uniformly random legal action (baseline)"

    def __init__(self, player, seed=None, **kwargs):
        super().__init__(player)
        self.rng = random.Random(seed)

    def choose_action(self, state):
        return self.rng.choice(state.legal_actions(self.player))


class HumanAgent(BaseAgent):
    """The GUI pushes the pressed key into `queue_action`; the match waits until one is queued."""

    name = "Human"
    description = "Keyboard: arrows/WASD move, SPACE fire, ENTER stay"
    is_human = True

    def __init__(self, player, **kwargs):
        super().__init__(player)
        self.pending = None

    def queue_action(self, action):
        self.pending = action

    def has_action(self):
        return self.pending is not None

    def choose_action(self, state):
        action, self.pending = self.pending or Action.STAY, None
        return action
