# Đồ án cuối kỳ Introduction to AI — hướng dẫn chạy khi demo

Ba task nằm ở ba thư mục độc lập, mỗi task có môi trường ảo và README riêng.

| Task | Thư mục | Nội dung | Giao diện |
|---|---|---|---|
| 1 | `task1/` | N-Queens: logic mệnh đề + Glucose3, Min-Conflicts | Web, mở trong cửa sổ Chrome |
| 2 | `task2/` | Tank Battle: Minimax, Alpha-Beta, Heuristic Minimax | PyGame |
| 3 | `task3/` | Kakuro: CSP, Backtracking + lan truyền ràng buộc | PyGame |

## Chạy nhanh

Trên máy mới, làm **mục 1 (Cài đặt)** một lần trước: gói nộp không kèm thư mục `.venv`. Sau đó mở Terminal tại thư mục chứa file README này, dán từng lệnh sau; mỗi lệnh mở một giao diện, nên dùng một tab Terminal riêng cho mỗi task (`Cmd + T`).

```bash
# Task 1: N-Queens (mở trong cửa sổ Chrome)
cd task1 && .venv/bin/python main.py

# Task 2: Tank Battle (cửa sổ PyGame)
cd task2 && .venv/bin/python main.py

# Task 3: Kakuro (cửa sổ PyGame)
cd task3 && .venv/bin/python main.py
```

Tắt giao diện: đóng cửa sổ, hoặc bấm `Ctrl + C` trong Terminal. Thao tác trong từng giao diện xem mục 3.

Yêu cầu: Python 3.8 trở lên. Task 1 cần thêm Google Chrome hoặc Edge để mở giao diện ở dạng cửa sổ riêng (không có thì mở bằng trình duyệt mặc định).

## 1. Cài đặt (làm một lần trên mỗi máy)

Chạy từ thư mục chứa file README này:

```bash
for t in task1 task2 task3; do
  (cd $t && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt)
done
```

Trên Windows, làm lần lượt trong từng thư mục: `python -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`.

Kiểm tra nhanh trước giờ demo (cả ba dòng phải in `OK`):

```bash
(cd task1 && .venv/bin/python -m unittest discover -s tests 2>&1 | tail -1)
(cd task2 && .venv/bin/python -m unittest discover -s tests 2>&1 | tail -1)
(cd task3 && .venv/bin/python -m unittest discover -s tests 2>&1 | tail -1)
```

## 2. Mở giao diện

Mỗi task dùng một cửa sổ Terminal riêng. Các lệnh dưới đây gọi thẳng Python của môi trường ảo, nên không cần `activate`.

```bash
cd task1 && .venv/bin/python main.py      # Task 1
cd task2 && .venv/bin/python main.py      # Task 2
cd task3 && .venv/bin/python main.py      # Task 3
```

## 3. Kịch bản demo

### Task 1 — N-Queens

| Bước | Thao tác | Yêu cầu của đề |
|---|---|---|
| 1 | Tab **Logic mệnh đề & SAT**: bấm xem từng bước 1 → 9 để thấy cách gán biến, 5 nhóm ràng buộc CNF và lời giải của Glucose3 | 1 |
| 2 | Tab **Thực nghiệm**: bảng Glucose3 theo N (số mệnh đề CNF, thời gian solve, decisions, propagations, conflicts) | 2 |
| 3 | Tab **Min-Conflicts**: nhập N và seed, bấm chạy; hai bàn cờ xuất phát từ cùng một trạng thái, chỉ khác bước chọn biến | 3 |
| 4 | Tab **Thực nghiệm**: bảng và biểu đồ so sánh bản chuẩn với heuristic chọn biến | 3 |

Lưu ý khi demo bước 3: một seed đơn lẻ có thể cho heuristic nhiều bước hơn bản chuẩn. Kết luận lấy từ bảng 200 lần chạy ở bước 4.

Chạy lại thực nghiệm từ dòng lệnh (khoảng 5–10 phút, chậm nhất là Glucose3 với N = 80 và 100):

```bash
cd task1 && .venv/bin/python main.py experiments --no-gui
```

Lý thuyết: `task1/docs/BAO_CAO.md`. Số liệu: `task1/results/report.md`.

### Task 2 — Tank Battle

| Bước | Thao tác | Yêu cầu của đề |
|---|---|---|
| 1 | Menu mặc định: P1 = `Heuristic Alpha-Beta`, P2 = `Minimax (cutoff, EVAL = 0)` (cắt độ sâu, không heuristic), map `classic`, rồi `Enter`. Bên có heuristic thắng sau khoảng 25 chu kỳ | 1, 2, 3 |
| 2 | Trong trận, chỉ vào thẻ của từng bên: số nút đã thăm, số lần cắt tỉa, độ sâu (chu kỳ và ply), giá trị minimax | 2 |
| 3 | `Esc` về menu, đổi P2 = `Heuristic Minimax`: cùng hàm EVAL nhưng Alpha-Beta thăm ít nút hơn nhiều nên trong 50 ms tìm sâu hơn (3–4 chu kỳ so với 2) | 2 |
| 4 | Đổi P2 = `Example: Sniper` (agent nạp từ thư mục `plugins/`) để minh họa cơ chế nhập agent của nhóm khác | 3 |
| 5 | Chọn P1 = `Human` nếu thầy muốn tự chơi: phím mũi tên, `Space` bắn, `Enter` đứng yên | 3 |

