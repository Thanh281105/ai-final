"""Experiments for Requirement 2: compare the four search configurations on identical scenarios.

    python experiments.py --quick      # a few minutes
    python experiments.py              # full run (~15-25 minutes on a laptop)

Terminology follows Lecture 07. A *ply* is one move of one player; one game cycle = 2 plies
(MAX picks, then MIN picks). Time complexity is measured by the number of game-tree nodes visited
(compare O(b^m) for minimax and O(b^(m/2)) for alpha-beta with perfect ordering); wall-clock time is
reported next to it. Space complexity of the depth-first search is O(b*m), so it is reported as the
deepest ply reached.

Experiment A - exact search. Minimax Search and Alpha-Beta Search explore the game tree down to the
               TERMINAL states, as defined in the lecture. This is only feasible when few cycles are
               left, so the scenarios are endgame positions with m = 2, 4, 6, 8 plies remaining. Both
               must return the same minimax value; we compare the number of nodes.
               From an opening position (m = 400 plies) both are run once against a time budget to
               show that exact search is infeasible there.
Experiment B - depth-limited search. Heuristic Minimax and Heuristic Alpha-Beta replace the terminal
               test by CUTOFF-TEST(s, d) and UTILITY by EVAL. Same root states, same cutoff depths.
               Ablation: Heuristic Alpha-Beta without move ordering.
Experiment C - decision quality. All four configurations on the same endgame positions; the exact
               value of every root move is known from experiment A's full search, so we can check
               whether a depth-limited configuration still picks an optimal move.
Experiment D - playing strength: round-robin matches on symmetric maps, both sides swapped.

Results are written to results/ (CSV + summary.md + PNG charts if matplotlib is installed).
"""

import argparse
import csv
import os
import random
import sys
import time

from tank_battle.agents import (
    AlphaBetaAgent, HeuristicAlphaBetaAgent, HeuristicMinimaxAgent, MinimaxAgent, RandomAgent,
)
from tank_battle.core.constants import DRAW
from tank_battle.core.map_loader import load_map
from tank_battle.match import Match

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

# Full-depth search from an opening recurses one frame per ply (m = 400 plies).
sys.setrecursionlimit(10000)

EXACT_CONFIGS = [
    ("Minimax", MinimaxAgent),
    ("Alpha-Beta", AlphaBetaAgent),
]
HEURISTIC_CONFIGS = [
    ("Heuristic Minimax", HeuristicMinimaxAgent),
    ("Heuristic Alpha-Beta", HeuristicAlphaBetaAgent),
]
# Without a heuristic, a depth cutoff can only score a non-terminal state as 0 (a draw).
# That is H-Minimax with EVAL = 0, not the Minimax of the lecture, so it is always labelled as such.
ZERO_EVAL = " (cutoff, EVAL = 0)"


def effective_branching_factor(nodes, plies):
    """b* such that a uniform tree of depth `plies` has `nodes` nodes:
    nodes = 1 + b* + b*^2 + ... + b*^plies   (AIMA, effective branching factor). Solved by bisection."""
    if nodes <= 1 or plies <= 0:
        return 0.0
    if nodes <= plies + 1:
        return 1.0

    def total(b):
        return sum(b ** i for i in range(plies + 1))

    lo, hi = 1.0, float(nodes)
    for _ in range(100):
        mid = (lo + hi) / 2
        if total(mid) < nodes:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


# ---------------------------------------------------------------------- scenarios
def play_random(state, cycles, seed):
    """Reach a reproducible mid-game position by random play with a fixed seed."""
    rng = random.Random(seed)
    for _ in range(cycles):
        if state.is_terminal():
            break
        state = state.next_state(rng.choice(state.legal_actions(0)), rng.choice(state.legal_actions(1)))
    return state


def search_scenarios():
    combat = load_map("open")
    combat.tanks[0].row, combat.tanks[0].col = 5, 4     # tanks face each other on column 4
    combat.tanks[1].row, combat.tanks[1].col = 2, 4
    combat.tanks[0].hp, combat.tanks[1].hp = 3, 3
    return [
        ("classic-opening", load_map("classic")),
        ("duel-midgame", play_random(load_map("duel"), 12, seed=1)),
        ("open-combat", combat),
    ]


