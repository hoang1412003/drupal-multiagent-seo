# Thiết kế policy chặn xuất bản theo finding

**Ngày:** 2026-08-17

**Trạng thái:** Hướng kiến trúc và việc bổ sung B11 cho CP7 đã được chủ dự án đồng ý; đã audit coverage A/B/C, chưa triển khai

**Implementation plan:** [`../plans/2026-08-17-publish-blocking-decision-policy.md`](../plans/2026-08-17-publish-blocking-decision-policy.md) — đã lập ngày 2026-08-17, chưa thực thi

**Policy hiện hành:** `cam-nang-vn-v1` — trung bình trọng số + ngưỡng

**Policy đề xuất:** `cam-nang-vn-v2` — blocking rule quyết định nhãn, điểm tổng dùng để mô tả/xếp hạng

**Phạm vi:** Aggregator, hợp đồng dữ liệu criterion/finding, audit coverage A/B/C, thiết kế lại CP7, truy vết `policy_version`, kiểm thử và hợp đồng đo lại

**Không thuộc phạm vi của bước thiết kế này:** sửa code runtime, sửa trực tiếp nhãn/gold set đang có hiệu lực, tạo synthetic calibration để ép ra ngưỡng, sửa B15/CP5, sửa BV3, thay UI Drupal, chạy API trả phí

Release candidate được thiết kế theo một bộ version mới, không sửa chồng lên bằng chứng cũ:

```text
annotation guideline  v1.4  (dự kiến)
rubric                 v2    (dự kiến)
prompt version         hash mới sau khi sửa CP7/CQ9/CP10/SEO11
decision policy        cam-nang-vn-v2
```

Tài liệu này chỉ mô tả bộ candidate. Guideline v1.3, rubric v1, prompt
`020738e209017213`, policy v1 và toàn bộ evidence ngày 2026-08-16 vẫn bất biến
cho tới khi có implementation, gán lại và evidence mới.

## 1. Quyết định

Policy v2 tách hai câu hỏi mà policy v1 đang gộp vào một con số:

1. **Bài có finding nào bắt buộc chặn hay không?** Câu này quyết định `publish` / `needs_revision` / `rejected`.
2. **Chất lượng tổng thể của bài cao hay thấp?** Câu này tiếp tục được biểu diễn bằng `final_score` để xếp hạng, so sánh và theo dõi.

Quy tắc nghiệp vụ đích:

```text
có finding nhóm A đủ độ chắc chắn       -> rejected
không có A, có finding nhóm B            -> needs_revision
có nghi vấn nghiêm trọng chỉ từ LLM      -> needs_revision, chờ người duyệt
chỉ có finding advisory/nhóm C           -> publish
thiếu kết quả cần thiết để xác nhận sạch -> needs_revision
```

`decision = "publish"` vẫn chỉ là **đề xuất**. Hệ thống không thay đổi moderation state; người duyệt Drupal quyết định cuối cùng như `docs/architecture.md` mục 2.3.

`final_score` vẫn được tính bằng công thức và trọng số hiện hành, nhưng policy v2 **không dùng nó để bù trừ finding chặn**. Một điểm SEO/Brand cao không thể xoá quyền sửa một lỗi chính tả B8 hay quyền chặn một lỗi A đã xác minh.

## 2. Bằng chứng dẫn tới quyết định

### 2.1. E5 đã đo được giới hạn của score-only

Trên 33 bài gold set, ngưỡng `publish_min = 80` đề xuất `publish` cho 9 bài mà người gán nhãn nói phải sửa hoặc từ chối. Quét tự do đẩy ngưỡng lên 96, cao hơn điểm lớn nhất 93,3; đó là vô hiệu hoá nhánh `publish`, không phải calibrate nó.

### 2.2. Functional-clean loại giả thuyết “hệ thống không có đường publish”

Mười bài corrected sạch đều ra `publish` ở ngưỡng 80. Bộ phát hiện cũng phân biệt được bài sạch với bài có B8: Content Quality đạt 100 trên bộ sạch và 78,6–85,7 trên các bài B8.

### 2.3. Hai điểm số đảo thứ tự chứng minh không có ngưỡng hoàn hảo

| Mẫu | Nhãn mong đợi | Dấu hiệu chính | `final_score` |
|---|---|---|---:|
| `C-006` | `publish` | corrected, không có A/B | 91,49 |
| `G-002` | `needs_revision` | 6 lỗi chính tả B8; AI có trừ CQ | 93,3 |

Không có một ngưỡng đơn nào phân loại đúng cả hai:

- ngưỡng thấp cho cả hai `publish`;
- ngưỡng ở giữa chặn bài sạch nhưng vẫn cho bài lỗi qua;
- ngưỡng trên 93,3 chặn bài lỗi nhưng cũng chặn bài sạch.

Đây là lỗi **biểu diễn quyết định**, không phải bằng chứng gold set bị gán sai và cũng không được chữa bằng cách tạo thêm bài cho tới khi một con số đẹp xuất hiện.

### 2.4. P-006a chứng minh LLM-only không được một mình tạo `rejected`

P-006a được người gán nhãn `needs_revision` vì B10. CP4 vẫn có thể sinh `critical` chỉ từ phán đoán của LLM rằng điều kiện áp dụng chưa đủ, dù chính LLM xác nhận thời hạn có mặt. Policy v2 giữ nghi vấn đó cho người duyệt nhưng hạ quyền máy xuống `needs_revision`; chỉ finding A đủ assurance mới được đề xuất `rejected`.

### 2.5. Audit mã lỗi cho thấy CP7 không phải khoảng trống duy nhất

