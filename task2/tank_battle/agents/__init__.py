from .base_agent import BaseAgent, SearchStats
from .heuristics import HeuristicEvaluator
from .plugin_loader import AgentEntry, FunctionAgent, discover_plugins, resolve_agent
from .search_agents import (
    AdversarialSearchAgent, AlphaBetaAgent, HeuristicAlphaBetaAgent, HeuristicMinimaxAgent, MinimaxAgent,
)
from .simple_agents import HumanAgent, RandomAgent

# GUI presets: depth is in game cycles (1 cycle = 2 plies). Optimized for real-time responsiveness (<20ms).
BUILTIN_AGENTS = [
    AgentEntry("Heuristic Alpha-Beta",
               lambda p: HeuristicAlphaBetaAgent(p, depth=4, time_limit=0.15, iterative_deepening=False),
               description="Fast H-AlphaBeta with TT & Move Ordering (8 plies, ~8ms per move)"),
    AgentEntry("Heuristic Minimax", lambda p: HeuristicMinimaxAgent(p, depth=2),
               description="Cutoff at 2 cycles (4 plies), EVAL at the cutoff (~8ms)"),
    AgentEntry("Alpha-Beta", lambda p: AlphaBetaAgent(p, depth=2, time_limit=0.2),
               description="Cutoff at 2 cycles (4 plies), no heuristic: cutoff states count as 0"),
    AgentEntry("Minimax", lambda p: MinimaxAgent(p, depth=2, time_limit=0.2),
               description="Cutoff at 2 cycles (4 plies), no heuristic: cutoff states count as 0"),
    AgentEntry("Random", lambda p: RandomAgent(p), description="Baseline random moves"),
    AgentEntry("Human", lambda p: HumanAgent(p), description=HumanAgent.description),
]


def build_registry(include_plugins=True):
    """Built-in agents followed by every agent found in plugins/. Returns (entries, errors)."""
    entries = list(BUILTIN_AGENTS)
    errors = []
    if include_plugins:
        plugins, errors = discover_plugins()
        entries.extend(plugins)
    return entries, errors


__all__ = [
    "BaseAgent", "SearchStats", "HeuristicEvaluator", "AgentEntry", "FunctionAgent", "discover_plugins",
    "resolve_agent", "AdversarialSearchAgent", "AlphaBetaAgent", "HeuristicAlphaBetaAgent",
    "HeuristicMinimaxAgent", "MinimaxAgent", "HumanAgent", "RandomAgent", "BUILTIN_AGENTS", "build_registry",
]
