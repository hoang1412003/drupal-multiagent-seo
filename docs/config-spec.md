# Đặc tả file cấu hình

**Phiên bản:** v1 (2026-07-27)
**Trạng thái:** đặc tả - chưa triển khai
**Hiện thực hoá:** `docs/architecture.md` mục 5.6 (thiết kế config-driven)

---

## 1. Vấn đề: cùng một con số đang nằm ở 4 nơi

`architecture.md` mục 5.6 cam kết rubric và ngưỡng lưu theo khoá `(content_type, langcode)` trong config, và tự thừa nhận chưa triển khai. Nhưng vấn đề đã lớn hơn "chưa triển khai": **các ngưỡng đang bị chép ra nhiều bản, và đã trôi lệch một lần.**

Hiện trạng:

| Nơi | Chứa gì |
|---|---|
| `multiagent/src/graph.py` | `WEIGHTS` (0.25/0.20/0.25/0.30), ngưỡng quyết định 80/50, ngưỡng veto Compliance 50 |
| `multiagent/scripts/label_helper.py` | `TITLE_MIN/MAX = 40, 70`, `META_MIN/MAX = 140, 170`, `LONG_SENTENCE_WORDS = 30`... |
| `docs/rubrics.md` | Ngưỡng chấm điểm từng tiêu chí |
| `docs/goldset/annotation-guideline.md` | Ngưỡng gán nhãn từng mã lỗi |

Bốn bản chép tay của cùng một tập số. Hậu quả đã xảy ra thật: B3 từng ghi `150-160` trong guideline trong khi rubric ghi `140-170` - lệch do sơ suất, phát hiện tình cờ khi đối chiếu, phải sửa và tăng version guideline lên v1.1. Nếu phát hiện sau khi đã gán 33 nhãn thì phải gán lại toàn bộ.

Config không phải để "cho có kiến trúc đẹp". Nó là để **con số chỉ tồn tại ở một chỗ**.

---

## 2. Hai họ ngưỡng, phải đặt tên khác nhau

Đây là điểm dễ làm sai nhất, và là nguyên nhân gốc của lần trôi lệch vừa rồi.

Dự án có **hai họ ngưỡng phục vụ hai mục đích khác nhau**, và chúng **cố ý khác giá trị**:

| | Dùng để | Ví dụ (title) | Nguồn |
|---|---|---|---|
| `scoring` | **Chấm điểm** - dải lý tưởng, cho điểm từng phần | 50-60 ký tự = mức 2 | `rubrics.md` |
| `labelling` | **Gán nhãn ground truth** - dải "sai rõ ràng" | ngoài 40-70 = lỗi B4 | `annotation-guideline.md` |

Vì sao khác nhau: nếu dùng dải lý tưởng 50-60 làm ranh giới **nhãn** thì gần như mọi bài thật đều dính lỗi → tất cả thành `needs_revision` → phân bố nhãn sụp đổ → Kappa mất ý nghĩa. Lý do đầy đủ ở `annotation-guideline.md` mục 11 (v1.1).

**Hệ quả cho config: không được gộp chúng vào một khoá.** Đặt tên tách bạch (`scoring.title_ideal` và `labelling.title_ok`) làm sự khác biệt trở nên hiển nhiên khi đọc file, thay vì là một cái bẫy.

---

## 3. Định dạng và vị trí

**YAML**, tại `multiagent/config/`.

Chọn YAML thay vì JSON vì **những con số này cần chú thích**: "tại sao 30 từ", "giá trị tạm chờ calibrate", "đừng sửa tay, do E5 sinh ra". JSON không có comment - mà đây là loại file mà mất phần giải thích là mất gần hết giá trị.

Không phát sinh dependency: `PyYAML 6.0.3` đã có sẵn trong `.venv` (kéo theo qua `langgraph`). Đã kiểm chứng.

```
multiagent/config/
└── scoring.yaml      # toàn bộ trọng số + ngưỡng, khoá theo (content_type, langcode)
```

Một file, không tách nhỏ. Quy mô hiện tại là vài chục con số - tách file chỉ thêm chỗ để lệch nhau.

`compliance_rules.json` (blacklist) **giữ nguyên** vị trí và định dạng: nó là danh sách dữ liệu, không phải tham số điều chỉnh, và không do calibration sinh ra.

