# Task 1 — N-Queens: Propositional Logic và Local Search

> Tài liệu lý thuyết cho cả ba yêu cầu. Mỗi khái niệm đều chỉ ra chỗ cài đặt trong code để dễ giải thích khi vấn đáp. Số liệu lấy từ `results/report.md`, tạo lại bằng `python main.py experiments`.

## 1. Mô hình hóa bằng logic mệnh đề (Requirement 1)

### 1.1 Các thành phần

| Thành phần | Trong bài toán N-Queens | Cài đặt |
|---|---|---|
| **Ký hiệu mệnh đề** (propositional symbol) | `x(r,c)` với 0 ≤ r, c < N. `x(r,c) = True` ⇔ ô (r,c) có hậu. Có N² ký hiệu. | `VariableMap`: đánh số `v = r·N + c + 1` (số nguyên dương, theo quy ước DIMACS của PySAT) |
| **Literal** | `x(r,c)` (dương) hoặc `¬x(r,c)` (âm) | số nguyên `v` hoặc `−v` |
| **Mệnh đề** (clause) | tuyển (∨) của các literal | danh sách số nguyên, ví dụ `[-1, -2]` là `¬x₁ ∨ ¬x₂` |
| **Cơ sở tri thức** KB | hội (∧) của mọi ràng buộc đặt hậu, viết ở dạng CNF | `NQueensCNF` gồm 5 `ConstraintGroup` |
| **Mô hình** (model) | một phép gán True/False cho cả N² ký hiệu, tức là một cách đặt quân lên bàn cờ | danh sách literal do `Glucose3.get_model()` trả về |
| **Bài toán** | **thỏa được** (satisfiability): tìm một mô hình `m` sao cho KB đúng trong `m`. Mỗi mô hình như vậy là một lời giải N-Queens, và ngược lại. | `GlucoseQueensSolver.solve` |

N = 2 và N = 3 không có lời giải, nên KB **không thỏa được** (unsatisfiable); test `test_unsat_for_n2_n3` kiểm tra điều này.

### 1.2 Các ràng buộc, viết bằng câu logic tự nhiên

Hai hậu tại a = (r₁,c₁) và b = (r₂,c₂) tấn công nhau khi và chỉ khi chúng cùng một **đường**: cùng hàng (r₁ = r₂), cùng cột (c₁ = c₂), cùng đường chéo chính (r₁ − c₁ = r₂ − c₂) hoặc cùng đường chéo phụ (r₁ + c₁ = r₂ + c₂).

| # | Ràng buộc | Câu logic (chưa ở dạng CNF) |
|---|---|---|
| 1 | Mỗi hàng có ít nhất một hậu | `x(r,0) ∨ x(r,1) ∨ … ∨ x(r,N−1)` với mỗi hàng r |
| 2 | Mỗi hàng có nhiều nhất một hậu | `x(a) ⇒ ¬x(b)` với mọi cặp ô a ≠ b cùng hàng |
| 3 | Mỗi cột có nhiều nhất một hậu | `x(a) ⇒ ¬x(b)` với mọi cặp ô cùng cột |
| 4 | Mỗi đường chéo chính có nhiều nhất một hậu | `x(a) ⇒ ¬x(b)` với mọi cặp ô cùng r − c |
| 5 | Mỗi đường chéo phụ có nhiều nhất một hậu | `x(a) ⇒ ¬x(b)` với mọi cặp ô cùng r + c |

**Vì sao chừng đó là đủ.** Từ (1) và (2), mỗi hàng có đúng một hậu, nên trên bàn có đúng N hậu. Có N hậu trên N cột mà theo (3) mỗi cột nhiều nhất một hậu, nên mỗi cột cũng có đúng một hậu (nguyên lý chuồng bồ câu). Do đó không cần viết thêm "mỗi cột ít nhất một hậu": KB đã **suy ra** (entail) mệnh đề đó. Đường chéo thì chỉ cần "nhiều nhất một", vì có đường chéo không chứa hậu nào. Mục 2.4 cho thấy thêm nhóm mệnh đề dư thừa này tuy không đổi tập mô hình nhưng giúp solver suy diễn nhanh hơn nhiều khi N lớn.

**Tương ứng một-một giữa mô hình và lời giải.** Test `test_models_are_exactly_the_n_queens_solutions` liệt kê **toàn bộ** mô hình của KB với N = 1..8 và được đúng 1, 0, 0, 2, 10, 4, 40, 92 mô hình, bằng số lời giải N-Queens đã biết; mọi mô hình đều giải mã thành một bàn cờ hợp lệ.

