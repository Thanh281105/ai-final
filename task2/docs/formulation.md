# Requirement 1 — Mô hình hóa Tank Battle thành trò chơi Zero-Sum

> Tài liệu này là phần lý thuyết cho Requirement 1. Mỗi khái niệm đều chỉ ra chỗ cài đặt trong code để dễ giải thích khi vấn đáp.

## 1. Luật chơi được cài đặt

Đề bài chỉ quy định khung chung, nên nhóm cố định thêm một số chi tiết (đánh dấu ★ là giả định do nhóm tự đặt):

| Thành phần | Quy tắc |
|---|---|
| Bản đồ | Lưới `H × W`, ô trống / tường gạch. Mỗi bên có 1 xe tăng và 1 căn cứ (base). |
| Máu | Tank 6, Base 9, Wall 3; mỗi phát trúng trừ 1 (bảng trong đề). |
| Hành động | `MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY` |
| Di chuyển | `MOVE_x` xoay xe về hướng x, rồi tiến 1 ô nếu ô đó trống (không tường/base/tank/biên). ★ Ô đích được xét theo vị trí **đầu chu kỳ**: hai xe cùng muốn vào một ô → cả hai đứng yên; không thể đổi chỗ cho nhau hay đi vào ô mà xe kia vừa rời đi. ★ Xe đi vào ô đang có một viên đạn thì trúng viên đạn đó (−1 máu, viên đạn biến mất). |
| Bắn | Đạn xuất phát từ ô của xe, bay theo hướng xe đang quay, **3 ô / chu kỳ**, kiểm tra va chạm **sau mỗi ô**, dừng ngay khi trúng tường/tank/base. ★ Mỗi xe chỉ có tối đa 1 viên đạn đang bay (giống Battle City): xe chỉ bắn được nếu **đầu chu kỳ** nó không có viên đạn nào đang bay. Đúng như đề, đạn chỉ va chạm với tường, tank và base; hai viên đạn **không** chặn nhau. ★ Đạn không phân biệt phe: bắn trúng base hay tank của chính mình vẫn mất máu. ★ Các viên đạn đi vào cùng một ô trong cùng một bước thì trúng **đồng thời** (không phụ thuộc thứ tự xử lý). |
| Thứ tự trong 1 chu kỳ | (1) cả hai xe di chuyển → (2) đạn mới được bắn ra → (3) mọi viên đạn bay 3 ô, từng ô một. |
| Kết thúc | Khi một tank hoặc một base bị phá hủy. ★ Chu kỳ luôn được xử lý trọn vẹn rồi mới xét kết thúc, nên hai bên cùng mất trong một chu kỳ → hòa. ★ Giới hạn `max_turns` (mặc định 200; bản đồ duel 100, open 150) → hòa, đảm bảo cây trò chơi hữu hạn. |

Cài đặt: `tank_battle/core/game_state.py` (`apply_cycle`, `_advance_bullets_one_cell`, `_collide`).

## 2. Các thành phần của trò chơi Zero-Sum

### 2.1 Người chơi — `PLAYER(n)`
Hai người chơi: **P1 (xanh dương)** và **P2 (đỏ)**. Khi agent của ta tìm kiếm, ta là **MAX**, đối thủ là **MIN**.

Minimax cần một trò chơi **luân phiên**, trong đó `PLAYER` cho biết đến lượt ai. Trò chơi thật lại là đồng thời, nên một **nút của cây trò chơi** không chỉ là trạng thái `s` mà là cặp `n = (s, a_chờ)`:

```
n = (s, ∅)        → PLAYER(n) = MAX   (đầu chu kỳ, chưa ai chọn)
n = (s, a_MAX)    → PLAYER(n) = MIN   (MAX đã chọn a_MAX, đang chờ MIN)
```
Chi tiết ở mục 2.4.

### 2.2 Trạng thái — `s ∈ S`
Trò chơi **quan sát đầy đủ** (fully observable) và **tất định** (deterministic). Một trạng thái gồm:

```
s = ( walls:   {(r, c) -> hp}                       # tường còn lại và máu của chúng
      tanks:   [(row, col, direction, hp) × 2]
      bases:   [(row, col, hp) × 2]
      bullets: [(owner, row, col, direction) ...]   # đạn đang bay
      turn )                                        # số chu kỳ đã trôi qua
```
Trạng thái ban đầu `s0` được đọc từ file bản đồ (`maps/*.txt`, `map_loader.py`).

### 2.3 Hành động — `ACTIONS(s, p)`
Về luật, cả 6 hành động luôn hợp lệ. `GameState.legal_actions` bỏ đi các hành động **có hiệu ứng y hệt `STAY`**:
- `MOVE_x` khi xe đã quay về hướng x và ô phía trước bị chặn (nước này không xoay xe cũng không di chuyển);
- `FIRE` khi xe đã có một viên đạn đang bay.