Phím trong trận: `P` tạm dừng, `N` đi từng chu kỳ, `R` chơi lại, `+`/`-` chỉnh tốc độ, `Esc` về menu.

Nhập agent của nhóm khác: chép file `.py` của họ vào `task2/plugins/`, về menu bấm `F5`. Cách viết agent xem `task2/README.md`.

Các lệnh không cần giao diện:

```bash
cd task2
.venv/bin/python arena.py --list                                            # danh sách agent, kể cả plugin
.venv/bin/python arena.py --p1 "Heuristic Alpha-Beta" --p2 Random --map duel --games 3 --swap
.venv/bin/python experiments.py --quick                                     # thực nghiệm rút gọn, vài phút
.venv/bin/python experiments.py                                             # đầy đủ, khoảng 20-30 phút
```

Lý thuyết: `task2/docs/formulation.md`. Số liệu: `task2/results/summary.md`.

### Task 3 — Kakuro

| Bước | Thao tác | Yêu cầu của đề |
|---|---|---|
| 1 | Mở mặc định (đề 9x9, MAC + MRV/Degree + LCV + AC-3). Bấm `Space`: phần tô nhạt trên timeline là AC-3 tiền xử lý, các chữ số nhỏ bị gạch đỏ là giá trị bị tỉa | 2, 3 |
| 2 | Rê chuột lên một ô trắng để đọc miền giá trị và hai ràng buộc của biến đó | 3 |
| 3 | Chỉ vào thanh "Search space left": lan truyền ràng buộc làm nó co lại | 3 |
| 4 | Click dòng **Inference** đổi sang `FC`, **Variable order** sang `Static`, **Initial AC-3** sang `Off`, rồi `Space`: lúc này có quay lui, timeline thành hình răng cưa. Bấm `B` để nhảy tới từng lần quay lui | 3 |
| 5 | Click dòng **Puzzle** để đổi sang `example_5x5` hoặc các đề sinh ngẫu nhiên | 2 |

Phím: `Space` chạy/dừng, mũi tên trái/phải lùi/tiến một bước, `N` tới lần gán tiếp theo, `B` tới lần quay lui tiếp theo, mũi tên lên/xuống chỉnh tốc độ, `R` về đầu, `E` tới cuối. Click phải vào một dòng cài đặt để lùi về giá trị trước.

Mở thẳng cấu hình có quay lui:

```bash
cd task3
.venv/bin/python main.py --puzzle example_5x5 --inference FC --var-order Static --value-order Ascending --no-preprocess
```

Các lệnh không cần giao diện:

```bash
cd task3
.venv/bin/python solve.py complex_9x9 --all      # giải và kiểm tra nghiệm duy nhất
.venv/bin/python experiments.py                  # thực nghiệm đầy đủ, khoảng 1-2 phút
```

Lý thuyết: `task3/docs/formulation.md`. Số liệu: `task3/results/summary.md`.

## 4. Cách đo trong thực nghiệm

Cả ba task đo chi phí bằng các đại lượng của lý thuyết; số giây chỉ là số liệu đi kèm vì nó phụ thuộc máy.

| Task | Thời gian | Không gian |
|---|---|---|
| 1 | Số mệnh đề CNF; decisions, propagations, conflicts của Glucose3; số bước lặp của Min-Conflicts | — |
| 2 | Số nút của cây trò chơi đã thăm, hệ số phân nhánh hiệu dụng b* | Số nút giữ cùng lúc nhiều nhất (peak memory, O(b·m)) và số entry của bảng chuyển vị |
| 3 | Số nút của cây tìm kiếm, số lần quay lui, số lần kiểm tra ràng buộc | Độ sâu lớn nhất (O(n)) và độ dài trail lớn nhất (O(n·d)) |

## 5. Khi gặp lỗi

| Hiện tượng | Cách xử lý |
|---|---|
| `No module named pygame` hoặc `pysat` | Chưa cài hoặc đang dùng nhầm Python. Chạy lại mục 1 và gọi đúng `.venv/bin/python` của task đó. |
| Task 1 báo cổng đang bận | Thêm cổng khác: `.venv/bin/python main.py gui --port 8010` |
| Task 1 không tự mở cửa sổ | Mở trình duyệt và vào địa chỉ in ra trong Terminal |
| Cửa sổ PyGame không nhận phím | Click vào cửa sổ một lần để nó nhận focus; tắt bộ gõ tiếng Việt |
| Task 2 chạy quá nhanh hoặc quá chậm | Phím `+`/`-` trong trận, hoặc dòng "Pause between cycles" ở menu |

Đóng gói để nộp: `./package_submission.sh <Mã nhóm> <MSSV>` (macOS/Linux) hoặc `.\package_submission.ps1 -GroupId <Mã nhóm> -StudentId <MSSV>` (Windows). Script tạo `AI_final_<Mã nhóm>_<MSSV>.zip` đúng cấu trúc đề yêu cầu và bỏ qua `.venv`, `.venv-windows-old`, `__pycache__`, `.git`. Nhớ điền link video vào `demo.txt` trước khi đóng gói.
