# Kết quả thực nghiệm N-Queens

Môi trường: Python 3.9.6 · macOS-15.5-arm64-arm-64bit · arm

## 1. Glucose3 (PySAT)

Số mệnh đề CNF và các bộ đếm của Glucose3 (decisions, propagations, conflicts) là tất định; thời gian phụ thuộc máy. Solve = thời gian của `Glucose3.solve()`.

| N | Số biến | Số mệnh đề CNF | Solve (ms) | Sinh CNF (ms) | Nạp (ms) | Tổng (ms) | Decisions | Propagations | Conflicts | Nghiệm hợp lệ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 4 | 16 | 80 | 0.01 | 0.06 | 0.16 | 0.24 | 10 | 32 | 3 | ✓ |
| 6 | 36 | 296 | 0.06 | 0.16 | 0.13 | 0.36 | 73 | 349 | 38 | ✓ |
| 8 | 64 | 736 | 0.04 | 0.41 | 0.29 | 0.74 | 40 | 194 | 12 | ✓ |
| 10 | 100 | 1480 | 0.12 | 0.81 | 0.55 | 1.48 | 100 | 677 | 45 | ✓ |
| 12 | 144 | 2608 | 0.06 | 1.27 | 0.92 | 2.25 | 71 | 409 | 19 | ✓ |
| 16 | 256 | 6336 | 1.02 | 3.08 | 2.19 | 6.28 | 482 | 3904 | 207 | ✓ |
| 20 | 400 | 12560 | 4.15 | 6.88 | 4.25 | 15.27 | 953 | 11198 | 531 | ✓ |
| 24 | 576 | 21920 | 3.47 | 11.13 | 7.42 | 22.01 | 891 | 9866 | 431 | ✓ |
| 30 | 900 | 43240 | 7.40 | 23.49 | 14.40 | 45.29 | 1588 | 18144 | 649 | ✓ |
| 40 | 1600 | 103520 | 4.29 | 57.31 | 34.90 | 96.51 | 1500 | 13370 | 296 | ✓ |
| 50 | 2500 | 203400 | 260.85 | 117.40 | 67.76 | 446.01 | 11452 | 277349 | 7519 | ✓ |
| 60 | 3600 | 352880 | 42.33 | 224.35 | 120.11 | 386.78 | 5475 | 74396 | 1341 | ✓ |
| 80 | 6400 | 840640 | 10295.79 | 576.52 | 288.10 | 11160.41 | 138947 | 4168619 | 104415 | ✓ |
| 100 | 10000 | 1646800 | 8232.98 | 1216.97 | 564.44 | 10014.39 | 91881 | 5499245 | 70981 | ✓ |

## 2. Min-Conflicts chuẩn vs heuristic chọn biến đề xuất

200 lần chạy cho mỗi N, cùng bộ seed nên hai bản xuất phát từ cùng phép gán ban đầu. Hai bản chỉ khác nhau ở bước chọn biến. Một bước = một lần lặp của MIN-CONFLICTS (một lần gán lại một biến).

| N | Thuật toán | Tỉ lệ thành công | Số bước TB | Số bước trung vị | Số bước lớn nhất | Trung vị so với chuẩn | Thời gian TB (ms) |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 8 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 92% | 7566.8 | 35.5 | 100000 | — | 52.65 |
| 8 | Heuristic chọn biến đề xuất | 95% | 5029.9 | 19.0 | 100000 | 54% | 35.38 |
| 16 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 99% | 1087.3 | 66.0 | 100000 | — | 9.24 |
| 16 | Heuristic chọn biến đề xuất | 98% | 2544.8 | 34.5 | 100000 | 52% | 24.27 |
| 32 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 90.3 | 76.5 | 296 | — | 1.19 |
| 32 | Heuristic chọn biến đề xuất | 100% | 51.9 | 46.0 | 171 | 60% | 0.76 |
| 64 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 108.7 | 98.0 | 242 | — | 2.37 |
| 64 | Heuristic chọn biến đề xuất | 100% | 70.0 | 67.0 | 139 | 68% | 1.66 |
| 128 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 159.4 | 154.0 | 331 | — | 6.26 |
| 128 | Heuristic chọn biến đề xuất | 100% | 109.6 | 106.0 | 212 | 69% | 4.57 |
| 256 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 244.0 | 240.0 | 341 | — | 18.92 |
| 256 | Heuristic chọn biến đề xuất | 100% | 173.7 | 169.0 | 306 | 70% | 14.15 |
| 512 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 405.8 | 397.0 | 565 | — | 64.72 |
| 512 | Heuristic chọn biến đề xuất | 100% | 299.0 | 297.0 | 360 | 75% | 48.59 |
| 1000 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 714.1 | 708.5 | 876 | — | 218.82 |
| 1000 | Heuristic chọn biến đề xuất | 100% | 540.6 | 538.0 | 635 | 76% | 169.78 |