def with_remaining_cycles(state, cycles):
    """Copy of `state` in which the game ends (draw) after `cycles` more cycles."""
    s = state.deep_copy()
    s.max_turns = s.turn + cycles
    return s


def endgame_scenarios(count, remaining_cycles, max_attempts=5000):
    """Tactical positions a few cycles before the turn limit, so the full game tree can be searched:
    both tanks placed close to each other (Manhattan distance <= 4) with 1-2 HP, random facing.
    Only "interesting" positions are kept: at most half of the legal moves may be optimal.
    Returns (name, state, exact) where exact maps each root move to its true minimax value."""
    rng = random.Random(2026)
    scenarios = []
    for attempt in range(max_attempts):
        if len(scenarios) >= count:
            break
        s = load_map(rng.choice(["duel", "open"]))
        free = [(r, c) for r in range(s.height) for c in range(s.width) if s.is_free_for_tank(r, c)
                or s.tank_at(r, c) is not None]
        (r1, c1), (r2, c2) = rng.sample(free, 2)
        if abs(r1 - r2) + abs(c1 - c2) > 4:
            continue
        s.tanks[0].row, s.tanks[0].col, s.tanks[0].direction = r1, c1, rng.randrange(4)
        s.tanks[1].row, s.tanks[1].col, s.tanks[1].direction = r2, c2, rng.randrange(4)
        s.tanks[0].hp, s.tanks[1].hp = rng.randint(1, 2), rng.randint(1, 2)
        s.bases[0].hp, s.bases[1].hp = rng.randint(1, 3), rng.randint(1, 3)
        s.max_turns = s.turn + remaining_cycles
        exact = AlphaBetaAgent(0, depth=None).root_action_values(s)
        best = max(exact.values())
        if sum(abs(v - best) < 1e-6 for v in exact.values()) <= len(exact) // 2:
            scenarios.append(("endgame-%d" % attempt, s, exact))
    return scenarios


def stats_row(st, plies):
    return {"value": None if st.value is None else round(st.value, 2), "time_s": round(st.time, 4),
            "nodes": st.nodes, "states": st.states, "leaves": st.evaluations, "cutoffs": st.cutoffs,
            "max_ply": st.max_ply, "b_star": round(effective_branching_factor(st.nodes, plies), 2),
            "timed_out": st.timed_out}


# ---------------------------------------------------------------------- experiment A
def experiment_exact(scenarios, max_cycles, budget):
    """Minimax vs Alpha-Beta down to terminal states, m = 2 .. 2*max_cycles plies remaining."""
    rows = []
    for scen_name, state, _ in scenarios:
        for cycles in range(1, max_cycles + 1):
            root = with_remaining_cycles(state, cycles)
            values = {}
            for name, cls in EXACT_CONFIGS:
                agent = cls(0, depth=None, seed=0)
                agent.choose_action(root)
                st = agent.last_stats
                values[name] = st.value
                row = {"scenario": scen_name, "config": name, "remaining_cycles": cycles, "plies": 2 * cycles}
                row.update(stats_row(st, 2 * cycles))
                rows.append(row)
            same = abs(values["Minimax"] - values["Alpha-Beta"]) < 1e-9
            for row in rows[-2:]:
                row["same_value"] = same
            print("[A] %-12s m=%d plies  minimax=%8d nodes  alpha-beta=%7d nodes  same value=%s" % (
                scen_name, 2 * cycles, rows[-2]["nodes"], rows[-1]["nodes"], same))

    # Infeasibility of exact search from an opening position.
    opening = load_map("classic")
    plies = 2 * (opening.max_turns - opening.turn)
    infeasible = []
    for name, cls in EXACT_CONFIGS:
        agent = cls(0, depth=None, time_limit=budget, seed=0)
        agent.choose_action(opening)
        st = agent.last_stats
        infeasible.append({"scenario": "classic-opening", "config": name, "plies": plies, "nodes": st.nodes,
                           "max_ply": st.max_ply, "time_s": round(st.time, 2), "timed_out": st.timed_out})
        print("[A] classic-opening %-10s m=%d plies: %d nodes in %.1fs, timed out=%s" % (
            name, plies, st.nodes, st.time, st.timed_out))
    return rows, infeasible


