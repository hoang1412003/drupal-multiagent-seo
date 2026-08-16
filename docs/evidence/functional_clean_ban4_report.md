# Bộ kiểm thử chức năng — bài sạch (chạy 2026-08-16)

Số liệu thô: [`functional_clean_ban4.json`](functional_clean_ban4.json) ·
Chỉ số: [`functional_clean_chi_so.json`](functional_clean_chi_so.json) ·
Manifest: [`../functional-tests/clean_labels.csv`](../functional-tests/clean_labels.csv)

⚠️ **Bộ này TÁCH BIỆT với gold set.** Nó kiểm *cơ chế*, không đo *mức đồng thuận*: không
tính Kappa, không tham gia calibration, không được thêm vào `labels.csv`
(`technical-debt.md` mục 6 và 8.6).

## Kết quả

| Chỉ số | Giá trị |
|---|---|
| `publish_rate` | **1,000 (10/10)** |
| `false_positive_articles` | **0** |
| `false_positive_issues` | **22** |
| Phân bố quyết định | `{publish: 10}` |
| Chi phí | **$0,24** (167.638 token vào, 15.264 ra) |

Ngưỡng dùng: `veto=50, nr=50, publish=80` — đúng cấu hình đang chạy.
`prompt_version` `020738e209017213`, score-path snapshot `04f10e1` (diff rỗng).

### Trả lời được câu hỏi mà gold set không trả lời nổi

`technical-debt.md` mục 6 gọi đây là **"phản biện mạnh nhất"** với việc lớp `publish` rỗng:
*"Gold set không kiểm được AI có báo lỗi giả trên bài sạch không."*

**Trả lời: không báo lỗi giả ở mức quyết định.** 10/10 bài sạch đều ra `publish`, 0 bài bị
chặn oan. Đường ra `publish` **có hoạt động**, và ngưỡng 80 **không** chặn nhầm bài sạch.

### 22 issue — không phải báo động giả lung tung

| Số lần | Tiêu chí | Mã lỗi người tương ứng |
|---|---|---|
| 9 | SEO7 — nội dung ngắn hơn chuẩn (<600 từ) | **không có mã B nào** |
| 8 | SEO1 — độ dài `title` chưa tối ưu | B4 (chỉ khi ngoài 40-70) |
| 2 | BV6 — giọng văn lệch chuẩn thương hiệu | không có |
| 1 | BV5 — tiêu đề sai quy ước viết hoa | không có |
| 1 | BV3 — xưng hô không nhất quán | B5 |
| 1 | CP7 — chính sách pin thiếu điều kiện | không có |

17/22 đến từ SEO, và **9 trong số đó là SEO7** — một tiêu chí **người gán nhãn không hề
đánh giá** (không có mã A/B nào ánh xạ tới độ dài bài). Đây không phải báo động giả mà là
**chiều đo mà con người không xét**.

Điểm trung bình từng agent trên bộ sạch: `content_quality` **100,0** · `brand` 96,0 ·
`compliance` 98,3 · `seo` 91,5.

## 🔑 Phát hiện quyết định: Content Quality = 100,0 trên bài sạch

Đây là mảnh ghép làm sáng tỏ kết quả E5.

- Trên bộ **functional-clean** (đã sửa hết lỗi chính tả): `content_quality` = **100,0**, không
  tìm ra một issue nào.
- Trên các bài **gold có mã B8** (lỗi chính tả): `content_quality` = 78,6 – 85,7.

**Nghĩa là bộ phát hiện CHẠY ĐÚNG.** CQ1/CQ2 (chính tả, ngữ pháp — ánh xạ đúng mã B8) phân
biệt được bài có lỗi với bài sạch. Vấn đề của E5 **không phải** là hệ thống không nhìn thấy
lỗi.

## Vậy vì sao E5 đề xuất `publish` cho 9 bài người nói cần sửa?

Không phải lỗi phát hiện, mà là **hai cách gộp kết quả khác nhau về bản chất**.