### 1.3 Thuật toán phát hiện ràng buộc

Cài đặt: `ConstraintDiscoverer.discover` (`nqueens_solver/core/cnf.py`).

Cách ngây thơ là xét mọi cặp ô và kiểm tra điều kiện tấn công: có N² ô nên có O(N⁴) cặp. Thuật toán của nhóm dựa vào nhận xét: mỗi đường được xác định bởi một **khóa**, và hai ô tấn công nhau khi và chỉ khi chúng chung ít nhất một khóa.

```
DISCOVER(N):
    rows[r] ← [], cols[c] ← [], diag[k] ← [], anti[k] ← []
    for mỗi ô (r, c):                      # N² ô, mỗi ô xét đúng một lần
        thêm (r, c) vào rows[r]             # khóa hàng:          r
        thêm (r, c) vào cols[c]             # khóa cột:           c
        thêm (r, c) vào diag[r − c]         # khóa chéo chính:    r − c
        thêm (r, c) vào anti[r + c]         # khóa chéo phụ:      r + c
    return rows, cols, diag, anti           # N + N + (2N−1) + (2N−1) = 6N − 2 đường
```

Mỗi đường là một tập ô **đôi một tấn công nhau**. Vậy ràng buộc cần sinh là: "ít nhất một" cho mỗi hàng, và "nhiều nhất một" cho mỗi đường có từ 2 ô trở lên.

- **Độ phức tạp.** Gom nhóm: O(N²) thời gian và bộ nhớ. Sinh mệnh đề: tỉ lệ với số mệnh đề đầu ra, là Θ(N³) (mục 1.5). Cách ngây thơ tốn Θ(N⁴) phép kiểm tra để cho ra cùng tập mệnh đề đó.
- **Tính đúng.** Test `test_constraints_equal_brute_force_attack_relation` so tập cặp ô do thuật toán sinh ra với tập cặp ô tấn công nhau liệt kê bằng vét cạn (N = 2..7): hai tập **bằng nhau** (không thiếu, không thừa). Test `test_each_attacking_pair_appears_once` kiểm tra không cặp nào bị sinh hai lần; điều này đúng vì hai ô khác nhau chung nhiều nhất một đường.

### 1.4 Quy trình chuyển về CNF

CNF (Conjunctive Normal Form) là hội của các mệnh đề, mỗi mệnh đề là tuyển của các literal. Quy trình chuẩn của bài giảng gồm 4 bước:

1. Khử `⇔`: thay `α ⇔ β` bằng `(α ⇒ β) ∧ (β ⇒ α)`.
2. Khử `⇒`: thay `α ⇒ β` bằng `¬α ∨ β`.
3. Đưa `¬` vào trong (De Morgan, phủ định kép) cho đến khi `¬` chỉ đứng trước ký hiệu.
4. Phân phối `∨` qua `∧`.

Áp dụng cho từng loại ràng buộc:

| Ràng buộc | Câu ban đầu | Bước áp dụng | Kết quả CNF |
|---|---|---|---|
| Ít nhất một (hàng r) | `x(r,0) ∨ … ∨ x(r,N−1)` | đã là một mệnh đề, không cần biến đổi | 1 mệnh đề gồm N literal dương |
| Nhiều nhất một (cặp a, b cùng đường) | `x(a) ⇒ ¬x(b)` | bước 2: khử `⇒` | `¬x(a) ∨ ¬x(b)`: 1 mệnh đề gồm 2 literal âm |

Viết cách khác cho ràng buộc thứ hai: "a và b không cùng có hậu" là `¬(x(a) ∧ x(b))`; bước 3 (De Morgan) cho ngay `¬x(a) ∨ ¬x(b)`. Hai cách cho cùng một mệnh đề.

KB cuối cùng là hội của tất cả các mệnh đề này, nên đã ở dạng CNF và không cần bước 4.

**Vì sao mã hóa "nhiều nhất một" theo từng cặp (pairwise).** Nếu viết "đúng một hậu trên hàng r" một cách trực tiếp là `(x₀ ∧ ¬x₁ ∧ … ) ∨ (¬x₀ ∧ x₁ ∧ …) ∨ …` (dạng DNF), thì bước 4 phân phối `∨` qua `∧` sinh ra Nᴺ mệnh đề, tăng theo hàm mũ. Tách thành "ít nhất một" ∧ "nhiều nhất một theo cặp" cho ra các mệnh đề đã ở dạng CNF, số lượng chỉ là đa thức.

