# Nguồn dữ liệu thật từ vinfastauto.com

Danh sách URL thật thu thập từ nguồn công khai, dùng để (1) xây gold set và (2) làm knowledge base cho fact-check. Toàn bộ là nội dung công khai, không có tài liệu nội bộ VF O2O.

**Cách dùng:** site có WAF chặn bot (HTTP 403), nên thu thủ công theo quy trình sau: mở từng URL trên trình duyệt, `Ctrl+S` chọn **"Webpage, HTML Only"**, lưu vào `docs/goldset/raw_html/<sample_id>.html`, rồi chạy `scripts/extract_gold_sample.py` để bóc tách tự động ra `docs/goldset/raw/<sample_id>.txt`. Việc đọc từng bài để gán nhãn vẫn là bắt buộc, nên thu thủ công không phát sinh chi phí thừa.

**Không copy text thuần.** Copy nội dung bằng chuột từ trình duyệt sẽ mất hết thẻ HTML (`<h2>`, `<img alt>`, `<a href>`), khiến `scripts/label_helper.py` đếm heading = 0 và kết luận sai mã lỗi B9 ("không có h2") cho hầu hết bài dài - hỏng ground truth ngay từ khâu thu thập. Chi tiết xem `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md` mục 1.1.

Danh sách này là **ứng viên**, chưa phải gold set cuối. Mục tiêu chốt 30-50 mẫu: ~60% giữ nguyên (nhãn theo chất lượng thật) + ~40% chèn lỗi có chủ đích (perturbation, ground truth biết trước).

Mỗi URL được gán sẵn vào 1 trong 3 tập rời nhau (`BRAND` / `GOLD` / `PERT`) - xem mục 1.6 giải thích vì sao bắt buộc phải tách và cách gán.

---

## 1. Bài cẩm nang - ứng viên gold set

Ký hiệu: **`BRAND`** = corpus trích xuất brand guideline · **`GOLD`** = gold set, giữ nguyên · **`PERT`** = bài nguồn để tạo bản chèn lỗi

### 1.1. Lái xe / sử dụng / an toàn
- [ ] `BRAND` /vn_vi/cach-lai-xe-o-to-dien
- [ ] `GOLD` /vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai
- [ ] `GOLD` /vn_vi/cach-cham-soc-xe-dien-vf-e34
- [ ] `PERT` /vn_vi/cham-soc-xe-dien-vao-thoi-tiet-hanh-kho
- [ ] `BRAND` /vn_vi/cach-di-xe-may-dien-an-toan <!-- 2026-08-03: slug cũ /vn_vi/huong-dan-cach-di-xe-may-dien-an-toan-va-cach-tang-tuoi-tho-cho-xe trả 404. Vẫn ĐÚNG bài cũ (tiêu đề không đổi), site chỉ rút ngắn slug - không phải đổi sang bài khác nên không phát sinh thiên vị chọn mẫu. -->
- [ ] `GOLD` /vn_vi/cach-khoi-dong-xe-may-dien-vinfast
- [ ] `GOLD` /vn_vi/dinh-nghia-den-projector-la-gi

### 1.2. Sạc & pin
- [ ] `PERT` /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
- [ ] `BRAND` /vn_vi/huong-dan-cach-sac-xe-dien-khong-chai-pin
- [ ] `GOLD` /vn_vi/nhung-kien-thuc-co-ban-ve-sac-xe-o-to-dien-can-biet
- [ ] `GOLD` /vn_vi/thoi-gian-sac-day-xe-may-dien-vinfast-bao-lau
- [ ] `PERT` /vn_vi/cach-de-xe-dien-lau-het-pin-moi-nhat
- [ ] `BRAND` /vn_vi/sac-nhanh-o-to-dien-co-anh-huong-den-kha-nang-van-hanh-cua-xe-khong
- [ ] `GOLD` /vn_vi/cac-loai-pin-xe-may-dien-vinfast-dac-diem-gia-cach-su-dung
- [ ] `GOLD` /vn_vi/khi-nao-nen-sac-pin-xe-dien
- [ ] `PERT` /vn_vi/xe-dien-sac-bao-lau-thi-day
- [ ] `BRAND` /vn_vi/luu-y-su-dung-doi-voi-pin-cell-lfp-gotion
- [ ] `GOLD` /vn_vi/tim-hieu-cac-loai-pin-o-to-dien
- [ ] `GOLD` /vn_vi/cach-sac-pin-xe-may-dien-vinfast
- [ ] `PERT` /vn_vi/sac-pin-luu-dong-24-7 <!-- 2026-07-30: URL cũ /vn_vi/huong-dan-dich-vu-sac-o-to-dien-vinfast trả 404, thay bằng bài này (cùng chủ đề dịch vụ sạc) -->