**Người gán nhãn dùng quy tắc dừng sớm** (`annotation-guideline.md` mục 5):

```
Thấy 1 mã A       → rejected
Không A, có 1 mã B → needs_revision
Không A, không B   → publish
```

**Một** khiếm khuyết là đủ để loại khỏi `publish`.

**Hệ thống dùng trung bình có trọng số rồi so ngưỡng.** Một tiêu chí trượt trong 7-8 tiêu chí
của một agent chỉ làm điểm agent đó giảm ~14%, và sau khi nhân trọng số thì chỉ còn **~3,6
điểm** trên `final_score`.

### Số cụ thể — G-002

| | |
|---|---|
| Người tìm thấy | **6 lỗi chính tả** (B8) → `needs_revision` |
| `content_quality` | **85,7** = mất đúng 2/14 điểm mức — hệ thống **có** trừ điểm |
| `final_score` | **93,3** |
| Ngưỡng `publish` | 80 |

Để G-002 rơi xuống dưới 80, `content_quality` phải tụt từ 85,7 xuống **32,3** — tức gần như
**mọi** tiêu chí đều trượt. Một hay hai tiêu chí hỏng **không bao giờ** đủ.

Đó là lý do quét ngưỡng đẩy `publish` lên 96: đó là cách duy nhất để một trung bình có trọng
số bắt chước được quy tắc "một khiếm khuyết là đủ".

## Ba kết luận

1. **Đường ra `publish` không hỏng.** 10/10 bài sạch ra `publish`. Ngưỡng 80 không chặn oan.
2. **Bộ phát hiện không hỏng.** CQ = 100 trên bài sạch, 78-86 trên bài có B8. Nó nhìn thấy lỗi.
3. **Cách gộp điểm không khớp cách người quyết định.** Người dùng quy tắc *bất kỳ khiếm khuyết
   nào cũng loại khỏi publish*; hệ thống dùng *trung bình có trọng số*. Hai hệ đồng ý ở hai
   đầu (sạch hoàn toàn → publish; có `critical` → rejected) và **lệch nhau ở giữa**.

## Việc KHÔNG được làm ngay

Sửa cách gộp — ví dụ thêm cổng *"có bất kỳ tiêu chí nào ở mức 0 thì trần là `needs_revision`"*
— là **đổi `graph.aggregator_node`, tức đường chấm điểm**. Trong thời gian khoá đo lường,
việc đó **làm mất hiệu lực E1/E5/E6 vừa chạy** (`evaluation-plan.md` mục 3a).

Đây là **quyết định thiết kế cần mentor**, không phải việc sửa ngay. Ba lựa chọn, kèm cái giá:

| Lựa chọn | Nghĩa là | Cái giá |
|---|---|---|
| Giữ nguyên, đặt `publish_min` rất cao | Thực chất tắt đường `publish`, mọi bài đều qua người duyệt | Mất giá trị "tự động duyệt bài tốt"; và 96 là con số suy từ lớp rỗng, không phải calibrate |
| Thêm cổng "bất kỳ tiêu chí mức 0 → trần `needs_revision`" | Khớp đúng quy tắc người gán nhãn | **Đổi score path** → phải đo lại E1/E5/E6 |
| Giữ trung bình nhưng cho một số tiêu chí quyền phủ quyết riêng | Trung gian, giống cơ chế `critical` của Compliance | Cũng đổi score path; và phải quyết tiêu chí nào đáng phủ quyết |

## Giới hạn của chính bộ này

- **10 mẫu là ít.** `publish_rate` = 1,000 trên n=10 không loại trừ được tỉ lệ chặn oan thật
  cỡ 10-20%.
- **Mẫu là bài đã được chính người gán nhãn sửa**, nên nó kiểm *cơ chế có đường ra publish
  không*, chứ không chứng minh hệ thống xử lý đúng bài sạch **tự nhiên** — dự án chưa tìm được
  bài nào như vậy (0/20 bài thật đạt `publish`).
- Không thay thế gold set, không tính Kappa, không được gộp số liệu.
