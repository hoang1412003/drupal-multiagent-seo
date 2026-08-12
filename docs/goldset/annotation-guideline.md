# Hướng dẫn gán nhãn gold set

**Phiên bản:** v1.3 (2026-08-10)
**Phạm vi:** bài cẩm nang tiếng Việt về xe điện (P0 - xem `docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md`)

> **Nguồn thi hành các ngưỡng gán nhãn là `multiagent/config/scoring.yaml`** (khối `labelling`) - `label_helper.py` đọc thẳng từ đó. Tài liệu này giữ con số để đọc tại chỗ, nhưng khi lệch nhau thì file config đúng. Lưu ý ngưỡng gán nhãn **cố ý khác** ngưỡng chấm điểm ở `rubrics.md`; lý do ở `docs/config-spec.md` mục 2.

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
| **Ghi lại mã lỗi, không chỉ ghi nhãn cuối** | Nhãn cuối chỉ có 3 giá trị nên rất dễ trùng nhau ngẫu nhiên; mã lỗi mới cho biết AI và người có đồng ý về *lý do* hay không. *(Ghi mã tìm thấy — **không** bắt buộc liệt kê đầy đủ trên bài thật, xem mục 7)* |
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
| **B9** | Bài trên ~500 từ mà không có heading H2/H3 | Lỗi **cấu trúc**, không phải văn phong - xem C4/C5 ở mục 4.3 |
| **B10** | Số liệu định lượng không nêu nguồn | "90% người dùng hài lòng" không dẫn nguồn |

### 4.3. Nhóm C - không bắt buộc sửa (vẫn `publish`)

| Mã | Lỗi |
|---|---|
| **C1** | Ưu tiên phong cách: có cách diễn đạt hay hơn nhưng cách hiện tại không sai |
| **C2** | Có thể bổ sung nội dung mở rộng, nhưng bài hiện tại đã đủ dùng |
| **C3** | Ít internal link nhưng vẫn có |
| **C4** | Câu trên 30 **tiếng** xuất hiện từ 3 lần trở lên *(máy đếm, xem ghi chú dưới)* |
| **C5** | Đoạn trên 5 câu xuất hiện từ 3 lần trở lên *(máy đếm)* |

Ghi mã C vào cột `notes` để đối chiếu, **không** dùng để đổi nhãn.

**Ghi chú C4/C5 - vì sao chúng ở nhóm C chứ không phải nhóm B (v1.3).** Ba căn cứ, không căn cứ nào nhìn vào phân bố nhãn thu được:

1. **Định nghĩa.** `needs_revision` ở mục 3 là *"có lỗi **phải** sửa"*. Câu dài là khuyến nghị viết gọn lại, không phải thứ chặn xuất bản - đúng định nghĩa C1.
2. **Bằng chứng ngoài.** Cả 20 bài thật trong tập `GOLD` đã qua kiểm duyệt thật của đội content VinFast và **đã được đăng** với những câu đó. Nếu câu dài là lỗi phải sửa trước khi đăng thì chúng đã không lên sóng.
3. **Tiền lệ trong chính tài liệu này.** v1.1 đã sửa đúng lỗi cùng loại cho mã B4: dùng dải *lý tưởng* (dải để **chấm điểm**) làm ranh giới **nhãn** thì gần như mọi bài thật đều dính, phân bố nhãn sụp đổ và Kappa mất ý nghĩa. B9 là mã bị sót trong đợt đó.

**Đơn vị là "tiếng", không phải "từ".** `label_helper.py` đếm bằng `len(s.split())`, mà tiếng Việt viết rời từng âm tiết - nên con số đếm được là **tiếng**, không phải từ ("ô tô điện" = 1 từ ghép, 3 tiếng). Ngưỡng 30 vốn mượn từ quy ước readability tiếng Anh vốn đếm **từ**, nên 30 tiếng (≈20 từ) chưa bao giờ đo đúng thứ nó định đo. Từ v1.3 con số này **không còn quyết định nhãn** nên không cần calibrate; nó chỉ còn là bộ đếm ghi vào `notes`. Giữ nguyên 30 để số liệu C4 so sánh được với các lần chạy trước.

