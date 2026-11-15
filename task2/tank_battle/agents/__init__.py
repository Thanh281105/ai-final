from .base_agent import BaseAgent, SearchStats
from .heuristics import HeuristicEvaluator
from .plugin_loader import AgentEntry, FunctionAgent, discover_plugins, resolve_agent
from .search_agents import (
    NEAR_TIE_MARGIN, RANDOM_TIE_PROBABILITY, AdversarialSearchAgent, AlphaBetaAgent, HeuristicAlphaBetaAgent,
    HeuristicMinimaxAgent, MinimaxAgent,
)
from .simple_agents import HumanAgent, RandomAgent

# Minimax / Alpha-Beta of the lecture search down to the terminal states, which is only feasible in an
# endgame (experiment A). To let them play a whole game they are cut off at 2 cycles and, having no EVAL,
# score a cutoff state as 0: that is H-Minimax with EVAL = 0, and the menu says so.
CUTOFF_MINIMAX = "Minimax (cutoff, EVAL = 0)"
CUTOFF_ALPHA_BETA = "Alpha-Beta (cutoff, EVAL = 0)"

# GUI presets: depth is in game cycles (1 cycle = 2 plies). The strongest agent searches as deep as it can
# in 50 ms (iterative deepening) so the GUI stays real time on the evaluation laptop.
BUILTIN_AGENTS = [
    AgentEntry("Heuristic Alpha-Beta",
               lambda p: HeuristicAlphaBetaAgent(p, depth=12, time_limit=0.05, iterative_deepening=True, seed=None),
               description="Alpha-beta + TT + move ordering, iterative deepening, 50 ms/move"),
    AgentEntry("Heuristic Minimax", lambda p: HeuristicMinimaxAgent(p, depth=2),
               description="Cutoff at 2 cycles (4 plies), EVAL at the cutoff"),
    AgentEntry(CUTOFF_ALPHA_BETA, lambda p: AlphaBetaAgent(p, depth=2, time_limit=0.2),
               description="Cutoff at 2 cycles (4 plies); no EVAL: a cutoff state scores 0"),
    AgentEntry(CUTOFF_MINIMAX, lambda p: MinimaxAgent(p, depth=2, time_limit=0.2),
               description="Cutoff at 2 cycles (4 plies); no EVAL: a cutoff state scores 0"),
    AgentEntry("Heuristic Alpha-Beta (randomized)",
               lambda p: HeuristicAlphaBetaAgent(p, depth=12, time_limit=0.05, iterative_deepening=True, seed=None,
                                                  tie_random=RANDOM_TIE_PROBABILITY, tie_margin=NEAR_TIE_MARGIN),
               description="Same search; 20% random near-best moves (varied games, weaker)"),
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
    "NEAR_TIE_MARGIN", "RANDOM_TIE_PROBABILITY", "CUTOFF_MINIMAX", "CUTOFF_ALPHA_BETA", "BaseAgent", "SearchStats",
    "HeuristicEvaluator", "AgentEntry", "FunctionAgent", "discover_plugins",
    "resolve_agent", "AdversarialSearchAgent", "AlphaBetaAgent", "HeuristicAlphaBetaAgent",
    "HeuristicMinimaxAgent", "MinimaxAgent", "HumanAgent", "RandomAgent", "BUILTIN_AGENTS", "build_registry",
]