Đối chiếu 34 criterion/check hiện có (CQ1–CQ8, SEO1–SEO10, BV1–BV7,
CP1–CP9) với guideline v1.3 cho bốn loại phát hiện:

1. **Thiếu mã thật:** CP7 chưa có mã cho lỗi chính sách thiếu thông tin; CP9
   có quyền veto nhưng nằm ngoài taxonomy của người gán.
2. **Mã đã có nhưng không có check trực tiếp:** A5, A6 và vế “title gắn năm
   đã cũ” của B4.
3. **Ánh xạ sai hoặc không đủ định nghĩa:** SEO4 ghi B3 dù B3 không yêu cầu
   từ khoá; BV4 ghi B5 dù “khác chuẩn corpus” không đồng nghĩa “không nhất
   quán”; B7 không ghi mốc 75 ký tự ngay trong bảng guideline; B9 ghi
   H2/H3 trong khi code và config kiểm thiếu H2.
4. **Không có A/B là có chủ đích:** một số chiều SEO/style chỉ dùng để cho
   điểm hoặc khuyến nghị. Tự thêm mã B cho chúng sẽ biến best practice thành
   điều kiện bắt buộc mà không có căn cứ nghiệp vụ.

Vì vậy mục tiêu không phải “mọi level 0 phải có mã B”. Mục tiêu là mọi
criterion phải được khai báo tường minh thuộc đúng một lớp:
`blocking_code`, `advisory_code`, `measurement_only` hoặc
`unsupported/needs_design`; không để dấu `-` mang nghĩa mơ hồ.

`labels.csv` hiện có đủ 33 dòng guideline v1.3 (10 `rejected`, 23
`needs_revision`) nhưng không dòng nào ghi A5/A6. Không được dùng số 0 đó để
kết luận A5/A6 không cần detector: guideline mục 7 nói rõ `defect_codes` của
bài thật không bắt buộc liệt kê đầy đủ, còn tập perturbation hiện cũng không
chèn A5/A6. Đây là khoảng trống coverage, không phải bằng chứng hai loại lỗi
không tồn tại.

## 3. Mục tiêu và bất biến

### 3.1. Mục tiêu

- Khớp ngữ nghĩa A/B/C của annotation guideline mà không làm điểm agent mất giá trị.
- Chặn trường hợp một finding bắt buộc sửa bị điểm nơi khác bù mất.
- Không giao quyền `rejected` cho phán đoán LLM chưa có chốt xác minh phù hợp.
- Không đề xuất `publish` khi một phần kiểm tra bắt buộc bị lỗi hạ tầng.
- Mọi quyết định truy ngược được tới `agent`, `criterion_id`, `level`, mã A/B/C, evidence và policy version.
- Mọi mã A/B trong guideline có check sở hữu rõ ràng hoặc được công khai là chưa hỗ trợ; không được suy “không thấy finding = đã kiểm sạch” khi coverage còn thiếu.
- Riêng policy evaluator là tất định và không gọi LLM. Các check coverage mới phải đo và công khai phần token/chi phí tăng thêm, không được gộp mơ hồ vào chi phí Aggregator.
- Job mang policy cũ không được chạy âm thầm bằng semantics mới.

### 3.2. Bất biến

- Không đổi công thức `score_from_criteria()` và trọng số chỉ để làm đẹp nhãn.
- Không sửa `labels.csv`, functional-clean hoặc evidence E1/E5/E6 đã có.
- Không bật `meta.calibrated=true`; policy rule-based và calibration ngưỡng là hai khái niệm khác nhau.
- Không tự động publish Drupal.
- Không dùng chuỗi `rule`/`type` hiển thị làm khoá nghiệp vụ; khoá phải là `criterion_id` ổn định.
- Không mặc định criterion lạ là advisory. Criterion/level không có trong policy phải fail-closed thành `needs_revision`.

## 4. Mô hình finding và quyền quyết định

### 4.1. Bốn action nội bộ

| Action | Ý nghĩa | Ảnh hưởng nhãn |
|---|---|---|
| `reject` | Lỗi nhóm A hoặc rủi ro an ninh đã đủ assurance | `rejected` |
| `revise` | Lỗi nhóm B có thể sửa tại chỗ | `needs_revision` nếu chưa có `reject` |
| `manual_review` | Nghi vấn nghiêm trọng nhưng nguồn hiện tại chưa đủ quyền `reject`, hoặc tiêu chí chưa ánh xạ chắc chắn | `needs_revision` nếu chưa có `reject` |
| `advisory` | Khuyến nghị/nhóm C/chiều đo không có quyền chặn | Không đổi nhãn |

`manual_review` không đồng nghĩa finding sai. Nó ghi đúng giới hạn assurance: máy đã thấy điều cần xem, nhưng không tự nâng thành `rejected`.

### 4.2. Assurance

Mỗi rule không chỉ ghi action mà còn ghi nguồn assurance:

| Assurance | Ví dụ | Quyền tối đa mặc định |
|---|---|---|
| `deterministic` | đếm độ dài, regex có biên, thiếu field | theo bảng mapping |
| `llm_evidence` | LLM phân loại và trích dẫn nguyên văn | `manual_review`, trừ finding nhóm B đã được chủ dự án cho phép sửa tại chỗ |
| `verified_rag` | claim cùng model/cùng chỉ số lệch với KB có provenance `verified=true` | có thể `reject` |
| `hybrid` | LLM + chốt code, nhưng còn một vế phán đoán | không tự `reject` nếu vế LLM còn tranh chấp |
| `system` | agent/criterion không chạy được, policy mismatch | `manual_review` hoặc fail job trước đường trả phí |