**Ví dụ N = 4, hàng 0** (biến x₁..x₄):

```
ít nhất một:      (x₁ ∨ x₂ ∨ x₃ ∨ x₄)                                   → [1, 2, 3, 4]
nhiều nhất một:   (¬x₁ ∨ ¬x₂) ∧ (¬x₁ ∨ ¬x₃) ∧ (¬x₁ ∨ ¬x₄)
                ∧ (¬x₂ ∨ ¬x₃) ∧ (¬x₂ ∨ ¬x₄) ∧ (¬x₃ ∨ ¬x₄)             → [-1,-2], [-1,-3], …, [-3,-4]
```

### 1.5 Số mệnh đề CNF

Một đường có L ô sinh C(L,2) = L(L−1)/2 mệnh đề "nhiều nhất một".

| Nhóm | Số mệnh đề | N = 4 | N = 8 |
|---|---|---:|---:|
| Hàng, ít nhất một | N | 4 | 8 |
| Hàng, nhiều nhất một | N·C(N,2) | 24 | 224 |
| Cột, nhiều nhất một | N·C(N,2) | 24 | 224 |
| Chéo chính, nhiều nhất một | C(N,2) + 2·Σ_{L=2}^{N−1} C(L,2) = N(N−1)(2N−1)/6 | 14 | 140 |
| Chéo phụ, nhiều nhất một | như chéo chính | 14 | 140 |
| **Tổng** | **(5N³ − 6N² + 4N) / 3** | **80** | **736** |

Vậy số ký hiệu là N², số mệnh đề là Θ(N³). Chương trình đối chiếu công thức này với số mệnh đề thực sự sinh ra (`NQueensCNF.expected_clause_count`, test `test_clause_count_matches_closed_form`).

## 2. Giải bằng Glucose3 (Requirement 2)

### 2.1 Cách làm

`GlucoseQueensSolver.solve(n)` (`nqueens_solver/core/sat_solver.py`):

1. Sinh KB ở dạng CNF: `NQueensCNF(n)`.
2. Nạp vào solver: `Glucose3(bootstrap_with=clauses)`.
3. `solve()` trả lời KB có thỏa được không; nếu có, `get_model()` trả về một mô hình.
4. Giải mã: literal dương `v` ↦ ô `divmod(v − 1, N)` có hậu (`Board.from_model`).
5. Kiểm tra lại lời giải bằng một bộ kiểm tra **độc lập với solver** (`Board.is_solution`: đúng N hậu, không cặp nào tấn công nhau).

Glucose3 là solver kiểu DPLL có học mệnh đề (CDCL). Liên hệ với bài giảng: nó lặp lại ba việc của DPLL là **lan truyền đơn vị** (unit propagation), **chọn một ký hiệu để gán thử** (decision), và khi gặp **mâu thuẫn** (conflict) thì quay lui; phần bổ sung là mỗi lần mâu thuẫn nó học thêm một mệnh đề để không lặp lại sai lầm đó.

### 2.2 Cách đo

- **Số mệnh đề CNF**: đếm trực tiếp, và khớp với công thức ở mục 1.5.
- **Thời gian chạy của solver**: thời gian của riêng lời gọi `Glucose3.solve()`, trung bình 3 lần. Thời gian sinh CNF và thời gian nạp mệnh đề được báo riêng, vì đó không phải việc của solver.
- **Công việc của solver, không phụ thuộc máy**: số decisions, propagations và conflicts do chính Glucose3 đếm (`accum_stats()`). Đây là các đại lượng của thuật toán DPLL/CDCL, nên chúng giải thích được vì sao thời gian tăng hay giảm.

### 2.3 Kết quả