### 1.3. Bảo dưỡng & chi phí
- [ ] `BRAND` /vn_vi/bao-duong-o-to-dien
- [ ] `GOLD` /vn_vi/nguyen-tac-va-chi-phi-bao-duong-xe-may-dien-vinfast
- [ ] `GOLD` /vn_vi/chi-phi-su-dung-xe-dien
- [ ] `PERT` /vn_vi/so-sanh-chi-phi-van-hanh-xe-dien-va-xe-xang
- [ ] `BRAND` /vn_vi/so-sanh-xe-may-dien-va-xe-may-xang-chi-phi-su-dung
- [ ] `GOLD` /vn_vi/nuoi-o-to-dien-vinfast-vf-e34-co-re-hon-xe-xang
- [ ] `GOLD` /vn_vi/chi-phi-nuoi-xe-vf-e34-hang-thang-tiet-kiem-bao-nhieu
- [ ] `PERT` /vn_vi/o-to-dien-va-o-to-xang-co-gi-khac-nhau
- [ ] `BRAND` /vn_vi/chi-phi-su-dung-o-to-hang-thang-can-biet
- [ ] `GOLD` /vn_vi/co-nen-mua-o-to-thoi-diem-nay
- [ ] `GOLD` /vn_vi/so-sanh-chi-phi-bao-duong-o-to-dien-va-o-to-xang
- [ ] `PERT` /vn_vi/so-sanh-xe-may-dien-va-xe-may-xang

### 1.4. Trạm sạc & showroom
- [ ] `BRAND` /vn_vi/cach-tim-tram-sac-vinfast
- [ ] `GOLD` /vn_vi/tong-quan-tram-sac-vinfast
- [ ] `GOLD` /vn_vi/huong-dan-cach-tim-tram-sac-bang-app-vinfast-e-scooter
- [ ] `PERT` /vn_vi/huong-dan-tim-tram-sac-va-showroom-vinfast-tren-website

### 1.5. Ứng dụng VinFast
- [ ] `BRAND` /vn_vi/huong-dan-cai-dat-ung-dung-vinfast-cho-o-to-dien-p1 <!-- 2026-08-03: URL cũ /vn_vi/dieu-khien-o-to-dien-vinfast-qua-ung-dung-dien-thoai trả 403 "You are not authorized to access this page" (node còn tồn tại, bị gỡ xuất bản hoặc hạn chế truy cập), thử lại nhiều lần vẫn vậy. Thay bằng bài cùng nhóm chủ đề `ung_dung`, chọn theo quy tắc máy móc: kết quả đầu tiên cùng chủ đề KHÔNG thuộc GOLD/PERT, không đọc nội dung trước khi chọn. Không rút corpus xuống 9 bài vì `ung_dung` sẽ mất bài BRAND duy nhất, làm phép đo E2 trên G-019/G-020 không thể trúng. -->
- [ ] `GOLD` /vn_vi/ung-dung-vinfast-cho-o-to-dien
- [ ] `GOLD` /vn_vi/quan-ly-xe-o-to-dien-qua-ung-dung-vinfast
- [ ] `PERT` /vn_vi/huong-dan-su-dung-ung-dung-vinfast

**Tổng: 40 ứng viên** = 10 `BRAND` + 20 `GOLD` + 10 `PERT`. Mở rộng thêm bằng Google `site:vinfastauto.com/vn_vi` + từ khóa "cách/kinh nghiệm/hướng dẫn/lưu ý/so sánh".

### 1.6. Vì sao phải tách 3 tập rời nhau

**Vấn đề nếu không tách.** Brand guideline được **suy ra từ** corpus bài đã publish (spec mục 6.4), còn gold set cũng lấy **từ chính các bài đã publish đó**. Nếu hai tập giao nhau, Brand Voice Agent bị chấm trên đúng dữ liệu đã sinh ra quy tắc của nó - nó sẽ đạt điểm cao, nhưng con số đó không nói lên năng lực gì (rò rỉ dữ liệu / circularity). F1 và Kappa của Brand Voice ở Sprint 3 sẽ vô nghĩa. Đây là câu hỏi phản biện dễ gặp nhất, nên chốt trước bằng văn bản.

**Ba tập:**