Bằng chứng “trích dẫn có thật” chỉ chứng minh câu nằm trong bài, không tự chứng minh diễn giải pháp lý của LLM là đúng.

### 4.3. Hình dạng finding chuẩn hoá

Policy evaluator chuẩn hoá criterion/flag thành cấu trúc nội bộ:

```json
{
  "agent": "content_quality",
  "criterion_id": "CQ1",
  "level": 0,
  "action": "revise",
  "defect_code": "B8",
  "assurance": "llm_evidence",
  "field": "body",
  "excerpt": "...",
  "reason": "..."
}
```

Không yêu cầu bốn agent đổi toàn bộ output ngay. Aggregator đọc `criteria` đã có và enrich theo policy. Riêng CP9 hiện nằm ngoài `criteria`; flag CP9 phải có `criterion_id = "CP9"` ổn định để không nhận diện bằng chuỗi tiếng Việt.

## 5. Thuật toán quyết định v2

```text
1. Xác minh policy_version của job có policy evaluator tương ứng.
   Không khớp -> dừng trước lần gọi LLM đầu tiên; không fallback.

2. Thu kết quả bốn agent và trạng thái coverage.

3. Vẫn tính final_score như v1 nếu có đủ dữ liệu để tính.
   Điểm này không quyết định decision v2.

4. Chuẩn hoá mọi criterion mức 0/1 và CP9 thành finding theo bảng policy.

5. Nếu có agent/criterion bắt buộc chưa đánh giá được do hạ tầng:
      decision = needs_revision
      decision_basis = incomplete_assessment
   Không coi NA-do-không-áp-dụng là lỗi hạ tầng.

6. Nếu có ít nhất một finding action=reject:
      decision = rejected

7. Ngược lại, nếu có action=revise hoặc manual_review:
      decision = needs_revision

8. Ngược lại:
      decision = publish
```

Thứ tự `incomplete` và `reject` cần giữ cả hai thông tin. Nếu đã có finding `reject` chắc chắn nhưng một agent khác lỗi, kết quả vẫn có thể là `rejected` vì bằng chứng chặn đã đủ; report đồng thời ghi phần chưa đánh giá. Nếu không có `reject` chắc chắn, thiếu coverage luôn chặn `publish`.

### 5.1. Không còn ngưỡng điểm quyết định ở v2

Ba giá trị v1 vẫn cần tồn tại để tái lập run v1:

```text
publish_min
needs_revision_min
compliance_veto_below
```

Policy v2 khai báo rõ:

```text
decision_mode = blocking_policy
score_used_for_decision = false
```

Không xoá ngay ba giá trị khỏi `scoring.yaml`; xoá sẽ phá khả năng đọc lịch sử và làm migration/cutover khó truy vết. Chúng chỉ không có quyền quyết định trong evaluator v2.

## 6. Bảng quyền theo criterion và level

Mức `2` và `NA` không tạo finding chặn. `NA` phải được phân biệt giữa “không áp dụng” và “không đánh giá được” như mục 7.

### 6.1. Content Quality

| Criterion | Mức 0 | Mức 1 | Mã/giải thích |
|---|---|---|---|
| CQ1 chính tả | `revise` | `revise` | B8: từ một lỗi trở lên đã phải sửa |
| CQ2 ngữ pháp | `revise` | `revise` | B8 |
| CQ3 câu dài | `advisory` | `advisory` | C4, không đổi nhãn |
| CQ4 đoạn dài | `advisory` | `advisory` | C5, không đổi nhãn |
| CQ5 heading | `revise` | `advisory` | Mức 0 đúng B9: bài >500 từ không H2; mức 1 chỉ là phân cấp chưa đẹp |
| CQ6 mạch lạc | `manual_review` | `advisory` | Mức 0 hiện gộp “lặp ý” với “lạc đề”, chưa đủ sạch để sở hữu A5; mức 1 là C1 |
| CQ7 số liệu có nguồn | `revise` | `revise` | B10; trùng CP8 nhưng không được đếm quyền hai lần |
| CQ8 summary | `advisory` | `advisory` | C2; summary/teaser là chiều cải thiện, chưa có căn cứ bắt buộc publish |

### 6.2. SEO

| Criterion | Mức 0 | Mức 1 | Mã/giải thích |
|---|---|---|---|
| SEO1 độ dài title | `revise` | `advisory` | B4 chỉ khi ngoài 40–70; 40–49/61–70 vẫn trong dải nhãn chấp nhận |
| SEO2 title có từ khoá | `advisory` | không dùng | C2/chiều tối ưu; không tạo mã B |
| SEO3 meta tồn tại/độ dài | `revise` | `revise` | B3 gồm trống **hoặc** ngoài 140–170 |
| SEO4 meta có từ khoá | `advisory` | không dùng | C2; cột rubric v1 ghi B3 là sai vì B3 không yêu cầu từ khoá |
| SEO5 url_alias | `revise` | `revise` | B7 gồm trống/còn dấu/quá dài/thiếu từ khoá |
| SEO6 từ khoá ở mở đầu | `advisory` | không dùng | C2/chiều tối ưu; không tạo mã B |
| SEO7 độ dài body | `advisory` | `advisory` | C2; guideline nói rõ bài ngắn không phải lỗi riêng, phải xét A5 độc lập |
| SEO8 heading có từ khoá | `advisory` | `advisory` | C2; B9 do CQ5 sở hữu với đúng điều kiện bài dài thiếu H2 |
| SEO9 alt ảnh | `revise` | `revise` | B6 gồm thiếu/rỗng hoặc alt không mô tả đúng |
| SEO10 internal link | `advisory` | `advisory` | C3/chiều đo không có mã B |

