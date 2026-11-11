# Kết quả thực nghiệm N-Queens

Môi trường: Python 3.9.6 · macOS-15.5-arm64-arm-64bit · arm

## 1. Glucose3 (PySAT)

Số mệnh đề CNF và các bộ đếm của Glucose3 (decisions, propagations, conflicts) là tất định; thời gian phụ thuộc máy. Solve = thời gian của `Glucose3.solve()`.

| N | Số biến | Số mệnh đề CNF | Solve (ms) | Sinh CNF (ms) | Nạp (ms) | Tổng (ms) | Decisions | Propagations | Conflicts | Nghiệm hợp lệ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 4 | 16 | 80 | 0.02 | 0.06 | 0.13 | 0.22 | 10 | 32 | 3 | ✓ |
| 6 | 36 | 296 | 0.06 | 0.17 | 0.13 | 0.36 | 73 | 349 | 38 | ✓ |
| 8 | 64 | 736 | 0.03 | 0.39 | 0.27 | 0.69 | 40 | 194 | 12 | ✓ |
| 10 | 100 | 1480 | 0.12 | 0.78 | 0.52 | 1.42 | 100 | 677 | 45 | ✓ |
| 12 | 144 | 2608 | 0.08 | 1.23 | 1.00 | 2.32 | 71 | 409 | 19 | ✓ |
| 16 | 256 | 6336 | 1.00 | 3.01 | 2.13 | 6.14 | 482 | 3904 | 207 | ✓ |
| 20 | 400 | 12560 | 4.05 | 6.72 | 4.12 | 14.89 | 953 | 11198 | 531 | ✓ |
| 24 | 576 | 21920 | 3.39 | 10.88 | 7.02 | 21.29 | 891 | 9866 | 431 | ✓ |
| 30 | 900 | 43240 | 7.23 | 22.68 | 13.87 | 43.78 | 1588 | 18144 | 649 | ✓ |
| 40 | 1600 | 103520 | 4.20 | 55.34 | 33.10 | 92.64 | 1500 | 13370 | 296 | ✓ |
| 50 | 2500 | 203400 | 251.70 | 113.78 | 65.37 | 430.86 | 11452 | 277349 | 7519 | ✓ |
| 60 | 3600 | 352880 | 40.24 | 211.51 | 113.37 | 365.13 | 5475 | 74396 | 1341 | ✓ |
| 80 | 6400 | 840640 | 10055.50 | 567.30 | 278.03 | 10900.83 | 138947 | 4168619 | 104415 | ✓ |
| 100 | 10000 | 1646800 | 8120.31 | 1169.68 | 531.75 | 9821.74 | 91881 | 5499245 | 70981 | ✓ |

## 2. Min-Conflicts chuẩn vs heuristic chọn biến đề xuất

50 lần chạy cho mỗi N, cùng bộ seed nên hai bản xuất phát từ cùng phép gán ban đầu. Hai bản chỉ khác nhau ở bước chọn biến. Một bước = một lần lặp của MIN-CONFLICTS (một lần gán lại một biến).

| N | Thuật toán | Tỉ lệ thành công | Số bước TB | Số bước trung vị | Số bước lớn nhất | Trung vị so với chuẩn | Thời gian TB (ms) |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 8 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 94% | 6073.6 | 32.0 | 100000 | — | 37.67 |
| 8 | Heuristic chọn biến đề xuất | 94% | 6028.4 | 18.0 | 100000 | 56% | 41.66 |
| 16 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 89.7 | 73.5 | 287 | — | 0.78 |
| 16 | Heuristic chọn biến đề xuất | 98% | 2049.0 | 44.5 | 100000 | 61% | 19.04 |
| 32 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 86.8 | 76.0 | 244 | — | 1.12 |
| 32 | Heuristic chọn biến đề xuất | 100% | 47.3 | 46.5 | 101 | 61% | 0.69 |
| 64 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 107.9 | 98.5 | 182 | — | 2.31 |
| 64 | Heuristic chọn biến đề xuất | 100% | 71.7 | 70.5 | 107 | 72% | 1.68 |
| 128 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 150.7 | 145.5 | 331 | — | 5.77 |
| 128 | Heuristic chọn biến đề xuất | 100% | 108.9 | 107.0 | 155 | 74% | 4.42 |
| 256 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 240.0 | 233.0 | 317 | — | 18.07 |
| 256 | Heuristic chọn biến đề xuất | 100% | 172.8 | 169.0 | 245 | 73% | 13.69 |
| 512 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 407.7 | 404.5 | 520 | — | 63.45 |
| 512 | Heuristic chọn biến đề xuất | 100% | 296.1 | 294.0 | 340 | 73% | 47.88 |
| 1000 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 716.2 | 710.5 | 835 | — | 220.92 |
| 1000 | Heuristic chọn biến đề xuất | 100% | 540.7 | 539.0 | 582 | 76% | 176.77 |

## 3. Ablation: đóng góp của từng thành phần

Dòng cuối dùng thêm các kỹ thuật ngoài phạm vi chọn biến, đưa vào để tham khảo, không thuộc phép so sánh chính ở mục 2.

| N | Thuật toán | Tỉ lệ thành công | Số bước TB | Số bước trung vị | Số bước lớn nhất | Trung vị so với chuẩn | Thời gian TB (ms) |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 8 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 94% | 6073.6 | 32.0 | 100000 | — | 40.59 |
| 8 | Biến xung đột nhiều nhất, không tabu | 94% | 6062.6 | 49.5 | 100000 | 155% | 38.64 |
| 8 | Heuristic chọn biến đề xuất | 94% | 6028.4 | 18.0 | 100000 | 56% | 41.78 |
| 8 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 13.7 | 11.0 | 46 | 34% | 0.13 |
| 16 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 89.7 | 73.5 | 287 | — | 0.77 |
| 16 | Biến xung đột nhiều nhất, không tabu | 96% | 4078.1 | 64.0 | 100000 | 87% | 33.86 |
| 16 | Heuristic chọn biến đề xuất | 98% | 2049.0 | 44.5 | 100000 | 61% | 18.98 |
| 16 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 24.7 | 19.0 | 149 | 26% | 0.32 |
| 64 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 107.9 | 98.5 | 182 | — | 2.31 |
| 64 | Biến xung đột nhiều nhất, không tabu | 100% | 97.9 | 82.5 | 211 | 84% | 2.19 |
| 64 | Heuristic chọn biến đề xuất | 100% | 71.7 | 70.5 | 107 | 72% | 1.67 |
| 64 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 30.5 | 27.5 | 63 | 28% | 1.36 |
| 256 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 240.0 | 233.0 | 317 | — | 18.23 |
| 256 | Biến xung đột nhiều nhất, không tabu | 100% | 202.0 | 197.5 | 277 | 85% | 15.87 |
| 256 | Heuristic chọn biến đề xuất | 100% | 172.8 | 169.0 | 245 | 73% | 15.52 |
| 256 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 41.7 | 41.0 | 85 | 18% | 12.70 |