| Tập | Số bài | Dùng để | Tuyệt đối không dùng để |
|---|---|---|---|
| `BRAND` | 10 | Thống kê xưng hô, thuật ngữ chuẩn, cách viết tên model, độ dài câu → sinh `brand_guideline.md` nạp vào RAG | Gán nhãn / chấm điểm |
| `GOLD` | 20 | Gold set, giữ nguyên, gán nhãn theo chất lượng thật | Trích xuất brand guideline |
| `PERT` | 10 | Bài nguồn để tạo bản chèn lỗi (mỗi bài 1-2 biến thể → ~13 mẫu) | Trích xuất brand guideline |

**Gold set cuối = 20 (`GOLD`) + ~13 (từ `PERT`) ≈ 33 mẫu**, tỉ lệ ~61% bài thật / ~39% perturbation - nằm đúng trong khoảng 30-50 mẫu và đúng tỉ lệ 60/40 đã chốt.

Tách thêm `PERT` khỏi `GOLD` (thay vì chèn lỗi vào chính 20 bài `GOLD`) để tránh cùng một nội dung xuất hiện hai lần trong gold set - các mẫu như vậy không độc lập với nhau, làm khoảng tin cậy của Kappa hẹp một cách giả tạo.

**Cách gán (quyết định trước khi đọc nội dung, để không thiên vị).** Duyệt danh sách theo đúng thứ tự đã liệt kê, chu kỳ 4 bài: bài 1 → `BRAND`, bài 2 → `GOLD`, bài 3 → `GOLD`, bài 4 → `PERT`. Vì các bài được nhóm sẵn theo chủ đề (1.1-1.5), chu kỳ này tự động trải đều cả 3 tập trên mọi chủ đề - không tập nào bị lệch về một mảng nội dung.

**Việc cần làm thêm:** 10 bài `BRAND` là mức tối thiểu để thống kê tần suất. Muốn phát biểu kiểu *"92% bài dùng 'ô tô điện'"* đủ vững thì nên thu thêm ~10 URL nữa cho riêng tập `BRAND` (bằng Google search như trên) - thu thêm cho `BRAND` **không** làm giảm gold set, vì hai tập rời nhau.

### 1.7. Trạng thái thu thập tập `BRAND` (2026-08-03)

**Đã thu 16 bài**, bóc tách sang `docs/brand/corpus/`, manifest ở `docs/brand/corpus_index.csv`. Guideline sinh ra tại `docs/brand/brand_guideline.md`.

Mở rộng từ 10 lên 16 bài **có căn cứ định lượng, không phải cảm tính**: với 10 bài, nhóm "xe máy điện" chỉ được bàn trong 4 bài nên dù đồng thuận tuyệt đối 4/4 vẫn chỉ cho p = 0,125 — đó là **thiếu phủ sóng chủ đề**, không phải bất đồng thật. 6 bài bổ sung nhắm đúng chủ đề xe máy điện và sạc pin, chọn **mù với cách bài đó dùng thuật ngữ nào** (không thể biết trước khi thu). Kết quả: nhóm đó lên 10/10, p = 0,002.

**Không thu thêm nữa** dù nhóm "trạm sạc" đang ở 9/11 (p = 0,065), chỉ thiếu chút là đạt. Lý do: lần mở rộng vừa rồi chính đáng vì lý do là *thiếu phủ sóng*, biết trước khi nhìn kết quả; còn thu thêm bây giờ thì lý do là *"p đang gần 0,05"* — tức thu đến khi nào có ý nghĩa thì dừng, đúng lỗi thống kê **optional stopping**, làm mọi con số p mất giá trị.

Hai URL phải đổi trong quá trình thu, đã ghi chú ngay tại dòng tương ứng ở mục 1.1 và 1.5.

---

## 2. Trang thông số model - knowledge base cho fact-check

Nguồn đối chiếu claim định lượng (tầm hoạt động, thời gian sạc, pin) trong Compliance Agent (architecture.md mục 5.4).

- [ ] /vn_vi/thong-so-ky-thuat-vinfast-vf9
- [ ] /vn_vi/thong-so-ky-thuat-vf8-kich-thuoc-va-thiet-ke
- [ ] /vn_vi/thong-so-vf-7
- [ ] /vn_vi/xe-o-to-dien-vinfast-di-duoc-bao-nhieu-km-sau-moi-lan-sac-day
- [ ] /vn_vi/vinfast-vf-9-di-duoc-bao-nhieu-km
- [ ] /vn_vi/o-to-dien-chay-xa-nhat
- [ ] /vn_vi/tong-quan-vinfast-vf-9

### 2.1. Số liệu đã verify (2026-08-04)