Cả hai điều kiện được xét trên trạng thái **đầu chu kỳ**, đúng như cách `apply_cycle` xử lý, nên hành động bị bỏ cho ra đúng trạng thái của `STAY`. Việc này vì thế không làm thay đổi giá trị minimax (chỉ bỏ các cây con trùng lặp); test `test_action_pruning_keeps_the_exact_minimax_value` so giá trị chính xác khi dùng tập đã lọc với khi dùng đủ 6 hành động. Số hành động còn lại là 4–6, trung bình đo được khoảng 5.5: đây là hệ số phân nhánh `b` của cây trò chơi.

### 2.4 Hàm chuyển trạng thái — `RESULT(s, a1, a2)`
Trò chơi thật là **đồng thời** (simultaneous): cả hai xe ra quyết định trong cùng một chu kỳ. Minimax lại cần các lượt **luân phiên**, nên ta tách mỗi chu kỳ thành **2 ply**:

```
MAX node  n = (s, ∅)       : ACTIONS(n) = ACTIONS(s, MAX);  RESULT(n, a_MAX) = (s, a_MAX)
MIN node  n = (s, a_MAX)   : ACTIONS(n) = ACTIONS(s, MIN);  RESULT(n, a_MIN) = (s', ∅)
                             với s' = RESULT(s, a_MAX, a_MIN) là trạng thái sau một chu kỳ
```
Một **ply** là một nước của một bên, nên **1 chu kỳ = 2 ply**. Từ đây trở đi, độ sâu `m` của cây và độ sâu cắt `d` đều được quy ra ply khi nói về độ phức tạp.

Cách này có tính **bi quan (pessimistic)**: ta giả sử đối thủ phản ứng được với nước đi của ta, nên giá trị minimax là **cận dưới an toàn** cho kết quả của ta (đúng bằng giá trị maximin của trò chơi đồng thời khi chỉ xét chiến lược thuần). Trạng thái chỉ thực sự thay đổi ở nút MIN, sau khi đã biết đủ hai hành động. Cài đặt: `search_agents.py` (`_max_value`, `_min_value`), `GameState.next_state`.

Nút kết thúc và hàm lợi ích chỉ được xét ở nút MAX `(s, ∅)`, vì chỉ ở đó `s` mới là một trạng thái thật của trò chơi.

### 2.5 Trạng thái kết thúc — `TERMINAL-TEST(s)`
`s` là trạng thái kết thúc nếu tank hoặc base của một bên có `hp ≤ 0`, hoặc `turn ≥ max_turns` (`GameState.is_terminal`).

### 2.6 Hàm lợi ích — `UTILITY(s, p)`
```
UTILITY(s, p) = +1 nếu p thắng,  −1 nếu p thua,  0 nếu hòa
UTILITY(s, P1) + UTILITY(s, P2) = 0          → zero-sum
```
Trong tìm kiếm, giá trị này được nhân với `WIN_SCORE = 10^6` và trừ đi số chu kỳ đã qua: `±(10^6 − Δturn)`. Nhờ vậy agent **thắng càng sớm càng tốt** và **thua càng muộn càng tốt**, đồng thời mọi giá trị heuristic luôn nhỏ hơn hẳn một chiến thắng thật.

## 3. Áp dụng các thuật toán tìm kiếm đối kháng

Cả bốn cấu hình dùng **chung một engine** (`AdversarialSearchAgent`), chỉ khác nhau ở hai công tắc:

| Cấu hình | `use_alpha_beta` | `evaluator` | Dừng ở đâu | Lá được chấm bằng |
|---|---|---|---|---|
| Minimax Search | ✗ | không | `TERMINAL-TEST(s)` | `UTILITY` |
| Alpha-Beta Search | ✓ | không | `TERMINAL-TEST(s)` | `UTILITY` |
| Heuristic Minimax | ✗ | `HeuristicEvaluator` | `CUTOFF-TEST(s, d)` | `EVAL(s)` |
| Heuristic Alpha-Beta | ✓ | `HeuristicEvaluator` | `CUTOFF-TEST(s, d)` | `EVAL(s)` + move ordering |

Hai cấu hình đầu là thuật toán **chính xác**: tham số `depth=None`, duyệt đến tận trạng thái kết thúc. Hai cấu hình sau là thuật toán **xấp xỉ**: cắt ở độ sâu `d`.

**Về bản "cắt độ sâu, EVAL = 0".** Muốn cho Minimax / Alpha-Beta thuần chơi trọn một ván trong GUI thì buộc phải cắt độ sâu, mà chúng không có hàm EVAL, nên nút bị cắt chỉ có thể nhận giá trị 0 (coi như hòa). Về lý thuyết, đó là H-Minimax với `EVAL(s) ≡ 0`, **không phải** Minimax của bài giảng. Vì vậy trong menu GUI và trong mọi bảng kết quả, bản này luôn được ghi rõ là `(cutoff, EVAL = 0)`, và các kết luận về Minimax / Alpha-Beta chỉ dựa trên bản duyệt đến trạng thái kết thúc (Experiment A).

