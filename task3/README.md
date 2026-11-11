# Task 3 — Kakuro (Constraint Satisfaction Problems)

Mô hình hóa Kakuro thành CSP và giải bằng **Backtracking Search kết hợp constraint propagation** (Forward Checking, AC-3 / MAC cho ràng buộc n-ngôi), với các heuristic của Lecture 08: **MRV, Degree, LCV**. Giao diện PyGame trực quan hóa miền giá trị, quá trình lan truyền ràng buộc và quá trình tìm kiếm quay lui.

## Cài đặt

Yêu cầu Python ≥ 3.8 (đã kiểm tra trên Python 3.9, macOS).

```bash
cd task3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Solver, CLI và unit test chỉ dùng thư viện chuẩn. `pygame` dùng cho GUI, `matplotlib` (tùy chọn) dùng để vẽ biểu đồ thực nghiệm.

## Chạy

| Mục đích | Lệnh |
|---|---|
| Giao diện (Requirement 3) | `python main.py` |
| GUI với cấu hình yếu, để thấy rõ quá trình quay lui | `python main.py --puzzle example_5x5 --inference FC --var-order Static --value-order Ascending --no-preprocess` |
| Giải bằng dòng lệnh | `python solve.py complex_9x9` |
| Giải và kiểm tra nghiệm duy nhất | `python solve.py complex_9x9 --all` |
| So sánh cấu hình | `python solve.py complex_9x9 --inference FC --var-order Static --value-order Ascending --no-preprocess` |
| Thực nghiệm Requirement 2 | `python experiments.py --quick` (khoảng 1 phút) hoặc `python experiments.py` (đầy đủ, khoảng 5 phút) |
| Sinh thêm đề ngẫu nhiên | `python generate.py --rows 10 --cols 10 --seed 3` |
| Unit test | `python -m unittest discover tests` |

**Trong GUI:** click vào một dòng cài đặt (Puzzle / Inference / Variable order / Value order / Initial AC-3 / Tie-break seed) để đổi sang giá trị tiếp theo, click phải để lùi lại. Solver sẽ chạy lại và ghi lại trace mới.
Phím: `Space` chạy/dừng · `←`/`→` lùi/tiến một bước · `N` đến quyết định (gán/hủy) tiếp theo · `B` đến lần quay lui tiếp theo · `↑`/`↓` tốc độ · `R` về đầu · `E` đến cuối · `Esc` thoát. Click/kéo trên timeline để nhảy đến bước bất kỳ. Rê chuột lên một ô trắng để xem miền giá trị và hai ràng buộc của biến đó. Cửa sổ 1240×760, vừa màn hình 1280×800.

## Cấu trúc thư mục

```
task3/
├── main.py                 # GUI (Requirement 3)
├── solve.py                # giải từ dòng lệnh
├── experiments.py          # thực nghiệm A–D (Requirement 2)
├── generate.py             # sinh đề ngẫu nhiên (luôn có nghiệm), dùng để kiểm tra độ ổn định
├── docs/formulation.md     # mô hình CSP + giải thích thuật toán (Requirement 1)
├── puzzles/                # example_5x5, complex_9x9 (2 đề của bài) + vài đề sinh ngẫu nhiên
├── results/                # summary.md, CSV, biểu đồ do experiments.py sinh ra
├── tests/test_solver.py
└── kakuro/
    ├── core/
    │   ├── board.py        # Cell / ClueCell / WhiteCell, Run, KakuroBoard (đọc file, tách run, kiểm tra lời giải)
    │   ├── puzzles.py      # tìm và nạp đề
    │   └── generator.py    # sinh đề ngẫu nhiên
    ├── csp/
    │   ├── model.py        # KakuroCSP: X, D, C, đồ thị ràng buộc
    │   ├── constraint.py   # SumAllDiffConstraint + bảng tổ hợp + kiểm tra support (GAC)
    │   ├── inference.py    # AC3 (REVISE, vòng lặp AC-3), NoInference / ForwardChecking / MAC
    │   ├── heuristics.py   # Static / MRV / MRV+Degree, Ascending / LCV
    │   ├── solver.py       # BacktrackingSolver (trail, thống kê, giới hạn), SolverConfig
    │   └── events.py       # sự kiện tìm kiếm cho GUI
    └── gui/
        ├── replay.py       # phát lại trace, có keyframe để tua lùi
        ├── renderer.py     # vẽ bàn cờ, miền giá trị, highlight
        └── app.py          # cửa sổ, nút, timeline, log
```

Thiết kế hướng đối tượng:
- `KakuroBoard` chỉ chứa luật chơi. `KakuroCSP` là mô hình ⟨X, D, C⟩. `SumAllDiffConstraint` tự biết cách kiểm tra nhất quán và tính support cho chính nó.
- Heuristic chọn biến, heuristic chọn giá trị và chiến lược suy luận đều là các lớp cùng một interface (Strategy pattern). `BacktrackingSolver` ghép chúng lại theo `SolverConfig`, nên mỗi cấu hình trong thực nghiệm chỉ khác nhau một dòng cấu hình.
- Solver không phụ thuộc GUI. GUI chỉ nhận trace qua `Tracer`, nên CLI, thực nghiệm và GUI dùng chung một solver.

## Kết quả chính

- Cả hai đề của bài đều giải được, lời giải qua được bộ kiểm tra độc lập và là **nghiệm duy nhất**. Đề 9x9 được giải với 48 nút, 0 lần quay lui, 1 809 lần kiểm tra ràng buộc (khoảng 9 ms).
- Ablation trên đề 9x9: BT thuần cần 14 038 nút, BT + FC cần 275 nút, MAC + MRV/Degree + LCV + AC-3 chỉ cần 48 nút.
- Độ ổn định: 30 seed phá hòa ngẫu nhiên cho ra cùng một lời giải với số nút không đổi. 20 đề ngẫu nhiên (7x7 đến 12x12) đều giải được, chậm nhất 162 ms.
- Chi phí được đo theo lý thuyết: thời gian = số nút / số lần quay lui / số lần kiểm tra ràng buộc; không gian = độ sâu lớn nhất của cây tìm kiếm và độ dài trail lớn nhất.

Phân tích chi tiết: `docs/formulation.md` mục 5 và `results/summary.md`.
