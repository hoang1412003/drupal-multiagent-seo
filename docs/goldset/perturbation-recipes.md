# Công thức tạo bài perturbation

**Dùng cùng:** `docs/goldset/annotation-guideline.md` v1.1 mục 10 (quy tắc tạo bài perturbation)
**Phân công cụ thể:** cột `injected_codes` trong `docs/goldset/labels.csv`

Mục đích của tài liệu này: biến việc tạo 13 bản chèn lỗi từ *phải nghĩ* thành *thao tác máy móc*. Mỗi mã lỗi có một công thức và một mẫu câu sẵn.

---

## 0. Trước khi chèn - hai bước bắt buộc

1. **Kiểm tra bài gốc không sẵn có lỗi nhóm A.** Nếu có, bài gốc đã là `rejected`, chèn thêm không tạo tín hiệu gì mới → đổi bài khác (guideline mục 10.2).
2. **Chạy `label_helper.py` trên bài gốc** để biết bài đã sẵn có mã B nào. Ground truth của bản perturbation = `injected_codes` **cộng** các lỗi sẵn có, áp quy tắc mục 5 của guideline - không phải chỉ mã chèn vào.

Nguyên tắc chung: **chèn tối thiểu, không sửa gì khác.** Thêm 1-2 câu hoặc đổi đúng một trường. Viết lại cả đoạn sẽ làm ground truth mất kiểm soát.

---

## 1. Nhóm A - lỗi chặn (bản perturbation thành `rejected`)

### A1 - Claim tuyệt đối, so sánh nhất
Chèn một câu vào cuối đoạn mở đầu:

> *"VinFast là thương hiệu xe điện **số 1** Việt Nam với công nghệ pin **tốt nhất** thị trường hiện nay."*

Biến thể dùng được: "duy nhất", "hàng đầu", "nhất Việt Nam". Căn cứ: Luật Quảng cáo 2012.

### A2 - So sánh trực tiếp hơn hẳn đối thủ cụ thể
Chèn vào đoạn so sánh (chọn bài vốn đã có nội dung so sánh để câu chèn không lạc lõng):

> *"So với **Tesla Model 3** và **BYD Atto 3**, xe điện VinFast vận hành êm hơn hẳn và chi phí bảo dưỡng thấp hơn rõ rệt."*

Phải nêu **tên đối thủ cụ thể** - so sánh chung chung với "xe xăng" không phải A2. Căn cứ: Luật Cạnh tranh 2018.

### A3 - Số liệu sai lệch so với thông số công bố
Tìm một con số thật trong bài, đổi thành số **sai rõ ràng** so với `docs/goldset/sources.md` mục 2.1:

| Đúng (công bố) | Đổi thành |
|---|---|
| VF 9: 438km (Eco) | **550km** |
| VF 8: 420km (Eco) | **500km** |
| VF 5: 326km (NEDC) | **400km** |
| Bảo dưỡng mỗi 12.000km | **mỗi 30.000km** |

Ghi lại số gốc vào cột `notes` để đối chiếu về sau. **Đây là mã quan trọng nhất trong toàn bộ perturbation** - nó là thứ duy nhất kiểm tra được RAG fact-check (CP3) có hoạt động không.

### A4 - Khuyến mại thiếu thời hạn hoặc điều kiện
Chèn một khối ưu đãi nêu giá trị nhưng không nói thời hạn:

> *"Nhân dịp ra mắt, VinFast **giảm ngay 200 triệu đồng** cho khách hàng đặt cọc sớm."*

Không được thêm "áp dụng đến ngày…" hay "số lượng có hạn" - thiếu chính là lỗi. Căn cứ: Luật Thương mại.

### A5, A6 - không dùng
**A5** (lạc đề >50%) đòi viết lại phần lớn bài, phá nguyên tắc "chèn tối thiểu". **A6** (hướng dẫn gây mất an toàn) là nội dung có thể gây hại thật nếu file rò ra ngoài. Cả hai đã có khả năng xuất hiện tự nhiên trong tập `GOLD`; không chèn nhân tạo.

---

## 2. Nhóm B - lỗi sửa tại chỗ (bản perturbation thành `needs_revision`)

Chỉ áp dụng khi bài gốc **không** dính mã A nào - nếu không, nhãn vẫn là `rejected` và mã B chèn vào không kiểm tra được gì.

