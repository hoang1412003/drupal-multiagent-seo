# Nguồn dữ liệu thật từ vinfastauto.com

Danh sách URL thật thu thập từ nguồn công khai, dùng để (1) xây gold set và (2) làm knowledge base cho fact-check. Toàn bộ là nội dung công khai, không có tài liệu nội bộ VF O2O.

**Cách dùng:** site có WAF chặn bot (HTTP 403), nên thu thủ công - mở từng URL, copy nội dung phần thân bài (bỏ header/footer/khối CTA cuối bài - xem architecture.md mục 8.2), lưu lại kèm gán nhãn. Việc đọc từng bài để gán nhãn là bắt buộc, nên thu thủ công không phát sinh chi phí thừa.

Danh sách này là **ứng viên**, chưa phải gold set cuối. Mục tiêu chốt 30-50 mẫu: ~60% giữ nguyên (nhãn theo chất lượng thật) + ~40% chèn lỗi có chủ đích (perturbation, ground truth biết trước).

---

## 1. Bài cẩm nang - ứng viên gold set

### 1.1. Lái xe / sử dụng / an toàn
- [ ] /vn_vi/cach-lai-xe-o-to-dien
- [ ] /vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai
- [ ] /vn_vi/cach-cham-soc-xe-dien-vf-e34
- [ ] /vn_vi/cham-soc-xe-dien-vao-thoi-tiet-hanh-kho
- [ ] /vn_vi/huong-dan-cach-di-xe-may-dien-an-toan-va-cach-tang-tuoi-tho-cho-xe
- [ ] /vn_vi/cach-khoi-dong-xe-may-dien-vinfast
- [ ] /vn_vi/dinh-nghia-den-projector-la-gi

### 1.2. Sạc & pin
- [ ] /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
- [ ] /vn_vi/huong-dan-cach-sac-xe-dien-khong-chai-pin
- [ ] /vn_vi/nhung-kien-thuc-co-ban-ve-sac-xe-o-to-dien-can-biet
- [ ] /vn_vi/thoi-gian-sac-day-xe-may-dien-vinfast-bao-lau
- [ ] /vn_vi/cach-de-xe-dien-lau-het-pin-moi-nhat
- [ ] /vn_vi/sac-nhanh-o-to-dien-co-anh-huong-den-kha-nang-van-hanh-cua-xe-khong
- [ ] /vn_vi/cac-loai-pin-xe-may-dien-vinfast-dac-diem-gia-cach-su-dung
- [ ] /vn_vi/khi-nao-nen-sac-pin-xe-dien
- [ ] /vn_vi/xe-dien-sac-bao-lau-thi-day
- [ ] /vn_vi/luu-y-su-dung-doi-voi-pin-cell-lfp-gotion
- [ ] /vn_vi/tim-hieu-cac-loai-pin-o-to-dien
- [ ] /vn_vi/cach-sac-pin-xe-may-dien-vinfast
- [ ] /vn_vi/huong-dan-dich-vu-sac-o-to-dien-vinfast

### 1.3. Bảo dưỡng & chi phí
- [ ] /vn_vi/bao-duong-o-to-dien
- [ ] /vn_vi/nguyen-tac-va-chi-phi-bao-duong-xe-may-dien-vinfast
- [ ] /vn_vi/chi-phi-su-dung-xe-dien
- [ ] /vn_vi/so-sanh-chi-phi-van-hanh-xe-dien-va-xe-xang
- [ ] /vn_vi/so-sanh-xe-may-dien-va-xe-may-xang-chi-phi-su-dung
- [ ] /vn_vi/nuoi-o-to-dien-vinfast-vf-e34-co-re-hon-xe-xang
- [ ] /vn_vi/chi-phi-nuoi-xe-vf-e34-hang-thang-tiet-kiem-bao-nhieu
- [ ] /vn_vi/o-to-dien-va-o-to-xang-co-gi-khac-nhau
- [ ] /vn_vi/chi-phi-su-dung-o-to-hang-thang-can-biet
- [ ] /vn_vi/co-nen-mua-o-to-thoi-diem-nay
- [ ] /vn_vi/so-sanh-chi-phi-bao-duong-o-to-dien-va-o-to-xang
- [ ] /vn_vi/so-sanh-xe-may-dien-va-xe-may-xang

### 1.4. Trạm sạc & showroom
- [ ] /vn_vi/cach-tim-tram-sac-vinfast
- [ ] /vn_vi/tong-quan-tram-sac-vinfast
- [ ] /vn_vi/huong-dan-cach-tim-tram-sac-bang-app-vinfast-e-scooter
- [ ] /vn_vi/huong-dan-tim-tram-sac-va-showroom-vinfast-tren-website

### 1.5. Ứng dụng VinFast
- [ ] /vn_vi/dieu-khien-o-to-dien-vinfast-qua-ung-dung-dien-thoai
- [ ] /vn_vi/ung-dung-vinfast-cho-o-to-dien
- [ ] /vn_vi/quan-ly-xe-o-to-dien-qua-ung-dung-vinfast
- [ ] /vn_vi/huong-dan-su-dung-ung-dung-vinfast

**Tổng: ~40 ứng viên** (đủ dư cho gold set 30-50 mẫu). Mở rộng thêm bằng Google `site:vinfastauto.com/vn_vi` + từ khóa "cách/kinh nghiệm/hướng dẫn/lưu ý/so sánh".

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

### 2.1. Số liệu đã thu (cần verify lại khi mở trang thật)

| Model | Tầm hoạt động/lần sạc | Tiêu chuẩn đo | Ghi chú |
|---|---|---|---|
| VF 9 | 438km (Eco) / 423km (Plus) | (cần xác nhận) | |
| VF 8 | 420km (Eco) / 400km (Plus) | (cần xác nhận) | |
| VF 5 | 326km | **NEDC** (nêu rõ) | |
| Bảo dưỡng định kỳ | mỗi 12.000km hoặc 1 năm | | dùng cho claim bảo dưỡng |

**Điểm mấu chốt cho Compliance:** VF 5 nêu rõ "theo NEDC", các model khác trong kết quả search chưa thấy nêu tiêu chuẩn đo. Đây chính là loại lỗi Compliance Agent cần bắt: **claim tầm hoạt động thiếu điều kiện đo (NEDC/WLTP)**. Một bài viết ghi "chạy 420km" mà không nói chuẩn đo là claim chưa đầy đủ → flag. Đây là ví dụ thật, verify được, để đưa vào demo.

---

## 3. Ghi chú

- Các URL dạng `/vn_vi/node/<id>` (câu hỏi thường gặp) là trang Q&A hỗ trợ, **không** phải cẩm nang marketing → không đưa vào gold set.
- File PDF `static-cms-prod.vinfastauto.com/*owner_manual*` là sách hướng dẫn sử dụng - có thể dùng làm nguồn phụ cho fact-check KB, không đưa vào gold set.
- Bản tiếng Anh `/vn_en/*` xác nhận site đa ngôn ngữ (Drupal multilingual) - ngoài phạm vi hiện tại, chỉ ghi nhận cho định hướng mở rộng.
- URL `/vn_vi/node/<id>` cũng là bằng chứng site chạy trên Drupal - nêu khi bảo vệ để chứng minh dự án khớp hạ tầng thật.