# ---------------------------------------------------------------------- experiment B
class HeuristicAlphaBetaNoOrdering(HeuristicAlphaBetaAgent):
    """Ablation: same as Heuristic Alpha-Beta but without move ordering."""

    def __init__(self, player, **kwargs):
        super().__init__(player, move_ordering=False, **kwargs)


def experiment_depth_limited(depths, budget):
    rows = []
    configs = HEURISTIC_CONFIGS + [("H-Alpha-Beta (no ordering)", HeuristicAlphaBetaNoOrdering)]
    for scen_name, state in search_scenarios():
        for name, cls in configs:
            timed_out_before = False
            for depth in depths:
                plies = 2 * depth
                if timed_out_before:      # deeper search would only time out as well
                    rows.append({"scenario": scen_name, "config": name, "depth": depth, "plies": plies,
                                 "timed_out": True})
                    continue
                agent = cls(0, depth=depth, time_limit=budget, seed=0)
                action = agent.choose_action(state)
                st = agent.last_stats
                row = {"scenario": scen_name, "config": name, "depth": depth, "plies": plies,
                       "action": action.value}
                row.update(stats_row(st, plies))
                rows.append(row)
                timed_out_before = st.timed_out
                print("[B] %-16s %-26s d=%d (%2d plies) %8.3fs  nodes=%9d  cutoffs=%7d  value=%s%s" % (
                    scen_name, name, depth, plies, st.time, st.nodes, st.cutoffs, row["value"],
                    "  TIMEOUT" if st.timed_out else ""))
    return rows


# ---------------------------------------------------------------------- experiment C
def experiment_decision_quality(scenarios, depths):
    rows = []
    for scen_name, state, exact in scenarios:
        best = max(exact.values())
        good = sum(abs(v - best) < 1e-6 for v in exact.values())
        rows.append({"scenario": scen_name, "config": "Random (expected)", "depth": "-",
                     "optimal": good / len(exact), "time_s": 0.0, "nodes": 0})
        runs = [(name, cls, None) for name, cls in EXACT_CONFIGS]
        runs += [(name + ZERO_EVAL, cls, d) for name, cls in EXACT_CONFIGS for d in depths]
        runs += [(name, cls, d) for name, cls in HEURISTIC_CONFIGS for d in depths]
        for name, cls, depth in runs:
            agent = cls(0, depth=depth, seed=0)
            action = agent.choose_action(state)
            st = agent.last_stats
            optimal = abs(exact[action] - best) < 1e-6
            rows.append({
                "scenario": scen_name, "config": name, "depth": "terminal" if depth is None else depth,
                "action": action.value, "optimal": optimal, "exact_value_of_choice": exact[action],
                "best_value": best, "time_s": round(st.time, 4), "nodes": st.nodes,
            })
            print("[C] %-11s %-34s depth=%-8s %-10s optimal=%-5s %8.3fs nodes=%d" % (
                scen_name, name, "terminal" if depth is None else depth, action.value, optimal, st.time, st.nodes))
    return rows