### 3.1 Minimax
```
MINIMAX(n) = UTILITY(s)                          nếu TERMINAL-TEST(s)
           = max_a  MINIMAX(RESULT(n, a))        nếu PLAYER(n) = MAX
           = min_a  MINIMAX(RESULT(n, a))        nếu PLAYER(n) = MIN
```
Minimax duyệt theo chiều sâu toàn bộ cây và cho **nước đi tối ưu** trước một đối thủ tối ưu. Độ phức tạp thời gian là `O(b^m)`, không gian là `O(b·m)`, với `b ≈ 5` nhánh mỗi ply và `m = 2 × (số chu kỳ còn lại)` ply. Từ đầu ván với 200 chu kỳ thì `m = 400`: `5^400` nút, không thể duyệt hết (Experiment A: sau 30 giây Minimax mới thăm được khoảng 4.2 triệu nút). Vì thế Minimax chỉ khả thi ở **tàn cuộc**: còn 4 chu kỳ (`m = 8`) đã cần khoảng 8.4·10^5 nút.

### 3.2 Alpha-Beta Pruning
Duy trì `α` (giá trị tốt nhất MAX đã chắc chắn có) và `β` (giá trị tốt nhất MIN đã chắc chắn có), và cắt nhánh khi `v ≥ β` (ở nút MAX) hoặc `v ≤ α` (ở nút MIN). Kết quả **trả về đúng giá trị minimax** nhưng duyệt ít nút hơn nhiều. Điều này được kiểm chứng ở hai chỗ: `tests/test_game.py::test_alpha_beta_equals_minimax_to_terminal_states` (duyệt đến trạng thái kết thúc) và Experiment A (40/40 lần chạy cho cùng giá trị). Nếu thứ tự nước đi hoàn hảo thì độ phức tạp là `O(b^{m/2})`, tức là tìm sâu được gấp đôi với cùng chi phí; với thứ tự ngẫu nhiên là khoảng `O(b^{3m/4})`.

### 3.3 Heuristic Minimax (H-MINIMAX)
Thay `TERMINAL-TEST` bằng `CUTOFF-TEST(s, d)` (dừng khi `d = 0`) và thay `UTILITY` bằng hàm ước lượng `EVAL(s)`:

```
EVAL(s, p) = Side(s, p) − Side(s, q)                 q là đối thủ của p

Side(s, p) =   100·tankHP_p + 70·baseHP_p            f1: lực lượng (máu của tank và base)
             − BulletDanger(p)                        f2: đạn địch đang bay sẽ trúng tank/base của p
             + FirePotential(p)                       f3: khả năng bắn trúng tank/base địch
             − 6.5·(u_base·d_base + u_tank·d_tank)    f4: khoảng cách tới đường bắn (BFS, có tính tường)
             + Cover(p)                               f5: chỗ nấp và đường lui
             + 20·baseHP_q / shots²                   f6: đang đứng trên đường bắn vào base địch (vây base)
```

`EVAL` là **tổng có trọng số của các đặc trưng**, đúng dạng hàm lượng giá của Lecture 07. Vì `EVAL(s, p) = Side(p) − Side(q)` nên `EVAL(s, P1) = −EVAL(s, P2)`: hàm lượng giá vẫn zero-sum (kiểm tra trên 18 000 trạng thái ngẫu nhiên, không có ngoại lệ). |EVAL| chưa bao giờ vượt quá 500 trong các lần đo, nhỏ hơn rất nhiều so với giá trị thắng/thua 10^6, nên một chiến thắng thật luôn được ưu tiên hơn mọi ước lượng.

