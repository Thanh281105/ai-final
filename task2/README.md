# Task 2 — Tank Battle (Adversarial Search)

Điều khiển xe tăng bằng **Minimax, Alpha-Beta, Heuristic Minimax và Heuristic Minimax + Alpha-Beta** (Lecture 07). Giao diện dùng PyGame, và có cơ chế nạp agent của nhóm khác vào để thi đấu.

## Cài đặt

Yêu cầu Python ≥ 3.8 (đã kiểm tra trên Python 3.9, macOS).

```bash
cd task2
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Chạy

| Mục đích | Lệnh |
|---|---|
| Giao diện (menu chọn agent / bản đồ) | `python main.py` |
| Vào thẳng trận | `python main.py --p1 "Heuristic Alpha-Beta" --p2 Human --map classic --start` |
| Đấu không giao diện | `python arena.py --p1 "Heuristic Alpha-Beta" --p2 Random --map duel --games 3 --swap` |
| Xem danh sách agent (kể cả plugin) | `python arena.py --list` |
| Thực nghiệm Requirement 2 | `python experiments.py --quick` (vài phút) hoặc `python experiments.py` (đầy đủ, khoảng 15–25 phút) |
| Unit test | `python -m unittest discover tests` |

**Menu:** phím lên/xuống chọn dòng, trái/phải đổi giá trị, `Enter` bắt đầu, `F5` nạp lại plugin. Bên phải là bản xem trước của bản đồ đang chọn.

**Trong trận:** `P` tạm dừng · `N` đi từng chu kỳ · `R` chơi lại · `+/-` chỉnh khoảng nghỉ giữa các chu kỳ · `Esc` về menu. Bảng bên phải hiển thị cho mỗi bên: máu của tank và base (mỗi ô vuông là 1 HP), nước vừa đi, số nút đã thăm, số lần cắt tỉa alpha-beta, độ sâu tìm kiếm (chu kỳ và ply), giá trị minimax của gốc, và biểu đồ cột số nút đã thăm ở từng nước (thang log).
Người chơi: P1 dùng phím mũi tên, `SPACE` để bắn, `ENTER` để đứng yên. P2 dùng `WASD`, `F` để bắn, `E` để đứng yên.

## Cấu trúc thư mục

```
task2/
├── main.py                 # GUI (Requirement 3)
├── arena.py                # đấu headless giữa 2 agent bất kỳ / plugin
├── experiments.py          # thực nghiệm so sánh 4 cấu hình (Requirement 2)
├── docs/formulation.md     # mô hình hóa Zero-Sum Game (Requirement 1)
├── maps/                   # classic 13x13, open 9x9, duel 7x7 (đối xứng tâm)
├── plugins/                # agent của nhóm khác (thả file .py vào đây)
├── results/                # CSV, summary.md, biểu đồ do experiments.py sinh ra
├── tests/test_game.py
└── tank_battle/
    ├── core/               # constants, entities (Tank/Base/Bullet), GameState, map_loader
    ├── agents/
    │   ├── base_agent.py      # interface BaseAgent + SearchStats
    │   ├── search_agents.py   # Minimax / Alpha-Beta / Heuristic ... (1 engine, 4 cấu hình)
    │   ├── heuristics.py      # hàm EVAL + move ordering
    │   ├── simple_agents.py   # Random, Human
    │   └── plugin_loader.py   # nạp agent từ file .py
    ├── match.py            # chạy trận: 2 agent, cùng môi trường, giới hạn thời gian
    └── gui/                # renderer.py (vẽ), app.py (menu + màn chơi)
```

Thiết kế hướng đối tượng: các entity (`Tank`, `Base`, `Bullet`) và `GameState` chỉ chứa luật chơi. Mọi agent đều kế thừa `BaseAgent`. Bốn thuật toán là các lớp con của `AdversarialSearchAgent`. `Match` không phụ thuộc vào GUI, nên GUI, arena và experiments dùng chung một môi trường.

## Tích hợp agent của nhóm khác (Requirement 3)

Thả một file `.py` vào thư mục `plugins/`. Menu GUI (phím `F5` để nạp lại) và `arena.py` sẽ tự tìm thấy. Có hai cách viết:

**(a) Kế thừa `BaseAgent`** — xem `plugins/example_class_agent.py`:
```python
from tank_battle.agents import BaseAgent
from tank_battle.core import Action

class MyAgent(BaseAgent):
    name = "Group 7 - Alpha-Beta"
    def choose_action(self, state):          # state: GameState (bản sao)
        return Action.FIRE
```

**(b) Chỉ cần một hàm, không import code của nhóm mình** — xem `plugins/example_function_agent.py`. Cách này phù hợp khi nhóm khác có cấu trúc dữ liệu riêng: chỉ cần viết lớp chuyển đổi từ `observation` (dict thuần) sang dạng của họ.
```python
AGENT_NAME = "Group 7"
def get_action(observation, player_id):      # observation = GameState.to_dict()
    return "FIRE"                            # MOVE_UP / MOVE_DOWN / MOVE_LEFT / MOVE_RIGHT / FIRE / STAY
```

Cả hai bên nhận cùng một trạng thái và cùng luật. Nếu một agent ném lỗi, trả về hành động sai, hoặc vượt giới hạn thời gian mỗi nước (chỉnh trong menu), thì nước đó bị thay bằng `STAY`. Lỗi khi nạp plugin chỉ được hiển thị trên menu, không làm sập chương trình. Có thể chỉ định file cụ thể: `python arena.py --p2 "plugins/group7.py:MyAgent"`.

## Ghi chú thực nghiệm

Cách đo bám theo lý thuyết của Lecture 07 (chi tiết ở `docs/formulation.md` mục 3.5):

- **Ply** là một nước của một bên; 1 chu kỳ = 2 ply (MAX đi, rồi MIN đi).
- **Độ phức tạp thời gian** được đo bằng **số nút của cây trò chơi đã thăm** và hệ số phân nhánh hiệu dụng `b*`. Số giây chỉ là số liệu đi kèm.
- **Độ phức tạp không gian** được đo bằng **độ sâu lớn nhất đã tới** (tìm kiếm theo chiều sâu chỉ giữ một nhánh, bộ nhớ là `O(b·m)`).

| Thí nghiệm | Nội dung |
|---|---|
| A. Tìm kiếm chính xác | Minimax và Alpha-Beta duyệt **đến trạng thái kết thúc** trên 10 thế tàn cuộc, cây sâu m = 2, 4, 6, 8 ply. Kiểm tra hai thuật toán cho cùng giá trị minimax và so số nút. Thêm một lần chạy từ thế khai cuộc (m = 400 ply) để cho thấy tìm kiếm chính xác không khả thi ở đó. |
| B. Tìm kiếm cắt độ sâu | Heuristic Minimax và Heuristic Alpha-Beta trên cùng trạng thái gốc, cùng độ sâu cắt. Có ablation: tắt move ordering. |
| C. Chất lượng quyết định | Cả bốn cấu hình trên cùng các thế tàn cuộc của A; nước đi được coi là tối ưu nếu giá trị minimax chính xác của nó bằng giá trị tốt nhất. |
| D. Sức mạnh khi thi đấu | Đấu vòng tròn, đổi bên, trên các bản đồ đối xứng. |

Minimax / Alpha-Beta khi bị cắt độ sâu mà không có heuristic thì chấm nút bị cắt bằng 0. Bản này là H-Minimax với `EVAL ≡ 0`, nên trong bảng kết quả luôn được ghi là `(cutoff, EVAL = 0)`, tách khỏi Minimax / Alpha-Beta đúng nghĩa.