| N | Số ký hiệu | Số mệnh đề CNF | Solve (ms) | Decisions | Propagations | Conflicts |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 16 | 80 | 0.01 | 10 | 32 | 3 |
| 6 | 36 | 296 | 0.06 | 73 | 349 | 38 |
| 8 | 64 | 736 | 0.04 | 40 | 194 | 12 |
| 10 | 100 | 1 480 | 0.12 | 100 | 677 | 45 |
| 12 | 144 | 2 608 | 0.06 | 71 | 409 | 19 |
| 16 | 256 | 6 336 | 1.02 | 482 | 3 904 | 207 |
| 20 | 400 | 12 560 | 4.15 | 953 | 11 198 | 531 |
| 24 | 576 | 21 920 | 3.47 | 891 | 9 866 | 431 |
| 30 | 900 | 43 240 | 7.40 | 1 588 | 18 144 | 649 |
| 40 | 1 600 | 103 520 | 4.29 | 1 500 | 13 370 | 296 |
| 50 | 2 500 | 203 400 | 260.85 | 11 452 | 277 349 | 7 519 |
| 60 | 3 600 | 352 880 | 42.33 | 5 475 | 74 396 | 1 341 |
| 80 | 6 400 | 840 640 | 10295.79 | 138 947 | 4 168 619 | 104 415 |
| 100 | 10 000 | 1 646 800 | 8232.98 | 91 881 | 5 499 245 | 70 981 |

Thời gian đo trên macOS 15.5, Apple Silicon (M1), Python 3.9; trên máy khác số mili-giây sẽ khác, còn các cột đếm thì giữ nguyên. Mọi lời giải đều qua được bộ kiểm tra độc lập.

Nhận xét:

- **Số mệnh đề tăng đúng theo Θ(N³)**: N tăng gấp đôi thì số mệnh đề tăng khoảng 8 lần (N = 40 → 80: 103 520 → 840 640, gấp 8.1 lần).
- **Thời gian solve không tăng đơn điệu theo N.** N = 40 chỉ mất 4.3 ms trong khi N = 30 mất 7.4 ms; N = 80 chậm hơn N = 100. Lý do nằm ở cột Conflicts: thời gian đi theo số lần solver đoán sai chứ không đi theo kích thước công thức. N = 40 chỉ gặp 296 mâu thuẫn, N = 50 gặp 7 519. Số mâu thuẫn phụ thuộc vào thứ tự chọn ký hiệu của solver trên từng công thức cụ thể.
- **Vì sao N = 80, 100 mất hàng giây.** SAT là NP-đầy đủ, nhưng đó là phát biểu về trường hợp xấu nhất; N-Queens không phải bài toán khó (Min-Conflicts ở mục 3 giải N = 1000 trong khoảng 0.2 giây). Nguyên nhân nằm ở cách mã hóa: KB chỉ nói "mỗi cột nhiều nhất một hậu", còn sự kiện "mỗi cột phải có một hậu" thì solver phải tự phát hiện qua các lần mâu thuẫn (đây là suy luận kiểu chuồng bồ câu, vốn khó với lan truyền đơn vị). Mục 2.4 kiểm chứng điều này.

### 2.4 Ablation: thêm mệnh đề mà KB đã suy ra

`NQueensCNF(n, column_alo=True)` thêm nhóm thứ sáu "mỗi cột có ít nhất một hậu": `x(0,c) ∨ x(1,c) ∨ … ∨ x(N−1,c)`, tức đúng N mệnh đề (tổng số mệnh đề thành (5N³ − 6N² + 7N)/3). Chạy bằng `python main.py satalo`; số liệu đầy đủ ở `results/report.md` mục 4.

- **Không đổi bài toán.** KB gốc đã suy ra các mệnh đề này (KB ⊨ α, mục 1.2), nên hai KB có **cùng tập mô hình**. Test `test_column_alo_is_entailed_by_the_kb` liệt kê toàn bộ mô hình của hai KB với N = 1..8 và so sánh: hai tập bằng nhau.
- **Vì sao solver nhanh hơn.** Lan truyền đơn vị (unit propagation) chỉ suy diễn trên từng mệnh đề. Với KB gốc, khi N − 1 ô của một cột đã False, không mệnh đề nào ép ô còn lại phải True; solver tiếp tục gán thử và chỉ gặp mâu thuẫn rất muộn. Có mệnh đề cột thì ô cuối cùng trở thành mệnh đề đơn vị và được suy ra ngay.