---

## 4. Cấu trúc

```yaml
version: 1

# Tra cứu theo khoá "<content_type>:<langcode>". Không có khoá khớp -> dùng
# "default". KHÔNG kế thừa/gộp từng phần: mỗi khoá là một khối đầy đủ, để
# đọc file là biết chắc hệ thống đang chạy bằng số nào.
default:

  # --- Xuất xứ: khối này do calibration (evaluation-plan.md E5) ghi ra ------
  meta:
    calibrated: false            # false = đang dùng giá trị minh hoạ
    calibrated_at: null
    gold_set: null               # ví dụ "labels.csv @ 1ceeb2f"
    guideline_version: null      # v1.1
    rubric_version: null         # v1
    prompt_version: null         # hash/tag của bộ system prompt
    model: null                  # model đã dùng khi calibrate
    kappa: null                  # Kappa đạt được, để đối chiếu về sau

  # --- Aggregator ----------------------------------------------------------
  weights:
    content_quality: 0.25
    seo: 0.20
    brand: 0.25
    compliance: 0.30

  decision:
    publish_min: 80              # >= -> publish
    needs_revision_min: 50       # >= -> needs_revision, dưới -> rejected
    compliance_veto_below: 50    # điểm Compliance dưới mức này -> rejected

  # --- Ngưỡng CHẤM ĐIỂM (rubrics.md) --------------------------------------
  scoring:
    title_ideal: [50, 60]        # ký tự
    title_acceptable: [40, 70]
    meta_ideal: [140, 170]
    body_min_words: 600
    long_sentence_words: 30
    long_paragraph_sentences: 5

  # --- Ngưỡng GÁN NHÃN (annotation-guideline.md) --------------------------
  # CỐ Ý khác họ scoring - xem config-spec.md mục 2 trước khi sửa
  labelling:
    title_ok: [40, 70]           # ngoài dải -> B4
    meta_ok: [140, 170]          # ngoài dải -> B3
    url_max_chars: 75            # -> B7
    long_sentence_words: 30      # -> B9
    long_paragraph_sentences: 5  # -> B9
    repeat_threshold: 3          # số lần lặp mới tính là lỗi
    heading_required_words: 500

  # --- Retrieval (rag-design.md) ------------------------------------------
  retrieval:
    top_k_factcheck: 3
    top_k_brand: 3
    min_similarity: null         # chốt từ bộ eval E2

# Khoá thật của phạm vi hiện tại. Trước khi calibrate, để y hệt default.
"cam_nang:vi":
  # ... khối đầy đủ như trên
```

---

## 5. Config là **đầu ra** của calibration, không phải file điền tay

Đây là quyết định thiết kế quan trọng nhất trong tài liệu này.

`evaluation-plan.md` E5 quét ngưỡng và chọn ra bộ cho Kappa cao nhất. **Kết quả đó ghi thẳng ra `scoring.yaml`** cùng khối `meta` mô tả nó được sinh ra trong điều kiện nào.

Hai hệ quả:

**(a) Quy tắc versioning trở nên cưỡng chế được, không còn là lời hứa.** `rubrics.md` mục 10 và `architecture.md` mục 8.2 đều nói ngưỡng chỉ có hiệu lực với đúng bộ `(rubric version, prompt version, model)`. Trước đây đó chỉ là câu văn trong tài liệu. Với `meta` nằm trong config, hệ thống **tự kiểm tra được lúc chạy**:

```
Nếu meta.model != model đang dùng:
    Cảnh báo: "Ngưỡng calibrate cho <X>, đang chạy <Y>. Ngưỡng có thể không còn đúng."
Nếu meta.calibrated == false:
    Cảnh báo: "Đang dùng ngưỡng minh hoạ, chưa calibrate."
```

