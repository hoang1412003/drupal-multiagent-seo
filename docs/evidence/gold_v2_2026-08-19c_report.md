# Gold v2 — Đo lại sau E1 v2 đợt 3 đạt (chạy 2026-08-19, đợt 2)

Số liệu thô: [`gold-v2-2026-08-19c.json`](gold-v2-2026-08-19c.json), report
thô: [`gold-v2-2026-08-19c-report.json`](gold-v2-2026-08-19c-report.json).
Lượt đo trước (đã hết hiệu lực vì sau đó sửa prompt A5):
[`gold_v2_2026-08-19_report.md`](gold_v2_2026-08-19_report.md).

**Kết luận: `Kappa = 0,608` ≥ 0,60 → ĐẠT. `false_publish = 0/33` → ĐẠT.
`needs_revision_recall = 0,957` ≥ 0,80 → ĐẠT. `rejected_recall = 0,60` <
0,80 → KHÔNG ĐẠT. Theo đúng "Pass chỉ khi đồng thời" ở plan gốc, Gold v2
CHƯA đạt full pass — nhưng đây là gap đã biết trước, tái hiện y hệt lượt
đo trước, không phải phát hiện mới.**

## Truy vết

| Thành phần | Giá trị |
|---|---|
| HEAD lúc chạy | `7cdcd6107919ff45daf1cc7c614e98aa17a6f20b` |
| `release_sha256` | `b154057aee95429493c407e3b077c6ec8ad29a010e5129ed153c4d3b2b4f0f9a` |
| Mẫu | 33 bài gold (`gold-real` + `gold-pert`), mỗi bài 1 lượt |
| Chi phí thật | **$1,99** (trần preflight $8,57) |

## Chỉ số tổng hợp

| Đại lượng | Giá trị | Ngưỡng | Đạt? |
|---|---|---|---|
| `kappa` | **0,608** | ≥ 0,60 | ✅ |
| `needs_revision_recall` | **0,957** | ≥ 0,80 | ✅ |
| `rejected_recall` | **0,60** | ≥ 0,80 | ❌ |
| `false_publish` | **0/33** | = 0 | ✅ |

Ma trận nhầm lẫn (hàng = nhãn người gán, cột = quyết định hệ thống, thứ tự
`publish, needs_revision, rejected`):

```
                 publish  needs_revision  rejected
publish              0        0              0
needs_revision       0       22              1
rejected             0        4              6
```

Không có mẫu `publish` nào trong gold set (đã biết từ E5 v1) nên
`recall[publish]` là `null`, không tính vào gate.

## 4 bài `rejected` bị đoán thành `needs_revision`

| Bài | Mã kỳ vọng (nhãn người) | Mã hệ thống bắn ra | Nguyên nhân |
|---|---|---|---|
| `P-004b` | A4;B4;B5;B8 | A4, A6, B2, B4, B5, B8, B10 | **A4 có bắn đúng** — nhưng nhóm đã hạ xuống B nên không tự đẩy `rejected` một mình được nữa. Đây là **cái giá thật, đã biết trước** của quyết định hạ A4 (do E1 v2 lượt 1 cho thấy CP4 dao động). |
| `P-010a` | A4;B8;B11 | A4, B5, B8 | Y hệt trên — A4 bắn đúng, bị hạ nhóm. |
| `G-011` | A1;B3;B8 | B1, B3, B5, B8, B10, B11 | **A1 không bắn** — hệ thống không phát hiện được claim so sánh nhất/tuyệt đối hoá vô căn cứ ("có một không hai... không có ở bất kì loại xe điện hãng khác"). **Lỗ hổng cũ từ v1**, không liên quan gì tới các thay đổi trong phiên này (A5/A6/A4/CV-A7-01). |
| `G-020` | A1 | B2, B5, B10 | Y hệt trên — A1 không bắn ("mẫu xe được săn đón nhất thị trường xe xanh"). |

**Đối chiếu với lượt đo trước (2026-08-19, trước khi sửa A5):** đúng 4 bài
này, cùng nguyên nhân, cùng cách chia 2 (cái giá của quyết định hạ A4) + 2
(lỗ hổng A1 cũ từ v1). **Tái hiện y hệt** — không có bài nào mới bị bỏ sót,
không có bài nào trong 29 bài còn lại đổi quyết định. Sửa A5/CV-A7-01
không làm xấu đi hay tốt lên gì ở Gold.

## Đính chính liên quan tới lượt đo trước

Báo cáo Gold v2 đầu tiên (`gold_v2_2026-08-19_report.md`) đã ghi kết luận
là "ĐẠT" dựa trên Kappa và false_publish, nêu `rejected_recall = 0,60` chỉ
như một "giới hạn cần nêu" chứ không phải điều kiện chặn. Đọc lại plan gốc
(`superpowers/plans/2026-08-17-publish-blocking-policy-v2-evaluation-cutover.md`
dòng 432-443, "Gate không post-hoc... Pass chỉ khi đồng thời") và hàm
`policy_release.approve()` (`gold_rejected_recall` là một gate riêng, bắt
buộc `>= 0.80`) cho thấy **`rejected_recall` LÀ một gate thật**, không như
σ `final_score` của E1 (chưa bao giờ được nối vào gate nào). Nên kết luận
đúng của cả lượt trước lẫn lượt này là: Gold **CHƯA đạt full pass**, dù
Kappa/false_publish đạt.

## Ghi chú diễn giải

- **Không phải mọi gate ngang hàng nhau.** `false_publish = 0` là gate an
  toàn quan trọng nhất (không có bài nào lẽ ra phải chặn lại được đề xuất
  publish) — gate này **đạt tuyệt đối cả hai lượt đo**. `rejected_recall`
  đo việc phân biệt "chặn nhẹ" (`needs_revision`) và "chặn hẳn"
  (`rejected`) — quan trọng nhưng khác bản chất: cả 4 bài trượt đều **vẫn
  bị chặn xuất bản** (rơi vào `needs_revision`, không phải `publish`),
  chỉ khác mức độ chặn.
- **2/4 lỗi là quyết định đã cân nhắc, không phải bug.** Hạ A4 xuống nhóm
  B là đánh đổi có chủ đích (đổi lấy ổn định E1), đã ghi nhận đây là cái
  giá phải trả từ lúc quyết định.
- **2/4 lỗi (`A1`) là nợ độc lập, không nằm trong phạm vi phiên sửa này.**
  Cần điều tra riêng compliance/CP1 nếu muốn đóng.

## Việc kế tiếp

Gold KHÔNG đạt full pass ("Pass chỉ khi đồng thời") do `rejected_recall`.
Theo plan gốc, bước sau Gold (Corrected/Coverage) phụ thuộc Gold đạt — cần
người dùng quyết định có tiếp tục Corrected/Coverage với gap `A1` đã biết
này hay dừng lại điều tra/sửa A1 trước. Không tự ý chạy tiếp.
`scoring.yaml.meta.calibrated` không đổi.
