# Evidence gán lại gold set bởi AI theo guideline v1.4

**Ngày khóa lượt gán:** 2026-08-17\
**Nhánh/worktree:** `ai/v14-relabel` / `.worktrees/ai-v14-relabel`\
**Commit nền:** `b0fa1c862a03250a629525623885e054d2548d65`\
**Annotator:** `AI-A1`\
**Đầu ra:** `docs/goldset/labels-ai-v1.4.csv`

## 1. Kết luận sử dụng dữ liệu

Đây là một lượt **AI-annotated, partially exposed**, không phải ground truth độc lập của con người và không thay thế `docs/goldset/labels.csv` v1.3. Có thể dùng nó làm dữ liệu phát triển/đối chiếu contract v1.4, nhưng không được dùng để tuyên bố đã có đồng thuận AI-người hoặc người-người trên bài thật.

Lý do không thể gọi là gán mù tuyệt đối:

- trước lượt này model đã nhìn thấy một phần nhãn/phân bố cũ trong quá trình audit;
- chính guideline v1.3 chứa ví dụ gắn với một số `sample_id`;
- cuộc trao đổi thiết kế đã nhắc một số acceptance case cụ thể.

Lượt gán vẫn được khóa trước khi mở toàn bộ `labels.csv` để đối chiếu. Việc này giảm thêm neo nhận thức nhưng không xóa được phơi nhiễm đã xảy ra.

## 2. Contract áp dụng

Toàn bộ 33 mẫu được rà lại theo `annotation-guideline.md` v1.4:

- A1-A6 và B1-B10 giữ semantics cũ;
- thêm A7 cho văn xuôi ẩn khỏi người đọc nhưng còn trong input evaluator;
- thêm B11 và CP7 v2 cho claim chính sách pin/bảo hành pin/thuê pin thiếu thành phần thiết yếu;
- B7 được chốt là URL dài trên 75 ký tự;
- B9 được chốt là bài trên 500 tiếng, đếm bằng `split()`, không có H2.

Quy tắc nhãn không đổi: có A → `rejected`; không A nhưng có B → `needs_revision`; chỉ A/B đều vắng → `publish`. Nhiều B không tự nâng thành A.

## 3. Quy trình đã thực hiện

1. Tạo worktree riêng từ commit nền; không đụng các tài liệu đang sửa dở trên nhánh `main`.
2. Đọc `sources.md` để khóa nguồn đối chiếu A3 trước khi gán.
3. Chia 33 bài thành ba batch 11 bài, trộn `G` và `P`, không đọc liên tiếp toàn bộ perturbation.
4. Với mỗi bài, chạy `label_helper.py` chỉ để lấy số đo tất định B3/B4/B6/B7/B9 và C4/C5. Helper không đọc nhãn cũ.
5. Đọc trường đầu vào và nội dung raw; duyệt A trước B; đối chiếu claim số liệu, sạc, chính sách và lỗi ngôn ngữ bằng evidence trong bài.
6. Quét riêng dấu hiệu CP9/A7 trên toàn bộ `docs/goldset/raw/*.txt`.
7. Ghi và khóa `labels-ai-v1.4.csv` với `injected_codes` để trống vì lượt gán không dùng manifest lỗi chèn làm đáp án.
8. Chỉ sau khi khóa file mới mở `labels.csv` v1.3 để đối chiếu quyết định cuối.

Không mở output pipeline E1/E5/E6 khi gán, không gọi model/API trả phí và không sửa nội dung 33 bài.

## 4. Kết quả

| Nhãn | Số bài |
|---|---:|
| `publish` | 0 |
| `needs_revision` | 23 |
| `rejected` | 10 |
| **Tổng** | **33** |

Kết quả này không tạo được lớp `publish`. Vì vậy lượt AI v1.4 **không giải quyết khoảng trống calibration ngưỡng publish của E5 v1**. Không được chuyển 20 bài G thành `publish` chỉ vì chúng từng được xuất bản trên website; các lỗi A/B quan sát được vẫn tồn tại trong raw.

### 4.1. A7

Không mẫu nào có A7 theo detector shape đã thiết kế. Lượt quét không thấy `display:none`, `visibility:hidden`, `opacity:0`, thuộc tính `hidden`, `aria-hidden`, HTML comment chứa văn xuôi, hay chuỗi chỉ dẫn/prompt ẩn trong raw.

Kết luận A7=absent chỉ áp dụng cho representation TXT hiện có; nó không chứng minh HTML nguồn hoặc detector tương lai không có false negative.

### 4.2. B11 / CP7 v2

