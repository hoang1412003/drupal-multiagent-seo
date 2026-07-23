# BÁO CÁO NGHIÊN CỨU DRUPAL CMS

*Giai đoạn 3 - Chương trình AI Thực Chiến VinUni**
Thực tập tại VinFast O2O (VF O2O)*



**Đề tài:** Nghiên cứu và xây dựng hệ thống Multi-Agent AI hỗ trợ quy trình kiểm duyệt, đánh giá và tối ưu hóa nội dung Marketing trước khi xuất bản trên nền tảng Drupal CMS nhằm nâng cao chất lượng nội dung, tối ưu SEO và đảm bảo tính nhất quán của thương hiệu.

**Nhiệm vụ trong báo cáo này:** Theo chỉ đạo của mentor, nghiên cứu Drupal CMS và dựng nhanh một instance thử nghiệm để sử dụng làm nguồn input (nội dung) cho hệ thống Multi-Agent, trước khi tiến hành nghiên cứu thiết kế các agent.

## 1. Drupal CMS là gì

Drupal là một hệ quản trị nội dung (CMS - Content Management System) mã nguồn mở, viết bằng ngôn ngữ PHP, dùng để xây dựng và quản lý website mà không cần lập trình lại từ đầu mỗi khi thêm nội dung mới. Drupal cung cấp sẵn phần khung của một website (hệ thống đăng nhập, phân quyền người dùng, lưu trữ dữ liệu, giao diện quản trị...), cho phép người dùng tập trung vào việc tạo, chỉnh sửa và xuất bản nội dung.

So với các CMS phổ biến khác (WordPress, Joomla), Drupal thiên về các hệ thống có quy mô lớn, yêu cầu tính linh hoạt và khả năng mở rộng cao - phù hợp với môi trường doanh nghiệp như VF O2O, nơi cần quản lý khối lượng lớn nội dung marketing với quy trình kiểm duyệt chặt chẽ.

### 1.1. Các khái niệm cốt lõi

- Node: đơn vị nội dung cơ bản trong Drupal (một bài viết, một trang, một chương trình khuyến mãi...).

- Content Type: khuôn mẫu quy định cấu trúc của một node (ví dụ: "Article", "Page"), gồm các trường dữ liệu (field) cụ thể.

- Field: từng trường dữ liệu trong content type, ví dụ tiêu đề, nội dung, ảnh đại diện, mô tả SEO, thẻ (tags).

- Taxonomy: hệ thống phân loại và gắn nhãn nội dung (ví dụ danh mục sản phẩm, khu vực).

- Module: thành phần mở rộng chức năng của Drupal (ví dụ module JSON:API để xuất dữ liệu qua API).

- Moderation state: trạng thái nội dung có sẵn trong Drupal như Draft (nháp), Published (đã xuất bản) - phù hợp với luồng "Đạt / Cần sửa / Từ chối" trong kiến trúc hệ thống được mentor đề xuất.

### 1.2. Lý do Drupal phù hợp với bài toán của đề tài

Drupal hỗ trợ sẵn khả năng xuất dữ liệu nội dung ra ngoài dưới dạng API tiêu chuẩn (JSON:API, REST) mà không cần viết thêm nhiều code. Điều này cho phép một hệ thống bên ngoài (hệ Multi-Agent AI) có thể:

1. Gọi API để lấy nội dung nháp (title, body, các trường SEO...) dưới dạng JSON, dùng làm input cho Orchestrator Agent.

2. Sau khi các agent chấm điểm/đánh giá xong, gọi ngược API để cập nhật trạng thái nội dung và ghi gợi ý chỉnh sửa trở lại Drupal.

Đây chính là mô hình kiến trúc "Headless / Decoupled Drupal": Drupal chỉ đóng vai trò kho nội dung và backend quản trị, còn toàn bộ logic xử lý AI được đặt ở một hệ thống riêng, giao tiếp với Drupal thông qua API.

### 1.3. Kiến trúc và ưu điểm SEO có sẵn của Drupal