## 3. Ablation: đóng góp của từng thành phần

Dòng cuối dùng thêm các kỹ thuật ngoài phạm vi chọn biến, đưa vào để tham khảo, không thuộc phép so sánh chính ở mục 2.

| N | Thuật toán | Tỉ lệ thành công | Số bước TB | Số bước trung vị | Số bước lớn nhất | Trung vị so với chuẩn | Thời gian TB (ms) |
|---:|:---|---:|---:|---:|---:|---:|---:|
| 8 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 92% | 7566.8 | 35.5 | 100000 | — | 47.36 |
| 8 | Biến xung đột nhiều nhất, không tabu | 94% | 6564.4 | 36.5 | 100000 | 103% | 42.16 |
| 8 | Heuristic chọn biến đề xuất | 95% | 5029.9 | 19.0 | 100000 | 54% | 34.26 |
| 8 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 13.2 | 10.0 | 98 | 28% | 0.13 |
| 16 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 99% | 1087.3 | 66.0 | 100000 | — | 9.02 |
| 16 | Biến xung đột nhiều nhất, không tabu | 96% | 3580.3 | 65.5 | 100000 | 99% | 30.12 |
| 16 | Heuristic chọn biến đề xuất | 98% | 2544.8 | 34.5 | 100000 | 52% | 23.99 |
| 16 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 24.5 | 20.0 | 149 | 30% | 0.31 |
| 64 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 108.7 | 98.0 | 242 | — | 2.32 |
| 64 | Biến xung đột nhiều nhất, không tabu | 100% | 94.2 | 87.0 | 220 | 89% | 2.10 |
| 64 | Heuristic chọn biến đề xuất | 100% | 70.0 | 67.0 | 139 | 68% | 1.62 |
| 64 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 31.7 | 27.0 | 82 | 28% | 1.38 |
| 256 | Chuẩn (chọn ngẫu nhiên biến xung đột) | 100% | 244.0 | 240.0 | 341 | — | 18.39 |
| 256 | Biến xung đột nhiều nhất, không tabu | 100% | 203.6 | 199.0 | 289 | 83% | 15.86 |
| 256 | Heuristic chọn biến đề xuất | 100% | 173.7 | 169.0 | 306 | 70% | 13.92 |
| 256 | Heuristic chọn biến + khởi tạo tham lam + tabu giá trị + restart | 100% | 39.9 | 37.0 | 89 | 15% | 12.48 |

## 4. Ablation SAT: thêm nhóm mệnh đề "mỗi cột có ít nhất một hậu"

Nhóm này được KB gốc suy ra (nguyên lý chuồng bồ câu) nên hai KB có cùng tập mô hình; chỉ thêm N mệnh đề. Khác biệt nằm ở công việc của Glucose3: có mệnh đề cột thì unit propagation suy ra ngay ô cuối cùng của một cột.

| N | Mệnh đề (gốc) | Conflicts (gốc) | Decisions (gốc) | Solve gốc (ms) | Mệnh đề (+cột) | Conflicts (+cột) | Decisions (+cột) | Solve +cột (ms) | Nghiệm hợp lệ |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|:---:|
| 4 | 80 | 3 | 10 | 0.01 | 84 | 2 | 12 | 0.01 | ✓ |
| 6 | 296 | 38 | 73 | 0.07 | 302 | 7 | 18 | 0.01 | ✓ |
| 8 | 736 | 12 | 40 | 0.03 | 744 | 21 | 39 | 0.06 | ✓ |
| 10 | 1480 | 45 | 100 | 0.13 | 1490 | 14 | 39 | 0.04 | ✓ |
| 12 | 2608 | 19 | 71 | 0.06 | 2620 | 34 | 75 | 0.15 | ✓ |
| 16 | 6336 | 207 | 482 | 0.99 | 6352 | 952 | 1195 | 7.52 | ✓ |
| 20 | 12560 | 531 | 953 | 4.00 | 12580 | 167 | 542 | 1.11 | ✓ |
| 24 | 21920 | 431 | 891 | 3.43 | 21944 | 2805 | 3678 | 37.35 | ✓ |
| 30 | 43240 | 649 | 1588 | 7.32 | 43270 | 137 | 632 | 1.27 | ✓ |
| 40 | 103520 | 296 | 1500 | 4.17 | 103560 | 312 | 1809 | 3.74 | ✓ |
| 50 | 203400 | 7519 | 11452 | 250.36 | 203450 | 250 | 1842 | 3.49 | ✓ |
| 60 | 352880 | 1341 | 5475 | 39.72 | 352940 | 203 | 2593 | 4.95 | ✓ |
| 80 | 840640 | 104415 | 138947 | 9898.06 | 840720 | 276 | 7154 | 10.75 | ✓ |
| 100 | 1646800 | 70981 | 91881 | 8299.46 | 1646900 | 277 | 8211 | 14.75 | ✓ |
