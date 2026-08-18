# Thiết kế policy quyết định chặn xuất bản v2

**Ngày:** 2026-08-17

**Trạng thái:** Đã được chủ dự án duyệt về nguyên tắc; tài liệu này khôi phục
artifact thiết kế bị thiếu trước khi triển khai code

**Policy candidate:** `cam-nang-vn-v2`

**Liên quan:**

- `docs/goldset/annotation-guideline.md` v1.4;
- `docs/superpowers/specs/2026-08-17-corrected-publish-criterion-coverage-design.md`;
- `docs/superpowers/plans/2026-08-17-corrected-publish-criterion-coverage-evaluation.md`;
- `docs/technical-debt.md` mục 8.2, 8.4, 8.6 và nợ B15.

## 1. Vấn đề cần giải quyết

Policy v1 tính `final_score` bằng trung bình có trọng số rồi so với ba ngưỡng.
Cách này cho phép một tiêu chí hỏng được các tiêu chí điểm cao bù lại. Kết quả
E5 v1 cho thấy `publish_min = 80` đề xuất `publish` cho 9/33 bài mà nhãn yêu
cầu phải sửa; functional-clean đồng thời cho thấy bộ phát hiện vẫn nhìn thấy
lỗi nhưng mức trừ điểm không đủ đổi quyết định.

Ground-truth v1.4 dùng một contract khác:

```text
có ít nhất một mã A  -> rejected
không có A, có B     -> needs_revision
không có A hoặc B    -> publish
```

Vấn đề vì vậy không phải tìm thêm một ngưỡng điểm. Vấn đề là xác định chính
xác phép kiểm nào có quyền chặn và tách quyền đó khỏi điểm tổng.

## 2. Quyết định

Tạo policy candidate `cam-nang-vn-v2` theo taxonomy A/B đã khóa ở guideline
v1.4:

1. Mã A1--A7 có quyền đưa quyết định lên `rejected`.
2. Mã B1--B11 có quyền chặn `publish` ở `needs_revision` nhưng không tự nâng
   lên `rejected`, kể cả khi có nhiều mã B.
3. Chỉ tiêu chí/phép kiểm có ánh xạ canonical trong tài liệu này mới có quyền
   đổi quyết định. Không áp dụng luật thô "mọi criterion mức 0 đều chặn".
4. `final_score` tiếp tục được tính và lưu để chẩn đoán, xếp hạng và so sánh
   lịch sử, nhưng không tham gia quyết định v2.
5. Đánh giá không đầy đủ không bao giờ được `publish`. Nếu chưa có bằng chứng
   nhóm A thì kết quả fail-safe là `needs_revision` kèm
   `incomplete_assessment=true`.
6. Policy v1 vẫn là mặc định cho tới khi v2 qua đủ gate đã đăng ký trước.
   Không sửa hoặc diễn giải lại evidence E1/E5/E6 v1.

Đây là phương án ở giữa hai cực "đẩy `publish_min` lên mức vô hiệu hóa
publish" và "cho mọi mức 0 quyền phủ quyết". Nó khớp ground-truth mà không
biến các khuyến nghị như câu dài, độ dài bài hay internal link thành blocker.

## 3. Phạm vi và ngoài phạm vi

### 3.1. Trong phạm vi

- một decision engine thuần, versioned, ánh xạ kết quả bốn agent sang A/B;
- bổ sung hai phép kiểm semantic còn thiếu cho A5 và A6 trong chính lượt gọi
  Content Quality/Compliance hiện có;
- chuẩn hóa CP7 v2 thành B11 và CP9 thành A7;
- sửa B15 cho CP5 trong release v2;
- theo dõi coverage của từng phép kiểm để phân biệt `NA` với chưa đánh giá;
- route exact `cam-nang-vn-v1|cam-nang-vn-v2` trong graph/worker;
- evaluator v2, paid guard, release manifest và evidence cho E1/gold trước
  khi mở rộng sang corrected/coverage;
- giữ full decision basis, provenance, usage, cost và latency trong raw output.

### 3.2. Ngoài phạm vi

- fit `publish_min`, bật `scoring.yaml.meta.calibrated` hoặc dùng C/GC/CV để
  chọn ngưỡng;