Tám mẫu có B11:

| Mẫu | CP7 | Lý do ngắn |
|---|---:|---|
| G-007 | 1 | Bảng giá thuê pin có đối tượng và phí nhưng không nêu thời hạn hiệu lực |
| G-009 | 1 | Claim thay/sửa pin dưới 70% không nêu thời hạn hiệu lực |
| G-012 | 1 | Claim đổi pin dưới 70% không nêu thời hạn hiệu lực |
| G-013 | 1 | Claim thay pin dưới 70% không nêu thời hạn hiệu lực |
| G-014 | 1 | Claim hỗ trợ thay pin dưới 70% không nêu thời hạn hiệu lực |
| G-015 | 1 | Claim đổi pin dưới 70% không nêu thời hạn hiệu lực |
| P-003a | 0 | Claim trả pin/tạm dừng hợp đồng khi không dùng lâu thiếu điều kiện cụ thể, phí và thời hạn |
| P-010a | 0 | Claim có hai gói thuê pin nhưng thiếu điều kiện, mức phí và thời hạn |

Các bài chỉ nhắc/link chung được coi là CP7=`NA`; các claim đã nêu đủ yếu tố áp dụng được coi là CP7=2. B11 có thể đồng thời với mã B khác nhưng không làm `needs_revision` thành `rejected`.

### 4.3. Đối chiếu sau khóa với v1.3

Nhãn cuối trùng `33/33`: không có mismatch giữa v1.3 và lượt AI v1.4. Cả hai cùng có 23 `needs_revision`, 10 `rejected`, 0 `publish`.

Không diễn giải con số này là Kappa độc lập hoặc bằng chứng AI-người hoàn hảo. Ngoài phơi nhiễm đã nêu, hai vector không có lớp `publish`, nên chúng không trả lời câu hỏi hệ thống có phân biệt được bài thật sự sẵn sàng xuất bản hay không. Lượt AI còn ghi nhiều defect code hơn v1.3 vì đọc theo contract mới và không dùng short-circuit tối đa; điều đó không có nghĩa các mã bổ sung đã được người thứ hai xác nhận.

## 5. Giới hạn và việc chưa được phép tuyên bố

- Chưa có inter-annotator agreement độc lập.
- Chưa có test-retest v1.4. Guideline yêu cầu chờ ít nhất 3 ngày; sớm nhất là 2026-08-20 và lượt hai phải mù với file này.
- Chưa có lớp `publish` tự nhiên trong gold calibration.
- Không được trộn v1.3 và v1.4 trong cùng phép Kappa/evaluation như thể cùng một contract.
- Không được dùng kết quả này để bật `meta.calibrated=true`, đổi `scoring.yaml` hoặc chốt `publish_min`.
- Không được dùng `injected_codes` trống trong file AI để thay manifest perturbation lịch sử khi tính recall theo mã.

## 6. Trạng thái kiểm thử nền

Lệnh chuẩn `scripts/run_test_group.py all-offline` đã được khởi chạy trước khi sửa nhưng lệnh bọc bị timeout sau 600 giây mà runner chưa in tổng kết. Sau khi hoàn tất dữ liệu, cùng lệnh được chạy lại với timeout 1.800 giây và tiếp tục timeout trước khi có `TOM TAT`. Cả hai lượt đều không đủ bằng chứng để báo pass hoặc fail theo từng test.

Điều tra đọc-only xác nhận runner capture output và chỉ in sau khi chạy xong cả nhóm; manifest tại commit nền có 46 file `pure` + 29 file `postgres` = 75 file, lệch dòng bàn giao ghi 72 file. Không có `test_group_summary.json` hoàn chỉnh được dùng làm evidence cho hai lượt timeout.

Các thay đổi trong worktree chỉ gồm guideline/CSV/evidence; validation cấu trúc riêng của bộ nhãn phải được ghi ở lần kiểm cuối.

## 7. Kiểm contract khi khóa

Chạy từ `multiagent/` bằng Python offline của repository cha vì worktree không có `.venv`:

```powershell
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\test_goldset_ai_v14.py
```

Kết quả: 8/8 PASS — đủ 12 cột manifest, 33 dòng (20 `G`, 13 `P`), nhãn
`needs_revision=23`/`rejected=10`, provenance duy nhất
`AI-annotated-partially-exposed`, guideline `v1.4`, và SHA-256 literal của
`labels.csv` v1.3 đúng `ac74ee3e3f11103f8afb0223685aa3e4004dae7e8eaf3b9cd6f716bb58dfcb17`.
