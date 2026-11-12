"""Tank Battle GUI.

    python main.py                                   # menu
    python main.py --p1 "Heuristic Alpha-Beta" --p2 Human --map classic --start
"""

import argparse

from tank_battle.gui import TankBattleApp


def main():
    parser = argparse.ArgumentParser(description="Tank Battle - adversarial search (PyGame)")
    parser.add_argument("--p1", help="agent name for player 1 (blue)")
    parser.add_argument("--p2", help="agent name for player 2 (red)")
    parser.add_argument("--map", help="map name in maps/ (classic, duel, open)")
    parser.add_argument("--delay", type=int, default=250, help="ms between turns (0, 100, 250, 500, 1000)")
    parser.add_argument("--start", action="store_true", help="skip the menu")
    args = parser.parse_args()
    settings = {k: v for k, v in vars(args).items() if v is not None and k != "start"}
    TankBattleApp(settings, autostart=args.start).run()


if __name__ == "__main__":
    main()