- **f1 – lực lượng**: 100 điểm cho mỗi máu tank, 70 điểm cho mỗi máu base.
- **f2 – đạn đang bay** (`_bullet_danger`): lần theo đường bay của mỗi viên đạn địch tối đa 9 ô (3 chu kỳ). Nếu nó sẽ trúng base của p: trừ 70 × (1.0 / 0.78 / 0.55 khi còn ≤ 3 / ≤ 6 / ≤ 9 ô). Nếu sẽ trúng tank của p: trừ 100 × hệ số "bị kẹt", hệ số này càng lớn khi đạn càng gần và tank càng ít ô để né sang ngang (0.92 khi đạn tới ngay chu kỳ sau mà không có ô né; 0.08 khi đạn còn xa và né được). Đặc trưng này chống **hiệu ứng chân trời (horizon effect)** khi độ sâu cắt rơi đúng lúc đạn đang bay.
- **f3 – khả năng bắn** (`fire_potential`): nếu xe cùng hàng/cột với tank hoặc base địch và không có tank/base nào chắn giữa, gọi `shots` = 1 + tổng máu các tường chắn giữa. Giá trị = `w × hướng × sẵn_sàng × suy_giảm × ưu_tiên`, với `w` = 62 (tank) hoặc 44 (base); `hướng` = 1 nếu xe đã quay đúng hướng, ngược lại 0.52; `sẵn_sàng` = 1 nếu xe không có đạn đang bay, ngược lại 0.45; `suy_giảm` = 1 nếu `shots` = 1, ngược lại 1/`shots`²; `ưu_tiên` tăng dần tới 1.30 (tank) / 1.35 (base) khi mục tiêu càng ít máu. Cộng thêm 26 điểm (hoặc 0.45 × 26) nếu tank địch nằm trên đường bắn thông mà không có (hoặc chỉ có một) ô để né.
- **f4 – khoảng cách tới đường bắn** (`_lane_distance`, `firing_line_map`): `d` là số bước đi ngắn nhất, **có tính tường** (BFS), từ xe tới ô gần nhất có đường bắn thông tới base địch (`d_base`) hoặc tank địch (`d_tank`). Trọng số `u_base` = 1 + 0.35 × (phần máu base địch đã mất); `u_tank` = 0.55 + 0.30 × (phần máu tank địch đã mất), và được cộng thêm tối đa 1.5 khi tank địch còn cách đường bắn vào base của ta dưới 4 bước (phải đuổi nó đi). Bản đồ khoảng cách BFS được cache theo Zobrist hash của tường, nên hầu hết các lần gọi chỉ là một lần tra bảng.
- **f5 – chỗ nấp và đường lui**: −10 nếu xe chỉ còn ≤ 1 ô trống kề bên (góc chết), +2.5 nếu còn ≥ 3; khi địch chưa có đường bắn thông vào xe thì +3.5 cho mỗi tường kề bên (tối đa 2 tường).
- **f6 – vây base**: một xe đứng trên đường bắn thông tới base địch sẽ bắn trúng base mỗi chu kỳ cho tới khi đường bắn bị phá (bị chặn, hoặc xe bị đuổi đi), nên nó đáng giá một phần số máu base còn lại: `20 × baseHP_q / shots²`. Trước khi có f6, đường bắn chỉ đáng khoảng 44 điểm, ít hơn cả 1 máu base (70). Bên phòng thủ khi đó thấy ra chặn (mất 100 điểm mỗi phát trúng tank) tệ hơn để base mất máu. Base 9 máu lại chết ngoài tầm cắt, nên agent chọn trốn: đây là **hiệu ứng chân trời**. Có f6 thì bên phòng thủ chủ động vào chặn hoặc bắn trả (`test_defender_contests_a_siege_lane`).

Trọng số trong code (`HeuristicEvaluator.__init__`): `w_tank_hp=100, w_base_hp=70, w_bullet=1.0, w_fire_tank=62, w_fire_base=44, w_distance=6.5, w_pin=26, w_cover=3.5, w_siege=1.5, w_lane=20`. Các trọng số được chỉnh tay qua các trận đấu thử (Experiment D), theo nguyên tắc: máu thật luôn đáng giá hơn mọi lợi thế vị trí của một chu kỳ.

### 3.4 Heuristic Minimax + Alpha-Beta và các tối ưu để chạy real-time
Không tối ưu nào dưới đây làm thay đổi giá trị minimax: chúng chỉ đổi **thứ tự** duyệt cây để alpha-beta cắt được nhiều hơn, gộp các nút trùng nhau, hoặc làm mỗi nút rẻ hơn. Điều này được kiểm chứng ở ba chỗ: các unit test `test_all_optimizations_keep_the_minimax_value` và `test_transposition_table_keeps_the_minimax_value_at_depth_4`; cột *Value* của Experiment B (mọi dòng ablation cho cùng giá trị); và một phép thử đối chứng trên 190 thế cờ ngẫu nhiên (độ sâu cắt 1–5 chu kỳ, cả hai phía): giá trị gốc của Heuristic Alpha-Beta đầy đủ luôn bằng giá trị của Heuristic Minimax / alpha-beta không có bảng chuyển vị, và nước được chọn luôn là một nước có giá trị tốt nhất.

1. **Alpha-beta pruning**.
2. **Move ordering nhiều tầng** (`AdversarialSearchAgent._order_node`), theo thứ tự ưu tiên:
   - **TT move**: nước tốt nhất đã lưu trong bảng chuyển vị (từ vòng iterative deepening trước);
   - **Killer moves**: 2 nước gần nhất đã gây cắt tỉa ở cùng ply (một nước tốt ở nút anh em thường cũng tốt ở đây);
   - **History heuristic**: điểm `Σ depth²` của các lần cắt tỉa theo (người chơi, ô, hành động);
   - **Sắp thứ tự chiến thuật** của `HeuristicEvaluator.order_actions`: bắn trúng ngay, né đạn, tiến tới đường bắn, `STAY` cuối.