# ---------------------------------------------------------------------- experiment D
def experiment_tournament(depth, maps, max_turns, include_id):
    players = [(name + ZERO_EVAL, (lambda cls: lambda p: cls(p, depth=depth, seed=p))(cls))
               for name, cls in EXACT_CONFIGS]
    players += [(name, (lambda cls: lambda p: cls(p, depth=depth, seed=p))(cls)) for name, cls in HEURISTIC_CONFIGS]
    players.append(("Random", lambda p: RandomAgent(p, seed=p)))
    if include_id:
        players.append(("H-Alpha-Beta ID 0.2s",
                        lambda p: HeuristicAlphaBetaAgent(p, depth=10, time_limit=0.2, iterative_deepening=True)))
    rows = []
    for i in range(len(players)):
        for j in range(i + 1, len(players)):
            for map_name in maps:
                for a, b in ((i, j), (j, i)):
                    na, fa = players[a]
                    nb, fb = players[b]
                    match = Match(load_map(map_name, max_turns), [fa(0), fb(1)])
                    start = time.perf_counter()
                    r = match.play()
                    w = r["winner"]
                    depth_reached = [sum(rec.stats[p].get("depth", 0) for rec in match.history)
                                     / max(1, len(match.history)) for p in (0, 1)]
                    rows.append({
                        "map": map_name, "p1": na, "p2": nb,
                        "winner": "draw" if w == DRAW else (na if w == 0 else nb),
                        "turns": r["turns"], "p1_tank_hp": r["tank_hp"][0], "p2_tank_hp": r["tank_hp"][1],
                        "p1_base_hp": r["base_hp"][0], "p2_base_hp": r["base_hp"][1],
                        "p1_avg_ms": round(r["avg_time"][0] * 1000, 2), "p2_avg_ms": round(r["avg_time"][1] * 1000, 2),
                        "p1_max_ms": round(r["max_time"][0] * 1000, 2), "p2_max_ms": round(r["max_time"][1] * 1000, 2),
                        "p1_avg_nodes": round(r["avg_nodes"][0], 1), "p2_avg_nodes": round(r["avg_nodes"][1], 1),
                        "p1_avg_depth": round(depth_reached[0], 2), "p2_avg_depth": round(depth_reached[1], 2),
                    })
                    print("[D] %-6s %-32s vs %-32s -> %-32s turns=%3d (%.1fs)" % (
                        map_name, na, nb, rows[-1]["winner"], r["turns"], time.perf_counter() - start))
    return rows, [p[0] for p in players]


# ---------------------------------------------------------------------- reporting
def write_csv(path, rows):
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def md_table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return "\n".join(lines)


def mean(values):
    values = list(values)
    return sum(values) / len(values) if values else 0.0