### 6.3. Brand Voice

| Criterion | Mức 0 | Mức 1 | Mã/giải thích |
|---|---|---|---|
| BV1 tên model | `revise` | `revise` | B5: một chỗ sai cũng phải sửa |
| BV2 thuật ngữ | `revise` | `revise` | B5 |
| BV3 xưng hô | `advisory` | `advisory` | Tạm tước quyền chặn do nợ B13: đang gộp danh từ ngôi ba với cách xưng hô |
| BV4 khớp corpus | `advisory` | không dùng | C1; cột rubric v1 ghi B5 là quá rộng vì khác corpus không đồng nghĩa không nhất quán |
| BV5 viết hoa title | `revise` | `advisory` | Mức 0 viết hoa toàn bộ đúng B4; mức 1 chỉ là chưa lý tưởng |
| BV6 trang trọng | `advisory` | `advisory` | C1; mức style không tự chặn |
| BV7 từ bị loại | `revise` | không dùng | B5, rule tất định |

### 6.4. Compliance và security

| Criterion | Mức 0 | Mức 1 | Assurance/mã |
|---|---|---|---|
| CP1 claim tuyệt đối có phạm vi | `reject` | `advisory` | `deterministic`, A1; mức 1 không đủ điều kiện A1 theo guideline |
| CP2 so sánh trực tiếp đối thủ | `manual_review` | không dùng | `llm_evidence`, nghi A2 nhưng LLM không một mình tạo rejected |
| CP3 số liệu sai | `reject` nếu provenance `verified=true`, ngược lại `manual_review` | `advisory` | `verified_rag`, A3; phải cùng model + cùng chỉ số |
| CP4 khuyến mại | `manual_review` | không dùng | `hybrid`, nghi A4; vế điều kiện còn là phán đoán LLM và đã có P-006a bất đồng |
| CP5 tầm hoạt động | `revise` | `revise` | `deterministic`, B1 |
| CP6 thời gian sạc | `revise` | `revise` | `deterministic`, B2 |
| CP7 chính sách pin | `revise` | `revise` | `llm_evidence`, B11; chỉ áp dụng sau khi CP7 được định nghĩa lại ở mục 6.6 |
| CP8 số liệu có nguồn | `revise` | `revise` | B10; trùng CQ7, quyết định chỉ cần “có”, không cộng severity |
| CP9 chỉ dẫn ẩn | `reject` | không dùng | `deterministic`, A7 dự kiến; rủi ro toàn vẹn hệ thống có mã truy vết riêng |

### 6.5. Quy tắc trùng và xung đột

- CQ7 và CP8 cùng ánh xạ B10: giữ cả hai nguồn trong audit, nhưng một defect không được cộng thành “nặng gấp đôi”. Policy chỉ xét sự tồn tại.
- Một finding `reject` thắng mọi finding nhẹ hơn.
- Hai `revise` không tự nâng thành `reject`; tám lỗi B vẫn là `needs_revision` đúng guideline.
- Criterion không có trong bảng hoặc trả level ngoài `{0,1,2,NA}` tạo `manual_review` + cảnh báo policy drift, không được publish.
- Nếu policy mapping mâu thuẫn với rubric/annotation version khai báo trong snapshot, loader từ chối kích hoạt release.

### 6.6. Hai mã mới trong guideline v1.4 candidate

#### B11 — chính sách pin thiếu thông tin thiết yếu

Định nghĩa độc lập với output AI:

> **B11:** Bài đưa ra claim cụ thể về chính sách pin, bảo hành pin hoặc thuê
> pin nhưng thiếu ít nhất một thông tin thiết yếu đang áp dụng để người đọc
> hiểu và sử dụng claim đó: đối tượng/điều kiện, thời hạn hiệu lực, hoặc chi
> phí **nếu chính sách đó có phát sinh phí**.

Ranh giới bắt buộc:

- Chỉ nhắc chung “xem chính sách hiện hành”, đặt link tham khảo, hoặc nói về
  pin mà không đưa ra claim chính sách cụ thể → `NA`, không phải B11.
- “Phí” chỉ là yếu tố áp dụng khi loại chính sách đó thật sự có phí; không
  ép bài bảo hành miễn phí phải bịa thêm một con số phí.
- Thông tin chính sách **sai** so với công bố chính thức → xét A3, không hạ
  xuống B11.
- Khuyến mại có giá trị cụ thể thiếu thời hạn/điều kiện → A4.
- Số định lượng không nguồn → B10; có thể đồng thời với B11.

CP7 v2 phải đổi cùng lúc, không được chỉ đổi mapping trên output cũ:

| Mức | Định nghĩa CP7 v2 | Quyền |
|---|---|---|
| `NA` | Không có claim chính sách cụ thể; chỉ nhắc/link chung | không finding |
| `0` | Claim cụ thể thiếu từ hai yếu tố thiết yếu **đang áp dụng** trở lên | B11 → `revise` |
| `1` | Claim cụ thể thiếu đúng một yếu tố thiết yếu đang áp dụng | B11 → `revise` |
| `2` | Đủ mọi yếu tố thiết yếu đang áp dụng | không finding |

Không chỉ chặn mức 0: ranh giới “thiếu hai yếu tố” chỉ là mức độ để tính
điểm, còn định nghĩa B11 là thiếu **bất kỳ một** thông tin bắt buộc nào.

#### A7 — văn xuôi ẩn khỏi người đọc trong input đánh giá