### B1 - Claim tầm hoạt động thiếu điều kiện đo
Tìm câu có số km, **xoá phần điều kiện đo** (giữ nguyên con số - đó là điểm phân biệt với A3):

| Trước | Sau |
|---|---|
| "đi được 326km theo chuẩn NEDC" | "đi được 326km" |
| "420km (điều kiện lý tưởng)" | "420km" |

### B2 - Claim thời gian sạc thiếu loại trụ / dải phần trăm

| Trước | Sau |
|---|---|
| "sạc từ 10-70% trong 30 phút với trụ sạc nhanh" | "sạc đầy trong 30 phút" |

### B3 - Thiếu meta description
Để trống trường `meta_description` trong file mẫu. **Lưu ý:** để trống nghĩa là "đã kiểm tra và không có"; nếu chưa thu thì ghi `?` (xem hướng dẫn đầu `label_helper.py`).

### B4 - Tiêu đề sai quy ước
Chọn **một** trong ba, không làm cả ba:
- Viết hoa toàn bộ tiêu đề
- Kéo dài tiêu đề vượt 70 ký tự (thêm cụm thừa)
- Gắn năm cũ: thêm " 2024" vào cuối

### B5 - Sai thuật ngữ, tên model, xưng hô
Tìm-thay toàn bài, chọn **một** loại:
- `VF 8` → `VF8` (bỏ dấu cách, ít nhất 3 chỗ)
- `ô tô điện` → `xe hơi điện` (ít nhất 3 chỗ)
- Đổi xưng hô ở nửa sau bài để tạo lẫn lộn trong cùng bài

### B6 - Thiếu alt text
Để trống trường `image_alt`.

### B7 - Slug lỗi
Đổi `url_alias` thành bản **còn dấu tiếng Việt**: `/vn_vi/huong-dan-sac-pin` → `/vn_vi/hướng-dẫn-sạc-pin`

### B9 - Câu và đoạn quá dài
Gộp 3 câu ngắn liền nhau thành một câu dài bằng "và", "đồng thời", "bên cạnh đó". Cần **ít nhất 3 câu** vượt 30 từ mới đạt ngưỡng - chạy `label_helper.py` để xác nhận trước khi chốt.

### B10 - Số liệu không nguồn
Chèn một câu có số liệu thống kê không dẫn nguồn:

> *"Khoảng **90% người dùng** hài lòng với trải nghiệm sạc tại trạm VinFast."*

### B8 - không chèn
Cố ý gài lỗi chính tả tạo ra dữ liệu bẩn khó kiểm soát và khó tái lập chính xác. Lỗi chính tả xuất hiện tự nhiên trong tập `GOLD` là đủ.

---

## 3. Quy trình cho mỗi bản perturbation

```
1. Đọc labels.csv → lấy injected_codes của sample_id
2. Copy bài gốc từ tập PERT sang file mới docs/goldset/raw/<sample_id>.txt
3. Chạy label_helper.py trên BÀI GỐC → ghi lại các mã B sẵn có
4. Áp công thức ở trên cho từng mã trong injected_codes
5. Chạy lại label_helper.py trên bản đã chèn → xác nhận mã máy đo được
   đã xuất hiện (với các mã máy đo được: B3, B4, B6, B7, B9)
6. Ground truth = injected_codes + mã sẵn có ở bước 3, áp quy tắc guideline
   mục 5. Điền vào defect_codes và label
7. Ghi vào notes: đã đổi gì, số gốc là bao nhiêu (với A3)
```

Bước 5 chỉ xác nhận được các mã **máy đo được**. Các mã còn lại (A1-A4, B1, B2, B5, B10) tự bạn xác nhận bằng mắt - nhưng vì chính bạn chèn vào nên ground truth chắc chắn.

---

## 4. Giới hạn phải nêu trong báo cáo

Lỗi perturbation do **chính tác giả chèn vào**, và cũng chính tác giả viết rule Compliance. Agent bắt được lỗi mình tự chèn **không chứng minh được năng lực tổng quát hoá**. Vì vậy Sprint 3 phải **tách riêng chỉ số trên bài thật và trên bài perturbation**, không gộp chung (guideline mục 10.6).

Con số đáng tin hơn là chỉ số trên 20 bài thật; con số trên bài perturbation chủ yếu để xác nhận hệ thống **có bắt được** các loại lỗi hiếm, chứ không phải để chứng minh độ chính xác.
