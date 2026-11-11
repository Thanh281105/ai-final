# Requirement 1 — Mô hình hóa Kakuro thành CSP và các kỹ thuật giải

> Tài liệu này là phần lý thuyết cho Requirement 1. Mỗi khái niệm đều chỉ ra chỗ cài đặt trong code để dễ giải thích khi vấn đáp. Toàn bộ kỹ thuật dùng ở đây đều thuộc Lecture 08 (AIMA chương 6): Backtracking Search, Forward Checking, Arc Consistency / AC-3 / MAC, MRV, Degree, LCV. Không dùng học máy.

## 1. Luật chơi Kakuro

- Bàn cờ gồm **ô đen**, **ô gợi ý** (ô đen có đường chéo, mang số) và **ô trắng**.
- Một **run** (dãy) là một khối ô trắng liên tiếp theo hàng hoặc theo cột. Mỗi run có đúng một ô gợi ý đứng ngay trước nó:
  - số ở **góc trên-phải** là tổng của run đi **sang phải** (across);
  - số ở **góc dưới-trái** là tổng của run đi **xuống dưới** (down).
- Phải điền vào mỗi ô trắng một chữ số **1..9** sao cho trong mỗi run:
  1. các chữ số **đôi một khác nhau**;
  2. **tổng** các chữ số **bằng** số gợi ý.