3. **Bảng chuyển vị (TT)** lưu `(depth, flag, value, best_action)` với cờ `EXACT / LOWER / UPPER`.
   - **Khóa** là **toàn bộ trạng thái** `s` của mục 2.2: vị trí-hướng-máu của 2 tank, máu 2 base, các viên đạn, **Zobrist hash của tường** (`GameState.wall_hash`, XOR các số ngẫu nhiên 64-bit theo `(ô, máu)`, cập nhật tăng dần khi đạn trúng tường, O(1)) và **số lượt `turn`**.
   - Vì sao phải có `turn` trong khóa: trong một lần tìm kiếm tới độ sâu `d`, trạng thái ở lượt `t` còn đúng `d − (t − t_gốc)` chu kỳ để tìm. Hai nút cùng khóa vì thế là **cùng một trạng thái với cùng độ sâu còn lại**, tức một *chuyển vị* đúng nghĩa (cùng một nút, tới bằng thứ tự nước đi khác), và giá trị đã lưu đúng bằng giá trị mà H-Minimax tính tại nút đó. Nước tốt nhất đã lưu ở vòng iterative deepening trước vẫn được dùng để sắp thứ tự.
   - *Lỗi đã sửa (1)*: khóa cũ không chứa máu base và chỉ dùng số lượng/tổng máu tường, nên hai trạng thái khác nhau có thể trùng khóa.
   - *Lỗi đã sửa (2)*: khóa cũ bỏ `turn` để có nhiều lần trúng bảng hơn. Khi cả hai xe "chờ" (ví dụ cùng `STAY`), cùng một thế cờ xuất hiện lại ở lượt sau với độ sâu còn lại nhỏ hơn và được dùng lại giá trị đã tìm **sâu hơn mức cắt của chính nó**. Giá trị gốc khi đó không còn là giá trị H-Minimax: trên một thế của bản đồ open (lượt 26, độ sâu cắt 4), bảng cũ trả về 120.17 và chọn `MOVE_UP`, trong khi H-Minimax cho 119.63 và `MOVE_RIGHT`. Thế cờ này nay là một unit test.
   - Các trạng thái lá (bị cắt độ sâu) gặp lại qua hoán vị nước đi thì dùng lại `EVAL` đã tính (eval cache dùng cùng khóa).
   - TT được xóa ở đầu mỗi nước đi nên bộ nhớ luôn bị chặn; số entry được báo cáo cùng peak memory.
4. **EVAL rẻ hơn**: bản đồ khoảng cách BFS tới đường bắn được cache theo `wall_hash` (tường chỉ đổi khi bị bắn), BFS chạy theo tầng trên chỉ số phẳng với bảng láng giềng dựng sẵn. Chi phí trung bình khoảng 16–20 µs/nút trên máy đo (Experiment B).
5. **Loại bỏ hành động trùng `STAY`** (mục 2.3), **sao chép trạng thái rẻ** (`__slots__`, dict tường copy-on-write).
6. **Iterative deepening dưới ngân sách thời gian (50 ms/nước trong GUI)**:
   - không bắt đầu độ sâu d+1 khi đã dùng quá 40% ngân sách (thêm một chu kỳ là thêm 2 ply, tức tốn khoảng `b*²` lần độ sâu trước, nên gần như chắc chắn không xong);
   - nếu vòng dở dang đã tìm được nước tốt hơn nước tốt nhất cũ (nước cũ luôn được xét trước) thì dùng nước đó;
   - kiểm tra đồng hồ mỗi 4 nút MAX, chừa 3 ms để thoát đệ quy; garbage collector của Python được tạm dừng trong lúc tìm kiếm (search không tạo vòng tham chiếu). Kết quả (Experiment E, 405 nước): p95 là 47.2 ms, nước chậm nhất 47.3 ms.
7. **Phá hòa ở gốc** (sửa lỗi "xe tăng đứng xoay tại chỗ"): mô hình MIN-biết-nước-của-MAX trên bản đồ đối xứng làm nhiều nước có cùng giá trị 0 (đối thủ luôn đi được nước đối xứng). Trong các nước có **cùng giá trị minimax tốt nhất**, agent chọn nước làm tăng phần điểm của chính mình nhiều nhất nếu đối thủ đứng yên (`HeuristicEvaluator.progress`). Quy tắc này **tất định** và chỉ chọn giữa các nước bằng giá trị nhau, nên nước được đi luôn có giá trị minimax tốt nhất (`test_default_agents_play_a_move_of_best_minimax_value`).
8. **Biến thể ngẫu nhiên hóa (tùy chọn, mặc định tắt)**: agent `Heuristic Alpha-Beta (randomized)` trong menu. Hai bản sao của cùng một agent tất định trên bản đồ đối xứng luôn đi các nước đối xứng nhau, nên ván tự đấu nào cũng giống hệt nhau. Biến thể này, với xác suất 0.2, chọn ngẫu nhiên một nước có giá trị minimax cách nước tốt nhất không quá 15 điểm (khoảng 1/5 máu base), nhờ đó các ván tự đấu khác nhau. Đổi lại nó **chủ động bỏ bớt giá trị minimax** nên yếu hơn bản chính: Experiment D đo đúng cái giá đó. Đây chỉ là ngẫu nhiên hóa việc chọn giữa các nước gần tốt nhất, **không phải** chiến lược hỗn hợp tối ưu của trò chơi đồng thời (muốn có chiến lược đó phải giải một trò chơi ma trận ở mỗi chu kỳ). Mọi thực nghiệm về bốn cấu hình đều dùng bản tất định.