Vì đề tài có liên quan trực tiếp đến tối ưu SEO, phần này khảo sát các tính năng SEO có sẵn trong kiến trúc module hóa của Drupal - đây là nền tảng quan trọng vì SEO Agent (mục 5.2, xem architecture.md) sẽ dựa trên các trường dữ liệu này để đánh giá và đưa ra gợi ý.

Drupal có kiến trúc "module hóa" (modular architecture): mọi tính năng, kể cả tính năng SEO, đều được đóng gói thành các module có thể bật/tắt độc lập, thay vì phải sửa code lõi. Điều này cho phép bổ sung khả năng SEO mạnh mà không ảnh hưởng đến phần còn lại của hệ thống.

| Module SEO | Chức năng | Liên hệ với đề tài |
| --- | --- | --- |
| Metatag | Tự động sinh và quản lý meta title, meta description, Open Graph, Twitter Card cho từng nội dung. | Chính là các trường dữ liệu mà SEO Agent (mục 5.2) sẽ đọc để chấm điểm "meta_issues". |
| Pathauto | Tự động tạo URL thân thiện SEO theo mẫu (ví dụ "/khuyen-mai/vf3-thang-7" thay vì "/node/123") dựa trên tiêu đề/danh mục. | Giúp bài viết có URL chuẩn SEO ngay khi tạo, không cần AI can thiệp riêng cho phần này. |
| Simple XML Sitemap | Tự động sinh sitemap.xml theo chuẩn sitemaps.org, hỗ trợ đa ngôn ngữ, giúp công cụ tìm kiếm phát hiện và thu thập nội dung hiệu quả hơn. | Đảm bảo nội dung sau khi được duyệt "publish" được công cụ tìm kiếm index nhanh chóng. |
| Schema.org Metatag (Structured data) | Xuất dữ liệu có cấu trúc (JSON-LD) trong phần head của trang, giúp Google hiển thị rich results (đánh giá sao, breadcrumb, FAQ...). | Có thể mở rộng SEO Agent sau này để kiểm tra luôn cả structured data, không chỉ meta tag cơ bản. |



Ngoài các module SEO trực tiếp ở trên, kiến trúc nền tảng của Drupal còn có 2 ưu điểm gián tiếp nhưng ảnh hưởng đáng kể đến SEO:

**Kiến trúc caching (ảnh hưởng trực tiếp Core Web Vitals):**

Drupal có sẵn trong lõi (không cần cài thêm) các cơ chế cache: Internal Page Cache, Dynamic Page Cache, và BigPipe (tối ưu tốc độ cảm nhận cho người dùng đã đăng nhập). Google dùng Core Web Vitals (LCP dưới 2.5 giây, INP dưới 200ms, CLS dưới 0.1) làm tín hiệu xếp hạng tìm kiếm, nên tốc độ tải trang nhanh nhờ caching sẵn có này hỗ trợ trực tiếp cho SEO, không chỉ đơn thuần là vấn đề hiệu năng kỹ thuật.

**Kiến trúc đa ngôn ngữ gốc (native multilingual):**

Drupal tích hợp sẵn 4 module lõi cho đa ngôn ngữ: Language, Content Translation, Configuration Translation, Interface Translation. Trong khi đó, các CMS khác như WordPress phải phụ thuộc plugin bên thứ ba (WPML, Polylang...), thường trả phí và dễ gây lỗi SEO (cấu hình hreflang sai, thiếu liên kết 2 chiều giữa các phiên bản ngôn ngữ). Đây là điểm đáng lưu ý nếu VF O2O có nhu cầu xuất bản nội dung đa thị trường/đa ngôn ngữ trong tương lai.

Kết luận: Drupal không chỉ đóng vai trò "kho nội dung" như trình bày ở mục 1.1-1.2, mà bản thân kiến trúc của nó (module SEO trực tiếp, caching, đa ngôn ngữ gốc) đã có sẵn nền tảng hỗ trợ SEO khá toàn diện, từ nội dung (meta tag, structured data) đến hạ tầng (tốc độ tải trang, khả năng mở rộng đa ngôn ngữ). Vai trò của SEO Agent trong hệ Multi-Agent không phải để "thay thế" các nền tảng này, mà để kiểm tra xem đội content đã sử dụng đúng và đầy đủ các khả năng mà Drupal đã cung cấp sẵn hay chưa trước khi cho phép xuất bản.

