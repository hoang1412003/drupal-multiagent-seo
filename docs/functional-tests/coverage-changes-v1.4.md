# Nhật ký criterion coverage v1.4

## Phạm vi và provenance

- Ngày tạo/kiểm: **17/08/2026**.
- Annotator: `AI-A1`; provenance: `AI-annotated-partially-exposed`.
- Generator model: `not-exposed-by-runtime`; runtime không cung cấp model ID chính xác.
- Guideline: `v1.4`.
- Trạng thái của mọi sample trong tài liệu này: **TEST FIXTURE — KHÔNG XUẤT BẢN**.
- Criterion coverage là perturbation tổng hợp một lỗi, báo cáo tách khỏi 63 mẫu chính và không dùng để chọn ngưỡng sau khi xem output.
- Parent GC giữ nguyên và tiếp tục là đối chứng expected `publish`.

## CV-A3-01 ← GC-006

- **Target duy nhất:** A3.
- **Expected label:** `rejected`.
- **Source URL chủ đề:** `/vn_vi/thoi-gian-sac-day-xe-may-dien-vinfast-bao-lau`.
- **Nguồn đối chiếu:** `https://vinfastauto.com/vn_vi/thong-so-ky-thuat-evo200`, truy cập ngày 17/08/2026.
- **Giá trị đúng:** Evo200 dùng bộ sạc 400 W từ 0% đến 100% có thời gian tham khảo khoảng **10 giờ**.
- **Giá trị chèn sai:** khoảng **15 giờ**.

Thay đổi chính xác:

```diff
-<tr><td>Evo200</td><td>Bộ sạc 400 W, từ 0% đến 100%</td><td>Khoảng 10 giờ</td></tr>
+<tr><td>Evo200</td><td>Bộ sạc 400 W, từ 0% đến 100%</td><td>Khoảng 15 giờ</td></tr>
```

`git diff --no-index --ignore-cr-at-eol --unified=0` xác nhận đây là khác biệt duy nhất giữa content parent và fixture. Mẫu xe, bộ sạc, dải SOC và nguồn trực tiếp đều giữ nguyên, nên không tạo B2 hoặc B10. Các thông số khác khớp parent sạch và nguồn Task 4.

Rà full taxonomy: không A1/A2/A4/A5/A6/A7; không B1–B11 ngoài target. A3 có thể đối chiếu khách quan và làm nhãn `rejected`.

## CV-A5-01 ← GC-003

- **Target duy nhất:** A5.
- **Expected label:** `rejected`.
- **Source URL chủ đề:** `/vn_vi/cach-khoi-dong-xe-may-dien-vinfast`.
- **Field giữ nguyên:** title 53, meta 150, alias 41 và summary của GC-003.
- **Body thay thế:** bài về tổ chức tủ sách cá nhân; không trả lời cách khởi động xe máy điện.

Phép đo line-level trên body sau separator:

- parent có 116 semantic lines;
- fixture giữ nguyên 0 semantic lines;
- tỷ lệ semantic parent lines được thay: **100%**.

Body mới có 701 tiếng và 5 H2 nên không tạo B9; không có ảnh nên B6 không áp dụng. Nội dung không có claim kỹ thuật/số liệu/chính sách, không lẫn xưng hô và đã đọc B8. C4=3 là advisory. Kết luận đúng một target A5 vì body cần viết lại toàn bộ để trả lời title.

## CV-A5-02 ← GC-018

- **Target duy nhất:** A5.
- **Expected label:** `rejected`.
- **Source URL chủ đề:** `/vn_vi/huong-dan-cach-tim-tram-sac-bang-app-vinfast-e-scooter`.
- **Field giữ nguyên:** title 54, meta 144, alias 61 và summary của GC-018.
- **Body thay thế:** bài về quản lý kho ảnh số; không trả lời cách tìm trạm sạc.

Phép đo line-level trên body sau separator:

- parent có 23 semantic lines;
- fixture giữ nguyên 0 semantic lines;
- tỷ lệ semantic parent lines được thay: **100%**.

Body mới có 671 tiếng và 5 H2 nên không tạo B9; không có ảnh; không claim kỹ thuật/số liệu/chính sách; dùng nhất quán “người dùng”. Scanner không còn candidate sau khi thay cụm false positive. Kết luận đúng một target A5.

## Helper, scanner và manual review

| ID | Title | Meta | Alias | Body words | H2 | Helper A/B | Scanner cần disposition |
|---|---:|---:|---:|---:|---:|---|---|
| CV-A3-01 | 46 | 140 | 52 | 536 | 3 | không có mã máy kết luận | A3/B10 candidates |
| CV-A5-01 | 53 | 150 | 41 | 701 | 5 | không có mã máy kết luận | không có; C4=3 |
| CV-A5-02 | 54 | 144 | 61 | 671 | 5 | không có mã máy kết luận | không có |

Disposition:

- CV-A3-01 A3 xác nhận vì 15 giờ sai so với nguồn 10 giờ. B10 bác vì bảng có link nguồn chính thức trực tiếp ngay sau và fixture giữ nguyên provenance của parent.
- CV-A5-01/02: scanner không tự đo A5; manual so title với toàn body và phép đo thay 100% xác nhận A5.
- A1/A2/A4: không claim so sánh nhất, đối thủ hoặc khuyến mại.
- A6/A7: không hướng dẫn kỹ thuật nguy hiểm và không văn xuôi ẩn.
- B1/B2/B3/B4/B5/B6/B7/B8/B9/B10/B11: không có mã phụ sau rà tay; các field/HTML đều hợp lệ.

## Hashes khóa Task 7

| ID | Parent SHA-256 | Content SHA-256 |
|---|---|---|
| CV-A3-01 | `60599dea5732e1c9ed80e222093c651f3326c9b980f2c1d735a4109e00a778ed` | `02baa2fe48cceebe763af667019ff1925a054978d86d1b0a90d90dc07c419f4e` |
| CV-A5-01 | `871c36ce97a010d87feb76f2f23ab328b00286748462149f42e9eeda9fe9efd8` | `3aa00b2fb72326ce3500ac0144d039c8d08d8bcfbb2c849643a543c17b5e0b0e` |
| CV-A5-02 | `1ba51808dc0e247367339f403d2c149ad26f84dd990bf3032b031ef4fae086d9` | `549150a591c06d0b5b293ddf52e7e45223e8aac87ba07aeac70edcae48317713` |
