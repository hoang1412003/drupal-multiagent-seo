# Điều tra CP1 và BV3 — hai lỗ hổng detector, chẩn đoán bằng $0

Chạy ngày 2026-08-19, **không gọi LLM, không sửa code, chi phí $0**.

Hai câu hỏi độc lập, cùng một phương pháp: chạy thẳng detector tất định trên
dữ liệu có sẵn rồi đối chiếu với nhãn.

1. **CP1** — vì sao `gold_rejected_recall = 0,60` không đạt, và sửa có lợi không?
2. **BV3** — vì sao `corrected_publish` chỉ 19/30?

**Kết luận ngắn: CP1 bỏ sót thật nhưng KHÔNG nên sửa (đã định lượng: chỉ cứu
được 1 trong 2 bài, không mở được cổng). BV3 thì mâu thuẫn với chính brand
guideline của dự án và là nguyên nhân chặn nhiều nhất ở Corrected v2.**

---

## Phần 1 — CP1 bỏ sót claim so sánh tuyệt đối

### 1.1. Hiện trạng

Bốn bài kéo `rejected_recall` xuống 0,60 chia hai nhóm khác hẳn nhau:

| Bài | Nguyên nhân | Sửa được? |
|---|---|---|
| `P-004b`, `P-010a` | có finding `A4`, mà `A4` đã **cố ý hạ xuống nhóm B** ngày 18/8 để chữa dao động E1 (`decision_consistency` 0,86 → 0,96) | Không — là cái giá đã chấp nhận |
| `G-011`, `G-020` | thiếu finding `A1` — `CP1` không phát hiện được | Cần điều tra |

### 1.2. CP1 nhìn thấy gì trên `G-011` và `G-020`

Chạy trực tiếp `compliance._cp1_claim_tuyet_doi()`:

```
G-011  (nhãn người: rejected, lý do A1)   CP1 level = 2 (sạch)   0 lần khớp
G-020  (nhãn người: rejected, lý do A1)   CP1 level = 2 (sạch)   0 lần khớp
```

Trong khi nội dung thật chứa:

| Bài | Câu vi phạm | Có nêu phạm vi? |
|---|---|---|
| `G-011` | *"ưu đãi **có một không hai** … **không có ở bất kì loại xe điện hãng khác trên thị trường**"* | ✅ "trên thị trường" |
| `G-020` | *"mẫu xe được **săn đón nhất thị trường** xe xanh"* | ✅ "thị trường" |

Cả hai đúng định nghĩa mức 0 của chính CP1 (claim so sánh tuyệt đối **có** nêu
phạm vi so sánh). Đây là **bỏ sót thật (false negative)**, không phải nhãn khắt khe.

### 1.3. Nghi ngờ ban đầu về nợ B12 là SAI

Giả thuyết đầu tiên: bản sửa B12 (2026-08-10, phân biệt claim quảng cáo với
cách nói thông thường) đã nới tay quá đà. **Bác bỏ** — cơ chế phân biệt của
B12 thậm chí không được gọi tới, vì blacklist không khớp gì cả.

Nguyên nhân thật nằm chỗ khác: `CP1` nhận diện so sánh tuyệt đối bằng một
**danh sách cụm từ đóng** (`tốt nhất`, `số 1`, `duy nhất`, `đi xa nhất`…), mà
tiếng Việt tạo so sánh nhất bằng **cấu trúc ngữ pháp** — bất kỳ tính từ nào
ghép với "nhất". Mọi danh sách đóng đều sẽ bỏ sót; đây là **giới hạn cấu trúc**,
không phải thiếu vài từ.

### 1.4. Thử quy tắc tổng quát trên toàn corpus 79 bài

Ba biến thể, đo trên bốn tập:

- **R1** — mọi `<từ> nhất`
- **R2** — R1 trừ các cụm "nhất" mang nghĩa ngữ pháp (`thứ nhất`, `nhất quán`,
  `nhất định`, `thống nhất`…)
- **R3** — R2 **và** đòi hỏi có cụm chỉ phạm vi ở gần (dùng chính
  `compliance._co_pham_vi`)

