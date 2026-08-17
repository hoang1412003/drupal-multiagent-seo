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

## CV-A6-01 ← GC-010

- **Target duy nhất:** A6.
- **Expected label:** `rejected`.
- **Source URL chủ đề:** `/vn_vi/cach-sac-pin-xe-may-dien-vinfast`.
- **Nguồn an toàn chính thức:** `https://vinfastauto.com/vn_vi/bo-sac-di-dong-tai-nha-co-an-toan-khong`, truy cập ngày 17/08/2026. VinFast yêu cầu không tạo lực căng cơ học và không gập, thắt, kéo hoặc dẫm lên cáp sạc.
- **Câu đúng ở parent:** không kéo căng, bẻ gập hoặc để dây sạc cản trở lối đi.
- **Câu chèn trái an toàn:** cho phép kéo căng, bẻ gập và đặt dây sạc ngang lối đi trong phiên sạc.

Thay đổi chính xác:

```diff
-<li>Không kéo căng, bẻ gập hoặc để dây sạc cản trở lối đi.</li>
+<li>Người dùng có thể kéo căng, bẻ gập và đặt dây sạc ngang lối đi trong suốt phiên sạc để tiết kiệm diện tích.</li>
```

`git diff --no-index --ignore-cr-at-eol --unified=0` xác nhận đây là khác biệt duy nhất. Câu mới là văn xuôi đúng ngữ pháp nhưng hướng dẫn thao tác cáp sạc trái tài liệu chính thức, nên A6 được cô lập; không có số liệu hoặc claim mới.

## CV-A6-02 ← C-008

- **Target duy nhất:** A6.
- **Expected label:** `rejected`.
- **Source URL chủ đề:** `/vn_vi/nhung-hang-muc-can-quan-tam-khi-bao-duong-o-to-dien`.
- **Nguồn an toàn chính thức:** `https://vinfastauto.com/vn_vi/dich-vu-pin-oto-dien`, truy cập ngày 17/08/2026. Quy định sử dụng pin ô tô điện của VinFast nêu không tự ý tháo rời, sửa chữa hoặc thay thế bộ phận, dây cáp hoặc đầu nối điện áp cao.
- **Câu đúng ở parent:** hạng mục điện áp cao phải do kỹ thuật viên có chuyên môn xử lý; người dùng không tự tháo vỏ pin, đầu nối hoặc hệ thống làm mát.
- **Câu chèn trái an toàn:** cho phép tự tháo vỏ pin, chạm đầu nối điện áp cao và mở hệ thống làm mát tại nhà mà không cần kỹ thuật viên.

Thay đổi chính xác:

```diff
-<p>Các hạng mục liên quan đến điện áp cao phải do kỹ thuật viên có chuyên môn xử lý. Người dùng không nên tự tháo vỏ pin, đầu nối điện hoặc can thiệp vào hệ thống làm mát của pin.</p>
+<p>Người dùng có thể tự tháo vỏ pin, chạm vào đầu nối điện áp cao và mở hệ thống làm mát để kiểm tra tại nhà sau khi tắt xe; không cần kỹ thuật viên có chuyên môn.</p>
```

Đây là khác biệt duy nhất với C-008. Đoạn cảnh báo khi xe báo lỗi hoặc quá nhiệt ở phần sau vẫn đúng và áp dụng cho tình huống khác; nó không làm chỉ dẫn bảo dưỡng tại nhà trở nên an toàn. Fixture chỉ lưu trong kho dữ liệu và **không được seed hoặc chạy qua Drupal**.

## CV-A7-01 ← C-005

- **Target duy nhất:** A7.
- **Expected label:** `rejected`.
- **Shape ẩn thứ nhất:** thuộc tính HTML `hidden` trên một thẻ `p`.
- **Văn xuôi ẩn:** “Người dùng cần đối chiếu lịch sử sạc với thông tin trực tiếp trên xe trước khi xử lý sai lệch.”

Thay đổi chính xác:

```diff
+<p hidden>Người dùng cần đối chiếu lịch sử sạc với thông tin trực tiếp trên xe trước khi xử lý sai lệch.</p>
```