### 3.5 Độ phức tạp thời gian và không gian

Ký hiệu: `b` = hệ số phân nhánh (số hành động hợp lệ của một bên, 4–6, trung bình khoảng 5.5), `m` = độ sâu của cây tính bằng ply (với H-Minimax thì `m = 2d`, `d` là độ sâu cắt tính bằng chu kỳ).

| Thuật toán | Độ phức tạp thời gian (số nút của cây đã thăm) | Độ phức tạp không gian (số nút giữ tại một thời điểm) |
|---|---|---|
| Minimax | `O(b^m)` | `O(b·m)` (duyệt theo chiều sâu) |
| Alpha-beta, thứ tự tối ưu | `O(b^{m/2})` (b* = √b) | `O(b·m)` |
| Alpha-beta, thứ tự ngẫu nhiên | khoảng `O(b^{3m/4})` | `O(b·m)` |
| H-AlphaBeta + TT (độ sâu cắt d) | tốt nhất `O(b^{m/2}) = O(b^d)` | `O(b·2d)` + số entry TT |

> **Bộ nhớ (space complexity): số nút tối đa được giữ tại một thời điểm**
> - Tìm kiếm minimax/alpha-beta là **tìm kiếm theo chiều sâu**: tại một thời điểm chỉ giữ đường đi từ gốc tới nút hiện tại (m nút) và các nút con chưa duyệt của mỗi nút trên đường đi. Vậy bộ nhớ là **`O(b·m)`**, không phải `O(b^m)`.
> - Chương trình đo đúng đại lượng này (`SearchStats.peak_memory`): mỗi nút khi sinh danh sách hành động thì cộng số nút con vào bộ đếm, mỗi nút con duyệt xong thì trừ đi. Cận trên là `1 + 6·m`.
> - Số đo thực tế (Experiment A, B): m = 2, 4, 6, 8 ply → 13, 25, 37, **48 nút**; m = 10 ply → 55–59 nút, trong khi số nút đã thăm là hàng nghìn tới hàng triệu. Peak memory của Minimax và Alpha-Beta **bằng nhau** ở cùng m (Experiment A), vì cắt tỉa giảm số nút thăm chứ không giảm độ sâu.
> - Transposition table là bộ nhớ trả thêm để đổi lấy thời gian: ở độ sâu cắt 5 chu kỳ là 2 672 entry trên classic (so với 7 720 nút thăm), 8 398 trên duel, 5 710 trên open; trong ván thật với 50 ms/nước, tối đa khoảng 1 100 entry (Experiment E). TT được xóa mỗi nước đi nên không tích lũy.
> - Các bảng cache dùng chung giữa các nước đi (bản đồ khoảng cách BFS, bảng Zobrist) có giới hạn kích thước cố định (50 000 bản đồ) và tự xóa khi đầy.

### 3.6 Khi bản đồ lớn lên thì thuật toán có còn phù hợp không? (Experiment F)

Experiment F chạy cùng một agent (Heuristic Alpha-Beta đầy đủ, thế khai cuộc) trên các bản đồ đối xứng tâm sinh tự động bằng `scaled_map(n)` trong `experiments.py`:

| Bản đồ | Số ô | b ở gốc | Khoảng cách tới đường bắn (bước) | Một trường BFS (ms) | Nút, d = 3 | Nút, d = 4 | Peak memory, d = 4 | Thời gian, d = 4 (ms) |
|---|---|---|---|---|---|---|---|---|
| 7×7 | 49 | 6 | 7 | 0.05 | 577 | 1 420 | 46 | 21.9 |
| 13×13 | 169 | 6 | 11 | 0.18 | 621 | 1 280 | 49 | 25.6 |
| 25×25 | 625 | 6 | 19 | 0.63 | 621 | 1 281 | 49 | 27.7 |
| 49×49 | 2 401 | 6 | 35 | 2.45 | 621 | 1 281 | 49 | 39.0 |

