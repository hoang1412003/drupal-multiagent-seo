# BÁO CÁO NGHIÊN CỨU DRUPAL CMS

*Giai đoạn 3 - Chương trình AI Thực Chiến VinUni*
*Thực tập tại VinFast O2O (VF O2O)*



**Đề tài:** Nghiên cứu và xây dựng hệ thống Multi-Agent AI hỗ trợ quy trình kiểm duyệt, đánh giá và tối ưu hóa nội dung Marketing trước khi xuất bản trên nền tảng Drupal CMS nhằm nâng cao chất lượng nội dung, tối ưu SEO và đảm bảo tính nhất quán của thương hiệu.

**Phạm vi nội dung:** Bài cẩm nang / hướng dẫn tiếng Việt về xe điện (dạng URL `/vn_vi/<slug>` trên vinfastauto.com, ví dụ "cách lái xe ô tô điện", "hướng dẫn sạc pin") - đây là nhóm nội dung marketing tối ưu cho SEO, khác với thông cáo báo chí ở mục "Công ty" (không thuộc phạm vi). Toàn bộ dữ liệu lấy từ nguồn công khai; dự án không sử dụng tài liệu nội bộ VF O2O.

Đây là phạm vi **tập trung có chủ đích** để gold set đủ sâu, **không phải giới hạn cứng**: hệ thống được thiết kế content-agnostic, rubric và ngưỡng lưu theo config `(content_type, langcode)` nên mở rộng được sang loại nội dung khác (landing page, thông cáo báo chí) và ngôn ngữ khác mà không phải sửa logic 4 agent (chi tiết: architecture.md mục 5.6). Định nghĩa phạm vi đầy đủ, phân tầng lộ trình mở rộng, lý do chọn tiếng Việt xem `docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md`.

**Phạm vi báo cáo này:** Kiến trúc tổng thể của hệ thống Multi-Agent do mentor cung cấp (chi tiết ở architecture.md). Theo lộ trình mentor giao, bước đầu tiên là nghiên cứu nền tảng Drupal CMS và triển khai một instance thử nghiệm làm nguồn dữ liệu đầu vào (nội dung) cho hệ thống. Phần nghiên cứu thiết kế các agent được trình bày ở bước tiếp theo.

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
| Metatag | Tự động sinh và quản lý meta title, meta description, Open Graph, Twitter Card cho từng nội dung. | Chính là trường meta description mà SEO Agent (mục 5.2) đọc trực tiếp để chấm điểm theo từng field. |
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

