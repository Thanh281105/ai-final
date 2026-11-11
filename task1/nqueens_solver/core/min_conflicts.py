"""Thuật toán Min-Conflicts (Lecture 08) và heuristic chọn biến đề xuất.

Mô hình CSP: biến X_r = cột của quân hậu ở hàng r (r = 0..N-1), miền D = {0..N-1},
ràng buộc: hai hậu bất kỳ không cùng cột, không cùng đường chéo. Trạng thái của tìm kiếm
cục bộ là một phép gán ĐẦY ĐỦ (mỗi hàng đúng một hậu).

    function MIN-CONFLICTS(csp, max_steps)                       (AIMA, Lecture 08)
        current <- một phép gán đầy đủ ban đầu
        for i = 1 to max_steps:
            if current là nghiệm: return current
            var   <- một biến ĐANG XUNG ĐỘT, chọn ngẫu nhiên          <- VariableSelector
            value <- giá trị v của var làm CONFLICTS(var, v) nhỏ nhất  <- ValueSelector
            gán var = value trong current
        return failure

CONFLICTS(var, v) = số ràng buộc bị vi phạm nếu var = v = số hậu khác tấn công ô đó.
Nó được cập nhật tăng dần (O(1) mỗi lần đặt/bỏ quân) nhờ 3 mảng đếm cột / chéo chính / chéo phụ.

Ba "chiến lược" có thể hoán đổi (Strategy pattern):
  * Initializer       : phép gán đầy đủ ban đầu
  * VariableSelector  : chọn biến xung đột
  * ValueSelector     : chọn giá trị cho biến đó

  standard()   = RandomInitializer + RandomConflictedSelector + MinConflictsValue
  heuristic()  = RandomInitializer + MostConflictedTabuSelector + MinConflictsValue
                 -> chỉ khác bản chuẩn ở BƯỚC CHỌN BIẾN (heuristic đề xuất của bài)
  enhanced()   = thêm các kỹ thuật ngoài phạm vi chọn biến (khởi tạo tham lam, tabu trên
                 giá trị, khởi động lại) - chỉ dùng cho phần ablation.
"""
from __future__ import annotations

import random
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from nqueens_solver.core.board import Board
else:
    from .board import Board

INF = 10 ** 9


def argmin_random(values: Sequence[int], rng: random.Random) -> int:
    """Chỉ số của giá trị nhỏ nhất; hòa thì chọn ngẫu nhiên."""
    best_value = min(values)
    best = [i for i, v in enumerate(values) if v == best_value]
    return best[0] if len(best) == 1 else rng.choice(best)


# ---------------------------------------------------------------------------
# Trạng thái
# ---------------------------------------------------------------------------
class ConflictState:
    """Trạng thái N hậu (mỗi hàng một hậu) với đếm xung đột tăng dần."""

    def __init__(self, n: int):
        self.n = n
        self.cols: List[int] = [-1] * n
        self.col_cnt = [0] * n
        self.d1 = [0] * (2 * n - 1)  # r - c + n - 1
        self.d2 = [0] * (2 * n - 1)  # r + c
        self.total = 0  # tổng số cặp hậu tấn công nhau

    def cost(self, r: int, c: int) -> int:
        """Số hậu (khác) sẽ tấn công một hậu đặt tại (r, c). Hàng r phải đang trống."""
        return self.col_cnt[c] + self.d1[r - c + self.n - 1] + self.d2[r + c]

    def costs_for_row(self, r: int) -> List[int]:
        n, cc, d1, d2 = self.n, self.col_cnt, self.d1, self.d2
        base = r + n - 1
        return [cc[c] + d1[base - c] + d2[r + c] for c in range(n)]

    def place(self, r: int, c: int) -> None:
        self.total += self.cost(r, c)
        self.col_cnt[c] += 1
        self.d1[r - c + self.n - 1] += 1
        self.d2[r + c] += 1
        self.cols[r] = c

    def remove(self, r: int) -> None:
        c = self.cols[r]
        self.col_cnt[c] -= 1
        self.d1[r - c + self.n - 1] -= 1
        self.d2[r + c] -= 1
        self.total -= self.cost(r, c)
        self.cols[r] = -1

    def queen_conflicts(self, r: int) -> int:
        """Số hậu khác đang tấn công hậu ở hàng r."""
        c = self.cols[r]
        return self.col_cnt[c] + self.d1[r - c + self.n - 1] + self.d2[r + c] - 3

    def all_queen_conflicts(self) -> List[int]:
        n, cols, cc, d1, d2 = self.n, self.cols, self.col_cnt, self.d1, self.d2
        base = n - 1
        return [cc[c] + d1[r - c + base] + d2[r + c] - 3 for r, c in enumerate(cols)]


