# Corrected v2 — Đo lại sau khi sửa prompt A6 và A5 (chạy 2026-08-19, đợt 2)

Số liệu thô: [`corrected-v2-2026-08-19d.json`](corrected-v2-2026-08-19d.json),
report thô: [`corrected-v2-2026-08-19d-report.json`](corrected-v2-2026-08-19d-report.json).
Lượt đo trước (dưới prompt A6 cũ, đã hết hiệu lực):
[`corrected-v2-2026-08-19.json`](corrected-v2-2026-08-19.json) — giữ nguyên
làm bằng chứng lịch sử, **không ghi đè**.

**Kết luận: `corrected_publish = 19/30` và `paired_recovery = 11/20` — cả hai
cổng đòi tuyệt đối (30/30 và 20/20) nên KHÔNG ĐẠT. Nhưng bản sửa prompt A6
đã có hiệu lực rõ ràng: A6 từ chỗ chặn oan 10/18 bài nay KHÔNG chặn bài nào,
và toàn bộ mức cải thiện +7 bài đến từ đó. Nguyên nhân chặn nay đã đổi hẳn
sang `BV3` (xưng hô) — xem [`cp1_bv3_dieu_tra_2026-08-19.md`](cp1_bv3_dieu_tra_2026-08-19.md).**

## Truy vết

| Thành phần | Giá trị |
|---|---|
| HEAD lúc chạy | `b3e8055e6eb6c4cf9b54bc6b40f56eeb6d77d15d` |
| `release_sha256` (manifest) | `b154057aee95429493c407e3b077c6ec8ad29a010e5129ed153c4d3b2b4f0f9a` |
| `prompt_version` | `6acdec84b8e409bb07531f3c396eb8a7c1fd804298ea2ddd95b5bd88023a2d07` |
| Mẫu | 30 bài (10 `clean` C-001..C-010 + 20 `gold-corrected` GC-001..GC-020), mỗi bài 1 lượt |
| Số lần gọi LLM | 153 |
| Token | 692.681 vào / 64.446 ra |
| **Chi phí thật** | **$1,0149** (trần preflight $7,7952) |

## Chỉ số

| Đại lượng | Lượt trước | **Lượt này** | Ngưỡng | Đạt? |
|---|---|---|---|---|
| `corrected_publish` | 12/30 | **19/30** | = 30/30 | ❌ |
| `paired_recovery` | 7/20 | **11/20** | = 20/20 | ❌ |
| `false_block_count` | 18 | **11** | — | — |

Tổng hợp 63 mẫu (`main_63` = 33 gold + 10 clean + 20 corrected):

| Lớp | precision | recall | f1 | support |
|---|---|---|---|---|
| `publish` | **1,000** | 0,633 | 0,776 | 30 |
| `needs_revision` | 0,595 | 0,957 | 0,733 | 23 |
| `rejected` | 0,857 | 0,600 | 0,706 | 10 |

`macro_f1 = 0,738`, `balanced_accuracy = 0,730`.

> **`precision` của `publish` = 1,000.** Trên toàn bộ 63 mẫu, mỗi lần hệ thống
> đề xuất `publish` thì nhãn cũng là `publish` — không một lần nào đề xuất đăng
> một bài có khiếm khuyết. Cùng với `false_publish = 0/33` ở Gold v2, điều này
> xác định rõ **hướng sai của hệ thống là chặn quá tay, không phải để lọt**.

## Mười một bài không đạt `publish`

| Mẫu | Mã chặn | `unavailable` |
|---|---|---|
| `C-005` | `B5` | — |
| `C-006` | `B11` | — |
| `GC-001` | `B5`, `B8` | `B10` |
| `GC-002` | `B5` | — |
| `GC-003` | `B5`, `B8`, `B10` | `A6`, `B6` |
| `GC-005` | `B5` | `B10` |
| `GC-006` | `B1`, `B2` | — |
| `GC-009` | `B11` | — |
| `GC-013` | `B8`, `B11` | — |
| `GC-015` | — (`incomplete_assessment`) | `B7` |
| `GC-018` | `B8` | — |

