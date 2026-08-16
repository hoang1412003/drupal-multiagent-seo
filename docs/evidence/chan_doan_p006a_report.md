# Chẩn đoán P-006a — vì sao vẫn bị gắn `critical` sau chốt CP4

Chạy 2026-08-16, **$0,044**, chấm lại đúng một bài với `cham_mot_bai(giu_chi_tiet=True)`.
Số liệu thô: [`chan_doan_p006a.json`](chan_doan_p006a.json). `prompt_version` `020738e209017213`.

## Câu hỏi

`technical-debt.md` mục B14 (dòng 476) nêu **đúng câu này** làm ví dụ CP4 báo oan:

> *CP4 mắc lỗi cùng họ: gắn cờ "khuyến mại thiếu thời hạn" cho câu **có** thời hạn ngay trong
> trích dẫn (…, **"Trước 6/4/2022"**)*

Mục 8.4 tuyên bố đã sửa. Nhưng E5 bản 4 cho thấy P-006a **vẫn** `critical`. Vì sao?

## Kết luận: chốt chặn thời hạn CHẠY ĐÚNG — cờ đến từ vế còn lại

CP4 ghép hai vế (`compliance._chot_cp4`): **LLM** chấm *điều kiện áp dụng*, **code** kiểm
*thời hạn*. Thiếu vế nào cũng ra mức 0 → `critical`.

**Vế code — đạt.** Kiểm trực tiếp regex `_CP4_MOC_THOI_HAN` trên chính câu đó:

| Đầu vào | Nhận ra mốc thời hạn? |
|---|---|
| `"Trước 6/4/2022"` | ✅ khớp `trước 6/4/2022` |
| `"6/4/2022"` | ✅ |
| `_cp4_co_thoi_han()` với evidence là cả câu | ✅ `True` |
| … với evidence là mệnh đề khuyến mại (không có ngày) | ✅ `True` — cửa sổ 240 ký tự bắt được |

**Vế LLM — trượt.** Nhánh `muc in (0, 1)` của `_chot_cp4` được kích hoạt. Lý do do chính LLM
viết ra:

> *"Bài nêu giá trị cụ thể khuyến mại (250 triệu đồng) nhưng thiếu điều kiện áp dụng chi tiết.
> **Chỉ nêu thời hạn (trước 6/4/2022)** và sản phẩm (VF 8, VF 9) mà không rõ điều kiện cụ thể
> để nhận ưu đãi này (ví dụ: mức cọc tối thiểu, điều kiện khác)."*

LLM **tự xác nhận thời hạn có mặt**. Nó chặn vì cho rằng *điều kiện áp dụng* chưa đủ chi tiết.

## Ý nghĩa cho mục 8.4

**Chốt CP4 đã sửa đúng thứ nó nhắm tới** — vế thời hạn nay tất định và chạy đúng, G-008 đã hết
báo oan. Nhưng **kết quả người dùng nhìn thấy ở P-006a không đổi**: cùng một câu, vẫn `critical`,
chỉ khác lý do.

Đó là điều mục 8.4 chưa nói. Phát biểu đúng phải là: *"CP4 vế thời hạn đã tất định hoá và hết
báo oan; vế điều kiện vẫn là phán đoán thuần LLM và vẫn có thể sinh `critical`."*

## Vấn đề cấu trúc phía sau

Dự án đã làm **severity** tất định (`scoring.severity_for` tra bảng theo mã tiêu chí) vì
*"`critical` là thứ kích hoạt quyền phủ quyết"*. Nhưng với CP4, **mức** của vế điều kiện vẫn do
LLM quyết, và mức 0 → `critical` → chặn xuất bản.

Nói cách khác: đã khoá được *"LLM không được tự chọn severity"*, nhưng chưa khoá
*"LLM không được một mình đẩy bài sang trạng thái bị chặn"*.

Và ở đây LLM **bất đồng với người gán nhãn**, không phải bịa: người gán P-006a là
`needs_revision` với `defect_codes = B10`, tức **không** ghi A4 (*khuyến mại thiếu thời hạn hoặc
điều kiện*). Người coi *"đặt cọc VF 8/VF 9"* là điều kiện đủ rõ; LLM thì không. Đây là bất đồng
phán đoán trên một khái niệm mờ, đúng chỗ mà một chốt chặn tất định chưa với tới được.

