# Requirement 1 — Mô hình hóa Tank Battle thành trò chơi Zero-Sum

> Tài liệu này là phần lý thuyết cho Requirement 1. Mỗi khái niệm đều chỉ ra chỗ cài đặt trong code để dễ giải thích khi vấn đáp.

## 1. Luật chơi được cài đặt

Đề bài chỉ quy định khung chung, nên nhóm cố định thêm một số chi tiết (đánh dấu ★ là giả định do nhóm tự đặt):

| Thành phần | Quy tắc |
|---|---|
| Bản đồ | Lưới `H × W`, ô trống / tường gạch. Mỗi bên có 1 xe tăng và 1 căn cứ (base). |
| Máu | Tank 6, Base 9, Wall 3; mỗi phát trúng trừ 1 (bảng trong đề). |
| Hành động | `MOVE_UP, MOVE_DOWN, MOVE_LEFT, MOVE_RIGHT, FIRE, STAY` |
| Di chuyển | `MOVE_x` xoay xe về hướng x, rồi tiến 1 ô nếu ô đó trống (không tường/base/tank/biên). ★ Hai xe cùng muốn vào một ô → cả hai đứng yên. |
| Bắn | Đạn xuất phát từ ô của xe, bay theo hướng xe đang quay, **3 ô / chu kỳ**, kiểm tra va chạm **sau mỗi ô**, dừng ngay khi trúng tường/tank/base. ★ Mỗi xe chỉ có tối đa 1 viên đạn đang bay (giống Battle City). Đúng như đề, đạn chỉ va chạm với tường, tank và base; hai viên đạn **không** chặn nhau. |
| Thứ tự trong 1 chu kỳ | (1) cả hai xe di chuyển → (2) đạn mới được bắn ra → (3) mọi viên đạn bay 3 ô, từng ô một. |
| Kết thúc | Khi một tank hoặc một base bị phá hủy. Cả hai bên cùng mất → hòa. ★ Giới hạn `max_turns` (mặc định 200) → hòa, đảm bảo cây trò chơi hữu hạn. |

Cài đặt: `tank_battle/core/game_state.py` (`apply_cycle`, `_advance_bullets_one_cell`, `_collide`).

## 2. Các thành phần của trò chơi Zero-Sum

### 2.1 Người chơi — `PLAYER(n)`
Hai người chơi: **P1 (vàng)** và **P2 (xanh)**. Khi agent của ta tìm kiếm, ta là **MAX**, đối thủ là **MIN**.

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

Việc này không làm thay đổi giá trị minimax (chỉ bỏ các cây con trùng lặp) nhưng giảm hệ số phân nhánh `b` từ 6 xuống còn khoảng 4–6.

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
Minimax duyệt theo chiều sâu toàn bộ cây và cho **nước đi tối ưu** trước một đối thủ tối ưu. Độ phức tạp thời gian là `O(b^m)`, không gian là `O(b·m)`, với `b ≈ 5` nhánh mỗi ply và `m = 2 × (số chu kỳ còn lại)` ply. Từ đầu ván với 200 chu kỳ thì `m = 400`: `5^400` nút, không thể duyệt hết (Experiment A: sau 30 giây Minimax mới thăm được 4.7 triệu nút). Vì thế Minimax chỉ khả thi ở **tàn cuộc**: còn 4 chu kỳ (`m = 8`) đã cần khoảng 8.4·10^5 nút.

### 3.2 Alpha-Beta Pruning
Duy trì `α` (giá trị tốt nhất MAX đã chắc chắn có) và `β` (giá trị tốt nhất MIN đã chắc chắn có), và cắt nhánh khi `v ≥ β` (ở nút MAX) hoặc `v ≤ α` (ở nút MIN). Kết quả **trả về đúng giá trị minimax** nhưng duyệt ít nút hơn nhiều. Điều này được kiểm chứng ở hai chỗ: `tests/test_game.py::test_alpha_beta_equals_minimax_to_terminal_states` (duyệt đến trạng thái kết thúc) và Experiment A (40/40 lần chạy cho cùng giá trị). Nếu thứ tự nước đi hoàn hảo thì độ phức tạp là `O(b^{m/2})`, tức là tìm sâu được gấp đôi với cùng chi phí; với thứ tự ngẫu nhiên là khoảng `O(b^{3m/4})`.

### 3.3 Heuristic Minimax (H-MINIMAX)
Thay `TERMINAL-TEST` bằng `CUTOFF-TEST(s, d)` (dừng khi `d = 0`) và thay `UTILITY` bằng hàm ước lượng `EVAL(s)`:

```
EVAL(s, p) = w1·(tankHP_p − tankHP_q) + w2·(baseHP_p − baseHP_q)          f1, f2: lợi thế máu
           + w3·Σ(sát thương dự kiến của các viên đạn đang bay)          f3: đạn sẽ trúng ai
           + FirePotential(p) − FirePotential(q)                         f4: khả năng bắn trúng
           + w5·(dist_q − dist_p)                                        f5: tiến tới base địch
```
- **f3**: lần theo đường bay của mỗi viên đạn (tối đa 9 ô) để biết nó sẽ trúng tank/base của ai. Đặc trưng này giúp tránh **hiệu ứng chân trời (horizon effect)** khi độ sâu cắt rơi đúng lúc đạn đang bay.
- **f4**: nếu xe đứng cùng hàng/cột với tank hoặc base địch, giá trị là `w / (số phát cần bắn)`, trong đó số phát = 1 + tổng máu các tường chắn giữa. Giá trị bị giảm một nửa nếu xe chưa quay đúng hướng hoặc đang có đạn bay.
- **f5**: "khoảng cách tới đường bắn" `min(|Δr|, |Δc|) + 0.1·Manhattan` tới base địch (và tank địch, trọng số 0.5).
- `EVAL(s, P1) = −EVAL(s, P2)` nên vẫn giữ tính zero-sum. Trọng số: `w1=100, w2=70, w3=0.8, w_fire_tank=60, w_fire_base=40, w5=6` (`heuristics.py`).

### 3.4 Heuristic Minimax + Alpha-Beta và các tối ưu để chạy real-time
1. **Alpha-beta pruning**.
2. **Move ordering** (`HeuristicEvaluator.order_actions`): xét trước `FIRE` khi đang ngắm trúng mục tiêu, sau đó các nước tiến gần đường bắn, `STAY` xét sau cùng. Ở gốc, nước tốt nhất của vòng lặp trước (PV move) được xét đầu tiên. Thứ tự không làm đổi giá trị trả về, chỉ làm tăng số nhánh bị cắt.
3. **Iterative deepening + giới hạn thời gian**: tìm ở độ sâu 1, 2, 3, … cho đến khi hết thời gian (mặc định 0,5 s mỗi nước trong GUI) và trả về kết quả của độ sâu cuối cùng đã hoàn thành. Nhờ vậy agent luôn trả lời đúng hạn (anytime).
4. **Loại bỏ hành động trùng `STAY`** (mục 2.3).
5. **Sao chép trạng thái rẻ**: dùng `__slots__`; dict tường được dùng chung (copy-on-write) và chỉ sao chép khi có tường bị bắn.
6. Dừng iterative deepening sớm khi đã chứng minh được thắng/thua chắc chắn.

### 3.5 Độ phức tạp và cách đo

Ký hiệu: `b` = hệ số phân nhánh (số hành động hợp lệ của một bên, 4–6), `m` = độ sâu của cây tính bằng ply (với H-Minimax thì `m = 2d`, `d` là độ sâu cắt tính bằng chu kỳ).

| | Thời gian | Không gian |
|---|---|---|
| Minimax | `O(b^m)` | `O(b·m)` (tìm kiếm theo chiều sâu) |
| Alpha-beta, thứ tự tốt nhất | `O(b^{m/2})` | `O(b·m)` |
| Alpha-beta, thứ tự ngẫu nhiên | khoảng `O(b^{3m/4})` | `O(b·m)` |

Thực nghiệm đo đúng các đại lượng xuất hiện trong bảng trên, không đo bằng công cụ của hệ điều hành:

- **Thời gian = số nút của cây trò chơi đã thăm** (`SearchStats.nodes`, gồm cả nút MAX và nút MIN). Số giây chỉ là số liệu đi kèm, vì nó phụ thuộc máy.
- **Hệ số phân nhánh hiệu dụng `b*`**: nghiệm của `N = 1 + b* + (b*)² + … + (b*)^m`, với `N` là số nút đã thăm. Đây là `b` của một cây đều có cùng độ sâu và cùng số nút. So `b*` của alpha-beta với `b` và `√b` cho biết cắt tỉa đang gần trường hợp tốt nhất đến đâu.
- **Không gian = độ sâu lớn nhất đã tới** (`SearchStats.max_ply`). Tìm kiếm theo chiều sâu chỉ giữ một nhánh trong bộ nhớ, nên bộ nhớ tỉ lệ với `b·m` chứ không tỉ lệ với số nút.

### 3.6 Tóm tắt kết quả (Requirement 2)