- sửa 33 gold gốc, evidence v1 hoặc nhãn v1.3;
- tuyên bố dữ liệu synthetic là đồng thuận người--AI;
- tự kích hoạt v2 cho production hoặc limited pilot trước khi gate đạt;
- thêm agent thứ năm hoặc thêm một lượt gọi LLM riêng cho policy;
- sửa PHP/JS/CSS của Drupal;
- giải quyết các nợ không phục vụ trực tiếp decision contract này.

## 4. Ba lớp trách nhiệm

### 4.1. Agent phát hiện

Bốn agent tiếp tục phát hiện vấn đề theo miền. LLM chỉ xác định trạng thái của
phép kiểm và trích bằng chứng; nó không được chọn `decision`, nhóm A/B hoặc
severity cuối.

Hai phép kiểm semantic mới được ghép vào lời gọi sẵn có, không tăng số lần gọi:

- Content Quality đánh giá A5: title có được body trả lời hay không và việc
  sửa có vượt quá 50% nội dung hay không.
- Compliance đánh giá A6: bài có đưa ra thao tác kỹ thuật nguy hiểm, bỏ cảnh
  báo an toàn bắt buộc hoặc hướng dẫn trái nguyên tắc an toàn hay không.

Kết quả của hai phép kiểm này nằm trong `policy_checks`, không đi vào mẫu số
`score_from_criteria()`. Nhờ vậy chúng không cộng điểm miễn phí cho bài không
áp dụng và không pha loãng các điểm cũ.

Hình dạng check dùng chung:

```python
{
    "id": "A5 | A6",
    "status": "present | absent | not_applicable | unavailable",
    "occurrences": [{"field": "body", "text": "trích dẫn nguyên văn"}],
    "reason": "căn cứ kết luận",
    "reference_id": None,
}
```

`not_applicable` không hợp lệ cho A5 khi title/body đã có nội dung; A6 dùng
trạng thái này khi bài không có hướng dẫn kỹ thuật. Exception hoặc output
thiếu check phải thành `unavailable`, không được suy thành `absent`.

### 4.2. Decision engine

Module thuần nhận `fields` và bốn agent results, chuẩn hóa thành
`effective_findings`, tính coverage rồi quyết định bằng thứ tự cố định A -> B
-> incomplete -> publish. Module này không gọi model, database, Drupal hoặc
mạng.

### 4.3. Runtime/evaluator

Graph và evaluator chỉ route exact policy version rồi gọi decision engine.
Runtime production giữ v1 mặc định. Evaluator v2 là nơi đầu tiên gọi candidate
v2 để tạo bằng chứng; một kết quả đẹp không tự thay đổi profile production.

```text
fields
  -> bốn agent hiện hành
  -> raw criteria/issues/flags + policy_checks
  -> normalize/dedupe theo canonical registry
  -> coverage + effective_findings
  -> A/B decision v2
  -> raw evidence/report
```

## 5. Contract quyết định

Decision engine trả tối thiểu:

```python
{
    "policy_version": "cam-nang-vn-v2",
    "decision": "publish | needs_revision | rejected",
    "final_score": 0.0,                  # diagnostic; có thể None
    "effective_findings": [],
    "advisory_findings": [],
    "decision_basis": {
        "highest_group": "A | B | none",
        "blocking_codes": [],
        "reason": "defect | incomplete_assessment | clean",
    },
    "coverage": {
        "required_checks": [],
        "assessed_checks": [],
        "not_applicable_checks": [],
        "unavailable_checks": [],
        "complete": True,
    },
    "incomplete_assessment": False,
    "missing_agents": [],
    "drift": [],
}
```

Thứ tự quyết định literal:

```python
if any(finding["group"] == "A" for finding in effective_findings):
    decision = "rejected"
elif any(finding["group"] == "B" for finding in effective_findings):
    decision = "needs_revision"
elif not coverage["complete"]:
    decision = "needs_revision"
else:
    decision = "publish"
```

Một hoặc nhiều B không bao giờ thành A. `final_score`, số lượng issue và mức
severity hiển thị không được chen vào công thức trên.

## 6. Hình dạng finding và coverage

Mỗi effective finding có hình dạng ổn định:

```python
{
    "defect_code": "B8",
    "group": "B",
    "source_agent": "content_quality",
    "source_check": "CQ1",
    "level": 1,
    "field": "body",
    "evidence_kind": "excerpt",
    "evidence": "đoạn trích nguyên văn",
    "observed": None,
    "suggestion": "cách sửa",
    "reference_id": None,
    "sources": ["CQ1"],
}
```

Quy tắc dữ liệu:

- `defect_code` chỉ nhận A1--A7/B1--B11 trong registry;
- finding từ LLM mà không có bằng chứng nguyên văn hợp lệ không được tạo;
- phép kiểm tất định về thiếu field/độ dài/cấu trúc dùng
  `evidence_kind=absence|measurement` và lưu giá trị quan sát ở `observed`,
  không bịa một excerpt rỗng thành bằng chứng;
- finding trùng `(defect_code, field, normalized evidence)` được gộp nhưng
  giữ tất cả `sources`, tránh CQ7/CP8 tạo hai lỗi B10 giống nhau;
- advisory criterion không ánh xạ A/B vẫn được giữ riêng, không bị xóa;
- thứ tự code là A1..A7 rồi B1..B11, không phụ thuộc thứ tự agent trả về;
- không dùng confidence tự do của LLM để đổi quyết định.

Mỗi required check phải có một trong ba trạng thái:

- `assessed`: đã chạy và có thể kết luận hiện diện/vắng mặt;
- `not_applicable`: đã chạy, nhưng bài không có đối tượng để kiểm;
- `unavailable`: chưa thể đánh giá vì agent/LLM/RAG/schema lỗi.

`NA` chỉ hợp lệ khi chính phép kiểm đã xác nhận không áp dụng. Không được dùng
`NA` để che một lần gọi hỏng. Có ít nhất một `unavailable` thì coverage không
complete.

Coverage được tổng hợp theo defect code, không chỉ theo tên agent. Với một mã
có nhiều nguồn như B5 hoặc B10:

- chỉ cần một nguồn có finding hợp lệ để chứng minh mã đang hiện diện;
- muốn kết luận mã vắng mặt, mọi nguồn canonical của mã phải
  `assessed/not_applicable`;
- một nguồn báo vắng nhưng nguồn còn lại `unavailable` chưa đủ để cho
  `publish`.

## 7. Canonical registry A/B

| Mã | Nguồn canonical | Điều kiện tạo effective finding |
|---|---|---|
| A1 | CP1 | `level == 0`; claim tuyệt đối có phạm vi và nói về sản phẩm/dịch vụ VinFast |
| A2 | CP2 | `level == 0`; so sánh trực tiếp với đối thủ cụ thể |
| A3 | CP3 | `level == 0`; cùng model, cùng chỉ số và số mâu thuẫn nguồn công bố |
| A4 | CP4 | `level == 0`; ưu đãi có giá trị cụ thể thiếu thời hạn hoặc điều kiện |
| A5 | CQ policy check A5 | `status == present`, đồng thời body không trả lời title và cần viết lại trên 50% |
| A6 | Compliance policy check A6 | `status == present`, có thao tác/cảnh báo kỹ thuật gây nguy cơ rõ ràng và có `reference_id` trong safety source đã khóa |
| A7 | hidden-prose check/CP9 | có văn xuôi bị ẩn trong exact evaluator input; loại CSS, tracking, URL và marker kỹ thuật |
| B1 | CP5 | `level in {0, 1}` sau chốt ngữ cảnh B15 |
| B2 | CP6 | `level in {0, 1}` |
| B3 | field check | meta trống hoặc độ dài ngoài 140--170 ký tự |
| B4 | field check | title ngoài 40--70 ký tự, viết hoa toàn bộ, hoặc chứa năm nhỏ hơn năm `assessment_as_of` |
| B5 | BV1/BV2/BV3/BV4/BV7 | bất kỳ criterion tương ứng có `level in {0, 1}` và evidence hợp lệ |
| B6 | SEO9 | `level in {0, 1}` cho ít nhất một ảnh body thiếu/rỗng/sai alt |
| B7 | SEO5 | `level in {0, 1}`: alias trống, còn dấu, trên 75 ký tự hoặc thiếu từ khóa chính |
| B8 | CQ1/CQ2 | `level in {0, 1}`; một lỗi chính tả/ngữ pháp đã đủ tạo B8 |
| B9 | field check/CQ5 | body trên 500 tiếng và không có H2; H3 không thay thế H2 |
| B10 | CQ7/CP8 | `level in {0, 1}`; gộp finding trùng giữa hai agent |
| B11 | CP7 v2 | `level in {0, 1}` cho claim chính sách cụ thể |

Mọi mapping khác đều bị từ chối ở validation. Đặc biệt:

- CQ3/CQ4 chỉ tương ứng C4/C5, không chặn;
- SEO7 không có mã A/B, không chặn;
- SEO10 chỉ tương ứng C3, không chặn;
- CQ6 cũ không tự động thành A5 vì `level == 0` còn bao gồm lặp ý;
- compliance score dưới 50 của v1 không còn tự biến thành `rejected` ở v2.

## 8. Các phép kiểm cần chuẩn hóa trong release v2

### 8.1. A5

Content Quality trả một policy check riêng với trạng thái
`present|absent|unavailable`. `present` chỉ hợp lệ khi output xác nhận cả hai
vế và trích được title/body liên quan:

1. body không trả lời được câu hỏi hoặc intent ở title;
2. sửa đúng chủ đề đòi viết lại trên 50% nội dung.

Lạc một đoạn nhỏ, lặp ý hoặc bài ngắn đơn thuần không phải A5.

### 8.2. A6

Compliance trả một policy check riêng với trạng thái
`present|absent|not_applicable|unavailable`. `present` phải có:

- trích dẫn nguyên văn thao tác/cảnh báo bị thiếu;
- mô tả nguy cơ cụ thể;
- hướng sửa an toàn, không lặp lại chỉ dẫn nguy hiểm như lời khuyên thật.
- `reference_id` trỏ tới hướng dẫn an toàn chính thức trong safety source đã
  được version/hash cùng release.

LLM không chọn severity. Code ánh xạ check A6 hiện diện sang nhóm A. False
positive/negative của phép kiểm này phải được đo bằng gold/CV, không sửa prompt
sau khi nhìn output trong cùng release.

Nếu LLM nhận thấy nguy cơ nhưng không ghép được `reference_id` hợp lệ, check
phải là `unavailable`: policy chặn `publish` ở `needs_revision` để con người
xác minh, nhưng chưa đủ căn cứ đẩy lên `rejected`.

Safety source là file versioned `multiagent/src/kb/safety_rules.json`. Mỗi
entry có `reference_id`, `source_url`, `accessed_at`, `content_type`,
`langcode` và mô tả quy tắc an toàn. Chỉ dùng nguồn chính thức; không chứa
sample ID, expected label hoặc câu chữ target từ CV. Các rule phù hợp được
đưa vào chính prompt Compliance hiện hành, và structured output chỉ được trả
`reference_id` thuộc allowlist. File này được hash trong release tuple và
không được bổ sung sau khi xem paid output của cùng release.

### 8.3. A7/CP9

Giữ detector tất định của phần văn xuôi ẩn, nhưng output v2 ghi rõ
`defect_code=A7`. Tên CP9 cũ có thể giữ để tương thích; canonical mapping chỉ
dựa vào identifier/rule đã khóa, không fuzzy-match chuỗi hiển thị.

### 8.4. B11/CP7 v2

Trước hết xác định có claim chính sách pin/bảo hành/thuê pin cụ thể:

- không có claim cụ thể -> `not_applicable`;
- thiếu ít nhất hai thành phần thiết yếu -> level 0;
- thiếu đúng một thành phần -> level 1;
- đủ đối tượng/điều kiện, thời hạn và mức phí nếu có thu phí -> level 2.

CP7 level 0 hoặc 1 đều là B11, không phải A. Thông tin trái nguồn chính thức
là A3; ưu đãi có giá trị cụ thể thiếu thời hạn/điều kiện là A4.

### 8.5. B15/CP5

Release v2 sửa B15 trước mọi paid run:

- chỉ nhận số có `km` khi cửa sổ ngữ cảnh có tín hiệu tầm hoạt động như
  `quãng đường`, `đi được`, `tầm hoạt động`, `sau một lần sạc`;
- loại các tỷ lệ `/100km`, `kWh/100km`, `lít/100km`, `đồng/km` và ngữ cảnh
  chi phí/tiêu hao;
- test literal P-006a phải loại `13,4 kWh/100km` và `chi phí trong 1km` nhưng
  vẫn nhận `quãng đường di chuyển 80km`.

Sửa B15 làm evidence E1/E5/E6 v1 hết khả năng đại diện cho code mới; vì vậy
v2 phải chạy bộ evidence riêng, không ghi đè file cũ.

## 9. Routing và tương thích runtime

Hai version hợp lệ duy nhất ở phạm vi hiện tại:

```text
cam-nang-vn-v1 -> aggregator trung bình/ngưỡng legacy
cam-nang-vn-v2 -> taxonomy decision engine trong spec này
```

