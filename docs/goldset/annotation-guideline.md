# Hướng dẫn gán nhãn gold set

**Phiên bản:** v1.2 (2026-07-29)
**Phạm vi:** bài cẩm nang tiếng Việt về xe điện (P0 - xem `docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md`)

---

## 1. Vì sao cần tài liệu này

Toàn bộ deliverable quan trọng nhất của Sprint 3 - calibration ngưỡng bằng F1 / Cohen's Kappa (`docs/architecture.md` mục 8.2) - đo mức khớp giữa quyết định của AI và **nhãn do người gán**. Nếu nhãn không nhất quán thì mọi chỉ số phía sau đo phải nhiễu, không đo phải chất lượng hệ thống.

Không có tài liệu này sẽ phát sinh 2 vấn đề cụ thể:

1. **Trôi nhãn theo thời gian (intra-annotator drift).** Người gán nhãn là tác giả dự án, gán 30-50 bài trong nhiều phiên. Không có quy tắc viết ra, tiêu chuẩn ở bài số 3 và bài số 40 sẽ khác nhau, và Kappa cuối cùng đo cả phần lệch đó.
2. **Không có trần trên để diễn giải Kappa.** Kappa AI-người = 0.60 là tốt hay kém phụ thuộc vào việc hai người gán cùng bộ mẫu đạt bao nhiêu. Mục 8 dưới đây quy định cách đo trần đó.

Nguyên tắc chung: **nhãn phải suy ra được từ các dấu hiệu quan sát được trên bài viết, không dựa vào cảm nhận tổng thể.** Hai người đọc cùng bài, theo cùng tài liệu này, phải ra cùng nhãn.

---

## 2. Nguyên tắc bắt buộc khi gán nhãn

| Nguyên tắc | Lý do |
|---|---|
| **Gán nhãn mù với kết quả AI.** Gán trước khi chạy hệ thống, hoặc nếu đã chạy thì tuyệt đối không mở `field_ai_status` / `field_ai_score` trước khi chốt nhãn | Xem điểm AI trước sẽ bị neo (anchoring) → Kappa bị thổi phồng, không còn giá trị chứng minh |
| **Chỉ đánh giá phần nội dung hệ thống thật sự đọc:** `title`, `body`, `summary`, `meta_description`, `url_alias` | Khối CTA/header/footer là template dùng chung, không thuộc quyền kiểm soát người viết (spec mục 7.1); ảnh (`alt`) nằm trong `body` nên không liệt riêng |
| **Gán theo bảng mã lỗi ở mục 4, không gán theo cảm nhận** | Bắt buộc để tái lập được; cũng là nguồn dữ liệu để đối chiếu AI bắt đúng loại lỗi hay không |
| **Ghi lại mã lỗi, không chỉ ghi nhãn cuối** | Nhãn cuối chỉ có 3 giá trị nên rất dễ trùng nhau ngẫu nhiên; mã lỗi mới cho biết AI và người có đồng ý về *lý do* hay không |
| **Tối đa 15 bài/phiên** | Chống mệt → trôi tiêu chuẩn |
| **Xáo trộn thứ tự, không gán liên tiếp toàn bộ bài perturbation** | Gán liên tiếp các bài đã biết trước là có lỗi sẽ tạo kỳ vọng "bài nào cũng lỗi" |

---

## 3. Ba nhãn

Nhãn gán cho **một node Drupal** (một bài, ở trạng thái chưa xuất bản):

| Nhãn | Nghĩa vận hành |
|---|---|
| `publish` | Đăng được ngay, không cần sửa gì bắt buộc |
| `needs_revision` | Có lỗi phải sửa, nhưng **sửa tại chỗ được** - không phải viết lại, người viết tự xử lý trong khoảng 30 phút |
| `rejected` | Có rủi ro pháp lý/an toàn rõ ràng, hoặc phải viết lại phần lớn nội dung - cần người có thẩm quyền xem xét, không đẩy lại cho người viết là xong |

---

## 4. Bảng mã lỗi

### 4.1. Nhóm A - lỗi chặn (dẫn tới `rejected`)