| Model | Tầm hoạt động/lần sạc | Tiêu chuẩn đo | Nguồn kiểm |
|---|---|---|---|
| VF 9 | 438km (Eco) / 423km (Plus) | **WLTP (dự kiến)** | bảng thông số trong bài G-009 |
| VF 8 | 420km (Eco) / 400km (Plus) | **WLTP (dự kiến)** | bảng thông số trong bài G-009 |
| VF 5 Plus | 326,4km — **nhưng xem cảnh báo dưới** | NEDC | trang tổng quan VF 5 Plus |
| Bảo dưỡng định kỳ | mỗi 12.000km **hoặc 12 tháng, tùy điều kiện nào đến trước** | | trang `lich-bao-duong-xe-vinfast` |

Bảng thông số nằm sẵn trong corpus (`docs/goldset/raw/G-009.txt`), tải từ vinfastauto.com. Nguyên văn:

```
VF 8       | 420km (Eco) / 400km (Plus) | (Dự kiến theo chuẩn WLTP)
VF 9       | 438km (Eco) / 423km (Plus) | (Dự kiến theo chuẩn WLTP)
VF 5 Plus  | >300km                     | (không nêu chuẩn)
```

#### Ba chỗ sai đã sửa

1. **Bản trước của mục này nói ngược sự thật.** Nó ghi *"VF 5 nêu rõ theo NEDC, các model khác chưa thấy nêu tiêu chuẩn đo. Đây chính là loại lỗi Compliance Agent cần bắt … để đưa vào demo."* Thực tế **VF 8 và VF 9 có nêu chuẩn** (WLTP dự kiến), còn bảng thông số cho **VF 5 Plus lại không nêu**. Ví dụ định mang đi demo dựng trên tiền đề sai.
2. **`source_url` của mục VF 5 trỏ sang trang VF 7** (`/vn_vi/thong-so-vf-7`). Đã sửa sang trang tổng quan VF 5 Plus.
3. **Tên model thiếu chính xác:** bản thương mại tại VN là **VF 5 Plus**, không phải "VF 5". Quan trọng vì `fact_check` truy vấn KB bằng chuỗi `"{model} {metric}"` — sai tên model là retrieve trượt.

#### ⚠️ Cảnh báo phải nhớ khi đọc kết quả CP3

**Chính VinFast công bố ba con số khác nhau cho VF 5 Plus:**

| Con số | Trang |
|---|---|
| `>300 km` | bảng thông số trong G-009 |
| `>320 km` | trang tổng quan VF 5 Plus |
| `326,4 km (NEDC)` | trang thông số chi tiết |

CP3 gắn cờ `critical` với nội dung *"sai lệch so với thông số công bố chính thức"*. Một bài viết **đúng**, trích `">300km"`, đối chiếu với `326km` trong KB thì **có thể bị flag oan**. Đã ghi cả ba con số vào trường `tam_hoat_dong` của `specs.json` để giảm rủi ro đó, nhưng **không khử được hoàn toàn** — "thông số công bố chính thức" ở đây không phải một giá trị duy nhất.

Đây cũng là lý do thiết kế CP3 chọn "không tra được → mức 1, không phải mức 0" (`rubrics.md` mục 6.2): nguồn sự thật của bài toán này vốn không sạch.

#### Ví dụ demo thay thế cho Compliance

Ví dụ cũ hỏng, dùng ví dụ này thay:

> Bảng thông số ghi rõ **"(Dự kiến theo chuẩn WLTP)"** cạnh con số 420km. Một bài marketing trích lại **"VF 8 đi được 420km một lần sạc"** mà bỏ mất vế chuẩn đo → đúng là mã lỗi **B1**, và CP5 bắt được bằng máy (`compliance_analysis.py`). Ví dụ này verify được, và mạnh hơn ví dụ cũ vì nó cho thấy **thông tin bị lược mất trong quá trình viết lại**, chứ không phải hãng không công bố.

---

## 3. Ghi chú

- Các URL dạng `/vn_vi/node/<id>` (câu hỏi thường gặp) là trang Q&A hỗ trợ, **không** phải cẩm nang marketing → không đưa vào gold set.
- File PDF `static-cms-prod.vinfastauto.com/*owner_manual*` là sách hướng dẫn sử dụng - có thể dùng làm nguồn phụ cho fact-check KB, không đưa vào gold set.
- Bản tiếng Anh `/vn_en/*` xác nhận site đa ngôn ngữ (Drupal multilingual) - ngoài phạm vi hiện tại, chỉ ghi nhận cho định hướng mở rộng.
- URL `/vn_vi/node/<id>` cũng là bằng chứng site chạy trên Drupal - nêu khi bảo vệ để chứng minh dự án khớp hạ tầng thật.
