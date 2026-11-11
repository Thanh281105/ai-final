"""Experiments for Requirement 2: correctness, stability and effectiveness of the solver.

    python experiments.py           # full run (~1-2 minutes)
    python experiments.py --quick   # skips the slowest configurations

A. Ablation: the same puzzle solved by 7 solver configurations, from plain backtracking up to
   MAC + MRV/Degree + LCV + initial AC-3.
   Time cost is counted in search-tree nodes, backtracks and constraint checks (wall-clock time is
   only a secondary figure). Space cost is counted in the quantities the theory talks about: the
   maximum depth of the search tree (O(n)) and the maximum length of the trail (O(n*d)).
B. Correctness: every solution is re-checked by an independent rule checker (KakuroBoard.is_solution),
   and the search continues for a 2nd solution to prove the solution is unique.
C. Stability: the full solver with random tie-breaking (30 seeds) on the complex board, plus
   20 randomly generated boards (sizes 7x7..12x12), comparing FC and MAC.
D. Propagation power: how much the initial AC-3 shrinks the domains / search space.
"""

import argparse
import csv
import math
import os
import statistics
import time

from kakuro.core import KakuroBoard, load_puzzle
from kakuro.core.generator import generate
from kakuro.csp import KakuroCSP, SolverConfig, solve
from kakuro.csp.solver import BacktrackingSolver
from kakuro.csp.inference import AC3

RESULTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")

ABLATION = [
    ("1. BT", SolverConfig("Static", "Ascending", "None", False)),
    ("2. BT + MRV", SolverConfig("MRV", "Ascending", "None", False)),
    ("3. BT + FC", SolverConfig("Static", "Ascending", "FC", False)),
    ("4. BT + FC + MRV/Deg", SolverConfig("MRV+Degree", "Ascending", "FC", False)),
    ("5. BT + FC + MRV/Deg + LCV", SolverConfig("MRV+Degree", "LCV", "FC", False)),
    ("6. BT + MAC + MRV/Deg", SolverConfig("MRV+Degree", "Ascending", "MAC", False)),
    ("7. BT + MAC + MRV/Deg + LCV + AC3-pre", SolverConfig("MRV+Degree", "LCV", "MAC", True)),
]
SLOW = {"2. BT + MRV"}
FULL = ABLATION[-1][1]


def log(lines, text=""):
    print(text)
    lines.append(text)