| Mã | Lỗi | Căn cứ / dấu hiệu quan sát |
|---|---|---|
| **A1** | Claim tuyệt đối, so sánh nhất không kèm tài liệu chứng minh: "số 1", "tốt nhất", "duy nhất", "hàng đầu", "nhất Việt Nam" | Luật Quảng cáo 2012 |
| **A2** | So sánh trực tiếp hơn hẳn một đối thủ cụ thể (Tesla, BYD, Toyota, Honda...) | Luật Cạnh tranh 2018 |
| **A3** | Số liệu **sai lệch** so với thông số VinFast công bố công khai (tầm hoạt động, thời gian sạc, dung lượng pin, giá, chu kỳ bảo dưỡng) | Đối chiếu `docs/goldset/sources.md` mục 2 |
| **A4** | Khuyến mại/ưu đãi nêu giá trị cụ thể nhưng **thiếu thời hạn hoặc điều kiện áp dụng** | Luật Thương mại |
| **A5** | Nội dung lạc đề/sai lệch tới mức phải viết lại trên 50%: bài không trả lời được câu hỏi ở chính tiêu đề của nó | Đọc tiêu đề → kiểm tra body có trả lời không |
| **A6** | Hướng dẫn kỹ thuật có nguy cơ gây mất an toàn (thao tác sạc/pin sai cách, bỏ cảnh báo an toàn bắt buộc) | Đối chiếu hướng dẫn sử dụng chính thức |

### 4.2. Nhóm B - lỗi sửa tại chỗ (dẫn tới `needs_revision`)

| Mã | Lỗi | Dấu hiệu quan sát |
|---|---|---|
| **B1** | Claim tầm hoạt động/quãng đường **thiếu điều kiện đo** (NEDC/WLTP) hoặc thiếu lưu ý thực tế có thể khác | "chạy được 420km" đứng một mình |
| **B2** | Claim thời gian sạc thiếu loại trụ sạc hoặc dải phần trăm | "sạc đầy 30 phút" không nói trụ nào, 10-70% hay 0-100% |
| **B3** | `meta_description` trống, hoặc độ dài ngoài khoảng **140-170** ký tự | Đếm ký tự |
| **B4** | `title` ngoài khoảng **40-70** ký tự, **hoặc** viết hoa toàn bộ, **hoặc** gắn năm đã cũ | VD thật trên site: *"LƯU Ý SỬ DỤNG ĐỐI VỚI PIN CELL LFP/GOTION"*, *"...đúng cách 2024"* |
| **B5** | Sai thuật ngữ/tên model so với chuẩn brand, hoặc xưng hô không nhất quán trong cùng bài | "VF8" thay vì "VF 8"; "xe hơi điện" thay vì "ô tô điện"; lẫn lộn "bạn"/"quý khách" |
| **B6** | Thiếu thuộc tính `alt` (hoặc `alt` rỗng) ở bất kỳ ảnh nào trong `body`, hoặc alt text không mô tả đúng ảnh | |
| **B7** | `url_alias` còn dấu tiếng Việt, thiếu từ khóa chính, hoặc quá dài | |
| **B8** | Lỗi chính tả hoặc ngữ pháp (từ 1 lỗi trở lên) | |
| **B9** | Câu trên 30 từ hoặc đoạn trên 5 câu xuất hiện từ 3 lần trở lên; hoặc bài trên ~500 từ mà không có heading H2/H3 | |
| **B10** | Số liệu định lượng không nêu nguồn | "90% người dùng hài lòng" không dẫn nguồn |

### 4.3. Nhóm C - không bắt buộc sửa (vẫn `publish`)

| Mã | Lỗi |
|---|---|
| **C1** | Ưu tiên phong cách: có cách diễn đạt hay hơn nhưng cách hiện tại không sai |
| **C2** | Có thể bổ sung nội dung mở rộng, nhưng bài hiện tại đã đủ dùng |
| **C3** | Ít internal link nhưng vẫn có |

Ghi mã C vào cột `notes` để đối chiếu, **không** dùng để đổi nhãn.