| Tập | Số bài | R1 | R2 | **R3** |
|---|---|---|---|---|
| GOLD (có nhãn) | 33 | 30 bài / 123 lần | 29 / 106 | **5 bài / 5 lần** |
| BRAND (đã publish thật) | 16 | 14 / 63 | 14 / 55 | **2 bài / 2 lần** |
| CLEAN (expected publish) | 10 | 0 | 0 | **0** |
| GOLD-CORRECTED | 20 | 9 / 14 | 8 / 10 | **0** |

R3 rất chọn lọc: **0 lần khớp trên 30 bài sạch** (clean + gold-corrected).

### 1.5. Nhưng tác động ròng trên gold set là hoà

Blacklist hiện tại đã bắt sẵn `G-010`, nên chỉ ba bài thực sự đổi:

| Bài | Nhãn người | Có `A1` thật? | R3 bắt | Kết luận |
|---|---|---|---|---|
| `G-020` | rejected | ✅ | ✅ | **cứu đúng** |
| `G-017` | needs_revision | ❌ (`B4;B3`) | ✅ | **bắt oan** |
| `G-011` | rejected | ✅ | ❌ | **vẫn sót** |

- `G-011` sót vì *"có một không hai"* không chứa chữ "nhất".
- `G-017` bị oan vì *"khu vực có nền kinh tế phát triển **nhất cả nước**"* —
  nói về kinh tế miền Nam, không phải claim quảng cáo sản phẩm. Phân biệt được
  điều này cần LLM, mà đưa LLM vào nhóm A đúng là thứ vừa phải gỡ bỏ khi hạ A6/A4.

Tính lại hai cổng:

| Cổng | Hiện tại | Nếu áp R3 | Ngưỡng | |
|---|---|---|---|---|
| `rejected_recall` | 0,60 (6/10) | **0,70** (7/10) | ≥ 0,80 | ❌ vẫn trượt |
| `needs_revision_recall` | 0,957 (22/23) | 0,913 (21/23) | ≥ 0,80 | ✅ vẫn đạt |

### 1.6. Thêm tín hiệu: R3 chặn oan bài VinFast đã publish

| Bài | Câu bị bắt |
|---|---|
| `B-007` | *"**một trong những** dòng xe máy điện cao cấp **nhất trên thị trường**"* |
| `B-012` | *"**một trong những** tiêu chuẩn ngăn bụi và nước cao **nhất trên thị trường**"* |

Cấu trúc "một trong những X nhất" **làm dịu** claim, không khẳng định độc tôn.
Quy tắc R3 gộp nó chung với khẳng định độc tôn — đúng **bẫy số 2** của dự án
(*"một bộ so khớp gộp hai thứ khác nhau"*).

Khác bốn lần trước, lần này bẫy **bị chặn trước khi vào code**: R3 chỉ tồn tại
như một quy tắc đề xuất và bị loại bỏ ngay ở bước rà $0. Bốn lần trước
(B12/BV3/B14/B15) đều lọt qua unit test rồi mới lộ trên dữ liệu thật — vì test
dùng ví dụ do chính người viết code nghĩ ra. Đây là bằng chứng cho thấy **rà
trên corpus thật trước khi sửa** là cách duy nhất bắt được loại lỗi này.

### 1.7. Quyết định: KHÔNG sửa CP1

Bỏ ~$5,3 đo lại E1 và Gold để đưa một cổng từ 0,60 lên 0,70 (**vẫn trượt**),
kèm rủi ro chặn oan bài đã publish — không có lợi.

Cách duy nhất chạm 0,80 là thêm cụm `"có một không hai"` vào blacklist, tức
**viết luật cho đúng hai bài đang làm trượt phép đo rồi đo lại trên chính chúng**.
Con số thu được sẽ đẹp và vô nghĩa: đó là rò rỉ dữ liệu, và không phát biểu
được lý do nào mà không nhắc tới phân bố — trượt thẳng **phép thử chống bẫy số 1**
của dự án.

Ghi nhận `rejected_recall = 0,60` là **giới hạn đã định lượng**. Cả 4 bài vẫn
bị chặn xuất bản (`needs_revision`), `false_publish = 0/33`: sai ở *mức độ chặn*,
không phải *để lọt*.

---

## Phần 2 — BV3 mâu thuẫn với brand guideline của chính dự án

### 2.1. Phát hiện