# ---------------------------------------------------------------------------
# Chiến lược khởi tạo
# ---------------------------------------------------------------------------
class Initializer(ABC):
    @abstractmethod
    def initialize(self, state: ConflictState, rng: random.Random) -> None: ...


class RandomInitializer(Initializer):
    """Mỗi hàng đặt hậu ở một cột ngẫu nhiên (chuẩn)."""

    def initialize(self, state: ConflictState, rng: random.Random) -> None:
        for r in range(state.n):
            state.place(r, rng.randrange(state.n))


class GreedyInitializer(Initializer):
    """Ngoài phạm vi chọn biến (chỉ dùng trong ablation): đặt lần lượt từng hàng (thứ tự ngẫu nhiên) vào cột ít xung đột nhất
    với các hậu đã đặt; hòa thì chọn ngẫu nhiên. Trạng thái đầu đã gần nghiệm."""

    def initialize(self, state: ConflictState, rng: random.Random) -> None:
        rows = list(range(state.n))
        rng.shuffle(rows)
        for r in rows:
            state.place(r, argmin_random(state.costs_for_row(r), rng))


# ---------------------------------------------------------------------------
# Chiến lược chọn biến
# ---------------------------------------------------------------------------
class VariableSelector(ABC):
    def reset(self, n: int) -> None:
        """Gọi lại mỗi khi bắt đầu một lần chạy hoặc khởi động lại."""

    @abstractmethod
    def select(self, state: ConflictState, rng: random.Random) -> Optional[int]: ...


class RandomConflictedSelector(VariableSelector):
    """Chuẩn: chọn ngẫu nhiên một hậu đang bị tấn công."""

    def select(self, state: ConflictState, rng: random.Random) -> Optional[int]:
        conflicted = [r for r, k in enumerate(state.all_queen_conflicts()) if k > 0]
        return rng.choice(conflicted) if conflicted else None


class MaxConflictedSelector(VariableSelector):
    """Chỉ dùng trong ablation: chọn biến vi phạm NHIỀU ràng buộc NHẤT (hòa -> ngẫu nhiên).

    Đứng một mình thì dễ lặp vô hạn: nếu biến xung đột nhiều nhất đã ở giá trị min-conflicts
    của nó thì nó được chọn lại mãi mà trạng thái không đổi."""

    def select(self, state: ConflictState, rng: random.Random) -> Optional[int]:
        counts = state.all_queen_conflicts()
        top = max(counts)
        if top <= 0:
            return None
        best = [r for r, k in enumerate(counts) if k == top]
        return best[0] if len(best) == 1 else rng.choice(best)