def summarize(rows_a, infeasible, rows_b, rows_c, rows_d, names_d, args):
    out = ["# Experiment results", "",
           "Generated by `python experiments.py%s`." % (" --quick" if args.quick else ""), "",
           "- A *ply* is one move of one player. One game cycle = 2 plies (MAX moves, then MIN moves).",
           "- **Nodes** = game-tree nodes visited (MAX nodes + MIN nodes, root included). This is the measure of "
           "time complexity; seconds are given next to it.",
           "- **b\\*** = effective branching factor: the b for which a uniform tree of the same depth has the same "
           "number of nodes, `nodes = 1 + b* + b*^2 + ... + b*^m`.",
           "- **Max ply** = deepest level reached. Depth-first search keeps one path in memory, so space is "
           "O(b·m) and grows with this number, not with the number of nodes.",
           "- Per-search time budget: %ss." % args.budget, ""]

    if rows_a:
        n_pos = len({r["scenario"] for r in rows_a})
        out += ["## A. Exact search: Minimax vs Alpha-Beta down to terminal states (%d endgame positions)" % n_pos,
                "",
                "The whole remaining game tree is searched; leaves are scored with UTILITY only.", ""]
        table = []
        for plies in sorted({r["plies"] for r in rows_a}):
            mm = [r for r in rows_a if r["plies"] == plies and r["config"] == "Minimax"]
            ab = [r for r in rows_a if r["plies"] == plies and r["config"] == "Alpha-Beta"]
            n_mm, n_ab = mean(r["nodes"] for r in mm), mean(r["nodes"] for r in ab)
            table.append([plies, "%.0f" % n_mm, "%.0f" % n_ab, "%.1fx" % (n_mm / n_ab),
                          "%.2f" % effective_branching_factor(n_mm, plies),
                          "%.2f" % effective_branching_factor(n_ab, plies),
                          "%.4f" % mean(r["time_s"] for r in mm), "%.4f" % mean(r["time_s"] for r in ab),
                          max(r["max_ply"] for r in mm),
                          "%d/%d" % (sum(r["same_value"] for r in mm), len(mm))])
        out += [md_table(["m (plies)", "Minimax nodes", "Alpha-Beta nodes", "Reduction", "b* Minimax",
                          "b* Alpha-Beta", "Minimax time (s)", "Alpha-Beta time (s)", "Max ply",
                          "Same minimax value"], table), "",
                "Nodes and times are averages over the positions.", ""]
        if infeasible:
            out += ["From the opening position of the classic map the tree is m = %d plies deep. "
                    "Exact search does not finish:" % infeasible[0]["plies"], ""]
            out += [md_table(["Config", "m (plies)", "Nodes visited before the budget ran out", "Max ply", "Time (s)",
                              "Finished"],
                             [[r["config"], r["plies"], r["nodes"], r["max_ply"], r["time_s"],
                               "no" if r["timed_out"] else "yes"] for r in infeasible]), ""]

    if rows_b:
        out += ["## B. Depth-limited search: Heuristic Minimax vs Heuristic Alpha-Beta on identical root states", "",
                "CUTOFF-TEST stops at depth d (in cycles); the cutoff states are scored with EVAL.", ""]
        for scen in sorted({r["scenario"] for r in rows_b}, key=[r["scenario"] for r in rows_b].index):
            out += ["### %s" % scen, ""]
            table = []
            for r in rows_b:
                if r["scenario"] != scen:
                    continue
                if "nodes" not in r:
                    table.append([r["config"], r["depth"], r["plies"], "not run (shallower depth timed out)"]
                                 + ["—"] * 6)
                elif r["timed_out"]:
                    table.append([r["config"], r["depth"], r["plies"], "> %d (timeout)" % r["nodes"], "—", "—",
                                  "—", r["max_ply"], "> %.0f" % r["time_s"], "—"])
                else:
                    table.append([r["config"], r["depth"], r["plies"], r["nodes"], r["leaves"], r["cutoffs"],
                                  r["b_star"], r["max_ply"], "%.4f" % r["time_s"], r["value"]])
            out += [md_table(["Config", "Depth d (cycles)", "Plies", "Nodes", "Leaves evaluated", "Cutoffs", "b*",
                              "Max ply", "Time (s)", "Value"], table), ""]

    if rows_c:
        out += ["## C. Decision quality on the endgame positions (%d positions)" % len({r["scenario"] for r in rows_c}),
                "",
                "A move is *optimal* if its exact minimax value (full search of experiment A) equals the best one. "
                "\"%s\" is a depth cutoff without a heuristic: every non-terminal cutoff state is worth 0." % ZERO_EVAL.strip(),
                ""]
        groups = {}
        for r in rows_c:
            groups.setdefault((r["config"], str(r["depth"])), []).append(r)
        table = []
        for (config, depth), rs in groups.items():
            table.append([config, depth, "%.1f/%d" % (sum(r["optimal"] for r in rs), len(rs)),
                          "%.4f" % mean(r["time_s"] for r in rs), int(mean(r["nodes"] for r in rs))])
        out += [md_table(["Config", "Depth (cycles)", "Optimal moves", "Avg time (s)", "Avg nodes"], table), ""]

    if rows_d:
        out += ["## D. Round-robin matches (cutoff depth %d cycles, sides swapped, maps: %s)" % (
            args.tournament_depth, ", ".join(args.maps)), ""]
        table = []
        for name in names_d:
            games = [r for r in rows_d if name in (r["p1"], r["p2"])]
            wins = sum(r["winner"] == name for r in games)
            draws = sum(r["winner"] == "draw" for r in games)
            times = [r["p1_avg_ms"] if r["p1"] == name else r["p2_avg_ms"] for r in games]
            maxes = [r["p1_max_ms"] if r["p1"] == name else r["p2_max_ms"] for r in games]
            nodes = [r["p1_avg_nodes"] if r["p1"] == name else r["p2_avg_nodes"] for r in games]
            table.append([name, len(games), wins, draws, len(games) - wins - draws,
                          "%.1f" % mean(times), "%.1f" % max(maxes), "%.0f" % mean(nodes)])
        out += [md_table(["Agent", "Games", "Wins", "Draws", "Losses", "Avg ms/move", "Max ms/move",
                          "Avg nodes/move"], table), ""]
    with open(os.path.join(RESULTS_DIR, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(out))


def plot(rows_a, rows_b):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed - skipping charts")
        return
    if rows_a:
        fig, ax = plt.subplots(figsize=(5.5, 4))
        plies = sorted({r["plies"] for r in rows_a})
        for name, style in (("Minimax", "s-"), ("Alpha-Beta", "o--")):
            ax.plot(plies, [mean(r["nodes"] for r in rows_a if r["plies"] == m and r["config"] == name)
                            for m in plies], style, label=name)
        ax.set_yscale("log")
        ax.set_xticks(plies)
        ax.set_xlabel("Depth of the game tree m (plies)")
        ax.set_ylabel("Nodes visited (average)")
        ax.set_title("Exact search to terminal states")
        ax.grid(True, alpha=0.3)
        ax.legend()
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "exact_search.png"), dpi=150)
        plt.close(fig)
    for scen in sorted({r["scenario"] for r in rows_b}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4))
        for name in sorted({r["config"] for r in rows_b}, key=[r["config"] for r in rows_b].index):
            rs = [r for r in rows_b if r["scenario"] == scen and r["config"] == name and "nodes" in r
                  and not r["timed_out"]]
            if not rs:
                continue
            style = "--" if "Alpha" in name else "-"
            marker = "o" if name.startswith("Heuristic") else "s"
            axes[0].plot([r["plies"] for r in rs], [r["nodes"] for r in rs], style, marker=marker, label=name)
            axes[1].plot([r["plies"] for r in rs], [r["time_s"] for r in rs], style, marker=marker, label=name)
        for ax, label in ((axes[0], "Nodes visited"), (axes[1], "Time (s)")):
            ax.set_yscale("log")
            ax.set_xlabel("Cutoff depth (plies)")
            ax.set_ylabel(label)
            ax.grid(True, alpha=0.3)
        axes[0].legend(fontsize=8)
        fig.suptitle("Depth-limited search - %s" % scen)
        fig.tight_layout()
        fig.savefig(os.path.join(RESULTS_DIR, "search_cost_%s.png" % scen), dpi=150)
        plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--quick", action="store_true", help="smaller settings for a fast run")
    parser.add_argument("--budget", type=float, default=None, help="time budget per search (s)")
    parser.add_argument("--tournament-depth", type=int, default=2)
    parser.add_argument("--skip", default="", help="experiments to skip, e.g. 'D' or 'BD'")
    args = parser.parse_args()
    if args.budget is None:
        args.budget = 10.0 if args.quick else 30.0
    depths = [1, 2, 3] if args.quick else [1, 2, 3, 4, 5]
    args.maps = ["duel"] if args.quick else ["duel", "open"]
    os.makedirs(RESULTS_DIR, exist_ok=True)

    rows_a = infeasible = rows_b = rows_c = rows_d = []
    names_d = []
    endgames = []
    if "A" not in args.skip or "C" not in args.skip:
        endgames = endgame_scenarios(4 if args.quick else 10, 4)
    if "A" not in args.skip:
        rows_a, infeasible = experiment_exact(endgames, 3 if args.quick else 4, args.budget)
        write_csv(os.path.join(RESULTS_DIR, "exp_a_exact_search.csv"), rows_a + infeasible)
    if "B" not in args.skip:
        rows_b = experiment_depth_limited(depths, args.budget)
        write_csv(os.path.join(RESULTS_DIR, "exp_b_depth_limited.csv"), rows_b)
    if "C" not in args.skip:
        rows_c = experiment_decision_quality(endgames, [1, 2, 3])
        write_csv(os.path.join(RESULTS_DIR, "exp_c_decision_quality.csv"), rows_c)
    if "D" not in args.skip:
        rows_d, names_d = experiment_tournament(args.tournament_depth, args.maps, 100, include_id=not args.quick)
        write_csv(os.path.join(RESULTS_DIR, "exp_d_tournament.csv"), rows_d)
    plot(rows_a, rows_b)
    summarize(rows_a, infeasible, rows_b, rows_c, rows_d, names_d, args)
    print("\nResults written to", RESULTS_DIR)


if __name__ == "__main__":
    main()