| N | Mệnh đề (gốc) | Conflicts (gốc) | Solve gốc (ms) | Mệnh đề (+cột) | Conflicts (+cột) | Solve +cột (ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 8 | 736 | 12 | 0.03 | 744 | 21 | 0.06 |
| 16 | 6 336 | 207 | 0.99 | 6 352 | 952 | 7.52 |
| 24 | 21 920 | 431 | 3.43 | 21 944 | 2 805 | 37.35 |
| 30 | 43 240 | 649 | 7.32 | 43 270 | 137 | 1.27 |
| 40 | 103 520 | 296 | 4.17 | 103 560 | 312 | 3.74 |
| 50 | 203 400 | 7 519 | 250.36 | 203 450 | 250 | 3.49 |
| 60 | 352 880 | 1 341 | 39.72 | 352 940 | 203 | 4.95 |
| 80 | 840 640 | 104 415 | 9898.06 | 840 720 | 276 | 10.75 |
| 100 | 1 646 800 | 70 981 | 8299.46 | 1 646 900 | 277 | 14.75 |

- Với N ≥ 50, số mâu thuẫn giảm 7–380 lần: N = 80 từ 104 415 xuống 276 (khoảng 9.9 giây xuống 11 ms), N = 100 từ 70 981 xuống 277 (khoảng 8.3 giây xuống 15 ms).
- Với N nhỏ thì không phải lúc nào cũng có lợi (N = 16: 207 → 952 mâu thuẫn; N = 24: 431 → 2 805), vì mệnh đề thêm vào làm đổi thứ tự chọn ký hiệu của solver; chênh lệch khi đó chỉ vài chục mili-giây.
- Nhóm giữ KB tối thiểu ở mục 1 làm mô hình chính (đúng những ràng buộc cần và đủ), và đưa nhóm mệnh đề cột vào như một tùy chọn tối ưu cho N lớn.

## 3. Min-Conflicts và heuristic chọn biến (Requirement 3)

### 3.1 Mô hình CSP cho tìm kiếm cục bộ

| Thành phần | Định nghĩa |
|---|---|
| Biến | `X_r` = cột của quân hậu ở hàng r, với r = 0..N−1 (N biến) |
| Miền giá trị | `D = {0, 1, …, N−1}` |
| Ràng buộc | với mọi cặp hàng r ≠ s: `X_r ≠ X_s` (khác cột) và `|X_r − X_s| ≠ |r − s|` (khác đường chéo) |
| Trạng thái | một phép gán **đầy đủ**: mỗi hàng đúng một hậu. Ràng buộc "khác hàng" luôn thỏa nhờ cách biểu diễn. |
| `CONFLICTS(X_r, v)` | số ràng buộc bị vi phạm nếu gán `X_r = v`, tức là số hậu khác đang tấn công ô (r, v) |

`ConflictState` giữ 3 mảng đếm (số hậu trên mỗi cột, mỗi đường chéo chính, mỗi đường chéo phụ), nên `CONFLICTS(X_r, v)` tính được trong O(1) và được cập nhật trong O(1) mỗi lần di chuyển một hậu.

### 3.2 Min-Conflicts chuẩn (Lecture 08)

```
function MIN-CONFLICTS(csp, max_steps):
    current ← một phép gán đầy đủ ban đầu                      # RandomInitializer
    for i = 1 to max_steps:
        if current là lời giải: return current
        var   ← một biến đang xung đột, chọn NGẪU NHIÊN          # RandomConflictedSelector
        value ← giá trị v làm CONFLICTS(var, v) nhỏ nhất         # MinConflictsValue (hòa → ngẫu nhiên)
        gán var = value trong current
    return failure
```

Cài đặt: `MinConflictsSolver.standard()` (`nqueens_solver/core/min_conflicts.py`). Mỗi bước tốn O(N): quét N biến để tìm các biến xung đột, và quét N giá trị để tìm giá trị ít xung đột nhất.

### 3.3 Heuristic chọn biến đề xuất: "biến xung đột nhiều nhất, có tabu"

Cài đặt: `MostConflictedTabuSelector`; cấu hình `MinConflictsSolver.heuristic()`.

Bản chuẩn chọn biến xung đột một cách ngẫu nhiên, tức là không dùng thông tin nào về mức độ xung đột. Heuristic đề xuất thay đúng một dòng của thuật toán:

```
var ← biến đang xung đột có CONFLICTS(var, giá trị hiện tại) LỚN NHẤT,
      trong số các biến KHÔNG được chọn ở `tenure` bước gần nhất  (hòa → ngẫu nhiên)
```

Hai ý:

1. **Chọn biến vi phạm nhiều ràng buộc nhất.** Cùng tinh thần với heuristic bậc (degree) và nguyên tắc fail-first của Lecture 08: ưu tiên biến dính tới nhiều ràng buộc nhất. Một hậu đang bị k hậu khác tấn công, khi chuyển sang ô ít xung đột nhất, có thể xóa tới k xung đột trong một bước; hậu chỉ bị 1 hậu tấn công thì xóa được nhiều nhất 1.
2. **Tabu trên biến.** Nếu chỉ dùng ý 1 thì thuật toán dễ lặp vô hạn: khi biến xung đột nhiều nhất đã đứng ở giá trị min-conflicts của nó, nó được chọn lại mãi mà trạng thái không đổi. Vì vậy biến vừa được chọn bị cấm chọn lại trong `tenure = max(2, min(10, N/4))` bước. Nếu mọi biến xung đột đều đang bị cấm thì bỏ cấm cho bước đó.

Chi phí mỗi bước vẫn là O(N), bằng bản chuẩn (cùng một lần quét N biến).

### 3.4 Thiết kế thực nghiệm

- **Chỉ thay đổi một yếu tố.** Hai cấu hình dùng chung cách khởi tạo (ngẫu nhiên), chung cách chọn giá trị (min-conflicts), không khởi động lại; chỉ khác bước chọn biến. Test `test_heuristic_differs_from_standard_only_in_variable_selection` kiểm tra điều này.
- **Cùng điểm xuất phát.** Với mỗi N, hai cấu hình chạy 200 lần trên cùng bộ seed, nên ở mỗi seed chúng bắt đầu từ cùng một phép gán ban đầu.
- **Thước đo.** Thước đo chính là **số bước lặp** của MIN-CONFLICTS cho đến khi tìm ra lời giải (mỗi bước = một lần gán lại một biến; đây chính là đại lượng `max_steps` giới hạn trong thuật toán). Báo cáo cả trung bình, trung vị và giá trị lớn nhất, cùng **tỉ lệ thành công** trong giới hạn 100 000 bước. Thời gian chạy là số liệu phụ.

### 3.5 Kết quả (200 lần chạy mỗi N)

| N | Thành công: chuẩn | Thành công: heuristic | Bước trung vị: chuẩn | Bước trung vị: heuristic | Tỉ lệ | Bước TB: chuẩn | Bước TB: heuristic |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 8 | 92.5% | 95% | 35.5 | 19.0 | 54% | 7 566.8 | 5 029.9 |
| 16 | 99% | 97.5% | 66.0 | 34.5 | 52% | 1 087.3 | 2 544.8 |
| 32 | 100% | 100% | 76.5 | 46.0 | 60% | 90.3 | 51.9 |
| 64 | 100% | 100% | 98.0 | 67.0 | 68% | 108.7 | 70.0 |
| 128 | 100% | 100% | 154.0 | 106.0 | 69% | 159.4 | 109.6 |
| 256 | 100% | 100% | 240.0 | 169.0 | 70% | 244.0 | 173.7 |
| 512 | 100% | 100% | 397.0 | 297.0 | 75% | 405.8 | 299.0 |
| 1000 | 100% | 100% | 708.5 | 538.0 | 76% | 714.1 | 540.6 |

Nhận xét:

- **Heuristic giảm số bước ở mọi N.** Số bước trung vị còn 52–76% so với bản chuẩn. Với N ≥ 32, cả trung bình lẫn giá trị lớn nhất đều giảm (N = 1000: nhiều nhất 635 bước so với 876).
- **Thời gian cũng giảm** (N = 1000: 170 ms so với 219 ms), vì chi phí mỗi bước của hai bản bằng nhau.
- **Tỉ lệ thành công của hai bản tương đương.** Với N = 8 và N = 16, cả hai bản đều có một số lần chạy hết 100 000 bước mà không ra lời giải (N = 8: 15/200 ở bản chuẩn, 10/200 ở bản heuristic; N = 16: 2/200 và 5/200). Chênh lệch vài lần chạy như vậy nằm trong nhiễu thống kê: khi tăng lên 500 lần chạy (`MinConflictsExperiment(500)`), hai bản đạt 93.6% và 94.4% ở N = 8, 98.4% và 98.6% ở N = 16. Các lần thất bại kéo số bước trung bình lên rất cao, nên ở N nhỏ phải đọc trung vị.
- **Nguyên nhân thất bại là cực tiểu địa phương**, không phải heuristic: Min-Conflicts không bao giờ nhận một nước làm tăng xung đột, nên khi mọi biến xung đột đều đã ở giá trị tốt nhất của mình thì thuật toán đứng yên, dù chọn biến nào. Đây là hạn chế của tìm kiếm cục bộ nói chung (không đầy đủ), không sửa được chỉ bằng cách chọn biến.

### 3.6 Ablation: từng thành phần đóng góp gì

| N | Cấu hình | Thành công | Bước trung vị | Bước lớn nhất |
|---:|:---|---:|---:|---:|
| 8 | Chuẩn | 92.5% | 35.5 | 100 000 |
| 8 | Biến xung đột nhiều nhất, **không** tabu | 93.5% | 36.5 | 100 000 |
| 8 | Heuristic đề xuất (có tabu) | 95% | 19.0 | 100 000 |
| 8 | Heuristic + khởi tạo tham lam + tabu giá trị + restart | 100% | 10.0 | 98 |
| 16 | Chuẩn | 99% | 66.0 | 100 000 |
| 16 | Biến xung đột nhiều nhất, **không** tabu | 96.5% | 65.5 | 100 000 |
| 16 | Heuristic đề xuất (có tabu) | 97.5% | 34.5 | 100 000 |
| 16 | Heuristic + khởi tạo tham lam + tabu giá trị + restart | 100% | 20.0 | 149 |
| 256 | Chuẩn | 100% | 240.0 | 341 |
| 256 | Biến xung đột nhiều nhất, **không** tabu | 100% | 199.0 | 289 |
| 256 | Heuristic đề xuất (có tabu) | 100% | 169.0 | 306 |
| 256 | Heuristic + khởi tạo tham lam + tabu giá trị + restart | 100% | 37.0 | 89 |

- **Tabu trên biến là phần không thể thiếu của heuristic.** Bỏ tabu thì ở N = 8 và N = 16 số bước trung vị gần như bằng bản chuẩn (36.5 so với 35.5; 65.5 so với 66.0), và ở N = 256 chỉ giảm được 17% thay vì 30%.
- **Dòng cuối không thuộc phép so sánh chính.** Nó thêm ba kỹ thuật nằm ngoài phạm vi "chọn biến": khởi tạo tham lam (đặt từng hậu vào cột ít xung đột nhất), tabu trên giá trị, và khởi động lại khi 20·N bước liên tiếp không cải thiện. Khởi động lại là cách chuẩn để thoát cực tiểu địa phương, nên cấu hình này đạt 100% ở mọi N. Nhóm đưa vào để cho thấy hạn chế ở mục 3.5 xử lý được, nhưng không tính nó vào hiệu quả của heuristic chọn biến.

## 4. Câu hỏi vấn đáp thường gặp

- **Vì sao không cần ràng buộc "mỗi cột ít nhất một hậu"?** Vì nó suy ra được từ các ràng buộc còn lại (mục 1.2, nguyên lý chuồng bồ câu), nên thêm vào không đổi tập mô hình. Nó thừa về logic nhưng có ích cho solver: với N ≥ 50 số mâu thuẫn giảm hàng chục đến hàng trăm lần (mục 2.4), vì lan truyền đơn vị suy ra được ngay ô cuối cùng của một cột.
- **Bước nào của quy trình chuyển CNF được dùng?** Chỉ bước khử `⇒` (hoặc tương đương là De Morgan). Không có `⇔` và không cần phân phối.
- **Số mệnh đề là bao nhiêu?** (5N³ − 6N² + 4N)/3, tức Θ(N³).
- **Vì sao thời gian Glucose3 không tăng đều theo N?** Vì thời gian đi theo số mâu thuẫn mà solver gặp, không đi theo kích thước công thức (mục 2.3).
- **Heuristic đề xuất khác bản chuẩn ở đâu?** Chỉ ở dòng chọn biến: chuẩn chọn ngẫu nhiên một biến xung đột; đề xuất chọn biến xung đột nhiều nhất và cấm chọn lại biến vừa chọn trong vài bước.
- **Vì sao đo bằng số bước chứ không chỉ bằng giây?** Số bước là đại lượng của thuật toán (số lần lặp của MIN-CONFLICTS), không phụ thuộc máy. Hai bản có cùng chi phí O(N) mỗi bước, nên ít bước hơn cũng có nghĩa là nhanh hơn.
- **Vì sao N = 8 có lần không ra lời giải?** Cực tiểu địa phương (mục 3.5). Tìm kiếm cục bộ không đầy đủ; khởi động lại ngẫu nhiên khắc phục được (mục 3.6).