Định dạng file đề (`puzzles/*.txt`): `#` là ô đen, `.` là ô trắng, `D\R` là ô gợi ý (D = tổng cột đi xuống, R = tổng hàng sang phải), ví dụ `14\12`, `21\` (chỉ có gợi ý dọc), `\16` (chỉ có gợi ý ngang). Đọc file và tách run: `kakuro/core/board.py` (`KakuroBoard._find_runs`).

## 2. Mô hình CSP ⟨X, D, C⟩

Cài đặt: `kakuro/csp/model.py` (`KakuroCSP`) và `kakuro/csp/constraint.py` (`SumAllDiffConstraint`).

### 2.1 Biến — X
Mỗi **ô trắng** là một biến: `X = { x(r,c) | ô (r, c) là ô trắng }`.

| Đề | Số biến | Số ràng buộc (run) | Độ dài run | Không gian tìm kiếm thô |
|---|---|---|---|---|
| `example_5x5` | 12 | 8 | 2..4 | 9¹² ≈ 2.8·10¹¹ |
| `complex_9x9` | 48 | 28 | 2..8 | 9⁴⁸ ≈ 6.4·10⁴⁵ |

### 2.2 Miền giá trị — D
`D(x) = {1, 2, …, 9}` cho mọi biến (`KakuroCSP.initial_domains`). Không cần tự tay thu hẹp miền trước: bước AC-3 ban đầu (mục 3.3) sẽ tự làm việc đó, và thu hẹp rất mạnh.

### 2.3 Ràng buộc — C
Với mỗi run `R = (x₁, …, x_k)` có tổng gợi ý `s`, ta đặt **một ràng buộc k-ngôi**:

```
SumAllDiff(R):   AllDifferent(x₁, …, x_k)   ∧   x₁ + x₂ + … + x_k = s
```

Mỗi ô trắng thuộc đúng **2 ràng buộc**: một run ngang và một run dọc. Với đề mẫu 5x5 có 8 ràng buộc, ví dụ:

| Ô gợi ý | Run | Ràng buộc |
|---|---|---|
| (1,1) gợi ý ngang 12 | x(1,2), x(1,3) | x(1,2) ≠ x(1,3), x(1,2) + x(1,3) = 12 |
| (0,2) gợi ý dọc 21 | x(1,2), x(2,2), x(3,2), x(4,2) | AllDiff, tổng = 21 |
| (4,1) gợi ý ngang 16 | x(4,2), x(4,3) | AllDiff, tổng = 16 ⇒ {7, 9} |
| … | … | … |

**Đồ thị ràng buộc** (constraint graph): hai biến kề nhau nếu cùng thuộc một run (`KakuroCSP.neighbors`). Vì ràng buộc là n-ngôi nên đây thực chất là siêu đồ thị: mỗi run là một siêu cạnh nối k biến.

**Vì sao giữ nguyên ràng buộc n-ngôi mà không tách thành các ràng buộc nhị phân `≠`?** Có thể viết AllDifferent thành k(k−1)/2 ràng buộc `xᵢ ≠ xⱼ`, nhưng ràng buộc tổng thì không tách nhị phân được nếu không thêm biến phụ. Hơn nữa, "tổng" và "khác nhau" đứng chung thì suy luận được nhiều hơn hẳn khi đứng riêng. Ví dụ run 2 ô tổng 3: chỉ riêng `≠` hoặc chỉ riêng tổng đều không loại được gì nhiều, nhưng gộp lại thì biết ngay tập chữ số phải là {1, 2}.

### 2.4 Bảng tổ hợp chữ số
`digit_combinations(k, s)` (`constraint.py`) liệt kê mọi tập k chữ số phân biệt có tổng s, ví dụ:

| k, s | Tổ hợp |
|---|---|
| 2, 3 | {1,2} |
| 2, 16 | {7,9} |
| 2, 17 | {8,9} |
| 4, 11 | {1,2,3,5} |
| 7, 28 | {1,2,3,4,5,6,7} |
| 8, 44 | {2,3,4,5,6,7,8,9} |

Với mọi (k, s) có nhiều nhất 12 tổ hợp, nên kiểm tra một giá trị theo bảng này rất rẻ. Bảng được tính một lần và lưu cache (`lru_cache`).

### 2.5 Trạng thái, phép gán, kiểm tra mục tiêu
- **Trạng thái**: một phép gán bộ phận `assignment: x → giá trị` cùng các miền hiện tại.
- **Phép gán nhất quán** (consistent): không vi phạm ràng buộc nào. Với phép gán bộ phận, run R bị coi là vi phạm nếu các ô đã gán có chữ số trùng nhau, hoặc tổng của chúng ≥ s khi run còn ô trống (mỗi ô trống còn cộng thêm ít nhất 1), hoặc tổng ≠ s khi run đã đầy (`SumAllDiffConstraint.is_consistent`).
- **Mục tiêu**: phép gán đầy đủ và nhất quán. Mọi lời giải đều được kiểm tra lại bằng một bộ kiểm tra độc lập, viết thẳng từ luật chơi (`KakuroBoard.is_solution`).

## 3. Thuật toán và kỹ thuật

### 3.1 Backtracking Search
Cài đặt: `kakuro/csp/solver.py` (`BacktrackingSolver._backtrack`). Cấu trúc theo AIMA Fig. 6.5:

```
BACKTRACK(assignment):
    if assignment đầy đủ: return assignment
    var ← SELECT-UNASSIGNED-VARIABLE()                 # Static / MRV / MRV+Degree
    for value in ORDER-DOMAIN-VALUES(var):             # Ascending / LCV
        if value nhất quán với assignment:
            gán var = value;  D(var) ← {value}
            if INFERENCE(var) không làm rỗng miền nào:   # None / FC / MAC
                result ← BACKTRACK(assignment)
                if result ≠ failure: return result
            hủy var = value và mọi giá trị đã bị tỉa kể từ lúc gán
    return failure