**Mã C vẫn phải ghi đầy đủ.** Chuyển xuống nhóm C **không mất thông tin nào**: `label_helper.py` vẫn đếm và in, người gán vẫn chép vào `notes`, Sprint 3 vẫn đối chiếu được AI có bắt đúng chỗ hay không. Thứ duy nhất bị tước là *quyền quyết định nhãn*.

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
| **VinFast công bố NHIỀU con số khác nhau cho cùng một thông số** | Bài trích **bất kỳ** con số nào hãng có công bố → **không phải A3**. Xem ghi chú dưới bảng |
| Đối chiếu A3 thì lấy nguồn ở đâu | `sources.md` mục 2.1 (thông số VinFast công bố), **KHÔNG** phải `multiagent/src/kb/specs.json` (KB của AI). Hai cái cố ý lệch nhau — xem ghi chú dưới bảng |
| Bài quá ngắn (dưới ~300 từ) | Không phải lỗi riêng. Xét bình thường theo bảng mã; ngắn thường kéo theo A5 (không trả lời được câu hỏi ở tiêu đề). **Không** kéo theo B9 - B9 chỉ áp dụng cho bài trên ~500 từ |
| Bài có lỗi lặp cùng một loại nhiều lần | Ghi mã lỗi **một lần**, ghi số lần vào `notes` |
| Bài thuộc mục "Công ty"/thông cáo báo chí | Loại khỏi gold set (spec mục 6.2), không gán nhãn |

**Ghi chú A1 (thêm 2026-08-10).** Cụm so sánh nhất chỉ tính là A1 khi thoả **cả hai**:

- **(a) Nêu phạm vi so sánh** — "thị trường", "Việt Nam", "thế giới", "phân khúc". Thiếu phạm vi thì thường là trạng ngữ, không phải claim: *"cách **tốt nhất** để khắc phục sự cố"*, *"giữ pin ở **trạng thái tốt nhất**"*, *"áp dụng **duy nhất** 01 Gói"* đều **không** phải A1.
- **(b) Nói về sản phẩm / dịch vụ / hạ tầng của chính VinFast.** Luật Quảng cáo và Luật Cạnh tranh điều chỉnh claim về **hàng hoá được quảng cáo**; khen một nhà cung cấp không phải là khẳng định sản phẩm mình hơn đối thủ.

Ba ca thật đã áp dụng:

| Bài | Cụm | (a) | (b) | Kết luận |
|---|---|---|---|---|
| G-020 | "mẫu xe được **săn đón nhất thị trường** xe xanh" | ✓ | ✓ xe VinFast | **A1** |
| G-010 | "hệ thống trạm sạc **hiện đại nhất Việt Nam**" | ✓ | ✓ trạm sạc VinFast | **A1** *(ca khó: nằm trong link "Tìm hiểu thêm")* |
| G-007 | "tập đoàn pin **hàng đầu thế giới** – LG Chem" | ✓ | ✗ bên thứ ba | **không A1** |

Vế (a) trùng đúng cách CP1 phân biệt mức 0 với mức 1 sau đợt sửa nợ B12 (`rubrics.md` mục 6.2) — **trùng là có chủ đích**, cùng một lập luận pháp lý, không phải chép từ code sang.

⚠️ **Hai cụm A1 tìm được bằng tay mà blacklist của AI KHÔNG có:** *"có một không hai"* (G-011) và *"săn đón nhất"* (G-020). Đây là false negative đã biết của CP1, ghi ở `technical-debt.md` B12b. **Không** bổ sung chúng vào `compliance_rules.json` — làm vậy là dạy AI bằng đáp án lấy từ chính gold set.

**Ghi chú A3 (thêm 2026-08-10, làm rõ chứ không đổi luật — xem cuối mục này).**

*Vì sao "trích số nào hãng có công bố cũng được".* A3 định nghĩa là *"số liệu **sai lệch** so với thông số VinFast công bố"*. Khi chính hãng công bố hai con số mâu thuẫn thì không thể quy người viết là sai vì trích một trong hai — lỗi nằm ở **nguồn**, không nằm ở bài. Đây không phải tình huống giả định: `sources.md` mục 2.1 ghi **hai** ca đã gặp — VF 5 Plus (`>300km` / `>320km` / `326,4km`) và VF e34 (`285km` / `318,6km`, **cả hai cùng ghi chuẩn NEDC**).

Quy tắc này **không làm mất khả năng bắt lỗi**: bản perturbation P-002a chèn *"VF 8 500km"*, mà 500km không xuất hiện ở bất kỳ công bố nào (thật là 420/400km), nên vẫn là A3 bình thường.

