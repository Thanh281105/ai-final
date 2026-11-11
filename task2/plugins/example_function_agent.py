"""Example plugin, style (b): a plain function, no import of our code required.

This is the easiest way to plug in an agent from another group whose code uses its own classes:
write `get_action` that converts the observation dict into their representation and calls them.

observation = {
    "width": int, "height": int, "turn": int, "max_turns": int,
    "walls":   [[row, col, hp], ...],
    "tanks":   [{"player": 0, "row": r, "col": c, "direction": "UP", "hp": 6}, {...player 1...}],
    "bases":   [{"player": 0, "row": r, "col": c, "hp": 9}, {...}],
    "bullets": [{"owner": 0, "row": r, "col": c, "direction": "LEFT"}, ...],
}
Return one of: "MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "FIRE", "STAY".
"""

import random

AGENT_NAME = "Example: Function (dodger)"

_rng = random.Random(7)


def get_action(observation, player_id):
    me = observation["tanks"][player_id]
    enemy = observation["tanks"][1 - player_id]
    my_bullet = any(b["owner"] == player_id for b in observation["bullets"])

    # Shoot the enemy tank when facing it on the same line.
    if not my_bullet:
        if me["row"] == enemy["row"] and me["direction"] == ("RIGHT" if enemy["col"] > me["col"] else "LEFT"):
            return "FIRE"
        if me["col"] == enemy["col"] and me["direction"] == ("DOWN" if enemy["row"] > me["row"] else "UP"):
            return "FIRE"

    # Dodge sideways when an enemy bullet flies along our row or column.
    for b in observation["bullets"]:
        if b["owner"] != player_id and (b["row"] == me["row"] or b["col"] == me["col"]):
            return _rng.choice(["MOVE_LEFT", "MOVE_RIGHT"] if b["col"] == me["col"] else ["MOVE_UP", "MOVE_DOWN"])

    return _rng.choice(["MOVE_UP", "MOVE_DOWN", "MOVE_LEFT", "MOVE_RIGHT", "FIRE", "STAY"])