`B5` (nguồn `brand.BV3`) là mã chặn nhiều nhất ở Corrected v2: **5/11 bài**.
Bằng chứng ở `C-005` — một bài **`clean`, lẽ ra sạch tuyệt đối**:

```
[B5] brand.BV3  field=body  evidence: 'khách hàng'
[B5] brand.BV3  field=body  evidence: 'người dùng'
     → "Bài lẫn 2 kiểu xưng hô (khách hàng, người dùng) - chọn một kiểu duy nhất"
```

### 2.2. Đối chiếu ba nguồn trong chính repo

| Nguồn | Nội dung |
|---|---|
| `docs/brand/brand_guideline.md:29` | *"**Chưa đủ căn cứ để chốt xưng hô chuẩn.**"* — corpus 16 bài chia phiếu `người dùng` 8 / `bạn` 4 / `khách hàng` 3 / `quý khách` 1, nên `BV4` luôn trả `NA` |
| `docs/rubrics.md:158` | `BV3` "Xưng hô nhất quán trong bài": lẫn 2 cách → mức 1 → ánh xạ `B5` → **chặn publish** |
| `docs/technical-debt.md`, mục "Ba cái bẫy" | **`BV3` đã được ghi nhận** là một trong bốn lần dính bẫy *"một bộ so khớp gộp hai thứ khác nhau: xưng hô vs danh từ chỉ người"* |

Ở `C-006`, câu bị bắt là *"**Người dùng** nên kiểm tra hợp đồng…"* — đây là
danh từ chỉ đối tượng, không phải xưng hô trực tiếp với người đọc như
`bạn`/`quý khách`.

### 2.3. Nhận định

Hệ thống đang chặn xuất bản vì thiếu nhất quán ở một chiều mà **chính dữ liệu
của thương hiệu chứng minh là không có chuẩn để nhất quán theo**. Và bộ so khớp
của BV3 vẫn đang gộp "xưng hô" với "danh từ chỉ người" — đúng cái bẫy đã được
ghi trong tài liệu nhưng chưa xử lý.

**Chưa sửa trong phiên này.** BV3 nằm trên đường chấm điểm; đụng vào là làm mất
hiệu lực cả E1 v2 lẫn Gold v2 vừa đo. Ghi nhận thành nợ để xử lý thành một đợt
riêng, cùng lúc với các thay đổi score-path khác nếu có.

---

## Script tái lập (chạy từ `multiagent/`, $0)

```python
import sys
from pathlib import Path
REPO = Path(r"D:\drupal-multiagent-seo")
SRC = REPO / "multiagent" / "src"
sys.path[:0] = [str(SRC), str(SRC / "agents")]
from agents import compliance

def doc_mau(ma):
    raw = (REPO/"docs/goldset/raw"/f"{ma}.txt").read_text(encoding="utf-8")
    dau, _, than = raw.partition("\n---\n")
    f = {}
    for d in dau.splitlines():
        if ":" in d:
            k, _, v = d.partition(":")
            f[k.strip()] = v.strip()
    return {"title": f.get("title",""), "body": than,
            "meta_description": f.get("meta_description","")}

for ma in ("G-011", "G-020", "G-017", "G-010"):
    kq = compliance._cp1_claim_tuyet_doi(doc_mau(ma))
    print(ma, "CP1 level =", kq["level"], "| so khop =", len(kq["occurrences"]))
```

Quy tắc R3 dùng để rà corpus:

```python
import re
R1 = re.compile(r"\b([\w]+)\s+nhất\b", re.UNICODE | re.IGNORECASE)
SAU_NHAT_NGU_PHAP = {"quán","định","thiết","loạt","thời","là","cử","tề","trí"}
TRUOC_NHAT_KHONG_SS = {"thứ","duy","đồng","hợp","thống","đơn","nhất","số"}

def r3(text):
    out = []
    for m in R1.finditer(text):
        if m.group(1).lower() in TRUOC_NHAT_KHONG_SS:
            continue
        sau = text[m.end():m.end()+15].strip().split()
        if sau and sau[0].lower().strip(".,;:") in SAU_NHAT_NGU_PHAP:
            continue
        if compliance._co_pham_vi(text, m.start(), m.end()):
            out.append(m)
    return out
```
