"""Headless matches between any two agents (built-in or plugins from other groups).

    python arena.py --list
    python arena.py --p1 "Heuristic Alpha-Beta" --p2 plugins/example_class_agent.py --map classic --games 4
    python arena.py --p1 "Heuristic Alpha-Beta" --p2 "plugins/group07.py:TheirAgent" --swap

--swap plays every game twice with sides exchanged (the map is symmetric, so this removes side bias).
"""

import argparse

from tank_battle.agents import build_registry, resolve_agent
from tank_battle.core.constants import DRAW
from tank_battle.core.map_loader import load_map
from tank_battle.match import Match


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--p1", default="Heuristic Alpha-Beta")
    parser.add_argument("--p2", default="Random")
    parser.add_argument("--map", default="classic")
    parser.add_argument("--games", type=int, default=1)
    parser.add_argument("--swap", action="store_true")
    parser.add_argument("--time-limit", type=float, default=None, help="seconds per move, else STAY")
    parser.add_argument("--max-turns", type=int, default=None)
    parser.add_argument("--list", action="store_true", help="list available agents")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    registry, errors = build_registry()
    for e in errors:
        print("plugin error:", e)
    if args.list:
        for e in registry:
            print("%-30s %-28s %s" % (e.name, e.source, e.description))
        return

    entries = [resolve_agent(args.p1, registry), resolve_agent(args.p2, registry)]
    score = {entries[0].name: 0, entries[1].name: 0, "draw": 0}
    for game in range(args.games):
        for swapped in ((False, True) if args.swap else (False,)):
            pair = entries[::-1] if swapped else entries
            agents = [pair[0].create(0), pair[1].create(1)]
            match = Match(load_map(args.map, args.max_turns), agents, args.time_limit)
            r = match.play(verbose=args.verbose)
            w = r["winner"]
            score["draw" if w == DRAW else pair[w].name] += 1
            print("game %d  P1=%-22s P2=%-22s -> %-8s turns=%3d tankHP=%s baseHP=%s avg time=%.1f/%.1f ms"
                  % (game + 1, pair[0].name, pair[1].name, r["outcome"], r["turns"], r["tank_hp"], r["base_hp"],
                     r["avg_time"][0] * 1000, r["avg_time"][1] * 1000))
    print("\nScore:", score)


if __name__ == "__main__":
    main()
