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

⏳ **Chưa có.** Điền sau khi nhãn lượt hai được khoá. Phải ghi: Kappa toàn bộ 4 mẫu, số
mẫu bất đồng kèm lý do, và Kappa tính riêng trên 3 mẫu `gold-real` để người đọc đối chiếu
với đoạn giới hạn ở trên.