Instance Drupal được dựng cục bộ bằng **DDEV** - công cụ local development được cộng đồng Drupal chọn làm khuyến nghị chính thức từ 6/2024 ([drupal.org/docs/official_docs/local-development-guide](https://www.drupal.org/docs/official_docs/local-development-guide)). Căn cứ lựa chọn: DDEV được 93% lập trình viên Drupal khuyến nghị và chiếm 72% thị phần công cụ local development (Drupal Developer Survey 2025), đồng thời giữ code Drupal trực tiếp trên đĩa nên xem/sửa được bằng editor thông thường, và có sẵn công cụ truy cập CSDL (`ddev mysql`, `ddev launch -y adminer`).

DDEV chạy trên nền Docker nhưng quản lý qua CLI thống nhất (`ddev start`, `ddev composer`, `ddev drush`), không cần tự viết cấu hình container. Project cấu hình theo **Drupal 10** (`--project-type=drupal10`), docroot `web/`, gồm 2 service:

- **web**: PHP 8.4, server nginx-fpm (image `ddev/ddev-webserver`)
- **db**: MariaDB 11.8 (image `ddev/ddev-dbserver-mariadb`) - DDEV mặc định dùng MariaDB thay cho MySQL, tương thích đầy đủ với Drupal và JSON:API

**Địa chỉ truy cập:** `http://drupal.ddev.site` (DDEV tự cấu hình router và DNS local).

### 2.2. Các bước cài đặt đã thực hiện

Theo đúng quy trình khuyến nghị chính thức ([DDEV Quickstart - Drupal](https://docs.ddev.com/en/stable/users/quickstart/)), dùng phương pháp Composer:

```bash
ddev config --project-type=drupal10 --docroot=web
ddev start
ddev composer create-project drupal/recommended-project:^10
ddev composer require drush/drush
ddev drush site:install --account-name=admin --account-pass=admin -y
```

Sau khi site chạy, cấu hình thêm qua Drush (script hóa được, tái lập được - xem `drupal/scripts/create_ai_fields.php`):

1. Bật module JSON:API và HTTP Basic Authentication (`ddev drush en jsonapi basic_auth -y`).
2. Tắt `read_only` của JSON:API để cho phép ghi (POST/PATCH), không chỉ đọc (`ddev drush config:set jsonapi.settings read_only 0`).
3. Tạo 4 field tùy chỉnh trên content type Article: `field_ai_status`, `field_ai_score`, `field_ai_suggestions` (OUTPUT - Multi-Agent ghi kết quả về) và `field_meta_description` (INPUT - Multi-Agent đọc để chấm SEO/Compliance). Chi tiết field xem `docs/architecture.md` mục 2.3.
4. Tạo nội dung mẫu (content type "Bài viết") bằng script tái lập được (`multiagent/scripts/seed_sample_articles.py`) thay vì nhập tay - bài cẩm nang xe điện đúng phạm vi đề tài, cố ý gài kịch bản lỗi cho từng agent (xem `docs/architecture.md` mục 8.1).

## 3. Kiểm thử lấy nội dung qua JSON:API

Sau khi kích hoạt module JSON:API, tiến hành gọi thử API để kiểm tra khả năng lấy nội dung nháp ra làm input, mô phỏng đúng cách Orchestrator Agent sẽ đọc dữ liệu từ Drupal trong kiến trúc hệ thống.

**Request:**

```
GET http://drupal.ddev.site/jsonapi/node/article/{uuid}
Header: Accept: application/vnd.api+json
Authorization: Basic (HTTP Basic Auth)
```

**Kết quả trả về (rút gọn, từ bài cẩm nang thật ở trạng thái chưa xuất bản):**

```
{
  "type": "node--article",
  "id": "d115f055-e97a-4757-af9e-6b4f53e1f408",
  "attributes": {
    "title": "Hướng dẫn sạc pin ô tô điện VinFast đúng cách và an toàn",
    "body": {
      "value": "<h2>Chuẩn bị trước khi sạc</h2><p>Trước khi sạc pin ô tô điện VinFast...",
      "format": "basic_html"
    },
    "status": false,
    "created": "2026-07-27T03:36:51+00:00",
    "changed": "2026-07-27T03:37:09+00:00"
  }
}
```

`status: false` xác nhận đúng use case chính của đề tài: bài ở trạng thái **chưa xuất bản** (bản nháp) - đúng đối tượng mà hệ Multi-Agent AI cần đánh giá trước khi cho phép publish.

### 3.1. Nhận xét về cấu trúc dữ liệu

- title, body.value: nội dung chính cần đưa vào cho các agent phân tích (Content Quality, SEO, Brand Voice, Compliance).

- id (UUID): định danh duy nhất của node, dùng để Orchestrator Agent ghi ngược kết quả đánh giá về đúng bài viết tương ứng.

- status: phản ánh trạng thái published/unpublished, có thể mở rộng để đồng bộ với quyết định "Đạt / Cần sửa / Từ chối" của Aggregator Agent.

## 4. Kết luận và bước tiếp theo

Đã hoàn thành việc dựng một instance Drupal CMS thử nghiệm cục bộ và xác minh được khả năng lấy nội dung nháp ra dưới dạng JSON thông qua JSON:API - đáp ứng đúng yêu cầu bước 1 mentor giao: "dựng nhanh 1 con Drupal để lấy nó làm input (nội dung)".