---

## 5. Quy tắc quy từ mã lỗi ra nhãn

```
if có ít nhất 1 lỗi nhóm A:   label = "rejected"
elif có ít nhất 1 lỗi nhóm B: label = "needs_revision"
else:                          label = "publish"
```

**Số lượng lỗi B không tự nâng lên `rejected`.** Một bài dính 8 lỗi B vẫn là `needs_revision`.

Lý do của quy tắc này (cần nêu khi bảo vệ, vì nó khác Aggregator): nếu cho phép "nhiều lỗi B thì thành rejected" thì phải chọn một ngưỡng đếm - mà không có căn cứ nào cho biết ngưỡng đó là 4 hay 6 hay 9. Đặt ngưỡng đếm ở đây chính là đưa một con số ảo vào **ground truth**, tức chỗ tuyệt đối không được có số ảo. Ranh giới A/B ngược lại đo được bằng bản chất lỗi (sửa tại chỗ được hay không), không cần ngưỡng.

Đây là **khác biệt có chủ đích** so với Aggregator - nơi nhiều lỗi nhỏ có cộng dồn làm tụt điểm tổng. Chính khoảng chênh giữa hai cách này là thứ calibration Sprint 3 phải đo và hiệu chỉnh, không phải thứ cần xoá đi trước khi đo.

### 5.1. Phân biệt A3 và B1/B2 (dễ nhầm nhất)

| Tình huống | Mã | Vì sao |
|---|---|---|
| "VF 8 đi được **500km**/lần sạc" (công bố thật là 420km) | **A3** | Thông tin **sai**. Sửa không đủ, phải kiểm tra lại toàn bộ số liệu trong bài |
| "VF 8 đi được **420km**/lần sạc" (đúng số, không nêu chuẩn đo) | **B1** | Thông tin **đúng nhưng thiếu điều kiện**. Sửa bằng cách thêm một cụm từ "(theo NEDC)" |

Ranh giới: **sai số liệu → A; đúng nhưng thiếu điều kiện → B.**

---

## 6. Trường hợp biên

| Tình huống | Xử lý |
|---|---|
| Không chắc giữa 2 nhãn liền kề | Chọn nhãn **nghiêm hơn**, và ghi vào `notes` là ca khó. Ca khó là dữ liệu quý - chính chỗ đó AI cũng sẽ sai |
| Nghi ngờ A3 nhưng chưa đối chiếu được thông số công bố | **Không đoán.** Dừng, tra `sources.md` mục 2, tra được rồi mới gán. Nếu VinFast không công bố số đó thì không phải A3; xét B10 (số liệu không nguồn) |
| Bài quá ngắn (dưới ~300 từ) | Không phải lỗi riêng. Xét bình thường theo bảng mã; ngắn thường kéo theo B9/A5 |
| Bài có lỗi lặp cùng một loại nhiều lần | Ghi mã lỗi **một lần**, ghi số lần vào `notes` |
| Bài thuộc mục "Công ty"/thông cáo báo chí | Loại khỏi gold set (spec mục 6.2), không gán nhãn |

---

## 7. Quy trình một phiên gán nhãn

1. Mở `labels.csv`, lấy các dòng chưa có nhãn, xáo trộn thứ tự.
2. Với từng bài: đọc hết → duyệt bảng mã lỗi mục 4 theo thứ tự A → B → ghi **mọi** mã lỗi tìm thấy.
3. Áp quy tắc mục 5 để ra nhãn. **Không** gán nhãn trước rồi tìm lỗi để biện minh.
4. Ghi `annotator`, `date`, `guideline_version`.
5. Tối đa 15 bài rồi nghỉ.

---

## 8. Đo độ tin cậy của chính nhãn

Hai phép đo này chạy **trước** khi báo cáo bất kỳ chỉ số AI nào ở Sprint 3.

### 8.1. Nhất quán nội bộ (intra-annotator, test-retest)