```

- **Trail (vết)**: miền được sửa tại chỗ. Mỗi giá trị bị xóa được đẩy vào một ngăn xếp `trail`. Khi quay lui, chỉ cần pop trail về mốc đã lưu là các miền được khôi phục đúng như cũ. Cách này rẻ hơn sao chép toàn bộ miền ở mỗi nút (`_assign`, `_undo`, `prune`). Test `test_domains_restored_after_search` kiểm tra rằng sau khi duyệt hết cây, các miền quay về đúng như ban đầu.
- Backtracking là thuật toán **đầy đủ** (complete): nếu có lời giải thì chắc chắn tìm được, nếu không có thì chứng minh được là vô nghiệm. Đặt `max_solutions = 2` để tìm tiếp lời giải thứ hai: không tìm thấy nghĩa là đề có **nghiệm duy nhất**.
- **Độ phức tạp thời gian** xấu nhất là O(dⁿ) = O(9ⁿ): cây tìm kiếm có n tầng (mỗi tầng gán một biến), mỗi nút có tối đa d = 9 nhánh. Vì vậy trong thực nghiệm, chi phí thời gian được đo bằng **số nút của cây tìm kiếm** (số phép gán đã thử, `nodes`), **số lần quay lui** (`backtracks`) và **số lần kiểm tra ràng buộc** (`checks`). Thời gian chạy tính bằng giây chỉ là số liệu phụ, vì nó phụ thuộc máy.
- **Độ phức tạp không gian** là O(n) cho độ sâu đệ quy (backtracking là tìm kiếm theo chiều sâu, chỉ giữ một nhánh), cộng O(n·d) cho trail (mỗi giá trị của mỗi biến bị xóa nhiều nhất một lần trên một nhánh). Thực nghiệm đo đúng hai đại lượng này: **độ sâu lớn nhất** (`max_depth`) và **độ dài trail lớn nhất** (`max_trail`). Nhóm không đo bộ nhớ bằng công cụ của hệ điều hành hay của Python, vì con số đó phản ánh cách cài đặt chứ không phản ánh thuật toán.

### 3.2 Constraint propagation: REVISE cho ràng buộc n-ngôi (GAC)
Cài đặt: `kakuro/csp/inference.py` (`AC3.revise`) và `SumAllDiffConstraint.supported_values`.

Với ràng buộc n-ngôi, khái niệm **arc consistency** được mở rộng thành **Generalized Arc Consistency (GAC)**:

> Một **cung** là cặp (Y, C) gồm một biến Y và một ràng buộc C chứa Y. Giá trị v ∈ D(Y) có **support** trong C nếu tồn tại một bộ giá trị cho mọi biến của C, mỗi giá trị lấy từ miền của biến đó, với Y = v và thỏa C. REVISE(Y, C) xóa khỏi D(Y) mọi giá trị không có support.

Cách kiểm tra support hiệu quả cho SumAllDiff: v có support ⇔ tồn tại một tổ hợp T (trong bảng ở mục 2.4) sao cho v ∈ T, và các chữ số còn lại T − {v} **ghép được một-một** với các ô còn lại của run, mỗi ô nhận một chữ số nằm trong miền của nó. Việc ghép này là bài toán **ghép cặp hai phía** (bipartite matching), giải bằng thuật toán đường tăng (Kuhn) `_matchable`. Run dài tối đa 9 ô nên bước ghép rất nhỏ.

Ví dụ trên đề 5x5: run ngang 16 gồm (4,2), (4,3) chỉ có tổ hợp {7,9}, nên D = {7,9}. Run dọc 21 chứa (4,2) có 4 ô. Sau khi các run khác bị thu hẹp, AC-3 suy ra x(4,2) = 9 và x(4,3) = 7 mà chưa cần gán biến nào (test `test_preprocess_gac`).

Chi phí một lần REVISE: ≤ 12 tổ hợp × ≤ 9 giá trị × một lần ghép cặp O(k²·9), với k ≤ 9. Nói cách khác là hằng số nhỏ, không bùng nổ theo kích thước bàn.

### 3.3 AC-3, Forward Checking và MAC
Ba chiến lược suy luận khác nhau ở **những cung nào được REVISE** (`inference.py`):

| Chiến lược | Khi nào chạy | Những cung được revise | Lan truyền tiếp? |
|---|---|---|---|
| **None** | — | không cung nào, chỉ kiểm tra nhất quán | — |
| **Forward Checking (FC)** | sau khi gán X = v | (Y, C) với C chứa X, Y chưa gán | **Không**: revise mỗi cung đúng một lần |
| **MAC** | sau khi gán X = v | khởi đầu như FC, rồi chạy **AC-3** | **Có**: miền Y bị thu hẹp thì đưa các cung (Z, C′) với C′ ∋ Y, C′ ≠ C vào hàng đợi, đến khi không còn gì thay đổi |
| **AC-3 tiền xử lý** | một lần, trước khi tìm kiếm | mọi cung (Y, C) | Có |

**Lưu ý về Forward Checking.** Trong bài giảng, FC được định nghĩa cho ràng buộc nhị phân: sau khi gán X = v, xóa khỏi miền của mỗi hàng xóm Y chưa gán các giá trị mâu thuẫn với v. Kakuro dùng ràng buộc n-ngôi, nên "mâu thuẫn với v" phải được hiểu qua cả run: nhóm dùng chính phép REVISE(Y, C) ở mục 3.2. Phép này xét cả miền của các ô chưa gán khác trong run, nên tỉa mạnh hơn FC nhị phân một chút. Điểm giữ đúng tinh thần FC là: chỉ revise các cung chứa biến vừa gán, mỗi cung đúng một lần, **không lan truyền tiếp**.

**Lưu ý về MAC.** MAC chỉ thật sự "duy trì" arc consistency khi bài toán đã arc-consistent trước khi tìm kiếm, tức là khi bật AC-3 tiền xử lý. Cấu hình 6 trong bảng ablation (MAC, không tiền xử lý) vẫn đúng và đầy đủ, nhưng ở các nút đầu tiên vẫn còn những cung chưa được revise.

**Độ phức tạp của AC-3.** Với c cung và miền kích thước d, mỗi cung được đưa lại vào hàng đợi nhiều nhất d lần (mỗi lần miền của một biến mất ít nhất một giá trị), nên có O(c·d) lần REVISE. Ở Kakuro, c = tổng độ dài các run (96 cung với đề 9x9), d = 9.

Vòng lặp AC-3 (`AC3.run`):

```
queue ← các cung ban đầu
while queue khác rỗng:
    (Y, C) ← pop(queue)
    if REVISE(Y, C) đã xóa giá trị:
        if D(Y) = ∅: return failure                      # wipe-out ⇒ quay lui ngay
        for mỗi ràng buộc C′ ≠ C chứa Y, mỗi Z ≠ Y chưa gán trong C′:
            push (Z, C′)