Không nhận alias, prefix hoặc fuzzy match như `cam-nang-v2`. Unknown version
phải lỗi trước khi gọi provider.

Worker truyền `job.policy_version` vào state. Graph route theo exact version:

- thiếu version ở script legacy được rơi về v1 để giữ tương thích;
- job/platform đã có version thì không được tự rơi về version khác;
- decision engine nhận `assessment_as_of` từ caller, không tự đọc đồng hồ;
  evaluator lấy exact ngày trong preflight, còn runtime chụp ngày UTC đúng
  một lần khi bắt đầu run rồi lưu vào report/audit;
- refactor nhánh v1 phải có characterization tests chứng minh quyết định,
  điểm, veto reason và missing-agent behavior không đổi;
- nhánh v2 vẫn tính `final_score` bằng công thức legacy cho diagnostic, nhưng
  decision lấy duy nhất từ A/B engine;
- report JSON bổ sung policy version, decision basis, finding codes và
  coverage theo cách cộng thêm field; Drupal renderer cũ tiếp tục bỏ qua
  field chưa biết.

Không sửa JS nên không được tuyên bố đã kiểm tương tác trình duyệt mới; phạm
vi này cũng không đòi một UI interaction mới.

## 10. Fail-safe và drift

Phân biệt ba loại lỗi:

1. **Vi phạm nội dung đã có bằng chứng:** áp A/B bình thường, kể cả khi một
   phép kiểm khác unavailable. A vẫn có thể `rejected` vì đã đủ căn cứ.
2. **Hạ tầng/assessment thiếu:** không có A thì trần ở `needs_revision`, ghi
   rõ unavailable checks và missing agents.
3. **Release/schema drift:** unknown policy, thiếu canonical registry, ID
   criterion lạ có ý định chặn, hash sai hoặc manifest mismatch là lỗi fatal;
   dừng run trước provider hoặc không ghi kết quả như một sample hợp lệ.

Không biến exception thành mức 2, không biến absence-of-evidence thành
evidence-of-absence và không cho `--force` bỏ qua release guard.

## 11. Evaluator v2 và raw schema

Core evaluator dùng chung đúng một đường gọi bốn agent và policy engine.
Prerequisite phase hỗ trợ E1 stability và gold; Evaluation Plan hiện hành mở
rộng cùng runner sang corrected và coverage, không tạo evaluator bản sao.

Mỗi raw file có `_meta` tối thiểu:

```text
dataset_kind, policy_version, guideline_version, rubric_version,
prompt_version, model, scoring_hash, policy_hash, KB/embedding provenance,
dataset_manifest_hashes, content_hashes_sha256, git_head,
assessment_as_of, is_fixture=false, created_at
```

Mỗi sample lưu:

```text
sample_id, expected_label, decision, final_score, decision_basis,
effective_findings, advisory_findings, criteria, coverage, drift,
incomplete_assessment, missing_agents, usage, cost, latency, status
```

Report-only chỉ đọc raw JSON và không import agent/provider. Resume chỉ hợp lệ
khi toàn bộ release tuple và ordered sample IDs khớp; mismatch là fatal.

## 12. Paid guard và release manifest

Mọi preflight chạy với `VF_ALLOW_PAID_EVAL=0`, có `usage_events=0` và tạo
token xác nhận từ ít nhất:

```text
dataset_kind + ordered sample IDs + manifest/content hashes
+ policy/prompt/rubric/guideline/model/scoring/KB/embedding/Git HEAD
+ assessment_as_of + exact output path
```

Token chỉ dùng cho đúng một dataset/output/release. Các paid gate tách biệt:

1. E1 v2;
2. gold v2;
3. corrected-publish 30;
4. criterion coverage 11;
5. smoke limited-pilot/cutover nếu và chỉ nếu gate định lượng đạt.

Mỗi gate cần xác nhận chi phí riêng của chủ dự án. Preflight không phải kết
quả thí nghiệm. Raw/report âm vẫn được hash và commit; không sửa mẫu/prompt
trong cùng release để làm đẹp kết quả.

Release manifest theo dõi trạng thái riêng cho `e1`, `gold`, `corrected`,
`coverage`, `smoke`, cùng SHA của preflight/raw/report, confirmation-token
hash, calls/tokens/cost và gate summary. Không lưu token thô hoặc API key.

## 13. Gate và ý nghĩa kết quả

Protocol đăng ký trước giữ các gate:

```text
E1 decision consistency >= 0.90
gold Kappa >= 0.60
gold rejected recall >= 0.80
gold needs_revision recall >= 0.80
gold false publish = 0/33
corrected publish = 30/30
paired recovery = 20/20
coverage target+decision+parent = 11/11
coverage failure = 0
policy/prompt/content drift = 0
independent_label_reliability = not_demonstrated
```

- Mức A `measured_complete`: đủ evidence hợp lệ, dù metric pass hay fail.
- Mức B `passed`: mọi gate định lượng cùng pass; mới được đề xuất limited
  pilot/cutover.
- Mức C `not_demonstrated`: không được suy từ corrected/synthetic data.

`scoring.yaml.meta.calibrated` vẫn `false` trong cả ba trạng thái vì policy
v2 không phải một calibration ngưỡng.

## 14. Chiến lược test

Tất cả code được triển khai TDD và thêm vào test-group manifest.

### 14.1. Pure policy tests

- từng A1--A7 tạo `rejected` độc lập;
- từng B1--B11 tạo `needs_revision` độc lập;
- nhiều B vẫn là `needs_revision`;
- advisory level 0 không chặn;
- không finding + coverage complete -> `publish`;
- không finding + unavailable -> `needs_revision`;
- A finding + unavailable khác -> `rejected` nhưng vẫn ghi incomplete;
- dedupe B10 giữ cả CQ7/CP8 sources;
- order output canonical và input không bị mutate;
- unknown/malformed mapping bị từ chối.

### 14.2. Detector/agent tests

- A5 đủ hai vế, ca chỉ lạc một đoạn và ca evidence bịa;
- A6 nguy hiểm rõ, lời khuyên an toàn, ca không áp dụng và evidence bịa;
- CP7 đủ bốn trạng thái NA/0/1/2 và mapping B11;
- A7 bắt văn xuôi ẩn nhưng bỏ CSS/tracking/URL/marker;
- B15 literal P-006a và positive tầm hoạt động;
- LLM/RAG failure được ghi unavailable, không thành pass.

### 14.3. Routing/compatibility tests

- characterization v1 khóa decision/score/veto/missing behavior;
- v2 bỏ quyền quyết định của threshold nhưng giữ diagnostic score;
- worker truyền exact job policy version;
- unknown version fail trước provider import/call;
- report JSON mới không phá consumer legacy.

### 14.4. Evaluator/release tests

- fake provider, zero paid calls;
- exact IDs/counts/hashes từng dataset;
- token không dùng chéo dataset/output/release;
- raw schema đầy đủ và `is_fixture=false` chỉ ở run thật;
- resume mismatch, dirty protected path, manifest drift và output tồn tại bị
  từ chối;
- report-only chạy khi paid env tắt;
- approval không có `--force` và không thể biến Mức C thành pass.

Full offline suite phải kết thúc với 0 fail/0 skip và in summary. Test PHP/DDEV
không cần cho thay đổi Python này; Docker cũng không cần cho pure/evaluator
tests.

## 15. Trình tự triển khai và cutover

1. Commit spec này và implementation plan trước code.
2. TDD decision engine, coverage contract và exact registry.
3. TDD A5/A6, CP7/A7 và B15.
4. TDD graph/worker routing, giữ v1 mặc định.
5. TDD evaluator/paid guard/release manifest cho E1 và gold.
6. Chạy full offline và các preflight $0.
7. Dừng xin xác nhận riêng trước từng paid run.
8. Mở rộng evaluator bằng Corrected Publish & Criterion Coverage Evaluation
   Plan đã có.
9. Chỉ sau Mức B pass mới xin xác nhận smoke/cutover. Fail thì giữ v1 active,
   commit evidence âm và phát hành candidate version mới nếu tiếp tục.

Không có bước nào tự động thay `review_profile.policy_version` của production.

## 16. Tiêu chí hoàn tất thiết kế

Thiết kế đủ rõ để lập implementation plan khi:

- quyền quyết định của A/B và ranh giới với score được khóa;
- mapping A1--A7/B1--B11 không còn mã trống;
- A5/A6/CP7/A7/B15 có contract cụ thể;
- legacy v1, evidence v1 và `scoring.yaml` được bảo toàn;
- fail-safe, coverage, drift và raw schema được xác định;
- năm paid gate tách token/xác nhận;
- Mức A/B/C và giới hạn synthetic/independent evidence được giữ nguyên.