*Vì sao đối chiếu với `sources.md` chứ không với `specs.json`.* `specs.json` là thứ **AI** tra được; `sources.md` là thứ **VinFast công bố**. Nếu người gán nhãn cũng chỉ đối chiếu với KB của AI thì người sẽ không bao giờ tìm ra A3 mà AI bỏ sót, và recall của CP3 đẹp lên do vòng tròn chứ không do đúng. Khoảng lệch giữa hai file **chính là độ phủ KB**, và đó là một trong những thứ Sprint 3 phải đo.

**Không tăng version, và không nhãn nào đã gán bị đổi.** Bảng mã lỗi (mục 4) và quy tắc quy nhãn (mục 5) không đổi một chữ; đây là làm rõ một dòng vốn đã có trong chính bảng này (*"Nếu VinFast không công bố số đó thì không phải A3"*) cho tình huống nó chưa lường tới. Đã rà lại 20 nhãn gán trước ngày này: **không nhãn nào thay đổi** dưới quy tắc này. Tăng version lúc đang gán dở sẽ tách gold set làm hai nhóm không trộn chung được khi tính Kappa (mục 11) — cái giá đó không có lý do để trả.

---

## 7. Quy trình một phiên gán nhãn

1. Mở `labels.csv`, lấy các dòng chưa có nhãn, xáo trộn thứ tự.
2. Với từng bài: duyệt bảng mã lỗi mục 4 theo thứ tự **A trước, B sau**, ghi các mã tìm thấy.
3. Áp quy tắc mục 5 để ra nhãn. **Không** gán nhãn trước rồi tìm lỗi để biện minh.
4. Ghi `annotator`, `date`, `guideline_version`.
5. Tối đa 15 bài rồi nghỉ.

**Quy tắc mục 5 dừng sớm (short-circuit) — không phải liệt kê đủ mới gán được nhãn.** Tìm thấy một mã A là chốt `rejected`, không cần duyệt tiếp; đã có một mã B là chắc chắn ít nhất `needs_revision`, chỉ còn phải kiểm có mã A nào không. Với bài mà `label_helper.py` đã tìm ra mã B, phần việc còn lại chỉ là *"có mã A không?"*.

**`defect_codes` KHÔNG bắt buộc đầy đủ trên bài thật.** Ghi những mã thực sự tìm thấy, không cố liệt kê cho đủ. Ba lý do, và không lý do nào là để làm ít đi:

- Trong 4 phép đo của Sprint 3, chỉ **Recall/F1 theo từng mã** cần `defect_codes`; E5 (calibration), E3 (baseline) và E6 (held-out) đều chỉ cần `label`.
- Recall/F1 theo mã báo cáo **trên tập perturbation**, nơi ground truth chính xác tuyệt đối vì lỗi do chính người gán chèn vào — mục 10.6 đã yêu cầu tách riêng hai tập.
- Liệt kê sót một mã trên bài thật sẽ khiến AI bắt đúng mã đó bị tính thành **báo động giả**. Danh sách thiếu sót không trung lập: nó làm AI trông tệ hơn thực tế.

Ghi giới hạn này vào báo cáo Sprint 3: *"`defect_codes` trên bài thật không liệt kê đầy đủ; chỉ số theo từng mã báo cáo trên tập perturbation."*

**Công cụ hỗ trợ:** `scripts/quet_ung_vien.py` đánh dấu sẵn các đoạn cần xem cho A1, A2, A3, A4, B1, B2, B5, B10 và tự xếp mỗi bài vào nhóm *đã xong / chỉ quét A / quét đầy đủ*. Nó **chỉ đánh dấu chỗ cần xem, không kết luận mã lỗi** — và cố ý quét rộng, nên phần lớn đoạn nó đánh dấu sẽ bị bác bỏ. Mẫu của nó viết độc lập, không lấy từ `compliance_rules.json`/`brand_rules.json`: dùng chính danh sách của AI để đi tìm nhãn thì chỗ nào danh sách đó thiếu, ground truth cũng thiếu y hệt.

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

Gold set calibration: 33 mẫu (20 original + 13 perturbed), không có lớp publish.

Functional-clean: 10 mẫu corrected, expected publish, không tham gia E5/Kappa.

Evaluation suite: 43 mẫu, chỉ số phải báo cáo riêng theo lát dữ liệu.

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

### 10.1. Quy tắc tạo bản functional-clean corrected

