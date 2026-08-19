# Coverage v2 — Đo lần đầu sau khi sửa prompt A5 và fixture CV-A7-01 (chạy 2026-08-19, đợt 2)

Số liệu thô: [`coverage-v2-2026-08-19d.json`](coverage-v2-2026-08-19d.json),
report thô: [`coverage-v2-2026-08-19d-report.json`](coverage-v2-2026-08-19d-report.json).
Lượt chẩn đoán trước: [`coverage-v2-2026-08-19.json`](coverage-v2-2026-08-19.json)
— lượt đó được đóng khung ngay từ đầu là **chạy chẩn đoán để tìm lỗi**, không
phải cổng đo lường.

**Kết luận: `passed = 3/11`, `failed = 8/11` → cổng KHÔNG ĐẠT (đòi 11 pass /
0 fail). Nhưng khả năng phát hiện đúng mã nhắm tới đạt 10/11 (lượt trước
8/11), và cả hai bản sửa hôm trước đều được xác nhận có hiệu lực bằng đo thật.
Tám mẫu `failed` đều do NHIỄU PHỤ trong fixture, không phải do bỏ sót mã mục
tiêu.**

## Truy vết

| Thành phần | Giá trị |
|---|---|
| HEAD lúc chạy | `b3e8055e6eb6c4cf9b54bc6b40f56eeb6d77d15d` |
| `release_sha256` (manifest) | `b154057aee95429493c407e3b077c6ec8ad29a010e5129ed153c4d3b2b4f0f9a` |
| Mẫu | 11 mẫu `CV-*`, mỗi mẫu 1 lượt |
| Số lần gọi LLM | 56 |
| Token | 220.093 vào / 22.724 ra |
| **Chi phí thật** | **$0,3337** (trần preflight $2,85824) |

## Kết quả từng mẫu

| Mẫu | Mã nhắm tới | Bắn đúng? | Quyết định | Nhiễu phụ | `unavailable` |
|---|---|---|---|---|---|
| `CV-A3-01` | A3 | ✅ | rejected | `B1`,`B3`,`B10` | — |
| `CV-A5-01` | A5 | ✅ | rejected | — | `B7` |
| `CV-A5-02` | A5 | ✅ | rejected | `B8` | — |
| `CV-A6-01` | A6 | ✅ | needs_revision | `B8` | — |
| `CV-A6-02` | A6 | ✅ | rejected | `A5`,`B8` | — |
| `CV-A7-01` | A7 | ✅ | rejected | `B5` | — |
| `CV-A7-02` | A7 | ✅ | rejected | — | — |
| `CV-B6-01` | B6 | ✅ | needs_revision | — | — |
| `CV-B7-01` | B7 | ❌ | needs_revision | `B8` | — |
| `CV-B9-01` | B9 | ✅ | needs_revision | — | — |
| `CV-B9-02` | B9 | ✅ | needs_revision | `B8` | — |

Ba mẫu `passed` đúng là ba mẫu **cô lập sạch tuyệt đối** (không nhiễu, không
`unavailable`): `CV-A7-02`, `CV-B6-01`, `CV-B9-01`.

Theo mã: A7 1/2 · B6 1/1 · B9 1/2 · A3 0/1 · A5 0/2 · A6 0/2 · B7 0/1.

## Hai bản sửa hôm trước đã được xác nhận bằng đo thật

| Mẫu | Lượt chẩn đoán trước | **Lượt này** | Commit sửa |
|---|---|---|---|
| `CV-A5-02` | A5 không bắn (evidence là câu tóm tắt, bị fail-safe exact-match từ chối) | ✅ **bắn đúng** | `76dd295` — bắt evidence phải là nguyên văn một câu |
| `CV-A7-01` | A7 không bắn (fixture dùng `<p hidden>`, ngoài phạm vi detector CP9) | ✅ **bắn đúng** | `f854ee6` — đổi sang `style="display:none"` |

## `CV-B7-01` vẫn miss — đúng rủi ro đã biết trước

`SEO5` không có ngưỡng số tất định; nó hoàn toàn dựa phán đoán chủ quan của
LLM về việc URL dài bao nhiêu là quá dài. LLM chấm URL 77 ký tự là `level=2`
(đạt), `coverage.unavailable_checks` rỗng nên mẫu **đã được đánh giá đầy đủ** —
đây là **miss thật của tiêu chí**, không phải lỗi hạ tầng và không phải bug
prompt. Rủi ro này đã được ghi nhận từ khi thiết kế fixture.

## Vì sao 8 mẫu `failed` dù 10/11 bắn đúng

Cổng `coverage_target_decision_parent` đòi **cô lập sạch**: mã mục tiêu bắn
**và** không có mã nào khác bắn kèm. Tám mẫu trượt đều vì nhiễu phụ, áp đảo là
**`B8`** (`content_quality.CQ1/CQ2` — lỗi chính tả, lặp từ) xuất hiện ở 5 mẫu.

Nghĩa là: bản thân văn bản fixture — vốn được tạo ra để test đúng **một** mã
lỗi — lại còn mang thêm lỗi chính tả. Đây là **vấn đề chất lượng fixture**,
không phải hệ thống chấm sai; hệ thống phát hiện `B8` là phát hiện đúng.

Nhận định này khớp với ghi nhận từ lượt chẩn đoán trước (*"5/11 dính nhiễu B8
phụ, nhiều khả năng do chất lượng fixture, không phải bug code"*) và nay đã có
số liệu đầy đủ hơn để khẳng định.

## Giới hạn phải nêu kèm

- 11 mẫu là **synthetic**, mỗi mã lỗi chỉ 1–2 mẫu. Không suy ra được tỉ lệ phát
  hiện trên dữ liệu thật.
- Cổng đòi tuyệt đối 11/0. Muốn đạt phải làm sạch chính tả trong fixture trước —
  việc này **không** chạm đường chấm điểm nên không làm mất hiệu lực E1/Gold,
  nhưng phải đo lại Coverage sau khi sửa.
- `CV-A6-02` lệch nhãn kỳ vọng (`needs_revision` → `rejected`) vì bài mang thêm
  một finding `A5` thuộc nhóm A. Đây là hành vi đúng của policy v2, không phải
  lỗi.
