# Gold v2 — Kappa so với nhãn người, policy `cam-nang-vn-v2` (chạy 2026-08-19)

Số liệu thô: [`gold-v2-2026-08-19.json`](gold-v2-2026-08-19.json), report thô:
[`gold-v2-2026-08-19-report.json`](gold-v2-2026-08-19-report.json).
Điều kiện tiên quyết: E1 v2 đã đạt — [`e1_v2_2026-08-19_report.md`](e1_v2_2026-08-19_report.md)
(`decision_consistency = 1,00`).

**Kết luận: `Kappa = 0,6765` ≥ 0,60 → ĐẠT. `false_publish = 0/33` → ĐẠT.**

## Truy vết

| Thành phần | Giá trị |
|---|---|
| HEAD lúc chạy | `a846ae08dbd3b1e9563b86be73a5b546b1539672` |
| Mẫu | 33 bài (20 G + 13 P), mỗi bài 1 lần |
| Nhãn đối chiếu | `docs/goldset/labels-ai-v1.4.csv` — **AI tự gán**, `provenance =
  AI-annotated-partially-exposed`; trùng khít 33/33 với `labels.csv` v1.3
  (người gán) tại thời điểm rà lại, nhưng `independent_label_reliability`
  vẫn `not_demonstrated` |
| Chi phí thật | **$1,975** |

## Chỉ số

| Đại lượng | Giá trị | Ngưỡng | Đạt? |
|---|---|---|---|
| Kappa | **0,6765** | ≥ 0,60 | ✅ |
| `false_publish_count` | **0/33** | = 0 | ✅ |
| `needs_revision_recall` | 1,00 | — | — |
| `rejected_recall` | **0,60** | — | ⚠️ xem chẩn đoán |

Ma trận nhầm lẫn (hàng = nhãn người, cột = quyết định máy; thứ tự
publish/needs_revision/rejected):

```
              publish  needs_revision  rejected
publish            0                0         0
needs_revision     0               23         0
rejected           0                4         6
```

Không có bài nào bị đề xuất `publish` sai (`false_publish = 0`) — đúng vấn
đề gốc E5 v1 từng thất bại (`publish_min=80` sai 9/33) đã được giải quyết
bằng thiết kế, không phải chỉnh số.

## Chẩn đoán `rejected_recall = 0,60` — 4 bài, hai nguyên nhân khác nhau

| Bài | Findings thật | Nguyên nhân |
|---|---|---|
| `P-004b` | có `A4` | **Cái giá trực tiếp** của quyết định hạ A6/A4 xuống nhóm B (2026-08-18) — trước đây A4 tự đủ đẩy `rejected` |
| `P-010a` | có `A4` | Cùng nguyên nhân |
| `G-011` | chỉ mã B, **không có finding nhóm A nào** | **Không liên quan** tới thay đổi hôm nay — lỗ hổng đã biết từ v1: *"G-011 và G-020 bỏ sót A1 (claim tuyệt đối)"* (`technical-debt.md` mục 8.2, chẩn đoán E5 bản 3) |
| `G-020` | chỉ mã B, **không có finding nhóm A nào** | Cùng lỗ hổng cũ, không phải phát sinh mới |

**Tóm lại:** cái giá thật của quyết định hạ A6/A4 chỉ là **2/33 bài** (`P-004b`,
`P-010a`) — đúng bằng đánh đổi đã cảnh báo trước khi làm (ổn định hơn,
nhưng kém nhạy hơn với đúng 2 loại vi phạm đó). 2 bài còn lại là lỗ hổng
A1 tồn tại từ trước, không phát sinh do hôm nay.

## Giới hạn phải nêu kèm số Kappa

- Nhãn đối chiếu là **AI tự gán** (`labels-ai-v1.4.csv`), chưa qua test–retest
  người thật độc lập (`independent_label_reliability = not_demonstrated`,
  dự kiến sớm nhất 2026-08-20). Kappa 0,6765 có tư cách **tạm**, chưa được
  coi là đã kiểm chứng độc lập.
- n=33, không quét lại ngưỡng (v2 không có ngưỡng điểm để quét) — đây là
  **một** phép đo, không phải kết quả tối ưu qua nhiều lượt.

## Việc kế tiếp

Theo đúng plan Evaluation (Task 5→8): tiếp theo là **Corrected v2** (30 mẫu,
ước ~$1,7) rồi **Coverage v2** (11 mẫu, ước ~$0,6). `scoring.yaml.meta.calibrated`
không đổi.
