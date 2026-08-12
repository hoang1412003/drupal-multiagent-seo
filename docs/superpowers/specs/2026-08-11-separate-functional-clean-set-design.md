# Thiết kế tách bộ functional-clean khỏi gold set

**Ngày:** 2026-08-11  
**Phạm vi:** dữ liệu đánh giá, script E5/extractor và tài liệu Sprint 2–3

## 1. Mục tiêu

Giữ nguyên giá trị của 10 bài `C-001`–`C-010` đã hiệu đính nhưng không để chúng tham gia calibration hoặc Kappa của gold set. Sau thay đổi:

- Gold set chính thức vẫn có 33 mẫu: 20 `gold-real` và 13 `gold-pert`.
- Bộ `functional-clean` có 10 mẫu corrected, dùng đo false positive và kiểm tra đường ra `publish`.
- Có thể báo cáo “evaluation suite gồm 43 mẫu”, nhưng mọi chỉ số phải tách theo lát dữ liệu.
- E5 không thể vô tình chấm hoặc calibrate trên mẫu functional-clean.
- Bóc tách lại HTML không thể âm thầm ghi đè bản perturbation/corrected.

## 2. Cấu trúc dữ liệu

Tách vật lý thay vì chỉ dựa vào cột `split`:

```text
docs/goldset/
  labels.csv                 # chỉ 33 mẫu G/P
  raw/                       # chỉ G/P dùng cho E1/E5
  raw_html/                  # bằng chứng nguồn G/P

docs/functional-tests/
  clean_labels.csv           # 10 mẫu C, expected_label=publish
  corrections.md             # nhật ký hiệu đính
  clean/                     # C-xxx.txt đã hiệu đính
  raw_html/                  # C-xxx.html nguyên bản
```

Không đổi nội dung 10 TXT hoặc HTML trong thao tác di chuyển. `clean_labels.csv` lưu nguồn, biến thể `corrected`, nhãn kỳ vọng và ghi chú, nhưng không được `eval_calibration.py` đọc.

## 3. Chốt an toàn trong code

### 3.1. E5 chỉ đọc manifest gold set

`eval_calibration.py` không liệt kê mọi `.txt` trong thư mục nữa. Script đọc `labels.csv`, chỉ nhận `split` thuộc `{gold-real, gold-pert}`, kiểm tra file tương ứng tồn tại rồi mới chấm.

Nếu manifest có split khác, script bỏ khỏi calibration. Nếu một dòng gold hợp lệ thiếu file, script dừng với lỗi rõ ràng thay vì âm thầm bỏ qua. Kết quả cũ chứa sample ngoài tập 33 cũng bị loại khỏi pha quét, không được tham gia Kappa.

### 3.2. Extractor không ghi đè mặc định

`extract_gold_sample.py` từ chối ghi khi file đích đã tồn tại. Người vận hành phải truyền `--force` khi thật sự muốn tái tạo file từ HTML nguồn. Cảnh báo phải in cả đường dẫn đích và chỉ dẫn dùng `--force`.

Chốt này bảo vệ cả perturbation hiện tại và mọi bản chỉnh tay trong tương lai. Tài liệu thu thập được cập nhật để lệnh chạy lần đầu không cần `--force`; tái tạo có chủ đích mới dùng cờ này.

### 3.3. E1 chống resume sai phiên bản

`eval_stability.py` ghi `_meta.prompt_version` giống E5. Khi file kết quả cũ thiếu metadata hoặc có phiên bản khác, script dừng trước khi gọi API và yêu cầu dùng `--ket-qua` mới. Dữ liệu E1 phải tiếp tục giữ cấu trúc đủ để chế độ `--bao-cao` đọc được.

## 4. Tài liệu cần đồng bộ

- `README.md`: đánh dấu gold set Sprint 2 đã hoàn thành.
- `docs/goldset/sources.md`: gold set 33; dẫn sang functional-clean 10; tổng evaluation suite 43.
- `docs/goldset/annotation-guideline.md`: schema gold chỉ còn `original|perturbed`; corrected không thuộc quy trình gán nhãn gold.
- `docs/functional-tests/corrections.md`: đổi thuật ngữ từ `gold-corrected` thành `functional-clean`.
- `docs/technical-debt.md`: giữ nguyên lịch sử E5 trên 33 mẫu, đánh dấu mục 8.6 đã có 10 mẫu sạch nhưng chưa chạy pipeline; ghi thêm hai chốt an toàn.
- `docs/sprint2-report.md`: thêm hậu kiểm rằng bộ functional-clean được tạo sau Sprint 2, không thay đổi kết quả 33 mẫu.
- `docs/evaluation-plan.md`: E5 chỉ dùng 33 mẫu; functional-clean báo cáo riêng tỷ lệ `publish` và số báo lỗi giả.

Không sửa lại các số E5 lịch sử (`Kappa=0,713`, accuracy `0,879`) vì chúng được đo trên đúng 33 mẫu.

## 5. Kiểm thử

Thực hiện TDD cho ba hành vi:

1. E5 chỉ trả ID `gold-real`/`gold-pert`, loại `functional-clean` và báo lỗi khi gold ID thiếu TXT.
2. Extractor từ chối ghi đè nếu không có `--force`, nhưng ghi được khi có `--force`.
3. E1 từ chối resume file thiếu/sai `prompt_version`, chấp nhận file cùng phiên bản và file mới.

Sau migration:

- `labels.csv` phải có đúng 33 dòng: 10 `rejected`, 23 `needs_revision`, 0 `publish`.
- `clean_labels.csv` phải có đúng 10 dòng và tất cả expected label là `publish`.
- Không còn `C-*.txt` hoặc `C-*.html` dưới `docs/goldset`.
- 37 test script cũ và test mới đều phải xanh.
- Chưa chạy E1/E5 có phí trong thay đổi này; E1 chỉ chạy sau khi người dùng xác nhận ngân sách API khoảng 3 USD.

## 6. Ngoài phạm vi

- Không thay đổi nội dung 10 bài C.
- Không thay đổi 13 bài P hoặc mã lỗi đã chèn.
- Không thay đổi rubric, prompt, trọng số hoặc ngưỡng quyết định.
- Không tự đặt `meta.calibrated: true`.
- Không chạy lại E5 cho tới khi xử lý CP4 và khóa phiên bản chấm điểm cuối.