*Nguồn tham khảo: acquia.com/blog/drupal-seo; digitalmarket.sg/learn/drupal-seo-the-2025-enterprise-guide-to-modules-ranking/; pantheon.io/learning-center/performance/drupal (caching, Core Web Vitals); eruptiv.lu/drupal/drupal-multilingue (kiến trúc đa ngôn ngữ)*

## 2. Triển khai thử nghiệm Drupal instance

### 2.1. Môi trường triển khai

Instance Drupal được dựng cục bộ (local) bằng Docker Compose, sử dụng image chính thức từ Docker Hub, gồm 2 container:

- drupal:10-apache - chạy Drupal 10 kèm Apache và PHP.

- mysql:8.0 - cơ sở dữ liệu MySQL lưu trữ toàn bộ dữ liệu nội dung, cấu hình.

Hai container giao tiếp với nhau qua mạng nội bộ (network) do Docker Compose tự tạo. Container Drupal kết nối tới container MySQL thông qua tên service "db" (thay vì "localhost", vì đây là hai container độc lập, không chia sẻ chung hệ điều hành).

**Địa chỉ truy cập:** http://localhost:8080 (cổng 8080 trên máy host được ánh xạ sang cổng 80 trong container Drupal).

### 2.2. Các bước cài đặt đã thực hiện

1. Cài đặt qua trình cài đặt web (web installer) của Drupal, chọn hồ sơ "Tiêu chuẩn" (Standard) - hồ sơ cài sẵn các content type và module phổ biến, phù hợp để thực hành nhanh.

2. Cấu hình kết nối cơ sở dữ liệu MySQL (tên CSDL, username, password, host = "db", port = 3306).

3. Cấu hình thông tin website và tài khoản quản trị (admin).

4. Tạo nội dung mẫu (content type "Bài viết") mô phỏng một bài viết marketing thực tế, đóng vai trò "nội dung nháp" để làm input thử nghiệm cho hệ Multi-Agent.

5. Bật module JSON:API (mặc định không được kích hoạt sẵn trong hồ sơ Standard của Drupal 10) để cho phép xuất nội dung ra dưới dạng dữ liệu JSON qua API.

## 3. Kiểm thử lấy nội dung qua JSON:API

Sau khi kích hoạt module JSON:API, tiến hành gọi thử API để kiểm tra khả năng lấy nội dung nháp ra làm input, mô phỏng đúng cách Orchestrator Agent sẽ đọc dữ liệu từ Drupal trong kiến trúc hệ thống.

**Request:**

```
GET http://localhost:8080/jsonapi/node/article
Header: Accept: application/vnd.api+json
```

**Kết quả trả về (rút gọn):**

```
{
  "type": "node--article",
  "id": "67859e3c-ccf8-45d5-b4e3-9ee68e0895fa",
  "attributes": {
    "title": "Khuyến mãi VinFast VF3 tháng 7 - Giảm giá đến 50 triệu",
    "body": {
      "value": "VinFast chính thức triển khai chương trình ưu đãi...",
      "format": "basic_html"
    },
    "status": true,
    "created": "2026-07-17T02:23:12+00:00",
    "changed": "2026-07-17T02:28:05+00:00"
  }
}
```

### 3.1. Nhận xét về cấu trúc dữ liệu

- title, body.value: nội dung chính cần đưa vào cho các agent phân tích (Content Quality, SEO, Brand Consistency, Compliance).

- id (UUID): định danh duy nhất của node, dùng để Orchestrator Agent ghi ngược kết quả đánh giá về đúng bài viết tương ứng.

- status: phản ánh trạng thái published/unpublished, có thể mở rộng để đồng bộ với quyết định "Đạt / Cần sửa / Từ chối" của Aggregator Agent.

## 4. Kết luận và bước tiếp theo

Đã hoàn thành việc dựng một instance Drupal CMS thử nghiệm cục bộ và xác minh được khả năng lấy nội dung nháp ra dưới dạng JSON thông qua JSON:API - đáp ứng đúng yêu cầu bước 1 mentor giao: "dựng nhanh 1 con Drupal để lấy nó làm input (nội dung)".