class MostConflictedTabuSelector(VariableSelector):
    """HEURISTIC CHỌN BIẾN ĐỀ XUẤT: "most-conflicted variable" + danh sách tabu trên biến.

    1. Trong các biến đang xung đột, chọn biến vi phạm nhiều ràng buộc nhất
       (hậu bị nhiều hậu khác tấn công nhất); hòa -> ngẫu nhiên.
       Ý tưởng giống heuristic bậc (degree) / fail-first của Lecture 08: xử lý trước biến
       dính tới nhiều ràng buộc nhất, vì gán lại nó có thể xoá nhiều xung đột nhất.
    2. Biến vừa được chọn bị cấm chọn lại trong `tenure` bước kế tiếp.
       Nhờ vậy tránh được vòng lặp của MaxConflictedSelector và buộc thuật toán sửa
       các biến xung đột khác quanh "điểm nóng".
    Nếu mọi biến xung đột đều đang bị cấm thì bỏ cấm cho bước đó.
    """

    def __init__(self, tenure: Optional[int] = None):
        self._fixed_tenure = tenure
        self.tenure = tenure or 2
        self._last_selected: Dict[int, int] = {}
        self._step = 0

    def reset(self, n: int) -> None:
        self.tenure = self._fixed_tenure or max(2, min(10, n // 4))
        self._last_selected = {}
        self._step = 0

    def select(self, state: ConflictState, rng: random.Random) -> Optional[int]:
        counts = state.all_queen_conflicts()
        self._step += 1
        last, now, tenure = self._last_selected, self._step, self.tenure
        top, best = 0, []
        for r, k in enumerate(counts):
            if k >= top and k > 0 and now - last.get(r, -INF) > tenure:
                if k > top:
                    top, best = k, [r]
                else:
                    best.append(r)
        if not best:  # mọi biến xung đột đều bị cấm (hoặc không còn xung đột)
            top = max(counts)
            if top <= 0:
                return None
            best = [r for r, k in enumerate(counts) if k == top]
        row = best[0] if len(best) == 1 else rng.choice(best)
        last[row] = now
        return row


# ---------------------------------------------------------------------------
# Chiến lược chọn giá trị
# ---------------------------------------------------------------------------
class ValueSelector(ABC):
    def reset(self, n: int) -> None:
        """Gọi lại mỗi khi bắt đầu một lần chạy hoặc khởi động lại."""

    @abstractmethod
    def choose(
        self, state: ConflictState, row: int, current: int, rng: random.Random, step: int
    ) -> int: ...


class MinConflictsValue(ValueSelector):
    """Chuẩn: cột có ít xung đột nhất (được phép giữ nguyên cột cũ, hòa -> ngẫu nhiên)."""

    def choose(self, state, row, current, rng, step):
        return argmin_random(state.costs_for_row(row), rng)


class TabuMinConflictsValue(ValueSelector):
    """Ngoài phạm vi chọn biến (chỉ dùng trong ablation): min-conflicts nhưng (a) luôn phải đổi cột và (b) không quay lại ngay
    cột vừa rời trong `tenure` bước (danh sách tabu) -> tránh dao động trên cao nguyên."""

    def __init__(self, tenure: Optional[int] = None):
        self._fixed_tenure = tenure
        self.tenure = tenure or 3
        self._tabu: Dict[int, Dict[int, int]] = {}

    def reset(self, n: int) -> None:
        self._tabu = {}
        self.tenure = self._fixed_tenure or max(3, n // 10)

    def choose(self, state, row, current, rng, step):
        costs = state.costs_for_row(row)
        banned = self._tabu.setdefault(row, {})
        costs[current] = INF
        for col, expire in list(banned.items()):
            if expire > step:
                costs[col] = INF
            else:
                del banned[col]
        if min(costs) >= INF:  # mọi cột đều bị cấm -> bỏ cấm
            costs = state.costs_for_row(row)
        new = argmin_random(costs, rng)
        banned[current] = step + self.tenure
        return new


# ---------------------------------------------------------------------------
# Kết quả & solver
# ---------------------------------------------------------------------------
@dataclass
class MinConflictsResult:
    algorithm: str
    n: int
    seed: Optional[int]
    solved: bool
    steps: int
    restarts: int
    time_s: float
    init_conflicts: int
    final_conflicts: int
    board: Board
    init_cols: List[int] = field(default_factory=list)
    # ("move", hàng, cột_cũ, cột_mới, tổng_xung_đột) | ("restart", cols, tổng_xung_đột)
    events: List[tuple] = field(default_factory=list)
    truncated: bool = False


class MinConflictsSolver:
    def __init__(
        self,
        initializer: Initializer,
        var_selector: VariableSelector,
        value_selector: ValueSelector,
        max_steps: int = 100_000,
        stall_factor: Optional[float] = None,
        name: str = "Min-Conflicts",
    ):
        self.initializer = initializer
        self.var_selector = var_selector
        self.value_selector = value_selector
        self.max_steps = max_steps
        self.stall_factor = stall_factor  # khởi động lại sau stall_factor*N bước không cải thiện
        self.name = name

    # ----- các cấu hình dựng sẵn ----------------------------------------
    @classmethod
    def standard(cls, max_steps: int = 100_000) -> "MinConflictsSolver":
        return cls(
            RandomInitializer(),
            RandomConflictedSelector(),
            MinConflictsValue(),
            max_steps,
            None,
            "Min-Conflicts chuẩn",
        )

    @classmethod
    def heuristic(cls, max_steps: int = 100_000, tenure: Optional[int] = None) -> "MinConflictsSolver":
        """Bản chuẩn, chỉ thay bước chọn biến bằng heuristic đề xuất (so sánh công bằng)."""
        return cls(
            RandomInitializer(),
            MostConflictedTabuSelector(tenure),
            MinConflictsValue(),
            max_steps,
            None,
            "Min-Conflicts + heuristic chọn biến",
        )

    @classmethod
    def most_conflicted_only(cls, max_steps: int = 100_000) -> "MinConflictsSolver":
        """Ablation: chọn biến xung đột nhiều nhất nhưng KHÔNG có tabu trên biến."""
        return cls(
            RandomInitializer(),
            MaxConflictedSelector(),
            MinConflictsValue(),
            max_steps,
            None,
            "Most-conflicted (không tabu)",
        )

    @classmethod
    def enhanced(
        cls,
        max_steps: int = 100_000,
        tabu_tenure: Optional[int] = None,
        stall_factor: Optional[float] = 20.0,
    ) -> "MinConflictsSolver":
        """Ablation: heuristic chọn biến + các kỹ thuật NGOÀI phạm vi chọn biến
        (khởi tạo tham lam, tabu trên giá trị, khởi động lại khi kẹt)."""
        return cls(
            GreedyInitializer(),
            MostConflictedTabuSelector(),
            TabuMinConflictsValue(tabu_tenure),
            max_steps,
            stall_factor,
            "Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart",
        )

    # ----- chạy -----------------------------------------------------------
    def solve(
        self, n: int, seed: Optional[int] = None, record: bool = False, max_record: int = 20_000
    ) -> MinConflictsResult:
        if n in (2, 3):
            raise ValueError("N = 2 và N = 3 không có nghiệm")
        rng = random.Random(seed)
        t0 = time.perf_counter()

        state = ConflictState(n)
        self.var_selector.reset(n)
        self.value_selector.reset(n)
        self.initializer.initialize(state, rng)
        init_cols = list(state.cols)
        init_total = state.total

        events: List[tuple] = []
        truncated = False
        steps = restarts = 0
        best = state.total
        since_improve = 0
        stall_limit = int(self.stall_factor * n) if self.stall_factor else None

        while state.total > 0 and steps < self.max_steps:
            row = self.var_selector.select(state, rng)
            if row is None:
                break
            old = state.cols[row]
            state.remove(row)
            new = self.value_selector.choose(state, row, old, rng, steps)
            state.place(row, new)
            steps += 1

            if record:
                if len(events) < max_record:
                    events.append(("move", row, old, new, state.total))
                else:
                    truncated = True

            if state.total < best:
                best, since_improve = state.total, 0
            else:
                since_improve += 1
            if stall_limit and since_improve >= stall_limit and state.total > 0:
                state = ConflictState(n)
                self.var_selector.reset(n)
                self.value_selector.reset(n)
                self.initializer.initialize(state, rng)
                best, since_improve = state.total, 0
                restarts += 1
                if record:
                    if len(events) < max_record:
                        events.append(("restart", list(state.cols), state.total))
                    else:
                        truncated = True

        elapsed = time.perf_counter() - t0
        return MinConflictsResult(
            algorithm=self.name,
            n=n,
            seed=seed,
            solved=state.total == 0,
            steps=steps,
            restarts=restarts,
            time_s=elapsed,
            init_conflicts=init_total,
            final_conflicts=state.total,
            board=Board.from_columns(state.cols),
            init_cols=init_cols,
            events=events,
            truncated=truncated,
        )


if __name__ == "__main__":
    for solver in (MinConflictsSolver.standard(), MinConflictsSolver.heuristic()):
        r = solver.solve(12, seed=1)
        print(f"{r.algorithm}: solved={r.solved}, steps={r.steps}, time={1000 * r.time_s:.2f} ms")
    from nqueens_solver.gui.server import serve

    serve(hash_tab="mc")