- Sau khi gán xong toàn bộ, **đợi ít nhất 3 ngày**.
- Chọn ngẫu nhiên 10% mẫu (3-4 bài), gán lại **mù với nhãn cũ** (không mở file cũ).
- Tính Cohen's Kappa giữa 2 lượt của cùng một người.
- **Tiêu chí:** Kappa ≥ 0.80. Dưới mức đó nghĩa là tài liệu hướng dẫn này chưa đủ rõ → sửa guideline, tăng version, gán lại toàn bộ.

### 8.2. Trần trên của Kappa

Kappa AI-người không diễn giải được nếu đứng một mình: 0.60 là tốt hay kém phụ thuộc vào mức đồng thuận **tối đa hợp lý** trên chính bộ mẫu này. Cần một con số làm trần.

**Phương án A - có người thứ hai (mạnh hơn, nếu nhờ được).** Người thứ hai gán độc lập 20% mẫu (khoảng 7 bài), chỉ dựa vào tài liệu này, mù với nhãn của người thứ nhất → Cohen's Kappa người-người. **Người này không cần biết gì về dự án, về VinFast hay về SEO** - chỉ cần đọc được tiếng Việt và làm theo bảng mã lỗi ở mục 4. Đó chính là lý do nhãn được thiết kế theo mã lỗi quan sát được thay vì theo cảm nhận: để việc gán nhãn chuyển giao được cho người ngoài.

**Phương án B - một người gán nhãn (mặc định của dự án).** Dự án không được cấp nhân sự hỗ trợ (spec mục 6.1), nên nếu không nhờ được ai thì dùng **Kappa test-retest ở mục 8.1 làm proxy cho trần**, kèm ghi chú rõ trong báo cáo.

Điều này chấp nhận được vì hướng sai lệch là an toàn: **đồng thuận của một người với chính mình luôn cao hơn đồng thuận giữa hai người**. Dùng test-retest làm trần tức là đặt thanh *cao hơn* trần thật, khiến AI trông kém hơn so với nếu có trần đúng - không thổi phồng kết quả. Nêu rõ điều này khi báo cáo.

Ở phương án B, hai yêu cầu khác trở thành **bắt buộc, không còn tuỳ chọn**:

- **Gán nhãn mù** (mục 2). Có hai người thì người kia là chốt chặn nếu một người bị neo theo kết quả AI; một người thì không có chốt chặn nào.
- **Test-retest ≥ 0.80** (mục 8.1). Dưới ngưỡng → sửa guideline, tăng version, gán lại toàn bộ. Vòng lặp này là thứ thay thế người thứ hai.

Ở Sprint 3 báo cáo **hai con số cạnh nhau**, ghi rõ con số trần đến từ phương án nào:

```
Trần (người-người, hoặc test-retest nếu một người)  = 0.xx
Kappa AI - người                                     = 0.yy
```

Diễn giải: nếu trần là 0.65 thì AI đạt 0.60 là **rất tốt**, không phải kém; ngược lại AI đạt 0.85 khi trần chỉ 0.65 là dấu hiệu **đáng nghi**, cần kiểm tra rò rỉ dữ liệu.

**Giới hạn phải nêu trong báo cáo cuối** (nếu dùng phương án B): *"Gold set do một người gán nhãn; không đo được inter-annotator agreement. Trần trên báo cáo ở đây là Kappa test-retest của cùng người gán, vốn là ước lượng lạc quan so với trần thật."* Nêu giới hạn không làm yếu kết quả - giấu giới hạn mới làm.

---

## 9. Định dạng ghi nhãn

File: `docs/goldset/labels.csv`

| Cột | Nội dung |
|---|---|
| `sample_id` | `G-001` (bài thật) hoặc `P-001a` (bản perturbation, hậu tố a/b nếu 1 bài gốc sinh nhiều biến thể) |
| `source_url` | Đường dẫn `/vn_vi/<slug>` |
| `split` | `gold-real` \| `gold-pert` (xem `sources.md` mục 1) |
| `variant` | `original` \| `perturbed` |
| `injected_codes` | Mã lỗi **cố ý chèn** (chỉ với bản perturbation) |
| `defect_codes` | Mọi mã lỗi người gán tìm thấy, phân tách bằng `;` |
| `label` | `publish` \| `needs_revision` \| `rejected` |
| `annotator` | Ký hiệu người gán (`A1`, `A2`) |
| `date` | Ngày gán |
| `guideline_version` | `v1` |
| `notes` | Ca khó, mã nhóm C, số lần lặp lỗi |