Cảnh báo thứ nhất chặn một lỗi rất dễ xảy ra: [`ai_core.py:9`](../multiagent/src/ai_core.py#L9) đọc model từ **biến môi trường** (`ANTHROPIC_MODEL`). Ai đó đổi `.env` là toàn bộ ngưỡng đã calibrate mất hiệu lực **mà không có dấu hiệu gì**. Đây là bẫy im lặng đúng nghĩa.

Cảnh báo thứ hai quan trọng khi báo cáo: không để lỡ trình bày kết quả chạy bằng ngưỡng minh hoạ như thể đã calibrate.

**(b) Không sửa tay file đã calibrate.** Muốn đổi ngưỡng thì chạy lại calibration. Sửa tay là làm mất mối liên hệ giữa con số và bằng chứng sinh ra nó - đúng thứ mà cả dự án đang cố tránh.

---

## 6. Cái gì KHÔNG vào config

| Không vào | Vì sao |
|---|---|
| **System prompt của 4 agent** | Là code, không phải tham số. Sửa prompt là thay đổi hành vi cần review qua git, không phải chỉnh cấu hình. Chỉ *phiên bản* prompt vào `meta.prompt_version` |
| **Danh sách blacklist** (`compliance_rules.json`) | Là dữ liệu tra cứu, không phải tham số điều chỉnh; không do calibration sinh ra |
| **API key, URL Drupal** | Đã ở `.env`, không được trộn bí mật vào file cấu hình theo dõi bởi git |
| **Bảng mã lỗi A/B/C** | Là định nghĩa ngữ nghĩa, đổi là phải gán lại nhãn - thuộc về guideline có version, không phải config |

Ranh giới: **config chứa những con số calibrate được; mọi thứ khác thuộc về code hoặc tài liệu có version.**

---

## 7. Đường chuyển đổi

Làm được ngay, không cần chờ calibration:

```
Bước 1  Tạo scoring.yaml, chép nguyên giá trị đang hard-code vào,
        đặt meta.calibrated = false
        → Hành vi hệ thống KHÔNG đổi. Đây là refactor thuần.

Bước 2  graph.py đọc weights + decision từ config thay vì hằng số module

Bước 3  label_helper.py đọc khối labelling thay vì hằng số của riêng nó
        → Xoá bản chép thứ hai

Bước 4  Thêm cảnh báo lúc chạy (mục 5a)

Bước 5  Khi implement rubric: đọc khối scoring từ config ngay từ đầu,
        không hard-code rồi tách sau
```

Bước 1-2 nên làm **trước** E5, vì E5 phải quét nhiều bộ ngưỡng - có config sẵn thì đó là vòng lặp đọc file, còn hard-code thì phải sửa code mỗi lần quét.

Hai tài liệu `rubrics.md` và `annotation-guideline.md` **vẫn giữ các con số** trong bảng của chúng - nhưng bổ sung ghi chú rằng nguồn thi hành là `scoring.yaml`, tài liệu chỉ diễn giải. Người đọc tài liệu cần thấy con số ngay tại chỗ, không nên phải mở file config.

---

## 8. Ảnh hưởng lên code

| File | Thay đổi |
|---|---|
| `multiagent/config/scoring.yaml` *(mới)* | Toàn bộ cấu hình |
| `src/config.py` *(mới)* | Nạp YAML, tra theo `(content_type, langcode)`, fallback `default`, phát cảnh báo mục 5a |
| `src/graph.py` | Bỏ hằng số `WEIGHTS` và 80/50, đọc từ config |
| `src/state.py` | Thêm `content_type`, `langcode` - hiện chưa có, mà thiếu chúng thì không tra config được |
| `scripts/label_helper.py` | Đọc khối `labelling` thay vì hằng số riêng |
| `scripts/` | Test: tra khoá đúng, fallback `default` hoạt động, cảnh báo bắn khi model lệch |

`state.py` thiếu `content_type`/`langcode` là điểm chặn thật: `architecture.md` mục 5.6 đã ghi nhận, và nó chặn toàn bộ cơ chế tra config. Phải thêm ở bước 2.

---

## 9. Chưa chốt

| Hạng mục | Ghi chú |
|---|---|
| Có kế thừa từ `default` không | v1 chọn **không** - mỗi khoá là khối đầy đủ. Đọc là biết chắc, đổi lại khi số lượng content_type tăng |
| Ngưỡng riêng cho từng agent | Hiện chỉ có ngưỡng tổng. Nếu calibration cho thấy Compliance cần ngưỡng riêng thì thêm sau |
| `min_similarity` của retrieval | Chốt từ E2, chưa có số |
| Lưu nhiều bộ đã calibrate | Hiện một bộ. Nếu cần so sánh giữa các lần calibrate thì đánh version file thay vì ghi đè |