Số liệu đầy đủ ở `results/summary.md`, tạo lại bằng `python experiments.py`. Các bộ đếm (nút, cắt tỉa, độ sâu) là tất định; chỉ có cột giây thay đổi theo máy.

**A. Tìm kiếm chính xác đến trạng thái kết thúc** (trung bình trên 10 thế tàn cuộc; biểu đồ `results/exact_search.png`)

| m (ply) | Nút Minimax | Nút Alpha-Beta | Giảm | b* Minimax | b* Alpha-Beta | Cùng giá trị minimax |
|---|---|---|---|---|---|---|
| 2 | 36 | 20 | 1.8 lần | 5.45 | 3.88 | 10/10 |
| 4 | 1 004 | 179 | 5.6 lần | 5.34 | 3.35 | 10/10 |
| 6 | 28 780 | 1 166 | 24.7 lần | 5.35 | 3.04 | 10/10 |
| 8 | 838 067 | 7 347 | 114.1 lần | 5.36 | 2.89 | 10/10 |

- Số nút của Minimax tăng đúng theo `b^m` với `b ≈ 5.36`: mỗi lần thêm 2 ply, số nút tăng khoảng 29 lần (≈ 5.36²).
- Alpha-Beta cho **đúng giá trị minimax** trong cả 40 lần chạy. Hệ số phân nhánh hiệu dụng giảm dần về 2.89, nằm giữa trường hợp tốt nhất `√b ≈ 2.32` và trường hợp thứ tự ngẫu nhiên `b^{3/4} ≈ 3.52`. Ở đây Alpha-Beta thuần không có move ordering, nên kết quả này phù hợp với lý thuyết.
- Độ sâu lớn nhất đã tới đúng bằng `m`, tức là bộ nhớ chỉ tăng tuyến tính theo độ sâu trong khi số nút tăng theo hàm mũ.
- Từ thế khai cuộc (`m = 400` ply), sau 30 giây Minimax mới thăm 4.7 triệu nút và Alpha-Beta 5.4 triệu nút, cả hai đều chưa xong. Đây là lý do phải dùng H-Minimax.

**B. Tìm kiếm cắt độ sâu** (bản đồ classic, thế khai cuộc)

| Độ sâu cắt | Nút H-Minimax | Nút H-Alpha-Beta | Nút H-Alpha-Beta không sắp thứ tự |
|---|---|---|---|
| 2 chu kỳ (4 ply) | 1 330 | 121 | 270 |
| 3 chu kỳ (6 ply) | 40 460 | 698 | 1 804 |
| 4 chu kỳ (8 ply) | 1 229 015 | 3 887 | 12 746 |
| 5 chu kỳ (10 ply) | quá 30 giây | 21 481 | 114 120 |

- Với cùng độ sâu cắt, H-Alpha-Beta trả về cùng giá trị với H-Minimax ở mọi dòng, nhưng `b*` giảm từ khoảng 5.6 xuống 2.6.
- Move ordering giảm thêm 2 đến 5 lần số nút ở độ sâu 4–5 chu kỳ, đúng với lý thuyết: thứ tự càng tốt thì alpha-beta càng gần `O(b^{m/2})`.

**C. Chất lượng quyết định** (10 thế tàn cuộc, so với giá trị minimax chính xác)
- Minimax và Alpha-Beta duyệt đến trạng thái kết thúc: 10/10 nước tối ưu, nhưng Minimax cần 838 066 nút, Alpha-Beta cần 7 346 nút.
- Ở độ sâu cắt 1 chu kỳ, H-Minimax và H-Alpha-Beta chọn đúng 7/10 (36 và 20 nút); bản cắt độ sâu không có heuristic (EVAL = 0) chỉ đúng 6/10, vì thắng/thua nằm ngoài tầm nhìn thì mọi nước đều có giá trị 0. Chọn ngẫu nhiên thì kỳ vọng đúng 2.2/10.
- Từ độ sâu cắt 2 chu kỳ trở lên, mọi cấu hình đều chọn đúng 10/10; H-Alpha-Beta chỉ cần 159 nút.

**D. Thi đấu vòng tròn** (độ sâu cắt 2 chu kỳ, 20 ván mỗi agent): hai cấu hình heuristic thắng 12, hòa 8, thua 0. Bản cắt độ sâu với EVAL = 0 không thắng ván nào (ngang với Random), vì ở độ sâu 2 chu kỳ nó hầu như không nhìn thấy trạng thái kết thúc nào. H-Alpha-Beta trung bình 1.7 ms mỗi nước so với 11.3 ms của H-Minimax, với cùng kết quả thi đấu.