CP9 hiện là hard veto có chủ đích nhưng nằm ngoài taxonomy. Guideline v1.4
candidate bổ sung:

> **A7:** Trường `body` chứa đoạn văn xuôi bị ẩn khỏi người đọc nhưng vẫn
> nằm trong input mà hệ thống đánh giá có thể đọc, sau khi đã loại CSS, mã
> tracking, URL và marker kỹ thuật theo đặc tả CP9.

A7 không áp dụng cho đoạn hiển thị bình thường đang thảo luận về AI hay trích
ví dụ prompt injection. Định nghĩa dùng **tín hiệu detector thật sự đo được**,
không khẳng định detector hiện tại hiểu được ý định của người viết: CP9 đang
phát hiện hình dạng văn xuôi bị ẩn, không phân loại ngữ nghĩa “hãy chấm 100”.
A7 dẫn tới `rejected` vì nội dung không minh bạch với người duyệt nhưng có thể
tác động input máy; CP9 vẫn đứng ngoài công thức điểm để không tạo “điểm miễn
phí” cho mọi bài sạch. Giới hạn detector đã biết ở `prompt-injection.md` mục
M2 phải tiếp tục xuất hiện trong report/evidence.

### 6.7. Ma trận coverage ngược: từ mã người gán sang check hệ thống

| Mã | Check sở hữu ở candidate | Trạng thái/việc phải làm trước activation |
|---|---|---|
| A1 | CP1 | Có nhưng blacklist còn false negative đã biết G-011/G-020; công khai giới hạn, không học từ gold |
| A2 | CP2 | Có; LLM-only chỉ `manual_review`, không tự reject |
| A3 | CP3 | Có; chỉ reject khi cùng model + cùng chỉ số + provenance verified |
| A4 | CP4 | Có; hybrid hiện chỉ `manual_review` do bất đồng P-006a |
| A5 | **CQ9 decision-only mới** | Tách khỏi CQ6; kiểm title-body có trả lời đúng lời hứa và ngưỡng phải viết lại >50%; LLM-only tối đa `manual_review` |
| A6 | **CP10 decision-only mới** | Phát hiện hướng dẫn kỹ thuật nguy hiểm; chỉ reject khi đối chiếu được nguồn hướng dẫn chính thức, nếu không `manual_review` |
| A7 | CP9 | Mã mới cho hard blocker security hiện có; detector đo văn xuôi ẩn chứ không suy ý định; không vào điểm |
| B1 | CP5 | Có nhưng detector B15 đang khớp mọi số có `km`; phải sửa trước activation v2 |
| B2 | CP6 | Có |
| B3 | SEO3 | Có; SEO4 không còn giả mạo quyền B3 |
| B4 | SEO1 + BV5 + **SEO11 decision-only mới** | SEO1 phủ độ dài, BV5 phủ ALL CAPS; SEO11 phủ “năm đã cũ” dưới dạng freshness marker |
| B5 | BV1/BV2/BV3/BV7 | BV3 chưa được trao quyền chặn cho tới khi sửa semantics B13; các check còn lại có |
| B6 | SEO9 | Có |
| B7 | SEO5 | Có; guideline v1.4 phải ghi rõ “quá dài” là >75 ký tự theo config |
| B8 | CQ1/CQ2 | Có |
| B9 | CQ5 | Có; guideline v1.4 phải thống nhất là bài >500 từ không có H2, không ghi H2/H3 mơ hồ |
| B10 | CQ7 + CP8 | Có hai detector; deduplicate quyền quyết định |
| B11 | CP7 v2 | Mã mới; phải chấm lại, không replay CP7 v1 |

`CQ9`, `CP10` và `SEO11` là **decision-only check**, giống nguyên tắc CP9:
không cộng thêm tiêu chí gần như luôn đạt vào mẫu số điểm. Chúng vẫn phải có
`criterion_id`, assurance, evidence và coverage status. Nếu chưa triển khai
đủ ba check này thì report v2 phải ghi coverage thiếu và không được tuyên bố
“toàn bộ A/B đã được kiểm”; không được lặng lẽ coi chúng là sạch.

### 6.8. Những criterion không cần thêm mã A/B

| Criterion | Phân loại | Lý do |
|---|---|---|
| CQ3/CQ4 | C4/C5 | Readability, guideline đã quyết định không chặn |
| CQ8 | C2 | Teaser là chiều cải thiện; chưa có yêu cầu nghiệp vụ bắt buộc |
| SEO2/SEO4/SEO6/SEO8 | C2 | Vị trí từ khoá là best practice, không phải lỗi phải sửa theo guideline |
| SEO7 | C2 hoặc A5 qua CQ9 | Độ dài tự nó không phải lỗi; bài ngắn chỉ bị chặn nếu thật sự không trả lời title |
| SEO10 | C3 | Internal link ít là advisory |
| BV4/BV5 mức 1/BV6 | C1 | Khác ưu tiên corpus hoặc hơi lệch style không đủ thành B5/B4 |

Các dòng này phải ghi `defect_code: null` hoặc mã C cụ thể cùng `rationale`
trong policy artifact; không dùng dấu `-` không giải thích.

## 7. Coverage và lỗi hạ tầng

### 7.1. Vấn đề hiện tại

`None` đang mang hai nghĩa khác nhau:

- criterion không áp dụng cho bài;
- criterion đáng lẽ phải chạy nhưng LLM/KB hỏng.

Một số agent bắt exception rồi trả các criterion LLM thành `NA`, trong khi các criterion máy vẫn cho điểm. Aggregator hiện không biết phần nào chưa được kiểm và có thể xem absence-of-finding như bằng chứng sạch.

