# Test–retest nhãn gold set — lượt hai (2026-08-15)

Giao thức: [`goldset/annotation-guideline.md` mục 8.1](../goldset/annotation-guideline.md#81-nhất-quán-nội-bộ-intra-annotator-test-retest)
và [`technical-debt.md` mục 8.3](../technical-debt.md).

**Mục đích:** đo Cohen's Kappa giữa hai lượt gán nhãn của **cùng một người** trên cùng
bộ mẫu, để có **trần trên** cho việc diễn giải Kappa AI–người ở E5. Chưa có trần thì con
số Kappa AI–người không nói lên điều gì (guideline mục 8.2).

**Tiêu chí:** Kappa ≥ 0,80. Dưới mức đó → sửa guideline, tăng version, gán lại toàn bộ.

## Điều kiện tiền đề

| Điều kiện | Giá trị |
|---|---|
| Lượt một gán xong | 2026-08-10 (`labels.csv`, annotator `A1`, guideline `v1.3`) |
| Yêu cầu chờ | ≥ 3 ngày |
| Lượt hai | 2026-08-15 — **đạt** (5 ngày) |

## Cách bốc mẫu — tái lập được

Pool = **toàn bộ 33 mẫu** trong `docs/goldset/labels.csv`, đúng chữ guideline mục 8.1
("chọn ngẫu nhiên 10% mẫu"). Danh sách `sample_id` được **sắp xếp trước** khi bốc để kết
quả không phụ thuộc thứ tự dòng trong file.

```bash
multiagent/.venv/Scripts/python.exe -c "
import csv, random
with open('docs/goldset/labels.csv', encoding='utf-8') as f:
    ids = sorted(r['sample_id'] for r in csv.DictReader(f))
random.seed(20260815)
print(sorted(random.sample(ids, 4)))
"
```

Seed `20260815` chọn theo ngày chạy, **chốt trước khi nhìn kết quả**. Chỉ bốc **một lần**;
không bốc lại. Bốc tới khi vừa ý là đúng bẫy "chỉnh cho phân bố đẹp" đã cắn dự án ở B9
(`technical-debt.md`, mục "Ba cái bẫy").

**Kết quả bốc:**

| `sample_id` | split | Nhóm việc (theo `quet_ung_vien.py`) |
|---|---|---|
| G-002 | `gold-real` | QUÉT ĐẦY ĐỦ |
| G-006 | `gold-real` | QUÉT ĐẦY ĐỦ |
| G-019 | `gold-real` | QUÉT ĐẦY ĐỦ |
| P-007a | `gold-pert` | XONG |

## Tài liệu cho người gán

- Bài gốc: `docs/goldset/raw/{G-002,G-006,G-019,P-007a}.txt`
- File trợ giúp lượt hai: [`test_retest_2026-08-15_helper.txt`](test_retest_2026-08-15_helper.txt)
  — sinh bằng `quet_ung_vien.py`, **cùng công cụ lượt một đã dùng**
- Quy tắc: `annotation-guideline.md` mục 4 (bảng mã lỗi) và mục 5 (quy tắc quy nhãn)
- Nhãn lượt hai ghi vào: [`test_retest_2026-08-15.csv`](test_retest_2026-08-15.csv)

**Mù với lượt một:** người gán không mở `docs/goldset/labels.csv`, không mở form soạn bài
Drupal của 4 bài này (báo cáo AI hiện trong đó), và model hỗ trợ không được nhắc lại
`label` / `defect_codes` / `notes` cũ. Nhãn lượt hai phải **khoá** trước khi mở nhãn lượt
một để tính Kappa.

## Giới hạn đã biết — phải nêu khi báo cáo

**1/4 mẫu (`P-007a`) thuộc `gold-pert`.** Nhãn lượt một của nhóm này **không** đến từ việc
đọc bài mà **suy tất định từ `injected_codes`** (`goldset/labeling-session-guide.md`: nhóm
XONG, *"Không cần đọc"*). Công cụ `quet_ung_vien.py` in thẳng nhãn suy ra cho nhóm này
(`multiagent/scripts/quet_ung_vien.py:171-174`).

Hệ quả: mẫu đó **đồng thuận 1,0 do cấu tạo, không phải do đo**. Nó đẩy Kappa lên cao hơn
mức phản ánh độ nhất quán thật của người gán.

Đây là **sai lệch theo hướng an toàn** và được guideline mục 8.2 chấp nhận tường minh:
trần cao hơn thật khiến AI trông *kém hơn* chứ không thổi phồng kết quả. Vẫn phải nêu ra,
không được báo cáo Kappa trần mà giấu chỗ này.

Đã cân nhắc và **không** chọn: (a) bốc riêng từ 20 mẫu `gold-real` — sạch hơn về phương
pháp nhưng lệch khỏi chữ guideline; (b) giấu `injected_codes` ở lượt hai — làm lượt hai
chạy quy trình **khác** lượt một, Kappa tụt vì hiện vật phương pháp chứ không vì guideline
mơ hồ, và nếu tụt dưới 0,80 sẽ kích hoạt yêu cầu gán lại toàn bộ 33 mẫu.

## Kết quả

Nhãn lượt hai được **khoá tại commit `cc872d6`** trước khi mở `labels.csv`. Thứ tự này
kiểm chứng được bằng lịch sử git: commit khoá không chứa kết quả Kappa nào.

### So khớp từng mẫu

| `sample_id` | Lượt một (2026-08-10) | Lượt hai (2026-08-15) | |
|---|---|---|---|
| G-002 | `needs_revision` | `needs_revision` | khớp |
| G-006 | `needs_revision` | `needs_revision` | khớp |
| G-019 | `needs_revision` | `needs_revision` | khớp |
| P-007a | `rejected` | `rejected` | khớp |

### Chỉ số

| | n | `po` | `pe` | Cohen's Kappa |
|---|---|---|---|---|
| Toàn bộ | 4 | 1,000 | 0,625 | **1,000** |
| Chỉ `gold-real` | 3 | 1,000 | 1,000 | **không xác định** (`pe = 1`) |

**Tiêu chí ≥ 0,80: đạt.** Nhưng con số này **không được báo cáo trần trụi** — ba giới hạn
dưới đây phải đi kèm, nếu không nó nói sai về mức tin cậy của nhãn.

### Ba giới hạn phải nêu kèm

**1. Tập `gold-real` không có phương sai nhãn → Kappa không tính được ở đó.** Cả 3 mẫu
`gold-real` đều là `needs_revision` ở cả hai lượt, nên `pe = 1` và Kappa là `0/0`. Nghĩa
là phần mẫu *thật sự cần phán đoán* không phân biệt được người gán với một cỗ máy luôn trả
lời `needs_revision`. **Toàn bộ phương sai nhãn của phép đo đến từ đúng một mẫu: P-007a.**

**2. Mẫu duy nhất tạo ra phương sai lại là mẫu đồng thuận do cấu tạo.** P-007a thuộc
`gold-pert`, nhãn suy tất định từ `injected_codes` (`A1;B5`) chứ không từ phán đoán. Vậy
Kappa = 1,000 đứng trên một mẫu vốn **không thể lệch**.

**3. Với n = 4, chỉ số cực kỳ mong manh.** Đo độ nhạy: chỉ cần **một** mẫu lệch là rơi
thẳng dưới ngưỡng.

| Nếu mẫu này lệch | Kappa còn |
|---|---|
| G-002 / G-006 / G-019 | 0,500 — trượt |
| P-007a | 0,000 — trượt |

Tức phép đo thực chất là nhị phân: khớp tuyệt đối thì đạt, lệch một mẫu là trượt. Không có
vùng trung gian để đọc mức độ.

### Diễn giải đúng khi dùng làm trần cho E5

Trần = **1,000**, và đó là **hướng an toàn** theo guideline mục 8.2: trần cao hơn thực tế
khiến Kappa AI–người trông *kém hơn* chứ không thổi phồng. Nhưng phải nói thẳng rằng trần
này **mất chức năng chẩn đoán** mà mục 8.2 thiết kế cho nó: với trần 1,000 thì không bao
giờ kích hoạt được cảnh báo *"AI đạt 0,85 khi trần chỉ 0,65 là dấu hiệu đáng nghi"*.

Câu phải viết trong báo cáo Sprint 3:

> *Test–retest trên 4/33 mẫu cho đồng thuận 4/4 và Kappa = 1,000 (đạt ngưỡng ≥ 0,80).
> Con số này là ước lượng lạc quan và không ổn định: 3/4 mẫu có cùng một nhãn ở cả hai
> lượt nên không đóng góp phương sai, mẫu còn lại thuộc tập perturbation nên đồng thuận
> do cấu tạo, và chỉ một mẫu lệch là chỉ số rơi xuống 0,50. Gold set do một người gán
> nhãn nên không đo được inter-annotator agreement; trần báo cáo ở đây là Kappa
> test–retest của cùng người gán.*

### Không mở rộng cỡ mẫu sau khi đã thấy kết quả

Đã cân nhắc bốc thêm mẫu cho ước lượng ổn định hơn và **không làm trong phép đo này**:
bốc thêm *sau khi* đã nhìn kết quả là optional stopping, đúng lỗi mà `technical-debt.md`
đã bác bỏ ở ca "thu thêm corpus để đẩy p qua ngưỡng". Kết quả trên là số đã đăng ký trước,
giữ nguyên.

Nếu muốn ước lượng tốt hơn thì phải chạy một lượt **riêng, độc lập**, khai báo cỡ mẫu
trước, và báo cáo **cạnh** kết quả này chứ không thay thế nó.