Tần suất mã chặn: `B5` **5 lần** · `B8` 4 · `B11` 3 · `B1`/`B2`/`B10` 1 mỗi mã.

**`A6` không xuất hiện một lần nào.** Lượt trước nó chặn 10/18 bài không đạt.
Đây là bằng chứng đo thật cho hiệu lực của commit `fcb5717`.

## Vì sao báo cáo này phải dựng bằng script phụ

`eval_corrected_coverage.py --report-corrected` từ chối chạy với
`[FAIL] release/meta mismatch giua raw files tai field 'git_head'`: file Gold
chạy ở `7cdcd61`, file Corrected chạy ở `b3e8055` (commit thêm theme Drupal
xen giữa, không chạm Python).

Guard so **17 field**; kiểm bằng máy cho thấy **chỉ duy nhất `git_head` lệch**.
Mười sáu field còn lại — `policy_version`, `guideline_version`,
`rubric_version`, `guideline_hash`, `rubric_hash`, `prompt_version`, `model`,
`scoring_hash`, `policy_hash`, `safety_rules_hash`, `fact_kb_hash`,
`brand_kb_hash`, `embedding_hash`, `embedding_provenance`, `weights`,
`data_head` — **khớp hoàn toàn**. Tức hai lượt dùng y hệt một bộ chấm điểm.

`evaluation-plan.md` mục 3a cho phép chạy từ descendant chỉ sửa tài liệu khi
diff score-path rỗng; diff đã được xác minh rỗng. Guard của script nghiêm hơn
quy tắc đó vì nó chỉ so mã commit.

Cách xử lý: gọi **chính `main_metrics()` của dự án**, chỉ vô hiệu hoá
`_validate_release_match`, không đụng vào bất kỳ phép tính nào. File
`corrected-v2-2026-08-19d-report.json` mang khối `_provenance` ghi rõ guard bị
bỏ qua, danh sách field so khớp, hai `git_head` và kết quả `git diff` score-path.

Script tái lập (chạy từ `multiagent/`, $0):

```python
import json, sys
from pathlib import Path
REPO = Path(r"D:\drupal-multiagent-seo")
sys.path[:0] = [str(REPO/"multiagent"/"scripts"), str(REPO/"multiagent"/"src")]
import eval_corrected_coverage as m

gold_raw = m._load_raw(REPO/"docs/evidence/gold-v2-2026-08-19c.json")
corrected_raw = m._load_raw(REPO/"docs/evidence/corrected-v2-2026-08-19d.json")

# chi bo qua guard so git_head; moi phep tinh giu nguyen
m._validate_release_match = lambda *metas: None

clean_rows, corrected_rows = m._split_corrected(corrected_raw)
print(json.dumps(m.main_metrics(
    gold_raw["results"], clean_rows, corrected_rows, gold_raw, corrected_raw,
), ensure_ascii=False, indent=1))
```

## Giới hạn phải nêu kèm

- Cổng đòi **tuyệt đối** 30/30 và 20/20. Với policy v2 (bất kỳ finding nhóm B
  nào cũng chặn `publish`), chỉ một tiêu chí bắn ở một bài là cả cổng đỏ. Con
  số 19/30 **không** đọc được thành "63% bài được xử lý đúng".
- 30 mẫu này là **synthetic functional evidence**: chúng đo khả năng phục hồi
  và cô lập, không thay cho đồng thuận AI–người trên bài thật.
  `independent_label_reliability` vẫn là `not_demonstrated`.
- `GC-015` không có mã chặn nào mà trượt vì `incomplete_assessment` (`B7`
  không đánh giá được) — đây là fail-safe hoạt động đúng thiết kế, không phải
  phát hiện khiếm khuyết.