---

## 10. Quy tắc tạo bài perturbation

1. Bài nguồn lấy **chỉ từ tập `gold-pert`** trong `sources.md` mục 1 - tuyệt đối không lấy từ tập `brand-corpus` (lý do: `sources.md` mục 1.6).
2. Trước khi chèn lỗi, kiểm tra bài gốc **không sẵn có lỗi nhóm A**. Nếu có, bài gốc đã là `rejected`, chèn thêm lỗi không tạo được tín hiệu gì mới → đổi bài khác.
3. Mỗi bản perturbation chèn **1-2 lỗi**, ghi rõ mã vào `injected_codes`. Không sửa gì khác trong bài.
4. Ground truth suy ra từ `injected_codes` **cộng với** các lỗi sẵn có của bài gốc, áp quy tắc mục 5. Không gán lại bằng cảm tính.
5. Phân bố lỗi chèn phải phủ đủ các nhóm, ưu tiên loại **hiếm gặp tự nhiên** trong bài đã publish: A1, A2, A3, A4, B3.
6. Khi báo cáo kết quả Sprint 3, **tách riêng chỉ số trên bài thật và trên bài perturbation**. Gộp chung sẽ thổi phồng kết quả, vì lỗi chèn do chính tác giả tạo ra và tác giả cũng là người viết rule Compliance - agent bắt được lỗi mình tự chèn không chứng minh được năng lực tổng quát hoá.

---

## 11. Phiên bản

Mọi thay đổi bảng mã lỗi (mục 4) hoặc quy tắc quy nhãn (mục 5) đều phải tăng version của tài liệu này. Nhãn gán theo version cũ **không trộn chung** với version mới trong cùng một phép tính Kappa - hoặc gán lại toàn bộ, hoặc báo cáo tách theo version.

**v1.1 (2026-07-27)** - nới hai ngưỡng đếm trong bảng mã lỗi:

| Mã | v1 | v1.1 | Lý do |
|---|---|---|---|
| B3 | ngoài 150-170 ký tự | ngoài **140-170** | Khớp với dải của `rubrics.md` SEO3; v1 lệch do sơ suất, không có chủ đích |
| B4 | ngoài 50-60 ký tự | ngoài **40-70** | 50-60 là dải *lý tưởng* để chấm điểm (rubric SEO1 giữ nguyên), nhưng dùng nó làm ranh giới *nhãn* thì hầu hết bài thật đều dính B4 → mọi bài thành `needs_revision`, phân bố nhãn sụp đổ và Kappa mất ý nghĩa. Nhãn dùng dải "sai rõ ràng", rubric dùng dải "lý tưởng" - đúng tinh thần hai thang đo cố ý khác nhau (`rubrics.md` mục 7) |

Tại thời điểm sửa **chưa có nhãn nào được gán theo v1**, nên không phải gán lại gì.

**v1.2 (2026-07-29)** - đổi phạm vi xét mã B6:

| Mã | v1.1 | v1.2 | Lý do |
|---|---|---|---|
| B6 | Thiếu `image_alt`, hoặc alt text không mô tả đúng ảnh | Thiếu thuộc tính `alt` (hoặc `alt` rỗng) ở bất kỳ ảnh nào trong `body`, hoặc alt text không mô tả đúng ảnh | Trang nguồn thật (vinfastauto.com) không có field ảnh đại diện riêng - mọi ảnh nằm trong `body` (xem `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md` mục 3.3). Trường `image_alt` không tồn tại nên định nghĩa cũ không đo được gì; B6 chuyển sang xét mọi thẻ `<img>` trong `body` |

Tại thời điểm sửa **chưa có nhãn nào được gán** (cột `label` trong `labels.csv` còn trống toàn bộ), nên không phải gán lại gì.