def write_csv(name, rows):
    if not rows:
        return
    with open(os.path.join(RESULTS, name), "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def table(lines, header, rows):
    log(lines, "| " + " | ".join(header) + " |")
    log(lines, "|" + "|".join("---" for _ in header) + "|")
    for r in rows:
        log(lines, "| " + " | ".join(str(x) for x in r) + " |")
    log(lines)


def timed_solve(board, config, repeats):
    """Solve `repeats` times; the counters are deterministic, the time is the median."""
    times, result = [], None
    for _ in range(repeats):
        result = solve(board, config)
        times.append(result.stats.time)
        if result.stats.time > 5:
            break
    return result, statistics.median(times)


# ---------------------------------------------------------------------------- A
def experiment_a(lines, quick, time_limit):
    log(lines, "## A. Ablation: from plain backtracking to MAC + heuristics\n")
    rows = []
    for puzzle in ("example_5x5", "complex_9x9"):
        board = load_puzzle(puzzle)
        log(lines, "### {}  ({} variables, {} constraints)\n".format(
            puzzle, len(board.white_cells), len(board.runs)))
        md = []
        for name, cfg in ABLATION:
            if quick and name in SLOW and puzzle == "complex_9x9":
                md.append([name, "skipped (--quick)"] + [""] * 8)
                continue
            cfg = cfg.copy(time_limit=time_limit)
            result, t = timed_solve(board, cfg, repeats=3)
            s = result.stats
            valid = result.solution is not None and board.is_solution(result.solution)
            rows.append({"puzzle": puzzle, "config": name, "status": result.status, "valid": valid,
                         "nodes": s.nodes, "backtracks": s.backtracks, "rejected": s.rejected,
                         "revisions": s.revisions, "checks": s.checks, "prunings": s.prunings,
                         "max_depth": s.max_depth, "max_trail": s.max_trail, "time_s": round(t, 5)})
            md.append([name, result.status + (" ✓" if valid else " ✗"), s.nodes, s.backtracks, s.rejected,
                       s.revisions, s.checks, s.max_depth, s.max_trail, "{:.4f}".format(t)])
        table(lines, ["Config", "Status", "Nodes", "Backtracks", "Rejected", "Revisions", "Checks", "Max depth",
                      "Max trail", "Time (s)"], md)
        log(lines, "Nodes = assignments tried (nodes of the search tree). Checks = constraint checks. "
                   "Max depth = deepest level reached (n = {} when solved). Max trail = most removed values "
                   "remembered at once for undoing (bounded by n·d = {}).\n".format(
                       len(board.white_cells), 9 * len(board.white_cells)))
    write_csv("exp_a_ablation.csv", rows)
    return rows


# ---------------------------------------------------------------------------- B
def experiment_b(lines):
    log(lines, "## B. Correctness and uniqueness (full solver, search continues for a 2nd solution)\n")
    md, rows = [], []
    for puzzle in ("example_5x5", "complex_9x9"):
        board = load_puzzle(puzzle)
        result = solve(board, FULL.copy(max_solutions=2))
        valid = all(board.is_solution(s) for s in result.solutions)
        unique = len(result.solutions) == 1 and result.status != "limit reached"
        rows.append({"puzzle": puzzle, "solutions": len(result.solutions), "all_valid": valid, "unique": unique,
                     "nodes": result.stats.nodes, "time_s": round(result.stats.time, 5)})
        md.append([puzzle, len(result.solutions), valid, unique, result.stats.nodes,
                   "{:.4f}".format(result.stats.time)])
        log(lines, "{}:\n```\n{}\n```".format(puzzle, board.format_solution(result.solution)))
    log(lines)
    table(lines, ["Puzzle", "Solutions", "All valid", "Unique", "Nodes (whole tree)", "Time (s)"], md)
    write_csv("exp_b_correctness.csv", rows)


# ---------------------------------------------------------------------------- C
def experiment_c(lines, seeds, n_random):
    log(lines, "## C. Stability\n")
    board = load_puzzle("complex_9x9")
    rows, solutions = [], set()
    for cfg_name, base in (("FC + MRV/Deg + LCV", ABLATION[4][1]), ("MAC + MRV/Deg + LCV + AC3-pre", FULL),
                           ("MAC + MRV/Deg + LCV (no pre)", FULL.copy(preprocess=False))):
        for seed in range(seeds):
            r = solve(board, base.copy(seed=seed, time_limit=20))
            if r.solution:
                solutions.add(tuple(sorted(r.solution.items())))
            rows.append({"config": cfg_name, "seed": seed, "status": r.status,
                         "valid": bool(r.solution) and board.is_solution(r.solution),
                         "nodes": r.stats.nodes, "backtracks": r.stats.backtracks, "time_s": r.stats.time})
    write_csv("exp_c_seeds.csv", rows)
    log(lines, "### C1. complex_9x9, {} random tie-breaking seeds per configuration (limit 20 s/run)\n".format(seeds))
    md = []
    for cfg_name in dict.fromkeys(r["config"] for r in rows):
        sub = [r for r in rows if r["config"] == cfg_name]
        nodes = [r["nodes"] for r in sub]
        times = [r["time_s"] * 1000 for r in sub]
        md.append([cfg_name, "{}/{}".format(sum(r["valid"] for r in sub), len(sub)),
                   "{:.1f} ± {:.1f}".format(statistics.mean(nodes), statistics.pstdev(nodes)),
                   "{}–{}".format(min(nodes), max(nodes)),
                   "{:.1f} ± {:.1f}".format(statistics.mean(times), statistics.pstdev(times)),
                   "{:.1f}".format(max(times))])
    table(lines, ["Config", "Solved & valid", "Nodes mean ± sd", "Nodes min–max", "Time ms mean ± sd", "Time ms max"], md)
    log(lines, "Distinct solutions over all runs: {} (the puzzle has a unique solution).\n".format(len(solutions)))

    log(lines, "### C2. {} randomly generated boards (always solvable, may have several solutions; limit 10 s/run)\n"
        .format(n_random))
    sizes = [7, 8, 9, 10, 11, 12]
    rand_rows = []
    for i in range(n_random):
        n = sizes[i % len(sizes)]
        text, _ = generate(n, n, seed=1000 + i)
        rb = KakuroBoard.from_text(text, "gen_{}x{}_{}".format(n, n, 1000 + i))
        for cfg_name, cfg in (("FC + MRV/Deg", ABLATION[3][1]), ("MAC + MRV/Deg + LCV + AC3-pre", FULL)):
            r = solve(rb, cfg.copy(time_limit=10))
            rand_rows.append({"board": rb.name, "variables": len(rb.white_cells), "config": cfg_name,
                              "status": r.status, "valid": bool(r.solution) and rb.is_solution(r.solution),
                              "nodes": r.stats.nodes, "backtracks": r.stats.backtracks,
                              "time_s": round(r.stats.time, 5)})
    write_csv("exp_c_random_boards.csv", rand_rows)
    md = []
    for cfg_name in ("FC + MRV/Deg", "MAC + MRV/Deg + LCV + AC3-pre"):
        sub = [r for r in rand_rows if r["config"] == cfg_name]
        md.append([cfg_name, "{}/{}".format(sum(r["valid"] for r in sub), len(sub)),
                   "{:.0f}".format(statistics.mean(r["nodes"] for r in sub)),
                   "{:.0f}".format(statistics.mean(r["backtracks"] for r in sub)),
                   max(r["backtracks"] for r in sub),
                   "{:.1f}".format(1000 * statistics.mean(r["time_s"] for r in sub)),
                   "{:.1f}".format(1000 * max(r["time_s"] for r in sub))])
    table(lines, ["Config", "Solved & valid", "Nodes mean", "Backtracks mean", "Backtracks max", "Time ms mean",
                  "Time ms max"], md)
    return rows, rand_rows


# ---------------------------------------------------------------------------- D
def experiment_d(lines):
    log(lines, "## D. How much does the initial AC-3 (GAC) shrink the problem?\n")
    md = []
    for puzzle in ("example_5x5", "complex_9x9"):
        board = load_puzzle(puzzle)
        solver = BacktrackingSolver(board, FULL)
        before = sum(math.log10(len(d)) for d in solver.domains.values())
        t = time.perf_counter()
        AC3(solver).run(AC3(solver).all_arcs())
        t = time.perf_counter() - t
        after = sum(math.log10(len(d)) for d in solver.domains.values())
        fixed = sum(1 for d in solver.domains.values() if len(d) == 1)
        md.append([puzzle, len(board.white_cells), "10^{:.1f}".format(before), "10^{:.1f}".format(after),
                   "{}/{}".format(fixed, len(board.white_cells)), solver.stats.prunings, solver.stats.revisions,
                   "{:.4f}".format(t)])
    table(lines, ["Puzzle", "Variables", "Search space before", "After AC-3", "Cells fixed", "Values pruned",
                  "Revisions", "Time (s)"], md)
    log(lines, "Search space = product of the domain sizes (∏|D(x)|).\n")


def plot(ablation_rows):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("(matplotlib not installed: charts skipped)")
        return
    rows = [r for r in ablation_rows if r["puzzle"] == "complex_9x9"]
    if not rows:
        return
    names = [r["config"] for r in rows]
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))
    for ax, key, title in ((axes[0], "nodes", "Search nodes (log scale)"), (axes[1], "time_s", "Time in seconds (log scale)")):
        values = [max(r[key], 1e-5) for r in rows]
        ax.barh(names, values, color="#3b6fb6")
        ax.set_xscale("log")
        ax.invert_yaxis()
        ax.set_title(title)
        for i, v in enumerate(values):
            ax.text(v, i, " {:g}".format(round(v, 4)), va="center", fontsize=8)
    axes[1].set_yticklabels([])
    fig.suptitle("complex_9x9: effect of propagation and heuristics")
    fig.tight_layout()
    path = os.path.join(RESULTS, "ablation_complex_9x9.png")
    fig.savefig(path, dpi=130)
    print("Saved", path)


def main():
    p = argparse.ArgumentParser(description="Requirement 2 experiments")
    p.add_argument("--quick", action="store_true")
    p.add_argument("--time-limit", type=float, default=120)
    args = p.parse_args()
    os.makedirs(RESULTS, exist_ok=True)
    lines = ["# Kakuro CSP — experiment results", "",
             "Generated by `python experiments.py{}`. Times are measured on the machine that ran the script."
             .format(" --quick" if args.quick else ""), ""]
    rows = experiment_a(lines, args.quick, args.time_limit)
    experiment_b(lines)
    experiment_c(lines, seeds=10 if args.quick else 30, n_random=6 if args.quick else 20)
    experiment_d(lines)
    with open(os.path.join(RESULTS, "summary.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    plot(rows)
    print("Results written to", RESULTS)


if __name__ == "__main__":
    main()
