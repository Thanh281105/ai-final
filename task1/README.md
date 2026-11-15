# N-Queens Lab — Local Search & Propositional Logic

Bài tập Task 1: giải bài toán N hậu bằng (1) logic mệnh đề + SAT solver **Glucose3** (PySAT) và
(2) **Min-Conflicts** (bản chuẩn của Lecture 08 và bản dùng heuristic chọn biến đề xuất), kèm giao diện trực quan.

## Cài đặt

Yêu cầu Python ≥ 3.8 (đã kiểm tra trên Python 3.9, macOS).

```bash
cd task1
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\activate
pip install -r requirements.txt        # chỉ cần python-sat
```

Giao diện dùng thư viện chuẩn của Python (một server HTTP cục bộ) và tự mở trong cửa sổ Chrome/Edge ở chế độ ứng dụng; nếu máy không có hai trình duyệt này thì mở bằng trình duyệt mặc định. Đóng cửa sổ là chương trình tự thoát.

## Chạy (mọi lệnh đều tự động hiện thành phẩm)

```bash
python main.py                              # tự mở cửa sổ giao diện và hiển thị sẵn thành phẩm ở cả 3 tab
python main.py experiments                  # chạy toàn bộ thực nghiệm (khoảng 5-10 phút) -> lưu vào results/ -> tự mở bảng & biểu đồ
python main.py experiments --no-gui         # như trên nhưng chỉ in ra terminal
python main.py sat --n 4 8 12 16            # chạy thực nghiệm Glucose3 -> tự mở bảng & biểu đồ
python main.py satalo --n 40 80 --no-gui    # ablation: KB gốc so với KB + "mỗi cột ít nhất một hậu" (mệnh đề được KB suy ra)
python main.py minconflicts --n 8 64 512    # chạy thực nghiệm Min-Conflicts -> tự mở bảng & biểu đồ
python -m unittest discover -s tests -v     # chạy 21 unit test
```

> Bạn cũng có thể chạy trực tiếp bất kỳ file `.py` nào (ví dụ `python nqueens_solver/core/sat_solver.py`, `python nqueens_solver/core/min_conflicts.py`, `python nqueens_solver/gui/server.py`) — chương trình sẽ tự động chạy và mở cửa sổ thành phẩm tương ứng.

## Giao diện

| Tab | Nội dung |
|---|---|
| 1 · Logic mệnh đề & SAT | Tự động hiển thị ngay **bàn cờ thành phẩm N = 8 (Bước 9)** cùng banner kết quả và bảng tóm tắt CNF. Bấm **▶ Xem từng bước (1 → 9)** để xem quá trình gán biến → 5 nhóm ràng buộc CNF → Glucose3 giải |
| 2 · Min-Conflicts | Tự động giải và hiển thị **bàn cờ thành phẩm** của bản chuẩn và bản dùng heuristic chọn biến, đặt cạnh nhau, cùng seed nên cùng bàn cờ ban đầu; bấm **▶ Phát quá trình** để xem quân hậu trượt mượt 60fps cùng đường nối xung đột và đồ thị giảm xung đột |
| 3 · Thực nghiệm | Tự động nạp và vẽ bảng + 4 biểu đồ từ `results/` (bảng Glucose3 có thêm số decisions, propagations, conflicts của solver); hoặc bấm chạy lại thực nghiệm trực tiếp trên giao diện |

## Cấu trúc (OOP)

```
main.py                         điểm vào (tự động mở cửa sổ thành phẩm)
nqueens_solver/
  core/
    board.py                    Board: kiểm tra nghiệm độc lập
    cnf.py                      VariableMap, ConstraintDiscoverer, ConstraintGroup, NQueensCNF
    sat_solver.py               GlucoseQueensSolver, SATResult
    min_conflicts.py            ConflictState + Strategy: Initializer / VariableSelector / ValueSelector
                                MinConflictsSolver.standard() / .heuristic() / .enhanced()
  experiments/                  SATExperiment, MinConflictsExperiment, ReportWriter
  gui/                          server.py (HTTP + cửa sổ ứng dụng tự động), presenters.py, static/ (HTML, CSS, JS)
tests/test_core.py              21 unit test
docs/BAO_CAO.md                 lý thuyết cho cả 3 yêu cầu: mô hình logic mệnh đề, CNF, Glucose3, Min-Conflicts, heuristic
results/                        kết quả thực nghiệm (CSV / JSON / Markdown)
```

## Đối chiếu với yêu cầu của đề

| Yêu cầu | Ở đâu |
|---|---|
| 1. Mô hình logic mệnh đề, thuật toán phát hiện ràng buộc, chuyển về CNF | `docs/BAO_CAO.md` mục 1; `core/cnf.py`; tab 1 của giao diện |
| 2. Glucose3 với N tăng dần (N ≥ 4), số mệnh đề CNF và thời gian chạy của solver | `docs/BAO_CAO.md` mục 2; `results/report.md` mục 1 và 4; `python main.py sat`, `python main.py satalo` |
| 3. Min-Conflicts, heuristic chọn biến, thực nghiệm so với bản chuẩn | `docs/BAO_CAO.md` mục 3; `results/report.md` mục 2–3; `python main.py minconflicts` |

## Heuristic chọn biến đề xuất

Đề yêu cầu một heuristic **chọn biến**, nên bản heuristic chỉ khác bản chuẩn ở đúng bước đó:

| | Chuẩn (`standard()`) | Heuristic (`heuristic()`) |
|---|---|---|
| Khởi tạo | ngẫu nhiên | ngẫu nhiên (cùng seed → cùng bàn cờ ban đầu) |
| **Chọn biến** | ngẫu nhiên trong các hậu đang bị tấn công | hậu bị tấn công **nhiều nhất**, không chọn lại hậu vừa chọn trong `max(2, min(10, N/4))` bước |
| Chọn giá trị | cột ít xung đột nhất | cột ít xung đột nhất |
| Khởi động lại | không | không |

Thước đo chính là **số bước lặp** của Min-Conflicts (không phụ thuộc máy); thời gian là số liệu phụ. Kết quả với 200 lần chạy mỗi N: số bước trung vị còn 52–76% so với bản chuẩn ở mọi N từ 8 đến 1000, với tỉ lệ thành công tương đương.

`enhanced()` thêm khởi tạo tham lam, tabu trên giá trị và khởi động lại. Các kỹ thuật này nằm ngoài phạm vi chọn biến, nên chỉ xuất hiện trong phần ablation (`results/report.md` mục 3).

Chi tiết và cách đọc kết quả xem `docs/BAO_CAO.md`.