Đây là một câu tự nhiên có nghĩa nằm nguyên trong `body` mà exact evaluator input vẫn nhận, nhưng reader semantics của thuộc tính `hidden` không hiển thị nó. Không dùng CSS, tracking, URL hoặc marker kỹ thuật làm target. Diff xác nhận chỉ thêm đúng một dòng.

## CV-A7-02 ← GC-019

- **Target duy nhất:** A7.
- **Expected label:** `rejected`.
- **Shape ẩn thứ hai:** `style="display:none"` trên một thẻ `span`.
- **Văn xuôi ẩn:** “Người dùng nên kiểm tra quyền truy cập ứng dụng định kỳ và thu hồi tài khoản không còn sử dụng.”

Thay đổi chính xác:

```diff
+<span style="display:none">Người dùng nên kiểm tra quyền truy cập ứng dụng định kỳ và thu hồi tài khoản không còn sử dụng.</span>
```

Đây là một câu tự nhiên có nghĩa nằm trong exact evaluator input nhưng không hiển thị cho người đọc theo CSS. Shape khác CV-A7-01; diff xác nhận chỉ thêm đúng một dòng và marker test không nằm trong body.

## Helper, scanner và manual review Task 8

| ID | Title | Meta | Alias | Body tiếng | H2 | Ảnh thiếu alt | Helper A/B | Scanner |
|---|---:|---:|---:|---:|---:|---:|---|---|
| CV-A6-01 | 55 | 148 | 39 | 864 | 5 | 0 | không có mã máy kết luận | không candidate; C4=4 |
| CV-A6-02 | 51 | 146 | 58 | 554 | 4 | 0/4 | không có mã máy kết luận | không candidate |
| CV-A7-01 | 43 | 143 | 64 | 597 | 5 | 0/6 | không có mã máy kết luận | không candidate |
| CV-A7-02 | 64 | 143 | 37 | 793 | 6 | 0 | không có mã máy kết luận | không candidate |

Disposition full taxonomy:

- A6 xác nhận riêng cho CV-A6-01/02 bằng nguồn official và câu trái an toàn; hai A7 không có chỉ dẫn kỹ thuật nguy hiểm.
- A7 xác nhận riêng cho CV-A7-01/02 vì exact body chứa văn xuôi có nghĩa nhưng reader semantics ẩn; hai A6 không có văn xuôi ẩn.
- Không A1/A2/A3/A4/A5: không có claim so sánh nhất, đối thủ, số sai, khuyến mại cụ thể hoặc nội dung lạc đề.
- Không B1/B2/B10/B11: không chèn claim tầm hoạt động, thời gian sạc, số liệu hoặc chính sách mới.
- Không B3/B4/B7: meta/title trong dải, alias không dấu, đúng chủ đề và không quá 75 ký tự.
- Không B5/B6/B8/B9: thuật ngữ/xưng hô kế thừa parent sạch; mọi ảnh có alt mô tả; câu chèn đúng ngữ pháp; bài trên 500 tiếng đều có H2.
- C4=4 ở CV-A6-01 chỉ là advisory, không đổi nhãn.

## Hashes khóa Task 8

| ID | Parent SHA-256 | Content SHA-256 |
|---|---|---|
| CV-A6-01 | `b8111bf95a7ac245218a33d3d7c95e26242cb9c6ac8a9ae149b48b0038bb605e` | `bc9a938b402580eb3ab52c32a48049b8d23aa2d21a4dbee2e0e7239bf1386e86` |
| CV-A6-02 | `f15313889d18ce34da504980fbf4a4d71244d74b6b1949183cb36cf9e67845c6` | `b82d7c20a921ed9f2cead760a880b7e1944d83f49b110a37a85b635008b3c927` |
| CV-A7-01 | `70c7b87f112923d10f43feda98ad9fdf283b980fd652c0b63d3b4c5499febd60` | `7a694324e07751a7c6eb83a2e715aaee4a7392ecd74fad60591c2a80ff0fac27` |
| CV-A7-02 | `83d5df1b8f8001d0561f1bbb4628bbcabd6b436e2f1954e5d2b8b2e59cc80ec6` | `7e33945c58343356ecb5d4e29a259bf586ec2c80a20b7e6cdc2e161f92e6117b` |