## 🆕 Phát hiện phụ: CP5 khớp mọi con số có `km` (chưa từng ghi nhận)

Cùng bài, CP5 nổ **12 cờ**. Đối chiếu ngữ cảnh trong bài gốc:

| Đoạn khớp | Thực chất là gì |
|---|---|
| `13,4 kWh/100km` | **mức tiêu thụ điện** |
| `7,8 lít/100km` | **mức tiêu hao xăng** |
| `chi phí … trong 1km` | **chi phí mỗi km** |
| `2,5 lít xăng cho quãng đường 100km` | mức tiêu hao |
| `quãng đường di chuyển 80km` | ✅ đúng là quãng đường |

Nguyên nhân — `compliance_analysis.claim_tam_hoat_dong()`:

```python
_KM = re.compile(_SO + r"\s*(?:km|ki-?lô-?mét)\b", re.IGNORECASE)

def claim_tam_hoat_dong(text_theo_field):
    return _tim(_KM, text_theo_field)      # KHÔNG kiểm ngữ cảnh
```

So với CP6 ngay bên dưới, vốn **có** kiểm ngữ cảnh — chỉ nhận mốc thời gian khi có chữ `"sạc"`
trong bán kính 120 ký tự. **CP6 biết ngữ cảnh, CP5 thì không.**

Đây là **lần thứ tư** của cái bẫy dự án đã ghi thành mục riêng (*"một bộ so khớp gộp hai thứ
khác nhau"* — B12, BV3, B14). B14 sửa đúng lỗi này **nhưng chỉ cho CP3**; CP5 dùng bộ khớp
riêng và không được đụng tới.

### Ảnh hưởng đo được

| Kịch bản | Điểm Compliance của P-006a |
|---|---|
| Hiện tại (CP5 mức 0) | **42,9** |
| Nếu CP5 là NA (không áp dụng) | 50,0 |
| Nếu CP5 đạt mức 2 | 57,1 |

CP5 báo oan làm mất **7–14 điểm** Compliance, tức **2–4 điểm** `final_score` (trọng số 0,30).
Không phải thứ quyết định nhãn của P-006a (cờ `critical` của CP4 mới quyết), nhưng nó bóp méo
điểm trên **mọi** bài so sánh chi phí vận hành — loại bài đầy `kWh/100km` và `đồng/km`.

Ngoài ra 12 cờ trùng lặp trên **một** bài là nhiễu nặng cho người soạn bài trong giao diện.

## Không được sửa ngay

Cả hai đều nằm trong **đường chấm điểm** (`agents/compliance.py`, `compliance_analysis.py`).
Sửa bây giờ **làm mất hiệu lực E1/E5/E6 vừa chạy** (`evaluation-plan.md` mục 3a).

Hai việc phải ghi vào backlog, kèm cách sửa đã có tiền lệ:

1. **CP5 cần cổng ngữ cảnh** — sao chép đúng cách CP6 làm: chỉ nhận số có `km` khi gần đó có
   từ chỉ tầm hoạt động (*"quãng đường"*, *"đi được"*, *"tầm hoạt động"*, *"sau một lần sạc"*),
   và loại trừ mẫu tỉ lệ (`/100km`, `đồng/km`, `lít/100km`, `kWh/100km`).
2. **CP4 vế điều kiện** — quyết định xem một phán đoán thuần LLM có được phép một mình sinh
   `critical` hay không. Đây cùng họ câu hỏi với *"có nên thêm cổng bất-kỳ-tiêu-chí-mức-0"* đã
   nêu ở báo cáo functional-clean; nên gộp lại thành một quyết định thiết kế cho mentor.

⚠️ **Chỉ dựa trên một bài.** Muốn biết CP5 bóp méo điểm trên bao nhiêu bài thì phải chấm lại
với `giu_chi_tiet=True` — từ 2026-08-16 hàm đó đã giữ flag nên không mất dữ liệu chẩn đoán nữa.