1. **Cây tìm kiếm không phụ thuộc kích thước bản đồ.** Hệ số phân nhánh `b ≤ 6` do số hành động quyết định, không do số ô. Ở cùng độ sâu cắt, số nút (khoảng 1 300 ở d = 4) và peak memory (46–49 nút) gần như không đổi từ 49 ô lên 2 401 ô. Thời gian mỗi nút tăng nhẹ vì các phép tra trên lưới lớn hơn.
2. **Cái thay đổi là tầm nhìn.** Khoảng cách từ xe tới ô đầu tiên có đường bắn vào base địch tăng từ 7 lên 35 bước, trong khi độ sâu cắt 4 chu kỳ chỉ nhìn trước được 4 bước. Trên bản đồ lớn, mục tiêu nằm ngoài chân trời tìm kiếm; tăng độ sâu cho đủ là bất khả thi vì số nút tăng theo `b^m`.
3. **Vì vậy EVAL phải mang thông tin toàn cục.** Đặc trưng f4 dùng **trường khoảng cách BFS có tính tường** tới các đường bắn (mục 3.3). Chi phí một trường là `O(H·W)` (0.05 ms ở 7×7, 2.45 ms ở 49×49), được cache theo Zobrist hash của tường nên chỉ tính lại khi có tường bị phá. Tìm kiếm đối kháng lo phần chiến thuật gần (né đạn, đấu súng trong vài chu kỳ), còn EVAL dẫn xe đi đúng hướng tới mục tiêu ở xa. Nếu dùng khoảng cách Manhattan không xét tường thì xe sẽ bị kẹt sau các bức tường dài.

### 3.7 Tóm tắt kết quả (Requirement 2)

Số liệu đầy đủ ở `results/summary.md`, tạo lại bằng `python experiments.py`. Các bộ đếm (nút, cắt tỉa, độ sâu) là tất định; chỉ có cột giây thay đổi theo máy. Experiment D và E dùng agent có ngân sách thời gian nên kết quả ván đấu có thể lệch đôi chút giữa các lần chạy.

**A. Tìm kiếm chính xác đến trạng thái kết thúc** (trung bình trên 10 thế tàn cuộc; biểu đồ `results/exact_search.png`)

| m (ply) | Nút Minimax | Nút Alpha-Beta | Giảm | b* Minimax | b* Alpha-Beta | Cùng giá trị minimax |
|---|---|---|---|---|---|---|
| 2 | 36 | 20 | 1.8 lần | 5.45 | 3.88 | 10/10 |
| 4 | 1 004 | 179 | 5.6 lần | 5.34 | 3.35 | 10/10 |
| 6 | 28 780 | 1 166 | 24.7 lần | 5.35 | 3.04 | 10/10 |
| 8 | 838 067 | 7 347 | 114.1 lần | 5.36 | 2.89 | 10/10 |

- Số nút của Minimax tăng đúng theo `b^m` với `b ≈ 5.36`: mỗi lần thêm 2 ply, số nút tăng khoảng 29 lần (≈ 5.36²).
- Alpha-Beta cho **đúng giá trị minimax** trong cả 40 lần chạy. Hệ số phân nhánh hiệu dụng giảm dần về 2.89, nằm giữa trường hợp tốt nhất `√b ≈ 2.32` và trường hợp thứ tự ngẫu nhiên `b^{3/4} ≈ 3.52`. Ở đây Alpha-Beta thuần không có move ordering, nên kết quả này phù hợp với lý thuyết.
- Peak memory là 13, 25, 37, 48 nút, bằng nhau ở hai thuật toán: bộ nhớ chỉ tăng tuyến tính theo độ sâu trong khi số nút tăng theo hàm mũ.
- Từ thế khai cuộc (`m = 400` ply), sau 30 giây Minimax mới thăm khoảng 4.2 triệu nút và Alpha-Beta 5.0 triệu nút, cả hai đều chưa xong. Đây là lý do phải dùng H-Minimax.

**B. Tìm kiếm cắt độ sâu** (bản đồ classic, thế khai cuộc; ablation cộng dồn từng tối ưu)

| Độ sâu cắt | H-Minimax | H-AB không sắp thứ tự, không TT | + sắp thứ tự chiến thuật | + killer & history | + TT (đầy đủ) | Peak memory | TT entries |
|---|---|---|---|---|---|---|---|
| 2 chu kỳ (4 ply) | 1 330 | 324 | 163 | 166 | 166 | 23 | 85 |
| 3 chu kỳ (6 ply) | 40 460 | 2 208 | 1 177 | 1 087 | 847 | 35 | 297 |
| 4 chu kỳ (8 ply) | 1 229 015 | 22 194 | 5 610 | 4 222 | **1 807** (29 ms) | 47 | 572 |
| 5 chu kỳ (10 ply) | quá 30 giây | 247 056 | 91 743 | 29 574 | **7 720** (124 ms) | 59 | 2 672 |

