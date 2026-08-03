# Thiết kế: Brand Voice Agent dùng RAG (Sprint 2 — phần 5/5)

**Ngày:** 2026-08-03
**Trạng thái:** thiết kế đã duyệt — chưa triển khai
**Phạm vi:** Sub-project cuối trong Sprint 2 theo thứ tự đã chốt ở `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md`: Compliance Agent (xong, PR #12) → Retry/backoff (xong, PR #13) → Gold set collection (xong) → CP3 RAG fact-check (xong, PR #23) → **Brand Voice Agent (tài liệu này)**.

**Lệch thứ tự có chủ đích:** thứ tự cũ đặt "UI báo cáo" trước Brand Voice. Đảo lại vì khâu gán nhãn gold set đang chờ mentor quyết (xem mục 1.3), trong khi Brand Voice không phụ thuộc gold set và đang chặn E5. UI báo cáo lùi xuống sau.

**Liên quan:** `docs/rubrics.md` mục 5 (BV1–BV7) · `docs/rag-design.md` mục 3–5 · `docs/goldset/sources.md` mục 1.6 (tập `BRAND`) · `docs/evaluation-plan.md` mục 3–4.5 · `docs/architecture.md` mục 5.3

---

## 1. Vấn đề

### 1.1. Stub đang bơm 25 điểm giả cho mọi bài

`multiagent/src/graph.py` hiện có:

```python
def brand_node(state: ContentReviewState) -> dict:
    return {"brand_result": _stub_agent_result("Brand Voice")}   # score = 100
```

Brand mang trọng số `0.25`, nên **mọi bài đều được cộng 25 điểm miễn phí**, không bài nào xuống dưới mức đó dù tệ đến đâu.

Bằng chứng định lượng đã đo được (`docs/evaluation-plan.md` mục 4.5, chạy thật trên `node/7` ngày 2026-07-30 — bài gần như rỗng: tiêu đề "test", body chỉ có chữ "test" + 1 ảnh, không meta description, không URL alias):

| Agent | Điểm | Trọng số | Đóng góp |
|---|---|---|---|
| Content Quality | 40 | 0.25 | 10 |
| SEO | 25 | 0.20 | 5 |
| **Brand (stub, luôn 100)** | **100** | 0.25 | **25** |
| Compliance | 100 | 0.30 | 30 |
| | | | **70.0** |

Một bài rỗng vẫn đạt 70 điểm.

### 1.2. Hệ quả: chặn calibration Sprint 3

`docs/evaluation-plan.md` mục 3 xếp đây là **điểm chặn số 4 của E5**. Calibrate ngưỡng trên hệ thống hiện tại sẽ cho ra ngưỡng phản ánh 25 điểm giả, và ngưỡng đó sai hoàn toàn khi agent thật đi vào hoạt động — tức phải calibrate lại từ đầu, tốn cả công gán nhãn lẫn công đo.

### 1.3. Vì sao làm việc này ngay bây giờ

Khâu gán nhãn gold set (33 mẫu) đang chờ mentor quyết định về quy trình. Brand Voice Agent **không phụ thuộc gold set**: nó chỉ cần tập `BRAND` — vốn đã được `docs/goldset/sources.md` mục 1.6 tách rời hẳn khỏi `GOLD`/`PERT` từ trước. Làm song song được, không lãng phí thời gian chờ.

---

## 2. Bốn quyết định đã chốt

| # | Quyết định | Lý do |
|---|---|---|
| **Q1** | Chấm theo **rubric BV1–BV7 (mức 0/1/2/NA) + hàm tất định**, không để LLM tự cho `score: 0-100` | Agent mới hoàn toàn, không có bản cũ phải giữ tương thích → viết đúng ngay, khỏi viết lại. 6/7 tiêu chí vốn đếm được bằng code, hỏi LLM là trả tiền để nhận câu trả lời kém chính xác hơn. Tạo bản thí điểm thực tế chứng minh luận điểm của `rubrics.md` |
| **Q2** | Corpus `BRAND` dùng **đúng 10 URL đã gán sẵn**, mở rộng sau chỉ khi số liệu cho thấy cần | 10 URL đó được gán **trước khi đọc nội dung** (chu kỳ 4 bài ở `sources.md` mục 1.6) nên không thiên vị; URL tìm thêm sau khi đã biết mình tìm gì thì có nguy cơ chọn lọc thiên vị. Điều kiện mở rộng là khách quan — xem mục 4.4 |
| **Q3** | Làm **cả regex lẫn RAG** trong cùng một đợt, theo thứ tự regex → RAG | Roadmap Sprint 2 ghi nguyên văn *"Xây Agent Brand Voice dùng kiến trúc RAG"*; bỏ RAG là không hoàn thành đề bài. RAG phục vụ 7/7 tiêu chí chứ không phải 1/7 (mục 6.3) |
| **Q4** | Prompt của BV6 dùng **thẻ ranh giới có hậu tố ngẫu nhiên** ngay từ đầu | Đây là prompt LLM mới duy nhất trong đợt này và nó nhận HTML thô do người ngoài soạn. Viết code mới mà biết trước có lỗ hổng (`docs/prompt-injection.md` mục 3.1) là vô lý, trong khi chi phí ~5 dòng |

---

## 3. Kiến trúc

Hai phần chạy ở hai thời điểm khác nhau, không được lẫn.

### 3.1. Phần offline — chạy một lần, không nằm trong pipeline chấm bài

```
docs/brand/raw_html/B-001.html … B-010.html      ← người thu tay (Ctrl+S)
        │
        │  scripts/extract_brand_corpus.py
        │  (import lại hàm bóc tách của extract_gold_sample.py, KHÔNG sửa file đó)
        ▼
docs/brand/corpus/B-001.txt … B-010.txt
        │
        │  scripts/build_brand_guideline.py       ← thống kê thuần, KHÔNG gọi LLM
        │  đọc thêm: docs/brand/variant_candidates.json (danh sách ứng viên do người soạn)
        ▼
   ┌──────────────────────────────┬────────────────────────────────┐
   ▼                              ▼                                ▼
docs/brand/                  multiagent/src/agents/          (dùng ở bước sau)
brand_guideline.md           brand_rules.json
(người đọc, kèm số liệu       (máy đọc lúc chấm)
 chứng minh từng quy tắc)
        │
        │  src/kb/build_brand_kb.py               ← cắt đoạn, nhúng vector
        ▼
   Chroma collection "kb_brand"
```

**Vì sao đặt corpus ở `docs/brand/` chứ không phải `docs/goldset/`:** tập `BRAND` **rời hẳn** gold set (`sources.md` mục 1.6) — để chung thư mục sẽ mời gọi việc vô tình trộn hai tập, đúng thứ rò rỉ dữ liệu mà cả thiết kế đang phòng. Tách vật lý làm ranh giới đó nhìn thấy được.

**Manifest `docs/brand/corpus_index.csv`** ánh xạ `sample_id → source_url → topic_group`, theo đúng quy ước `labels.csv` của gold set:

```csv
sample_id,source_url,topic_group
B-001,/vn_vi/cach-lai-xe-o-to-dien,lai_xe_an_toan
B-002,/vn_vi/huong-dan-cach-sac-xe-dien-khong-chai-pin,sac_pin
```

`topic_group` chép từ nhóm chủ đề đã có sẵn ở `sources.md` mục 1.1–1.5 (lái xe/an toàn, sạc & pin, bảo dưỡng & chi phí, trạm sạc, ứng dụng). File này là **đầu vào duy nhất** cho `topic_group` — cả `build_brand_kb.py` lẫn `eval_brand_retrieval.py` đọc từ đây, không suy đoán từ tên file hay nội dung.

**Vì sao hai file đầu ra (`.md` + `.json`) thay vì một:** `.md` để người và mentor đọc, kiểm chứng được từng quy tắc bằng số; `.json` để code so khớp lúc chạy. **Cùng một lần chạy sinh ra cả hai**, nên không trôi lệch được — đúng bài học ở `docs/config-spec.md` mục 1 (cùng một con số nằm ở 4 nơi và đã lệch một lần thật).

### 3.2. Phần runtime — mỗi lần chấm một bài

```
graph.py  brand_node
        ▼
src/agents/brand_voice.py — run(fields, *, content_type="cam_nang", langcode="vi")
        │
        ├── BV1,2,3,4,5,7 ─ regex, đối chiếu brand_rules.json ─ KHÔNG gọi LLM
        │                            │
        │                            └─ truy vấn kb_brand lấy đoạn thật
        │                               đính vào gợi ý làm BẰNG CHỨNG (vai trò b)
        │
        └── BV6 ─ truy vấn kb_brand lấy 3 đoạn cùng chủ đề ─ gọi Claude 1 lần
        │
        ▼
   criteria: 7 bản ghi kèm mức 0/1/2/NA
        │
        ├──> src/scoring.py    → score (0-100 hoặc None)
        └──> _issues_from_criteria()  → issues
        ▼
   {"score": 78.6, "issues": [...], "criteria": [...]}
        ▼
   Aggregator (KHÔNG sửa gì) → Write-back (KHÔNG sửa gì)
```

Chữ ký `run()` khớp `compliance.run()` hiện có (tham số `content_type`/`langcode` có giá trị mặc định), nên **không cần thêm trường vào `state.py`** ở đợt này.

### 3.3. Ba tính chất đáng chú ý

1. **Aggregator và write-back không phải sửa một dòng.** Agent vẫn trả `score` và `issues` (mỗi issue có trường `field`) đúng hợp đồng cũ. `criteria` là phần *thêm vào*.
2. **Chỉ 1/7 tiêu chí gọi LLM.** Claude lỗi hoặc KB chưa dựng thì agent vẫn chấm được 6 tiêu chí còn lại và vẫn trả điểm — suy giảm mềm thay vì chết hẳn (mục 7).
3. **`retrieval.py` sửa tối thiểu:** thêm tham số `collection_name` có giá trị mặc định là hằng số cũ, mọi lời gọi fact-check hiện có giữ nguyên hành vi.

---

## 4. Trích xuất brand guideline từ corpus

### 4.1. Nguyên tắc: người nêu ứng viên, dữ liệu chọn đáp án

| Việc | Ai làm | Ví dụ |
|---|---|---|
| Nêu **danh sách ứng viên** biến thể | Người (`variant_candidates.json`) | *"ô tô điện"* hay *"xe hơi điện"* |
| Quyết định **biến thể nào chuẩn** | **Dữ liệu** (thống kê corpus) | 10/10 bài dùng *"ô tô điện"* → chuẩn |

Danh sách ứng viên do người soạn là **không tránh được** — máy không tự biết "xe hơi điện" là biến thể của "ô tô điện". Điều đó **không làm hỏng tính khách quan**, vì phần *phán quyết* hoàn toàn do số liệu. Ranh giới này phải nêu thẳng trong báo cáo; để mập mờ mới là điểm yếu.

`docs/brand/variant_candidates.json` gồm đúng ba nhóm:

```json
{
  "model_names": ["VF 3", "VF 5", "VF 6", "VF 7", "VF 8", "VF 9", "VF e34", "..."],
  "term_pairs": [
    ["ô tô điện", "xe hơi điện", "xe ô tô điện"],
    ["xe máy điện", "xe gắn máy điện"],
    ["trạm sạc", "trụ sạc"]
  ],
  "address_forms": ["bạn", "quý khách", "khách hàng", "người dùng", "anh/chị"]
}
```

Trong `term_pairs`, thứ tự các biến thể **không mang ý nghĩa** — biến thể nào là chuẩn hoàn toàn do thống kê quyết định, không do vị trí trong danh sách. Với `model_names`, biến thể sai được sinh tự động từ dạng chuẩn (bỏ dấu cách, đổi hoa/thường: `VF 8` → `VF8`, `vf8`, `Vf8`), không phải liệt kê tay.

Danh sách này **bổ sung được về sau mà không phải nhúng lại KB** — nó chỉ ảnh hưởng bước thống kê, không ảnh hưởng vector store.

### 4.2. Quy tắc nào rút từ corpus

| Tiêu chí | Rút ra cái gì | Cách đo lúc chấm |
|---|---|---|
| **BV1** | Cách viết tên model chuẩn (`VF 8` hay `VF8`) | regex, đếm số chỗ sai |
| **BV2** | Thuật ngữ chuẩn cho từng cặp ứng viên | regex, đếm số chỗ dùng biến thể thiểu số |
| **BV3** | *(không cần corpus)* | đếm số kiểu xưng hô lẫn lộn **trong cùng bài** |
| **BV4** | Kiểu xưng hô phổ biến nhất của corpus | so kiểu xưng hô của bài với chuẩn corpus |
| **BV5** | Quy ước viết hoa tiêu đề (xem dưới) | kiểm tra title bài đang chấm |
| **BV7** | Danh sách biến thể corpus **chưa bao giờ dùng** | có xuất hiện = lỗi (nhị phân) |

**BV5 rút ra thế nào:** phân loại 10 title của corpus vào 3 kiểu — `ALL CAPS` (mọi chữ cái viết hoa), `Title Case` (viết hoa đầu hầu hết từ), `Sentence case` (chỉ viết hoa đầu câu và danh từ riêng) — rồi lấy kiểu chiếm đa số làm chuẩn, áp **cùng phép kiểm định ở mục 4.3**. Không đủ căn cứ thì BV5 trả `NA`, trừ trường hợp `ALL CAPS` vốn luôn là mức `0` (đây là lỗi B4 đã ghi trong `annotation-guideline.md`, có bằng chứng thật trên site: *"LƯU Ý SỬ DỤNG ĐỐI VỚI PIN CELL LFP/GOTION"*).

**Phân biệt BV2 và BV7** — cùng về thuật ngữ, khác mức chắc chắn:

- Biến thể **có xuất hiện nhưng thiểu số** → BV2, chấm theo số chỗ (0/1/2)
- Biến thể **0 lần trong toàn corpus** → BV7, nhị phân (corpus chuẩn chưa từng dùng thì bài mới cũng không nên dùng)

Ranh giới này **suy ra từ dữ liệu**, không phải ngưỡng tự đặt.

### 4.3. Khi nào một quy ước đủ điều kiện thành quy tắc

Đây là chỗ dễ đưa số ảo vào nhất. 10/10 bài thì rõ, nhưng **8/10 thì sao?** Đặt đại "≥80% thì thành quy tắc" chính là số ảo — đúng thứ cả dự án đang tránh.

**Dùng kiểm định nhị thức hai phía (binomial test) so với giả thuyết 50-50.** Với n = 10 bài, ngưỡng tự rơi ra từ phép kiểm định:

| Tỉ lệ | p-value | Kết luận |
|---|---|---|
| 10/10 | 0,002 | ✅ thành quy tắc |
| 9/10 | 0,021 | ✅ thành quy tắc |
| **8/10** | **0,109** | ❌ chưa đủ căn cứ |
| 7/10 | 0,344 | ❌ chưa đủ căn cứ |

Ngưỡng "≥9/10" **không do ai đặt ra** — nó là hệ quả của mức ý nghĩa 0,05 tiêu chuẩn. Cùng tinh thần với Youden's Index mà dự án đã dùng cho ngưỡng quyết định (`architecture.md` mục 6.2).

Cài đặt: hàm ~8 dòng dùng `math.comb` của thư viện chuẩn. **Không thêm dependency** (không cần `scipy`).

**Quy ước rơi vào vùng chưa đủ căn cứ thì KHÔNG sinh quy tắc** — ghi vào mục riêng *"chưa đủ căn cứ"* của `brand_guideline.md`, và tiêu chí tương ứng lúc chấm trả **`NA`** (bị loại khỏi cả tử số lẫn mẫu số, không phải cho 0 điểm).

### 4.4. Điều kiện khách quan để mở rộng corpus

Trực tiếp nối với Q2: **nếu có quy ước rơi vào vùng chưa đủ căn cứ (7/10 hoặc 8/10), đó là tín hiệu thu thêm 10 URL `BRAND`** — và thu **có mục đích**, nhằm giải quyết đúng chỗ mập mờ đó. Quyết định dựa trên số liệu chứ không đoán trước.

Nếu mọi quy ước đều rơi vào 9/10 hoặc 10/10 thì 10 bài là đủ, không thu thêm.

### 4.5. Đếm theo bài hay theo số lần — báo cáo cả hai, quyết định bằng số bài

```
"ô tô điện"  →  theo số bài:  10/10   (p = 0,002)   ← dùng để QUYẾT ĐỊNH
                theo số lần:  312/340 = 91,8%       ← số mô tả kèm theo
```

**Vì sao quyết định bằng số bài dù số lần có mẫu số lớn hơn nhiều:** 312 lần xuất hiện đó **không độc lập với nhau** — chúng đến từ 10 bài, một bài dùng "ô tô điện" 50 lần là *một* lựa chọn phong cách lặp lại chứ không phải 50 bằng chứng riêng biệt. Áp kiểm định thống kê lên dữ liệu không độc lập sẽ **thổi phồng mức ý nghĩa**; đây là lỗi phương pháp người chấm có kinh nghiệm sẽ bắt được.

Bài là đơn vị độc lập → dùng kiểm định. Số lần là số mô tả → đưa vào guideline cho trực quan. Câu *"92% bài dùng 'ô tô điện'"* ở spec mục 6.4 vẫn giữ, chỉ hiểu đúng vai trò.

### 4.6. Hai file đầu ra

**`docs/brand/brand_guideline.md`** — cho người đọc và mentor kiểm chứng:

```markdown
## Thuật ngữ chuẩn
| Chuẩn | Không dùng | Số bài | Số lần | p-value |
|---|---|---|---|---|
| ô tô điện | xe hơi điện | 10/10 | 312/340 (91,8%) | 0,002 |

## Chưa đủ căn cứ (không sinh quy tắc)
| Ứng viên | Số bài | p-value | Ghi chú |
|---|---|---|---|
| trạm sạc / trụ sạc | 6/10 | 0,754 | cần thêm corpus mới kết luận được |
```

**`multiagent/src/agents/brand_rules.json`** — cho code so khớp lúc chạy. Đặt cạnh `compliance_rules.json` theo đúng quy ước sẵn có của dự án.

---

## 5. Agent lúc chạy

### 5.1. `src/scoring.py` — hàm quy mức ra điểm

Đúng công thức `rubrics.md` mục 2.2. Hàm thuần, không gọi mạng, không gọi LLM:

```python
def score_from_criteria(criteria: list[dict]) -> float | None:
    """Mức 0/1/2 -> điểm 0-100.

    Tiêu chí NA (level=None) bị loại khỏi CẢ tử số lẫn mẫu số - NA tuyệt đối
    không được tính là 'đạt', nếu không mọi bài không nhắc tới tiêu chí đó đều
    được cộng điểm miễn phí (rubrics.md mục 2.2).
    """
    applicable = [c for c in criteria if c["level"] is not None]
    if not applicable:
        return None          # không tiêu chí nào áp dụng được -> CHƯA chấm được
    return round(100 * sum(c["level"] for c in applicable) / (2 * len(applicable)), 1)
```

Đây đúng file `rubrics.md` mục 8 đã ghi sẵn là sẽ cần, nên không phải abstraction thừa. Đợt này nó chỉ có **một hàm** phục vụ Brand Voice; khi 3 agent kia chuyển sang rubric thì dùng lại nguyên hàm.

Phần "tra bảng severity cho Compliance" mà `rubrics.md` mục 8 cũng xếp vào file này **không thuộc phạm vi đợt này**.

### 5.2. Bảy tiêu chí và cách quyết định mức

| Mã | Đo | `0` | `1` | `2` | `NA` khi |
|---|---|---|---|---|---|
| **BV1** Tên model | regex | ≥3 chỗ sai | 1–2 chỗ | không sai | bài không nhắc model nào |
| **BV2** Thuật ngữ | regex | ≥3 chỗ dùng biến thể thiểu số | 1–2 chỗ | chuẩn toàn bài | bài không nhắc thuật ngữ nào trong danh sách |
| **BV3** Xưng hô nhất quán | regex | lẫn ≥3 kiểu | lẫn 2 kiểu | 1 kiểu | bài không xưng hô với người đọc |
| **BV4** Xưng hô khớp corpus | regex | khác chuẩn corpus | — | khớp | BV3 = NA, **hoặc** corpus chưa đủ căn cứ |
| **BV5** Viết hoa tiêu đề | regex | VIẾT HOA TOÀN BỘ | không nhất quán | đúng quy ước | — |
| **BV6** Mức độ trang trọng | LLM + RAG | lệch rõ | hơi lệch | khớp | **KB lỗi / LLM lỗi** (mục 7) |
| **BV7** Từ bị loại | regex | có | — | không | danh sách loại rỗng |

**Cột `NA` là phần quan trọng nhất của bảng.** Bài không nhắc tên model nào thì BV1 bị **loại khỏi phép tính**, không phải được cộng 2 điểm miễn phí. Tính NA thành đạt sẽ khiến tiêu chí thành hằng số — đúng lỗi spec mục 7.1 đã cảnh báo.

Ngưỡng đếm trong bảng (3 chỗ, 2 kiểu) lấy nguyên từ `rubrics.md` mục 5, đều là **giá trị tạm chờ calibrate** ở Sprint 3.

### 5.3. Một nguồn dữ liệu duy nhất

```
criteria  ──(nguồn duy nhất)──┬──> scoring.score_from_criteria()  ──> score
                              └──> _issues_from_criteria()        ──> issues
```

Tiêu chí mức `0`/`1` sinh issue; mức `2`/`NA` không sinh gì. Một tiêu chí lỗi ở nhiều field (ví dụ `VF8` sai ở cả `title` lẫn `body`) sinh **một issue cho mỗi field**, để `write_back_node` gom đúng nhóm.

Bản ghi một tiêu chí:

```python
{
  "id": "BV2",
  "level": 0,                       # 0 | 1 | 2 | None (None = NA)
  "occurrences": [{"field": "body", "text": "xe hơi điện"}, ...],   # NGUYÊN VĂN
  "suggestion": "Dùng 'ô tô điện' thay cho 'xe hơi điện' (10/10 bài chuẩn dùng cách này).",
  "reference": "…đoạn trích thật từ corpus…"     # RAG vai trò (b), mục 6.3
}
```

**Bắt buộc trích nguyên văn khi hạ mức** (`rubrics.md` mục 2.5): không trích được nguyên văn thì không được hạ mức. Với 6 tiêu chí regex điều này miễn phí — regex vốn biết chính xác nó khớp ở đâu.

### 5.4. Đầu ra

```python
{
  "score": 78.6,                                  # Aggregator đọc — hợp đồng cũ
  "issues": [{"field", "type", "suggestion"}, …],  # write_back đọc — hợp đồng cũ
  "criteria": [...]                               # THÊM MỚI
}
```

Giá trị của `criteria` ở Sprint 3: so được **cả lý do** chứ không chỉ nhãn — *"AI hạ mức BV2"* đối chiếu *"người ghi mã lỗi B5"*. Trùng nhãn nhưng khác lý do là trùng ngẫu nhiên, cần xem lại (`rubrics.md` mục 7).

### 5.5. Ví dụ chạy

Bài có: 3 chỗ viết `VF8`, thuật ngữ chuẩn hết, lẫn "bạn" và "quý khách", dùng "bạn" đúng chuẩn corpus, tiêu đề đúng quy ước, giọng văn khớp, không có từ bị loại.

```
BV1 = 0   BV2 = 2   BV3 = 1   BV4 = 2   BV5 = 2   BV6 = 2   BV7 = 2
tổng mức = 11,  số tiêu chí áp dụng = 7

score = 100 × 11 / (2 × 7) = 78.6
```

Chạy lại vẫn ra **đúng 78.6** (6/7 tiêu chí là regex; chỉ BV6 có thể dao động).

---

## 6. Phần RAG

### 6.1. Dựng KB brand (offline)

```
docs/brand/corpus/*.txt
        │  src/kb/build_brand_kb.py
        │  • cắt theo ĐOẠN, giữ nguyên câu (rag-design.md mục 4.3)
        │  • thêm câu ngữ cảnh cố định vào đầu mỗi đoạn:
        │      "Trích từ bài '<title>' trên vinfastauto.com:"
        │  • nhúng bằng BGE-M3 (đã có sẵn ở src/embeddings.py, chạy local, 0đ)
        ▼
Chroma collection "kb_brand"
metadata: {sample_id, title, topic_group, content_type, langcode}
```

Câu ngữ cảnh dùng **prefix tất định**, không gọi LLM — giống hệt cách `build_kb.py` đang làm cho KB fact-check, giữ tính tất định và miễn phí.

`topic_group` đọc từ `docs/brand/corpus_index.csv` (mục 3.1), dùng cho phép đo ở mục 6.4.

**Giữ mọi đoạn, không lọc theo độ dài.** Bước bóc tách đã loại boilerplate (menu, CTA, mục lục tự sinh), nên đoạn còn lại đều là chữ tác giả. Đặt ngưỡng "đoạn phải dài hơn N câu" lúc này là thêm một số ảo; nếu phép đo ở mục 6.4 cho thấy nhiễu thì mới xử lý, có căn cứ.

**Sửa `src/retrieval.py`:**

```python
COLLECTION_FACTCHECK = "kb_factcheck"    # đổi tên từ COLLECTION
COLLECTION_BRAND = "kb_brand"            # mới

def retrieve(query, content_type, langcode, *, top_k=3,
             collection_name=COLLECTION_FACTCHECK, ...):   # ← thêm 1 tham số
```

Giá trị mặc định giữ nguyên collection cũ nên mọi lời gọi fact-check hiện có **không đổi hành vi**. Đổi tên hằng số `COLLECTION` → `COLLECTION_FACTCHECK` là cần thiết chứ không phải dọn dẹp tuỳ hứng: khi có hai collection, cái tên trần `COLLECTION` không còn nghĩa xác định.

**Ghi nhận, không sửa ở đợt này:** chuỗi `"kb_factcheck"` hiện bị chép ở **hai nơi** — `retrieval.py` và `kb/build_kb.py` đều khai báo hằng số riêng. Đây đúng dạng vấn đề `config-spec.md` mục 1 mô tả (một giá trị nằm ở nhiều bản chép tay). Nó có sẵn từ trước, không do thay đổi này gây ra, nên chỉ ghi nhận lại để xử lý cùng hạng mục config; sửa bây giờ sẽ kéo `build_kb.py` vào phạm vi mà không phục vụ mục tiêu nào của đợt này.

### 6.2. Vai trò (a) — BV6 chấm mức độ trang trọng

```
title bài đang chấm ──> truy vấn kb_brand ──> 3 đoạn cùng chủ đề
                                                     │
       body + summary bài đang chấm ─────────────────┤
                                                     ▼
                                             gọi Claude 1 lần
                                                     ▼
                                  level 0/1/2 + evidence trích nguyên văn
```

Dùng `title` làm truy vấn vì tiêu đề trên site rất mô tả (*"Hướng dẫn sạc pin ô tô điện VinFast đúng cách"*) — tín hiệu chủ đề sạch nhất và tất định. Không có title thì lùi về `summary`.

Đây là chỗ RAG làm được việc mà nhét cứng một đoạn cố định không làm được: **đoạn văn mẫu phải thay đổi theo chủ đề từng bài**.

**Chống prompt injection (Q4).** Prompt BV6 bọc nội dung bài trong thẻ có hậu tố ngẫu nhiên sinh mỗi lần gọi, kèm chỉ dẫn coi phần bên trong là dữ liệu:

```
<noi_dung_7f3a9c>
<title>…</title>
<body>…</body>
</noi_dung_7f3a9c>
```

**Không** tạo `src/prompt_builder.py` dùng chung ở đợt này — đó là hạng mục M1 áp cho cả 4 agent (`prompt-injection.md` mục 5), làm sau và khi đó rút phần này ra dùng chung.

### 6.3. Vai trò (b) — sinh bằng chứng cho 6 tiêu chí regex

Khi BV2 phát hiện bài dùng *"xe hơi điện"*:

```
truy vấn kb_brand với thuật ngữ CHUẨN ("ô tô điện")
        ▼
lấy 1 đoạn thật trong corpus dùng đúng thuật ngữ
        ▼
đính vào suggestion:
  "Dùng 'ô tô điện' thay cho 'xe hơi điện' (10/10 bài chuẩn dùng cách này).
   Ví dụ trong bài đã đăng: '…chi phí vận hành ô tô điện thấp hơn…'"
```

Miễn phí (nhúng chạy local, không gọi LLM). **Đây là phần làm RAG có giá trị vượt xa một tiêu chí** — nó phục vụ cả 7, và là câu trả lời cho phản biện *"dựng vector store cho đúng 1 tiêu chí có phải over-engineering không"* mà `rag-design.md` mục 1 đã dự đoán trước.

Đính bằng chứng **một lần cho mỗi loại lỗi**, không phải mỗi lần xuất hiện, để gợi ý không dài lê thê.

### 6.4. Đo chất lượng truy xuất trước khi nối vào agent (E2 cho KB brand)

`rag-design.md` mục 5 bắt buộc đo trước khi nối RAG vào agent. Nhưng chỉ số recall@k kiểu fact-check **không dùng được ở đây**: fact-check có đúng một chunk đúng (thông số VF 8), còn KB brand thì *nhiều đoạn cùng chủ đề đều hợp lệ* — không tồn tại "một đáp án đúng".

**Cách đo phù hợp hơn và không tốn công soạn tay:**

```
Truy vấn : title của 20 bài GOLD (đã biết thuộc nhóm chủ đề nào)
Đo       : trong top-3 trả về, bao nhiêu đoạn đến từ bài BRAND CÙNG nhóm chủ đề
Mốc so   : tỉ lệ ngẫu nhiên ≈ 2/10 bài mỗi nhóm ≈ 20%
Đạt      : cao hơn hẳn mốc ngẫu nhiên
```

Ground truth lấy sẵn từ nhóm chủ đề đã có trong `sources.md` mục 1.1–1.5, **không phải soạn 20 cặp bằng tay** như `rag-design.md` mục 5 dự kiến. Mốc so sánh 20% suy ra từ cấu trúc corpus, không phải số tự đặt.

Dùng title bài `GOLD` làm truy vấn **không gây rò rỉ**: chỉ mượn tiêu đề để đo chất lượng truy xuất, không rút quy tắc brand nào từ chúng.

### 6.5. Chi phí thêm vào

| | Trước | Sau |
|---|---|---|
| Gọi LLM mỗi bài | 5 (CQ, SEO, Compliance + fact-check trích/so sánh) | **6** (+1 cho BV6) |
| Nhúng vector | 0đ (local) | 0đ (local) |
| Dựng KB brand | — | 1 lần, ~200 đoạn, 0đ |

Tăng ~20% chi phí mỗi bài, đổi lấy việc gỡ bỏ 25 điểm giả đang bơm cho mọi bài.

---

## 7. Xử lý lỗi và tích hợp

### 7.1. Bảng suy giảm mềm

| Tình huống | BV1–BV5, BV7 | BV6 | Kết quả agent |
|---|---|---|---|
| Bình thường | chấm | chấm | điểm trên 7 tiêu chí |
| **KB brand chưa dựng** | chấm (thiếu đoạn trích làm ví dụ) | **NA** | điểm trên 6 tiêu chí |
| **LLM lỗi/timeout** | chấm | **NA** | điểm trên 6 tiêu chí |
| **`brand_rules.json` chưa có** | không có chuẩn để so | NA | **trả `None`** → Aggregator chia lại trọng số |
| Bài rỗng, mọi tiêu chí NA | NA hết | NA | **trả `None`** → Aggregator chia lại trọng số |

### 7.2. Quy tắc an toàn: hỏng hạ tầng → `NA`, không phải `0`

Khi KB chưa dựng hoặc Claude lỗi, **BV6 bị loại khỏi cả tử số lẫn mẫu số**, tuyệt đối không cho 0 điểm.

Nếu cho 0, một sự cố **của hệ thống** sẽ âm thầm kéo điểm brand của **mọi bài** xuống — biến lỗi hạ tầng thành hình phạt lên nội dung, mà không ai biết. Đây cùng một lớp lỗi dự án đã lập luận ở hai chỗ khác, và giữ nhất quán ba chỗ là điểm đáng nêu khi bảo vệ:

- CP3 fact-check: *"không tra được ≠ sai"* (`rubrics.md` mục 6.2)
- Compliance lỗi: `final_score = None` chứ không phải 0 (`architecture.md` mục 6.4)

### 7.3. Thay stub trong `graph.py`

```python
def brand_node(state: ContentReviewState) -> dict:
    try:
        result = brand_voice.run(state["fields"])
    except Exception:
        result = None      # giống 3 agent kia - Aggregator xử lý theo mục 6.4
    return {"brand_result": result}
```

Dọn phần thay đổi này tạo ra orphan:

- Xoá hàm `_stub_agent_result()` — sau khi thay thì không còn ai gọi
- Sửa docstring đầu `graph.py` (đang ghi *"Brand Voice vẫn là STUB"*)

**Aggregator, công thức trọng số, cơ chế veto, write-back: không đụng gì.**

### 7.4. Thay đổi hành vi phải lường trước

Sau thay đổi này **điểm tổng của mọi bài sẽ tụt** so với hiện tại, vì 25 điểm giả biến mất. Bài `node/7` từ 70 điểm xuống khoảng 45–50.

Đây là **đúng mục đích**, không phải hồi quy. Nhưng phải nêu rõ trong báo cáo: mọi số liệu chạy trước thay đổi này **không so trực tiếp được** với số liệu sau.

---

## 8. Kiểm thử

Theo khuôn đang dùng trong `multiagent/scripts/`: script chạy thẳng, tiêm phụ thuộc giả để không gọi LLM/KB thật, in `[PASS]/[FAIL]`, thoát mã 1 khi hỏng.

### 8.1. `test_scoring.py` — hàm tất định

| Ca kiểm | Kỳ vọng |
|---|---|
| 7 tiêu chí, tổng mức 11 | `78.6` |
| Cùng bộ `criteria` chạy 100 lần | đúng cùng một số cả 100 lần |
| 6 tiêu chí mức 2 + 1 tiêu chí **NA** | `100.0` — NA bị loại khỏi mẫu số |
| 6 tiêu chí mức 2 + 1 tiêu chí **mức 0** | `85.7` — khác hẳn ca trên |
| Tất cả NA | `None` |

Hai dòng giữa là **cặp đối chứng quan trọng nhất**: nếu ai đó lỡ code NA thành 0, hai ca này lệch nhau ngay.

### 8.2. `test_brand_guideline.py` — phần thống kê

| Ca kiểm | Kỳ vọng |
|---|---|
| Biến thể ở 10/10 bài | sinh quy tắc (p = 0,002) |
| 9/10 bài | sinh quy tắc (p = 0,021) |
| **8/10 bài** | **KHÔNG sinh quy tắc**, vào mục "chưa đủ căn cứ" |
| Biến thể **0 lần** trong corpus | vào danh sách BV7 |
| Đếm theo bài / theo số lần | ra 2 con số riêng, không lẫn nhau |

### 8.3. `test_brand_voice.py` — logic agent, KB và LLM giả

| Ca kiểm | Kỳ vọng |
|---|---|
| 3 chỗ viết `VF8` | BV1 = **0**, issue trích nguyên văn `VF8` |
| 1 chỗ viết `VF8` | BV1 = **1** |
| Viết `VF 8` đúng hết | BV1 = **2** |
| **Bài không nhắc model nào** | BV1 = **NA**, không phải 2 ← lỗi tinh vi nhất |
| KB brand lỗi | BV6 = NA, agent **vẫn trả điểm** trên 6 tiêu chí |
| LLM lỗi | BV6 = NA, agent vẫn trả điểm |
| Bài rỗng | `run()` trả **`None`** |
| Lỗi ở cả `title` và `body` | 2 issue, mỗi cái đúng `field` của nó |
| Tiêu chí mức 2 và NA | **không** sinh issue |
| Chấm cùng bài 5 lần (tắt BV6) | 5 lần đúng cùng một điểm |

Dòng cuối là **bằng chứng thực nghiệm cho luận điểm trung tâm của `rubrics.md`** — tài liệu đó tự thừa nhận ở mục 9 rằng rubric *"chưa được chứng minh bằng số liệu là ổn định hơn"*. Đây là con số đầu tiên chứng minh được, đáng đưa vào báo cáo cuối.

### 8.4. `eval_brand_retrieval.py` — đo E2 cho KB brand

Chạy riêng, cần KB thật (không phải test đơn vị). Đúng cách đo ở mục 6.4, in bảng để đưa thẳng vào báo cáo.

### 8.5. Không phá vỡ thứ đang chạy

| Kiểm tra | Vì sao |
|---|---|
| Chạy lại `test_retrieval.py` | Thêm `collection_name` không được đổi hành vi fact-check |
| Chạy lại `test_fact_check.py`, `test_aggregator_veto.py` | Không đụng phải Compliance/Aggregator |
| `smoke_test_graph.py` trên node thật | Pipeline 8 node vẫn chạy end-to-end, ghi ngược Drupal thành công |

Ở smoke test, **kỳ vọng điểm tổng tụt xuống** so với lần chạy trước (mục 7.4) — nếu điểm *không* đổi thì stub chưa thực sự bị thay.

---

## 9. Ảnh hưởng lên code

| File | Thay đổi |
|---|---|
| `docs/brand/raw_html/B-001…010.html` *(mới)* | Người thu tay, ~15–20 phút |
| `docs/brand/corpus/*.txt` *(mới)* | Script sinh |
| `docs/brand/corpus_index.csv` *(mới)* | Manifest `sample_id → source_url → topic_group`, người soạn |
| `docs/brand/variant_candidates.json` *(mới)* | Danh sách ứng viên biến thể (3 nhóm), người soạn |
| `docs/brand/brand_guideline.md` *(mới)* | Script sinh — bản cho người đọc |
| `multiagent/scripts/extract_brand_corpus.py` *(mới)* | Import hàm bóc tách từ `extract_gold_sample.py`, ghi sang thư mục brand |
| `multiagent/scripts/build_brand_guideline.py` *(mới)* | Thống kê + kiểm định nhị thức → sinh 2 file đầu ra |
| `multiagent/src/agents/brand_rules.json` *(mới)* | Script sinh — bản cho máy đọc |
| `multiagent/src/agents/brand_voice.py` *(mới)* | Agent: 6 tiêu chí regex + BV6 (LLM+RAG) |
| `multiagent/src/scoring.py` *(mới)* | `score_from_criteria()` |
| `multiagent/src/kb/build_brand_kb.py` *(mới)* | Cắt đoạn → nhúng → Chroma `kb_brand` |
| `multiagent/src/retrieval.py` | Thêm tham số `collection_name` (mặc định giữ hành vi cũ) |
| `multiagent/src/graph.py` | `brand_node` gọi agent thật; xoá `_stub_agent_result()`; sửa docstring |
| `multiagent/scripts/test_scoring.py`, `test_brand_guideline.py`, `test_brand_voice.py`, `eval_brand_retrieval.py` *(mới)* | Mục 8 |

**Không thay đổi:** kiến trúc 8 node, Aggregator, công thức trọng số, cơ chế veto, `write_back()`, `state.py`, 3 agent hiện có.

### 9.1. Đồng bộ tài liệu

Xong phần này thì các chỗ sau đang nói sai sự thật, phải sửa cùng lúc:

| Tài liệu | Chỗ cần sửa |
|---|---|
| `README.md` | Checklist Sprint 2 — tick Brand Voice Agent |
| `docs/architecture.md` mục 5.3 | Trạng thái Brand Voice (đang ghi là stub) |
| `docs/evaluation-plan.md` mục 3 + 4.5 | Điểm chặn số 4 "Brand Voice thật chặn E5" — đã gỡ |
| `docs/rag-design.md` mục 4.1, 8 | Trạng thái KB brand — đã triển khai |
| `docs/rubrics.md` mục 8 | BV1–BV7 + `scoring.py` đã vào code; 3 agent kia chưa |
| `docs/goldset/sources.md` mục 1.6 | Đánh dấu 10 URL `BRAND` đã thu |

---

## 10. Thứ tự triển khai

Hai giai đoạn, giai đoạn 1 tự nó đã chạy được:

**Giai đoạn 1 — gỡ stub (không cần KB, không cần LLM)**

1. Thu 10 bài `BRAND` + soạn `corpus_index.csv` → `extract_brand_corpus.py` → corpus
2. `variant_candidates.json` + `build_brand_guideline.py` → guideline + rules
3. `scoring.py` + `test_scoring.py`
4. `brand_voice.py` với 6 tiêu chí regex (BV6 tạm luôn trả NA) + `test_brand_voice.py`
5. Thay stub trong `graph.py` → **25 điểm giả biến mất, E5 hết bị chặn**

**Giai đoạn 2 — phần RAG**

6. `build_brand_kb.py` + sửa `retrieval.py`
7. `eval_brand_retrieval.py` → đo E2 **trước** khi nối vào agent (`rag-design.md` mục 5)
8. BV6 thật + vai trò (b) đính bằng chứng
9. Smoke test end-to-end + đồng bộ tài liệu (mục 9.1)

---

## 11. Chưa chốt / cần đo

| Hạng mục | Quyết bằng gì |
|---|---|
| Có phải thu thêm 10 URL `BRAND` không | Kiểm định ở mục 4.3: có quy ước nào rơi vào 7/10–8/10 không |
| Danh sách ứng viên biến thể đã đủ chưa | Đọc corpus lúc soạn `variant_candidates.json`; bổ sung được về sau mà không phải nhúng lại KB |
| Ngưỡng đếm trong rubric (3 chỗ sai, 2 kiểu xưng hô) | Calibration Sprint 3 — hiện lấy nguyên `rubrics.md` mục 5, là giá trị tạm |
| Cần lọc đoạn quá ngắn khỏi KB brand không | Chỉ xử lý nếu phép đo mục 6.4 cho thấy nhiễu |
| BV6 có ổn định không | Chạy lại nhiều lần trên cùng bài, đo tỉ lệ mức trùng nhau (biến thể của E1) |
| Rubric có thật sự ổn định hơn thang 0-100 không | Test ở mục 8.3 dòng cuối cho số liệu đầu tiên; kết luận đầy đủ cần E1 trên 3 agent kia |
