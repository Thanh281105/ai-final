"""Match: runs a game between two agents in the same environment (used by the GUI, CLI and experiments)."""

import time
import traceback

from .core.constants import Action, DRAW


class MoveRecord:
    __slots__ = ("turn", "actions", "times", "stats", "notes")

    def __init__(self, turn, actions, times, stats, notes):
        self.turn = turn
        self.actions = actions
        self.times = times
        self.stats = stats
        self.notes = notes


class Match:
    """Both agents see the same state, decide independently, then the cycle is resolved.

    move_time_limit: if an agent needs longer than this (seconds) its move is replaced by STAY.
    An agent that raises an exception or returns an invalid action also plays STAY.
    """

    def __init__(self, initial_state, agents, move_time_limit=None):
        self.initial_state = initial_state
        self.agents = agents
        self.move_time_limit = move_time_limit
        self.reset()

    def reset(self):
        self.state = self.initial_state.deep_copy()
        self.history = []
        for agent in self.agents:
            agent.reset()

    @property
    def over(self):
        return self.state.is_terminal()

    @property
    def winner(self):
        return self.state.winner()

    def decide(self, player):
        """Ask one agent for its action. Returns (action, seconds, stats_dict, note)."""
        agent = self.agents[player]
        note = ""
        start = time.perf_counter()
        try:
            action = Action.parse(agent.choose_action(self.state.deep_copy()))
        except Exception as exc:   # noqa: BLE001 - a foreign agent must not crash the game
            traceback.print_exc()
            action, note = Action.STAY, "error: %s" % exc
        elapsed = time.perf_counter() - start
        if self.move_time_limit is not None and elapsed > self.move_time_limit:
            action, note = Action.STAY, "time limit exceeded (%.2fs)" % elapsed
        stats = agent.last_stats.as_dict() if hasattr(agent, "last_stats") else {}
        return action, elapsed, stats, note

    def step(self):
        """Play one game cycle. Returns the MoveRecord."""
        if self.over:
            return None
        decisions = [self.decide(p) for p in (0, 1)]
        return self.apply(decisions)

    def apply(self, decisions):
        actions = tuple(d[0] for d in decisions)
        record = MoveRecord(self.state.turn, actions, tuple(d[1] for d in decisions),
                            tuple(d[2] for d in decisions), tuple(d[3] for d in decisions))
        nxt = self.state.clone()
        nxt.record_trails = True          # the GUI draws the path of every shot of this cycle
        nxt.apply_cycle(*actions)
        self.state = nxt
        self.history.append(record)
        return record

    def play(self, verbose=False):
        while not self.over:
            record = self.step()
            if verbose:
                print("turn %3d  P1 %-10s P2 %-10s" % (record.turn, record.actions[0].value,
                                                       record.actions[1].value))
        return self.result()

    def result(self):
        w = self.winner
        times = [[r.times[p] for r in self.history] for p in (0, 1)]
        nodes = [[r.stats[p].get("nodes", 0) for r in self.history] for p in (0, 1)]
        s = self.state
        return {
            "winner": w,
            "outcome": "draw" if w == DRAW else "P%d wins" % (w + 1),
            "turns": s.turn,
            "tank_hp": [t.hp for t in s.tanks],
            "base_hp": [b.hp for b in s.bases],
            "avg_time": [sum(t) / len(t) if t else 0.0 for t in times],
            "max_time": [max(t) if t else 0.0 for t in times],
            "avg_nodes": [sum(n) / len(n) if n else 0.0 for n in nodes],
        }