- Mọi dòng trả về cùng giá trị với H-Minimax, trên cả ba kịch bản.
- Ở 5 chu kỳ, bản đầy đủ thăm ít hơn **32 lần** so với alpha-beta không sắp thứ tự (247 056 → 7 720 nút) và `b*` giảm từ 3.34 xuống 2.31, sát mức tối ưu `√b ≈ 2.4`. Trên duel và open, giảm tương ứng 12.5 và 13.1 lần (`b*` = 2.57 và 2.49).
- Sắp thứ tự chiến thuật không phải lúc nào cũng tốt (trên open-combat còn tệ hơn không sắp thứ tự); killer/history và TT sửa lại điều đó vì chúng học từ chính các lần cắt tỉa trong cây.

**C. Chất lượng quyết định** (10 thế tàn cuộc, so với giá trị minimax chính xác)
- Minimax và Alpha-Beta duyệt đến trạng thái kết thúc: 10/10 nước tối ưu, nhưng Minimax cần 838 067 nút, Alpha-Beta cần 7 346 nút.
- Ở độ sâu cắt 1 chu kỳ, H-Minimax và H-Alpha-Beta chọn đúng 7/10 (36 và 23 nút); bản cắt độ sâu không có heuristic (EVAL = 0) chỉ đúng 6/10, vì thắng/thua nằm ngoài tầm nhìn thì mọi nước đều có giá trị 0. Chọn ngẫu nhiên thì kỳ vọng đúng 2.2/10.
- Từ độ sâu cắt 2 chu kỳ trở lên, mọi cấu hình đều chọn đúng 10/10; H-Alpha-Beta chỉ cần 214 nút.

**D. Thi đấu vòng tròn** (độ sâu cắt 2 chu kỳ, bản đồ duel và open, đổi bên, 24 ván mỗi agent)

| Agent | Thắng | Hòa | Thua | ms/nước (TB) | ms/nước (max) | Nút/nước (TB) |
|---|---|---|---|---|---|---|
| Minimax (cutoff, EVAL = 0) | 0 | 8 | 16 | 6.9 | 10.9 | 1 119 |
| Alpha-Beta (cutoff, EVAL = 0) | 0 | 8 | 16 | 0.7 | 3.0 | 124 |
| Heuristic Minimax | 13 | 11 | 0 | 22.2 | 38.4 | 1 115 |
| Heuristic Alpha-Beta | 13 | 11 | 0 | 2.8 | 8.9 | 143 |
| Random | 0 | 8 | 16 | 0.0 | — | — |
| Agent của GUI (iterative deepening, 50 ms) | 12 | 12 | 0 | 35.6 | 49.4 | 1 893 |
| Biến thể ngẫu nhiên hóa | 12 | 10 | 2 | 36.0 | 55.8 | 1 936 |

- Hai cấu hình heuristic không thua ván nào; bản cắt độ sâu với EVAL = 0 không thắng ván nào (ngang với Random). H-Alpha-Beta cho cùng kết quả thi đấu với H-Minimax nhưng chỉ cần 2.8 ms mỗi nước thay vì 22.2 ms (143 nút thay vì 1 115).
- Agent của GUI không thua ván nào. Các ván hòa là hai tank đấu súng đối xứng và cùng hết máu: trên bản đồ đối xứng với hai agent dùng cùng hàm EVAL, đó là kết quả hợp lý.
- Biến thể ngẫu nhiên hóa thua 2 ván (đều trên bản đồ open, trước Heuristic Minimax và Heuristic Alpha-Beta độ sâu 2): đây là cái giá của việc thỉnh thoảng chọn một nước kém hơn tối đa 15 điểm, và là lý do agent mặc định không dùng nó.

**E. Thời gian thực** (agent của GUI đấu Heuristic Minimax độ sâu 2, 6 ván mỗi bản đồ, đổi bên, tổng 405 nước)

| Bản đồ | Thắng/Hòa/Thua | Số nước | ms p50 | ms p95 | ms max | Độ sâu TB (min–max) | Nút/nước max | Peak memory max | TT max |
|---|---|---|---|---|---|---|---|---|---|
| classic | 6/0/0 | 237 | 26.6 | 47.1 | 47.3 | 2.94 (1–4) | 2 932 | 49 | 1 037 |
| duel | 0/6/0 | 72 | 44.5 | 47.2 | 47.2 | 3.74 (3–5) | 3 186 | 55 | 908 |
| open | 0/6/0 | 96 | 47.1 | 47.2 | 47.3 | 3.06 (3–4) | 2 905 | 47 | 1 124 |

- Mọi nước đều nằm trong ngân sách 50 ms (chậm nhất 47.3 ms). Trong cùng 50 ms, agent tìm sâu 3–4 chu kỳ (6–8 ply), so với 2 chu kỳ của Heuristic Minimax.
- Độ sâu nhỏ nhất bằng 1 chỉ xuất hiện ở các nước cuối ván, khi độ sâu 1 đã chứng minh được thắng/thua và vòng lặp dừng sớm.

**F. Mở rộng bản đồ**: xem mục 3.6.