### 7.2. Hợp đồng bổ sung

Mỗi agent result cần metadata không ảnh hưởng điểm:

```json
{
  "assessment": {
    "status": "complete",
    "unavailable_criteria": [],
    "errors": []
  }
}
```

Giá trị `status`:

- `complete`: mọi criterion cần chạy đã có kết luận hoặc NA vì không áp dụng;
- `partial`: còn criterion không đánh giá được;
- agent result `None`: agent không trả kết quả.

Không ghi exception/message nhạy cảm vào report Drupal. Log/audit chỉ ghi mã lỗi an toàn; chi tiết kỹ thuật ở log nội bộ.

### 7.3. Fail-closed cho đề xuất publish

- Thiếu bất kỳ agent nào: không `publish`.
- `assessment.status = partial`: không `publish`, trừ khi đã có blocker `reject` chắc chắn; khi đó vẫn `rejected` và report ghi coverage thiếu.
- Không biến lỗi hạ tầng thành điểm 0 hoặc finding nội dung.
- Không tái phân phối trọng số rồi dùng điểm partial để đề xuất publish.

## 8. Versioning và chọn policy thực sự

### 8.1. Khoảng trống hiện tại

Platform đã snapshot `review_job.policy_version`, nhưng worker hiện chỉ truyền `node_id`, `content_type`, `langcode` vào graph. Vì vậy `policy_version` đang có giá trị audit/dedup nhưng chưa thực sự chọn hành vi Aggregator.

Khi có v2, khoảng trống này trở thành lỗi correctness: một job ghi `cam-nang-vn-v1` có thể bị worker mới chấm bằng semantics v2 mà lịch sử vẫn nói v1.

### 8.2. Thiết kế bắt buộc

- `ContentReviewState` nhận `policy_version`.
- Worker truyền đúng snapshot từ job vào graph.
- Policy loader chọn **exact match** theo `policy_version`; không fallback sang “mới nhất” hoặc `default`.
- Unknown/mismatch phải dừng trước đường gọi LLM để không tốn tiền cho một run không có provenance đúng.
- Các script đánh giá và script chạy tay phải truyền policy version tường minh.
- Run/report/config metadata ghi policy version thật đã dùng.

### 8.3. Policy artifact

Mapping nên nằm trong một artifact khai báo, version hoá và hash được, ví dụ `multiagent/config/decision_policy.yaml`, thay vì rải `if criterion_id` trong `graph.py`.

Artifact phải khai báo tối thiểu:

```text
policy_version
decision_mode
score_used_for_decision
rubric_version
guideline_version
mapping đầy đủ criterion/level
coverage manifest đầy đủ mã A/B -> check sở hữu
quy tắc unknown/incomplete
```

Loader kiểm schema và tính hash. `policy_snapshot` của `cam-nang-vn-v2` bổ sung `decision_policy_sha256` cùng các hash prompt/rubric/scoring/rules/KB/embedding hiện có.

`cam-nang-vn-v1` là release lịch sử bất biến. Không sửa migration `0001` để giả rằng v2 luôn tồn tại từ đầu. Khi v2 đã qua đánh giá, tạo migration/CLI release mới và cutover có audit.

### 8.4. Cutover

1. Tạm dừng intake.
2. Chờ hoặc xử lý rõ mọi job v1 đang queued/running; không đổi policy của row cũ.
3. Deploy artifact/code biết exact policy v2.
4. Chạy offline acceptance và kiểm policy hash.
5. Chỉ sau evidence/approval mới chuyển profile active sang `cam-nang-vn-v2`.
6. Resume intake; job mới snapshot v2.

Rollback quay lại artifact/profile v1 có audit; không ghi đè run v2 thành v1.

## 9. Output và khả năng truy vết

Giữ các trường tương thích hiện có:

```text
decision
final_score
details
missing_agents
veto_reason
note
```

Bổ sung dữ liệu quyết định:

```json
{
  "policy_version": "cam-nang-vn-v2",
  "decision_basis": {
    "mode": "blocking_policy",
    "score_used_for_decision": false,
    "blockers": [],
    "advisories": [],
    "incomplete_checks": []
  }
}
```

`veto_reason` tiếp tục được sinh khi `decision = rejected` để UI Drupal hiện tại không mất banner. Các key mới là additive; chưa đổi report schema version chỉ vì thêm key mà consumer cũ có thể bỏ qua an toàn.

`agent_results` + exact policy artifact đủ để dựng lại decision. Nếu audit không lưu `decision_basis` thành cột riêng, phải giữ nó trong JSON report/config metadata; không chấp nhận chỉ lưu câu `veto_reason` đã mất cấu trúc.

## 10. Thành phần triển khai dự kiến

Đây là thiết kế, chưa phải code. Kế hoạch triển khai sau review dự kiến chạm:

- `docs/goldset/annotation-guideline.md`: tạo v1.4 với A7/B11 và làm rõ B7/B9; không sửa nhãn cũ tại chỗ.
- `docs/rubrics.md`: tạo rubric v2; sửa mapping SEO4/BV4, định nghĩa CP7 v2 và khai báo ba decision-only check.
- `multiagent/config/decision_policy.yaml`: policy artifact v1/v2 và mapping.
- `multiagent/src/decision_policy.py`: loader/schema validator/normalizer/evaluator thuần.
- `multiagent/src/state.py`: thêm `policy_version`.
- `multiagent/src/graph.py`: tính điểm như cũ, giao decision cho evaluator, xuất decision basis.
- `multiagent/src/worker.py`: truyền policy version và fail sớm khi mismatch.
- Content Quality/SEO/Compliance: sửa prompt/schema để có CP7 v2, CQ9, CP10, SEO11; CP9 thêm criterion ID ổn định; mọi prompt mới phải nằm trong `prompt_version()`.
- `multiagent/src/compliance_analysis.py`: sửa B15/CP5 theo ngữ cảnh trước khi B1 được trao quyền chặn ở v2.
- bốn agent: thêm metadata coverage phân biệt `NA` với check unavailable.
- audit/report metadata: lưu exact policy/hash/basis mà không phá consumer cũ.
- script gán nhãn: hỗ trợ A7/B11 và guideline v1.4; gán lại toàn bộ 33 mẫu theo protocol mù phù hợp.
- script evaluation: lưu criteria/decision basis; output E5 v1 hiện chỉ có điểm + `co_critical`, không đủ replay policy v2.
- migration/CLI release: chỉ làm ở phase activation sau khi candidate đạt, không sửa seed migration cũ.

Không sửa JS. Nếu phase sau chỉ thêm key JSON mà UI bỏ qua, không được tuyên bố UI đã hiển thị decision basis. Muốn hiển thị basis là một thay đổi UI riêng và phải kiểm bằng mắt theo `docs/editor-ui-design.md` mục 10.

## 11. Kiểm thử bắt buộc

### 11.1. Unit policy thuần, không API/DB

- Mỗi ô mức 0/1 trong bảng mục 6 có một test mapping.
- Mức 2 và NA-không-áp-dụng không tạo blocker.
- Criterion lạ/level lạ -> `manual_review`, không publish.
- Nhiều B không tự nâng thành rejected.
- `reject` thắng `revise/manual_review`.
- CQ7 + CP8 cùng B10 không làm tăng quyền quyết định.
- CP3 chỉ `reject` khi provenance verified.
- CP2/CP4 LLM-only không tự `rejected`.
- CP7 v2: generic mention/link -> NA; thiếu 1 hoặc nhiều yếu tố áp dụng -> B11/revise.
- CP9/A7 vẫn ngoài điểm nhưng xuất criterion ID và decision basis ổn định.
- CQ9/CP10/SEO11 có coverage status và không cộng “điểm sạch” vào mẫu số.
- Mọi mã A1–A7/B1–B11 xuất hiện đúng một lần trong coverage manifest; detector trùng như B10 khai báo alias/dedup rõ ràng.
- Thiếu agent/partial coverage không publish.
- Policy mismatch dừng trước fake/spy LLM call đầu tiên.

### 11.2. Ba acceptance case khóa quyết định

| Ca | Kỳ vọng v2 | Lý do |
|---|---|---|
| `G-002`, CQ1 mức 0, score 93,3 | `needs_revision` | B8 không được điểm khác bù |
| `C-006`, chấm lại bằng CP7 v2 | `publish` | Chỉ nhắc/chỉ dẫn tới chính sách, không đưa claim thiếu dữ kiện → CP7 phải là NA, không phải dựa vào mức 1 cũ |
| `P-006a`, CP4 mức 0 chỉ từ vế LLM + B10 | `needs_revision` | nghi A4 cần người duyệt; không LLM-only rejected |

### 11.3. Functional-clean không được replay CP7 v1 như CP7 v2

File functional-clean có criteria chi tiết, nhưng CP7 đã đổi **nghĩa**, không
chỉ đổi action. C-006 hiện mang CP7 mức 1 theo prompt cũ; nếu máy móc ánh xạ
mức đó sang B11 thì sẽ chặn oan chính bài sạch đã làm lộ vấn đề. Output cũ chỉ
dùng để xác nhận vì sao cần đổi rubric, không phải acceptance v2.

Sau khi prompt/rubric mới được khoá, phải chấm lại 10 bài functional-clean và
kỳ vọng C-006 trả CP7=`NA`. Lượt này gọi API nên chỉ chạy khi người dùng duyệt
riêng chi phí; trước đó chỉ được test offline bằng fixture CP7 v2 do con người
xác định, không báo “10/10 v2 đã pass”.

### 11.4. Regression hệ thống

- `final_score` của cùng agent results không đổi giữa evaluator v1/v2.
- Report cũ vẫn render; key mới không làm PHP lỗi.
- Audit ghi đúng policy version của job, không lấy profile version hiện tại sau khi job đã enqueue.
- Dedup tiếp tục dùng policy version nên cùng content hash có thể có một job v1 và một job v2.
- Full offline suite phải 0 fail, 0 skip theo lệnh chuẩn của project.
- Năm test PHP/DDEV vẫn chạy tay nếu thay đổi hợp đồng report phía Drupal; CI không chạy hộ.

## 12. Hợp đồng đo lường sau thay đổi

### 12.1. Evidence cũ

E1/E5/E6 ngày 2026-08-16 vẫn là bằng chứng hợp lệ của `cam-nang-vn-v1`. Không sửa, xoá, đổi tên thành kết quả v2 hoặc trình bày như thể policy v2 kế thừa các con số đó.

Aggregator v2 là score-path change. Theo `docs/evaluation-plan.md` mục 3a, mọi kết quả E1/E5/E6 cho code hiện hành phải đo lại hoặc thiết kế lại tương ứng trước khi kích hoạt.

### 12.2. E5 v2 không còn là quét `publish_min`

Policy v2 không học ngưỡng điểm, nên không được chạy script quét threshold cũ rồi gọi đó là E5 v2. Phép đánh giá mới cần báo cáo:

- agreement/Kappa và confusion matrix của quyết định rule-based;
- recall của `rejected` và `needs_revision`;
- false-publish rate trên 33 gold;
- publish rate/false-block rate trên 10 functional-clean, báo cáo **riêng**;
- kết quả theo từng defect code trên perturbation;
- số finding `manual_review` do assurance chưa đủ;
- coverage failure rate.

Không gộp 10 corrected vào `labels.csv` hay Kappa chính. Nếu sau này tạo synthetic study, nó phải có tên/version/protocol riêng và không thay bằng chứng người–AI.

### 12.2.1. Guideline đổi version nên nhãn cũ không tự nâng cấp

Thêm A7/B11 và đổi ranh giới B7/B9 là thay đổi bảng mã/quy tắc áp dụng, nên
phải tăng annotation guideline từ v1.3 lên v1.4. Theo chính guideline mục 11:

- không đổi cột `guideline_version` của 33 dòng cũ bằng thao tác hàng loạt;
- tạo một lượt gán lại v1.4 có provenance, không nhìn output AI candidate;
- rà lại đủ 33 mẫu, kể cả mẫu dự kiến không đổi nhãn;
- chạy test–retest mới theo mục 8 sau khi chờ tối thiểu 3 ngày;
- không trộn nhãn v1.3 và v1.4 trong cùng phép Kappa;
- functional-clean vẫn tách riêng, chỉ xác nhận expected A/B-free sau khi
  rà theo guideline v1.4.

Không được kết luận “A7/B11 không xuất hiện trong 33 bài nên khỏi gán lại”.
Đó là kết quả chỉ biết sau khi đã rà; dùng kết quả dự kiến để miễn quy trình
là vòng tròn.

### 12.3. Dữ liệu cũ không replay đủ

`e5_ban4_kfold.json` chỉ lưu điểm từng agent và `co_critical`, không lưu criteria/flag chi tiết. Không thể suy ngược mapping v2 một cách trung thực từ file này. Lượt đánh giá v2 phải lưu decision basis/criteria ngay từ đầu; không được đoán CP nào sinh critical.

### 12.4. Cổng trước lượt trả phí

- Viết và commit protocol đánh giá v2 trước khi xem output mới.
- Hoàn tất nhãn v1.4 + test–retest trước khi xem output AI v2 để tránh neo nhận thức.
- Khóa model, prompt version, rubric, guideline, policy hash, scoring hash, KB hash và embedding backend.
- Người dùng duyệt riêng chi phí cho đúng lượt chạy.
- Không resume output v1 vào file v2.
- Ghi HEAD thực tế và score-path snapshot mới.

Tại thời điểm viết spec, HEAD là `b0fa1c8`, prompt version vẫn `020738e209017213`, nhưng score-path diff so với snapshot E1/E5 `04f10e1` **không rỗng** ở `multiagent/src/embeddings.py` do thêm đường RemoteEmbedder. Trước phép đo v2 phải chốt backend embedding và provenance; không được ghi “chỉ Aggregator thay đổi” nếu môi trường chạy dùng đường embedding khác.

## 13. Rủi ro và giới hạn còn lại

- Policy chỉ quyết định trên finding mà agent phát hiện được; nó không sửa false negative A1 đã biết ở G-011/G-020.
- CQ9/CP10 chỉ giảm khoảng trống A5/A6; LLM-only vẫn không đủ assurance để tự `rejected`, và CP10 phụ thuộc độ phủ nguồn hướng dẫn chính thức.
- BV3 bị tước quyền chặn cho tới khi sửa semantics bằng căn cứ độc lập và đo lại.
- SEO11 phải phân biệt năm dùng như freshness marker với năm lịch sử; regex “mọi năm cũ” sẽ chặn oan.
- CP5/B15 vẫn có thể khớp mọi số chứa `km`; đây là blocker activation v2, không được che bằng policy.
- CP9 hiện phát hiện hình dạng văn xuôi ẩn chứ không hiểu ý định; A7 phải mô tả đúng tín hiệu này và báo kèm giới hạn false positive/false negative đã biết.
- CP2/CP4 thật sẽ được hạ thành `needs_revision` thay vì `rejected` nếu chỉ có assurance LLM. Đây là đánh đổi có chủ đích: tránh máy tự từ chối oan, giữ người duyệt làm chủ quyết định cuối.
- Functional-clean chỉ có 10 bài corrected; kể cả khi v2 đạt 10/10 cũng không suy ra false-block rate ngoài thực tế bằng 0.
- Vì policy mapping được thiết kế sau khi đã xem lỗi của corpus hiện tại, chỉ số trên cùng 43 output là development/regression evidence, không phải bằng chứng tổng quát hoá độc lập.

## 14. Tiêu chí hoàn tất design và điều kiện sang implementation

Design được coi là sẵn sàng để lập implementation plan khi:

- chủ dự án xác nhận bảng quyền mục 6; hướng B11/CP7 đã được xác nhận, còn implementation plan phải khóa chính xác A7/CQ9/CP10/SEO11;
- xác nhận `final_score` không quyết định nhãn v2;
- xác nhận fail-closed khi partial coverage;
- xác nhận policy v1/v2 là release bất biến, không sửa row/job lịch sử;
- thống nhất output decision basis và exact policy selection;
- coverage manifest không có mã A/B “mồ côi” hoặc criterion dấu `-` mơ hồ;
- chốt kế hoạch guideline v1.4 → gán lại 33 → test–retest → đánh giá v2 theo đúng thứ tự;
- không còn mâu thuẫn giữa guideline v1.4 candidate, rubric v2 candidate và nguyên tắc AI không tự publish.

Sau đó mới viết implementation plan theo TDD. Không sửa production code và không chạy phép đo trả phí trong chính bước thiết kế này.