1. Giữ nguyên HTML tải từ website tại `docs/functional-tests/raw_html/C-xxx.html`; không chỉnh sửa bằng chứng nguồn.
2. Bóc tách một lần sang `docs/functional-tests/clean/C-xxx.txt`, sau đó sửa bản TXT để loại các mã A/B. Extractor có write guard: muốn ghi đè tệp đã có phải truyền rõ `--force`.
3. Dùng manifest riêng `docs/functional-tests/clean_labels.csv`: `variant=corrected`, `expected_label=publish`; không có `injected_codes` hoặc `defect_codes` vì đây không phải manifest gold.
4. Không nhập C vào `docs/goldset/labels.csv`, không dùng để xây brand guideline, không đưa vào E5 hoặc tính Kappa.
5. Mọi thay đổi nội dung đáng kể phải ghi vào `docs/functional-tests/corrections.md`. Bản cuối vẫn phải chạy `label_helper.py`, `quet_ung_vien.py` và được người gán đọc kiểm A5/A6/B8.
6. Khi báo cáo, functional-clean dùng riêng `publish_rate`, `false_positive_articles` và `false_positive_issues`; không tạo chỉ số gộp với gold calibration.

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

**v1.3 (2026-08-10)** - tách mã B9 làm ba, chuyển hai tín hiệu văn phong xuống nhóm C:

| Tín hiệu | v1.2 | v1.3 | Lý do |
|---|---|---|---|
| Câu trên 30 tiếng (≥3 lần) | B9 (nhóm B) | **C4** (nhóm C) | Khuyến nghị văn phong, không phải lỗi phải sửa - ba căn cứ ở mục 4.3 |
| Đoạn trên 5 câu (≥3 lần) | B9 (nhóm B) | **C5** (nhóm C) | Cùng họ readability với C4 |
| Bài >500 từ không có H2/H3 | B9 (nhóm B) | **B9** (giữ nguyên nhóm B) | Lỗi **cấu trúc** thật, không phải văn phong |

**Vấn đề mà v1.3 sửa, đo được trên chính 33 mẫu** (`scripts/label_helper.py` chạy trên `docs/goldset/raw/*.txt`):

- B9 kích hoạt ở **33/33 bài**, nên áp quy tắc mục 5 thì **không bài nào ra nhãn `publish`** - gold set còn 2 lớp và ngưỡng publish không có dữ liệu để calibrate (E5 ở `docs/evaluation-plan.md`).
- Toàn bộ 33 lượt kích hoạt đến từ **một** tín hiệu duy nhất là câu dài; hai tín hiệu còn lại của B9 kích hoạt **0/33**. Một tiêu chí hoặc luôn đúng hoặc không bao giờ đúng thì phương sai bằng 0, không phân biệt được bài nào với bài nào.
- Hệ quả ít thấy hơn nhưng nặng ngang: **6/13 bài perturbation mất hết tác dụng ở mức nhãn.** Các bản chèn mã B (P-001b, P-003a, P-004a, P-006a, P-007b, P-009a) có nhãn giống hệt bài gốc vì bài gốc đã `needs_revision` sẵn do B9 - công chèn lỗi không tạo thêm tín hiệu nào cho calibration nhãn. *(Chúng vẫn giữ giá trị đo Recall theo từng mã lỗi.)*
- Đã kiểm: các câu dài là **câu thật**, không phải lỗi của bộ tách câu - câu dài nhất trong corpus là 70 tiếng, đọc được, đúng ngữ pháp. Nên đây không phải bug để sửa ở `split_sentences()`.

Phân bố nhãn dự kiến sau v1.3 (trần trên - người gán sẽ trừ bớt khi xét tiếp A1-A6, B1, B2, B5, B8, B10):

| Nhãn | Số bài | Từ đâu |
|---|---|---|
| `rejected` | 7 | perturbation chèn mã A |
| `needs_revision` | 13 | 6 perturbation chèn mã B + 7 bài thật dính B3/B4 |
| `publish` | ≤ 13 | 13 bài thật không dính mã máy nào |

Tại thời điểm sửa **chưa có nhãn nào được gán**, nên không phải gán lại gì. Quyết định được chốt **trước** khi gán bất kỳ nhãn nào và trước khi chạy hệ thống AI trên gold set.

**Cùng ngày, làm rõ thêm mục 7 (không phải đổi luật, nên không tăng version):** quy tắc mục 5 vốn đã dừng sớm, và `defect_codes` không bắt buộc đầy đủ trên bài thật. Bảng mã lỗi (mục 4) và quy tắc quy nhãn (mục 5) **không đổi một chữ** — chỉ ghi rõ cách vận dụng, kèm công cụ `scripts/quet_ung_vien.py`.