return success
```

**Lý do chọn MAC + AC-3 tiền xử lý làm cấu hình chính**
- Kakuro có ràng buộc rất "chặt" (tổng nhỏ/lớn ép tập chữ số, run nào cũng giao với run khác), nên mỗi lần tỉa thường kéo theo một chuỗi tỉa khác. FC chỉ nhìn một bước nên bỏ lỡ chuỗi này, còn MAC thì đi theo nó đến cùng.
- Thực nghiệm (`results/summary.md`): trên đề 9x9, chỉ riêng AC-3 tiền xử lý đã thu không gian tìm kiếm từ 10^45.8 về 1 (cả 48 ô đều chốt được). Sau đó backtracking đi thẳng 48 nút, **0 lần quay lui**. Trên đề sinh ngẫu nhiên khó hơn (có nhiều nghiệm, AC-3 không tự giải hết), MAC vẫn chỉ cần trung bình vài lần quay lui, trong khi FC có lúc cần hàng trăm nghìn.
- Đổi lại, mỗi nút của MAC tốn hơn (nhiều REVISE hơn). Bảng ablation cho thấy cái giá đó rất đáng: tổng thời gian giảm từ hàng trăm ms xuống khoảng 10 ms.

### 3.4 Heuristic chọn biến và giá trị
Cài đặt: `kakuro/csp/heuristics.py` (Strategy pattern: solver chỉ gọi `select` / `order`).

| Heuristic | Quy tắc | Lý do (Lecture 08) | Cài đặt |
|---|---|---|---|
| **Static** | ô đầu tiên theo thứ tự hàng-cột | mốc so sánh | `StaticOrder` |
| **MRV** (Minimum Remaining Values) | chọn biến còn **ít giá trị hợp lệ nhất** | "fail-first": nhánh nào sắp thất bại thì cho thất bại sớm, cắt được cây con lớn. Biến có \|D\| = 1 được gán ngay | `MRV` |
| **Degree** | phá hòa cho MRV: chọn biến tham gia ràng buộc với **nhiều biến chưa gán nhất** | biến ràng buộc nhiều biến khác nhất, gán sớm thì giảm nhánh cho các lựa chọn về sau | `MRVDegree` |
| **LCV** (Least Constraining Value) | thử trước giá trị **loại bỏ ít giá trị nhất** khỏi miền các hàng xóm | "succeed-first": giữ nhiều lựa chọn cho các biến sau, nên dễ đi thẳng tới một lời giải | `LeastConstrainingValue` |

- Degree: trong Kakuro, ô nào cũng thuộc đúng 2 ràng buộc, nên đếm số ràng buộc thì mọi biến hòa nhau. Nhóm đếm theo đồ thị ràng buộc: bậc của biến = số biến **chưa gán** cùng run với nó (`KakuroCSP.neighbors`).
- Khi không có suy luận, MRV đếm số giá trị **qua được bước kiểm tra nhất quán** (đúng định nghĩa "legal values" của AIMA). Khi có FC/MAC thì miền đã được lọc sẵn, chỉ cần lấy |D| (`BacktrackingSolver.legal_value_count`).
- LCV: với mỗi giá trị v, giả sử X = v rồi chạy REVISE một bước trên các hàng xóm (giống FC) và đếm số giá trị bị loại. Giá trị nào làm rỗng miền một hàng xóm thì xếp cuối (`count_ruled_out`).
- **Phá hòa ngẫu nhiên** (`seed`): khi nhiều biến cùng điểm MRV/Degree, hoặc nhiều giá trị cùng điểm LCV, thì chọn ngẫu nhiên theo seed. Dùng để đánh giá **độ ổn định**: kết quả không được phụ thuộc vào may rủi khi phá hòa.

### 3.5 Những kỹ thuật cố ý **không** dùng (và lý do)
Ngoài các kỹ thuật trên, nhóm có tìm hiểu thêm một số hướng khác. Các hướng này không dùng vì nằm ngoài phạm vi đề bài (đề yêu cầu "constraint propagation + Backtracking Search" với heuristic của Lecture 08) hoặc không cần thiết:

| Kỹ thuật | Lý do không dùng |
|---|---|
| Local search (min-conflicts, WalkSAT) | Không đầy đủ: không chứng minh được vô nghiệm hay nghiệm duy nhất. Ràng buộc tổng làm "số xung đột" thay đổi rất gồ ghề, dễ kẹt ở cực tiểu cục bộ. |
| Chuyển sang SAT / ILP / CP-SAT | Dùng solver có sẵn thì không thể hiện được thuật toán của môn học. |
| Conflict-directed backjumping, nogood learning | Với MAC + GAC, số lần quay lui đã gần 0, nên không còn chỗ để cải thiện. |
| Path consistency / k-consistency | Đắt hơn nhiều mà GAC đã đủ mạnh (thực nghiệm D). |
| Heuristic học máy | Ngoài phạm vi môn học, và không cần thiết. |

## 4. Giao diện (Requirement 3) — liên hệ với lý thuyết

Solver chạy một lần với `Tracer` và ghi lại mọi bước thành sự kiện (`kakuro/csp/events.py`). GUI phát lại các sự kiện đó (`kakuro/gui/replay.py`):

| Thứ hiển thị | Ý nghĩa CSP |
|---|---|
| Các chữ số nhỏ 1..9 trong ô trắng | **Miền hiện tại D(x)** của biến |
| Chữ số nhỏ màu đỏ, bị gạch | giá trị vừa bị **tỉa** bởi lan truyền ràng buộc (kể từ quyết định gần nhất) |
| Chữ số nhỏ màu xanh lá | giá trị được **khôi phục** khi quay lui (pop trail) |
| Chữ số nhỏ màu cam, bị gạch | giá trị bị **từ chối** vì không nhất quán (backtracking thuần) |
| Ô nền vàng, viền cam | biến được **MRV/Degree chọn** |
| Run nền xanh nhạt + ô gợi ý xanh đậm + ô viền xanh | **cung (Y, C) đang được REVISE** |
| Ô viền đỏ / nền đỏ | **wipe-out** (miền rỗng) hoặc **dead end** (mọi giá trị đều thất bại) |
| Chữ số lớn màu xanh dương | giá trị đã **gán** |
| Timeline | độ sâu của cây tìm kiếm theo thời gian: răng cưa = quay lui; đoạn tô nhạt ở đầu = AC-3 tiền xử lý |
| Thanh "Search space left" | ∏\|D(x)\| hiện tại (thang log): lan truyền ràng buộc làm thanh này co lại, quay lui làm nó giãn ra |
| Rê chuột lên một ô trắng | miền hiện tại D(x) của biến đó và hai ràng buộc (run ngang, run dọc) chứa nó; các ô cùng run được tô nhạt |
| Bộ đếm | Nodes, Backtracks, Depth (độ sâu hiện tại / n), Revisions, Values pruned, Values rejected |
| "Branch" | nhánh hiện tại của cây tìm kiếm (chuỗi phép gán) |
| Event log | từng bước SELECT / ASSIGN / REVISE / PRUNE / WIPEOUT / RESTORE / UNDO / DEADEND |

Có thể đổi đề, đổi chiến lược suy luận, thứ tự biến, thứ tự giá trị, bật/tắt AC-3 tiền xử lý và seed ngay trong GUI. Solver được chạy lại và trace được ghi lại theo cấu hình mới.

## 5. Tóm tắt kết quả (Requirement 2)

Số liệu đầy đủ ở `results/summary.md` và các file CSV, tạo lại bằng `python experiments.py`. Đo trên macOS, Python 3.9.

**Cách đo.** Thời gian: số nút của cây tìm kiếm, số lần quay lui, số lần kiểm tra ràng buộc (gồm kiểm tra nhất quán khi gán và kiểm tra support trong REVISE/LCV). Không gian: độ sâu lớn nhất và độ dài trail lớn nhất (mục 3.1). Các bộ đếm này tất định, chạy lại trên máy nào cũng ra đúng số đó; chỉ có cột giây là thay đổi theo máy.

**A. Ablation trên `complex_9x9`** (biểu đồ: `results/ablation_complex_9x9.png`)

| Cấu hình | Nút | Quay lui | Kiểm tra ràng buộc | Độ sâu lớn nhất | Trail lớn nhất | Thời gian |
|---|---|---|---|---|---|---|
| BT | 14 038 | 13 990 | 150 706 | 48 | 384 | 0.32 s |
| BT + MRV | 44 797 | 44 749 | 13 792 014 | 48 | 384 | 14.5 s |
| BT + FC | 275 | 227 | 5 760 | 48 | 384 | 0.020 s |
| BT + FC + MRV/Deg | 1 575 | 1 527 | 39 279 | 48 | 384 | 0.17 s |
| BT + FC + MRV/Deg + LCV | 1 594 | 1 546 | 77 166 | 48 | 384 | 0.28 s |
| BT + MAC + MRV/Deg | 49 | 1 | 1 930 | 48 | 384 | 0.0097 s |
| **BT + MAC + MRV/Deg + LCV + AC-3 tiền xử lý** | **48** | **0** | **1 809** | 48 | 384 | **0.0091 s** |

Không gian giống nhau ở mọi cấu hình và đúng bằng dự đoán lý thuyết: độ sâu lớn nhất = n = 48, trail lớn nhất = 384 = n·(d − 1) (khi tìm ra lời giải, mỗi biến đã mất 8 trong 9 giá trị). Các cấu hình chỉ khác nhau về thời gian.

Nhận xét:
- **Lan truyền ràng buộc là yếu tố quyết định.** Từ BT lên FC giảm khoảng 50 lần số nút, từ FC lên MAC giảm thêm khoảng 6–30 lần. Với MAC, số nút = số biến (48), tức là không có bước nào đi sai.
- **MRV phải đi cùng lan truyền mạnh mới phát huy.** Khi không có suy luận, hoặc chỉ có FC một bước, các biến có |D| gần như bằng nhau nên MRV/Degree nhảy lung tung trên bàn. Các phép gán khi đó rơi vào những run khác nhau, và ràng buộc tổng của mỗi run phải đợi lâu mới "đóng" lại để phát hiện mâu thuẫn. Thứ tự tĩnh (hàng-cột) thì lấp đầy từng run liên tiếp nên phát hiện sai sớm hơn. Khi đã có MAC, miền phản ánh đúng tình trạng ràng buộc, và MRV chọn đúng các ô bị ép (|D| = 1).
- **Không có suy luận thì MRV rất đắt.** BT + MRV tốn 13.8 triệu lần kiểm tra ràng buộc: ở mỗi nút, MRV phải kiểm tra nhất quán cho mọi giá trị của mọi biến chưa gán để đếm "giá trị hợp lệ còn lại". Khi có FC/MAC, miền đã được lọc sẵn nên MRV chỉ cần đọc |D|.
- **LCV** hầu như không đổi số nút trên đề nghiệm duy nhất (chỉ có một giá trị đúng, xếp thứ tự giá trị không giúp được bao nhiêu), nhưng tốn thêm phép kiểm tra. LCV có ích hơn trên các đề nhiều nghiệm (C2).

**B. Tính đúng:** cả hai đề đều tìm được lời giải, qua được bộ kiểm tra độc lập, và **có nghiệm duy nhất** (đã duyệt hết cây mà không có lời giải thứ hai).

**C. Tính ổn định:**
- C1: 30 seed phá hòa ngẫu nhiên trên `complex_9x9`. Cấu hình chính luôn đúng 48 nút, thời gian 9.7 ± 0.3 ms, mọi lần chạy cho cùng một lời giải. FC + MRV/Deg + LCV thì dao động rất mạnh (1 365 đến 93 270 nút, 7.4 ± 6.0 s). Đây là hiện tượng **heavy-tail** quen thuộc của backtracking với suy luận yếu.
- C2: 20 đề sinh ngẫu nhiên từ 7x7 đến 12x12. MAC giải 20/20, trung bình 36 ms, tối đa 162 ms, tối đa 66 lần quay lui. FC + MRV/Deg chỉ giải được 18/20 trong giới hạn 10 s.

**D. Sức mạnh của AC-3 tiền xử lý:** trên cả hai đề, AC-3 (GAC) một mình đã thu không gian tìm kiếm ∏|D(x)| từ 10^11.5 (5x5) và 10^45.8 (9x9) về **1**, tức là mọi ô đều được chốt, trong khoảng 7 ms.

## 6. Câu hỏi vấn đáp thường gặp

- **Vì sao miền là 1..9 mà không lọc theo tổng ngay khi tạo?** Để mô hình đúng định nghĩa và để AC-3 thể hiện vai trò của nó. Việc lọc theo bảng tổ hợp chính là REVISE ở lần chạy đầu.
- **FC khác MAC ở đâu?** FC revise mỗi hàng xóm của X một lần rồi dừng. MAC đưa các cung bị ảnh hưởng vào hàng đợi và lan truyền tiếp đến điểm bất động. MAC phát hiện mâu thuẫn sớm hơn, nhưng mỗi nút tốn hơn.
- **Vì sao 9x9 không cần quay lui?** Vì GAC trên ràng buộc SumAllDiff đủ mạnh để suy ra cả lời giải (đề Kakuro "đẹp" thường giải được hoàn toàn bằng suy luận). Muốn thấy quá trình quay lui, chọn trong GUI: Inference = FC, Variable order = Static, Initial AC-3 = Off (hoặc Inference = None).
- **Làm sao biết lời giải đúng?** `KakuroBoard.is_solution` kiểm tra lại từ luật chơi, độc lập với solver. Tìm tiếp lời giải thứ hai để khẳng định nghiệm duy nhất. Unit test: `tests/test_solver.py`.
- **Quay lui có khôi phục miền đúng không?** Có, nhờ trail. Test `test_domains_restored_after_search` và `TestReplay.test_seek_matches_sequential` kiểm tra điều này.
