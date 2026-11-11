"""Xuất kết quả thực nghiệm ra CSV / JSON / Markdown."""
from __future__ import annotations

import csv
import json
import platform
import sys
from pathlib import Path
from typing import Dict, List


class ReportWriter:
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)
        self.out_dir.mkdir(parents=True, exist_ok=True)

    def write_csv(self, name: str, rows: List[Dict]) -> Path:
        path = self.out_dir / f"{name}.csv"
        if rows:
            with path.open("w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
        return path

    def write_json(self, name: str, rows: List[Dict]) -> Path:
        path = self.out_dir / f"{name}.json"
        path.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    @staticmethod
    def environment() -> str:
        return f"Python {sys.version.split()[0]} · {platform.platform()} · {platform.processor() or platform.machine()}"

    ALGO_NAMES = {
        "standard": "Chuẩn (chọn ngẫu nhiên biến xung đột)",
        "heuristic": "Heuristic chọn biến đề xuất",
        "most_conflicted_no_tabu": "Biến xung đột nhiều nhất, không tabu",
        "enhanced": "Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart",
    }

    def _mc_table(self, rows: List[Dict]) -> List[str]:
        std = {r["n"]: r for r in rows if r["algorithm"] == "standard"}
        lines = [
            "| N | Thuật toán | Tỉ lệ thành công | Số bước TB | Số bước trung vị | Số bước lớn nhất | "
            "Trung vị so với chuẩn | Thời gian TB (ms) |",
            "|---:|:---|---:|---:|---:|---:|---:|---:|",
        ]
        for r in rows:
            base = std.get(r["n"])
            ratio = "—"
            if base and r["algorithm"] != "standard" and base["median_steps"]:
                ratio = f"{100 * r['median_steps'] / base['median_steps']:.0f}%"
            lines.append(
                f"| {r['n']} | {self.ALGO_NAMES.get(r['algorithm'], r['algorithm'])} | "
                f"{100 * r['success_rate']:.0f}% | {r['avg_steps']:.1f} | {r['median_steps']:.1f} | "
                f"{r.get('max_steps_seen', '—')} | {ratio} | {r['avg_time_ms']:.2f} |"
            )
        lines.append("")
        return lines

    def write_markdown(self, sat_rows: List[Dict], mc_rows: List[Dict], ablation_rows: List[Dict] = ()) -> Path:
        lines = ["# Kết quả thực nghiệm N-Queens", "", f"Môi trường: {self.environment()}", ""]
        if sat_rows:
            lines += [
                "## 1. Glucose3 (PySAT)",
                "",
                "Số mệnh đề CNF và các bộ đếm của Glucose3 (decisions, propagations, conflicts) là tất định; "
                "thời gian phụ thuộc máy. Solve = thời gian của `Glucose3.solve()`.",
                "",
                "| N | Số biến | Số mệnh đề CNF | Solve (ms) | Sinh CNF (ms) | Nạp (ms) | Tổng (ms) | "
                "Decisions | Propagations | Conflicts | Nghiệm hợp lệ |",
                "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|",
            ]
            for r in sat_rows:
                lines.append(
                    f"| {r['n']} | {r['variables']} | {r['clauses']} | {r['solve_ms']:.2f} | {r['build_ms']:.2f} | "
                    f"{r['load_ms']:.2f} | {r['total_ms']:.2f} | {r.get('decisions', '—')} | "
                    f"{r.get('propagations', '—')} | {r.get('conflicts', '—')} | "
                    f"{'✓' if r['valid'] else '✗'} |"
                )
            lines.append("")
        if mc_rows:
            runs = mc_rows[0].get("runs", "?")
            lines += [
                "## 2. Min-Conflicts chuẩn vs heuristic chọn biến đề xuất",
                "",
                f"{runs} lần chạy cho mỗi N, cùng bộ seed nên hai bản xuất phát từ cùng phép gán ban đầu. "
                "Hai bản chỉ khác nhau ở bước chọn biến. Một bước = một lần lặp của MIN-CONFLICTS "
                "(một lần gán lại một biến).",
                "",
            ]
            lines += self._mc_table(mc_rows)
        if ablation_rows:
            lines += [
                "## 3. Ablation: đóng góp của từng thành phần",
                "",
                "Dòng cuối dùng thêm các kỹ thuật ngoài phạm vi chọn biến, đưa vào để tham khảo, "
                "không thuộc phép so sánh chính ở mục 2.",
                "",
            ]
            lines += self._mc_table(ablation_rows)
        path = self.out_dir / "report.md"
        path.write_text("\n".join(lines), encoding="utf-8")
        return path


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from nqueens_solver.gui.server import serve

    serve(hash_tab="exp")
