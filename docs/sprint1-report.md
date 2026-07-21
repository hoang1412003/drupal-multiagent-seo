# PHẦN 4: BÁO CÁO SPRINT 1

## 1. Mục tiêu Sprint 1

Theo lộ trình 3 sprint đã được mentor duyệt (`docs/roadmap.md`), Sprint 1 có 4 mục tiêu:

1. Nghiên cứu kiến trúc, chốt công nghệ điều phối.
2. Cải tạo Drupal (tạo content type/field cần thiết) + xây dựng AI Core.
3. Dựng khung Orchestrator (node Fetch, Dispatch, State object).
4. Xây thử Agent SEO và Content Quality Agent (2 agent không phụ thuộc brand guideline), chạy thật end-to-end.

Báo cáo này trình bày kết quả đạt được, bằng chứng kiểm thử thực tế, và các vấn đề phát hiện/đã khắc phục trong quá trình rà soát lại trước khi bàn giao.

## 2. Kết quả đạt được

### 2.1. Kiến trúc & công nghệ điều phối

Đã khảo sát 3 lựa chọn (LangGraph, tự viết orchestrator bằng Python thuần, CrewAI) và chốt dùng **LangGraph** — do có sẵn cơ chế fan-out/fan-in (chạy song song nhiều agent rồi gộp kết quả) và quản lý state xuyên suốt, khớp trực tiếp với kiến trúc cố định/tuần tự của đề tài. Căn cứ lựa chọn chi tiết (bao gồm khảo sát case study ngành thực tế) xem `docs/research.md` mục 1 và mục 4.

### 2.2. Hạ tầng Drupal

- Dựng Drupal 10 + MySQL 8 local bằng Docker Compose (`docker-compose.yml`), truy cập qua `http://localhost:8080`.
- Bật module JSON:API và HTTP Basic Authentication.
- Tạo 3 field tùy chỉnh trên content type "Bài viết": `field_ai_status` (List text), `field_ai_score` (Number), `field_ai_suggestions` (Long text) — đã xác nhận có dữ liệu thật, không chỉ tạo field rỗng.

Bằng chứng: [danh sách field trong Drupal](evidence/screenshot_field_config.png), [module JSON:API đã bật](evidence/screenshot_jsonapi_module_enabled.png).

### 2.3. AI Core

`src/ai_core.py` — hàm dùng chung `call_agent()` gọi Claude (model `claude-haiku-4-5-20251001`) với structured output (JSON Schema), dùng chung cho toàn bộ 4 agent.

Bằng chứng: [output thật của `call_agent()`](evidence/smoke_test_ai_core_output.json) (chạy `scripts/smoke_test_ai_core.py`).

### 2.4. Khung Orchestrator (LangGraph, 8 node)

`src/graph.py` triển khai đủ 8 node theo đúng sơ đồ kiến trúc: Fetch → Orchestrator/Dispatch → 4 agent (song song) → Aggregator → Write-back. Content Quality và SEO Agent chạy thật; Brand Consistency và Compliance Agent là **stub có chủ đích** (luôn trả điểm 100, chưa đánh giá gì) — đúng theo kế hoạch, vì 2 agent này cần brand guideline (Brand) và thuộc phạm vi Sprint 2.

### 2.5. Content Quality Agent & SEO Agent

Cả 2 agent triển khai thật (`src/agents/content_quality.py`, `src/agents/seo.py`), gọi LLM thật với system prompt và output schema riêng biệt, đã kiểm thử end-to-end (xem mục 3).

## 3. Kiểm thử thực tế

Đã tạo 8 bài viết mẫu trên Drupal, cố ý bao phủ các loại lỗi khác nhau (bài tốt, lỗi chính tả, thiếu SEO, sai thuật ngữ thương hiệu, phóng đại/vi phạm compliance), theo đúng khuyến nghị bộ dữ liệu mẫu ở `docs/architecture.md` mục 8.1. Chạy toàn bộ pipeline thật (Fetch → 4 agent → Aggregator → Write-back) trên cả 8 bài:

Toàn bộ 8 bài được chạy trong **cùng một lượt** (1 script, gọi tuần tự `build_graph().invoke()` cho từng bài), đảm bảo mỗi dòng kết quả dưới đây đến từ đúng 1 lần gọi API duy nhất, không ghép số liệu từ các lần chạy khác nhau:

| Bài viết | Loại lỗi cố ý | Content Quality | SEO | Final score | Quyết định |
|---|---|---|---|---|---|
| Ưu đãi VF5 tháng 8 | Bài tốt | 85 | 72 | 90.65 | publish |
| Sự kiện lái thử VF8 | Bài tốt | 85 | 72 | 90.65 | publish |
| VF6 ra mắt phiên bản mới | Bài tốt | 85 | 72 | 90.65 | publish |
| VF9 | Bài tốt nhưng khá ngắn | 75 | 25 | 78.75 | needs_revision |
| Khuyến mãi VF3 thág 7 - ưu đải cực khủng | Lỗi chính tả/ngữ pháp cố ý | 65 | 45 | 80.25 | publish |
| Tin mới | Thiếu SEO cố ý (title/nội dung quá ngắn) | 35 | 15 | 66.75 | needs_revision |
| Vf 3 giảm giá tháng 8 | Sai thuật ngữ thương hiệu cố ý (vf3/VF 3/VF-3 lẫn lộn) | 75 | 72 | 88.15 | publish |
| VF3 - Chiếc xe điện tốt nhất thế giới... | Phóng đại/vi phạm compliance cố ý | 35 | 45 | 72.75 | needs_revision |

Bằng chứng: [log chạy đầy đủ 8 bài](evidence/run_all_samples_output.txt) (`scripts/run_all_samples.py`).

**Nhận xét:**

- Content Quality Agent bắt đúng và chi tiết các lỗi chính tả cố ý (ví dụ: "thág"→"tháng", "dc"→"được", "giãm"→"giảm", "goi"→"gói" ở bài lỗi chính tả), và chấm thấp cho các bài nội dung quá sơ sài (Tin mới, VF9 — dù VF9 không cố ý viết lỗi, chỉ vì nội dung quá ngắn nên vẫn bị SEO Agent chấm thấp).
- SEO Agent phản ánh đúng mức độ nghiêm trọng theo dữ liệu thực tế: bài "Tin mới" (cố ý thiếu SEO) chỉ được 15 điểm, thấp hơn hẳn các bài bình thường (~72 điểm); bài "VF9" tuy không cố ý lỗi SEO nhưng vì chỉ có 2 câu ngắn nên cũng chỉ được 25 điểm — cho thấy SEO Agent nhạy với độ dài nội dung một cách nhất quán, không chỉ với các bài cố ý làm lỗi.
- Bài "sai thuật ngữ thương hiệu" và bài "vi phạm compliance" **vẫn được Content Quality Agent phát hiện một phần** (nhờ đọc ra sự thiếu nhất quán tên sản phẩm/văn phong phóng đại như "tốt nhất thế giới", "giảm giá không giới hạn", "cơ hội duy nhất trong đời"), nhưng cả 2 vẫn có điểm Brand/Compliance = 100 vì **2 agent này còn là stub** — đây là giới hạn đã biết trước, đúng theo phạm vi Sprint 1, không phải lỗi. Đặc biệt bài vi phạm compliance là minh chứng rõ vì sao Compliance Agent thật là ưu tiên cao nhất ở Sprint 2 (nếu Content Quality Agent không tình cờ đọc ra văn phong phóng đại, sẽ không có gì phát hiện được cả).
- **Lưu ý quan trọng về tính không xác định (non-determinism) của LLM:** chạy cùng 1 bài ở các thời điểm khác nhau cho điểm số hơi khác nhau mỗi lần (ví dụ bài lỗi chính tả dao động quanh mốc 80, giữa các lần chạy đã ra cả `needs_revision` lẫn `publish`). Đây là đặc điểm tự nhiên của LLM, không phải lỗi hệ thống — nhưng cho thấy rõ tầm quan trọng của việc **hiệu chỉnh ngưỡng quyết định bằng gold set ở Sprint 3** (mục 8.2 `architecture.md`), vì các bài có điểm nằm sát ngưỡng 80/50 có thể đổi quyết định giữa các lần chấm.
- Đã test riêng cả trường hợp bài viết ở trạng thái **chưa công bố** (unpublished/"Needs Review") — đúng use case chính của đề tài — pipeline chạy và ghi kết quả thành công (xem mục 4.2). Bằng chứng: [bài test tạo ở trạng thái unpublished](evidence/create_unpublished_test_node.json), [output pipeline chạy thành công trên bài đó](evidence/smoke_test_graph_unpublished_output.json), [ảnh chụp field đã ghi ngược vào Drupal](evidence/screenshot_unpublished_article_after_writeback.png).

## 4. Lỗi phát hiện và đã khắc phục trong quá trình rà soát

Trong lúc chuẩn bị báo cáo, đã rà soát lại toàn bộ code (không chỉ dựa vào việc README tick sẵn) và phát hiện, sửa 3 lỗi thật:

### 4.1. Aggregator tính sai `final_score` khi bị Compliance veto

Khi Compliance phủ quyết (`score < 50` hoặc có flag `critical`), `final_score` trước đây bị gán bằng riêng điểm Compliance thay vì trung bình có trọng số của toàn bộ agent còn dữ liệu — sai lệch so với công thức ở `docs/architecture.md` mục 6.1, khiến điểm ghi vào `field_ai_score` không phản ánh đúng chất lượng tổng thể bài viết. Đã sửa: tách riêng logic tính điểm (luôn theo trung bình trọng số) và logic quyết định veto.

Bằng chứng: [diff commit sửa lỗi](evidence/bugfix_aggregator_score_veto.diff).

### 4.2. `fetch_content()` không đọc được bài viết chưa công bố

`fetch_content()` gọi GET không xác thực, chỉ dựa vào quyền đọc công khai (Anonymous role) — quyền này chỉ áp dụng cho bài đã publish. Vì use case chính của hệ thống là đánh giá bài ở trạng thái "Needs Review" (chưa publish), lỗi này khiến pipeline gãy ngay bước Fetch (401 Unauthorized) với đúng loại bài viết mà hệ thống được thiết kế ra để xử lý. Đã tái hiện lỗi bằng test thật (tạo bài chưa publish, xác nhận 401), sửa bằng cách thêm `auth=AUTH`, và verify lại toàn bộ pipeline chạy thành công trên bài chưa publish.

Bằng chứng: [diff commit sửa lỗi](evidence/bugfix_fetch_unpublished_401.diff), [output pipeline chạy thành công sau khi sửa](evidence/smoke_test_graph_unpublished_output.json).

### 4.3. Output lẫn lộn tiếng Anh/tiếng Việt giữa các agent

System prompt của Content Quality và SEO Agent không có chỉ dẫn ngôn ngữ đầu ra, khiến LLM tự chọn ngôn ngữ không nhất quán (có lần trả tiếng Anh, có lần tiếng Việt) trong cùng 1 lần chạy — gây khó hiểu cho đội content (người đọc `field_ai_suggestions`). Đã thêm chỉ dẫn "Luôn trả lời bằng tiếng Việt" vào cả 2 system prompt, verify lại output nhất quán tiếng Việt.

Bằng chứng: [diff commit sửa lỗi](evidence/bugfix_vietnamese_output.diff).

## 5. Giới hạn phạm vi hiện tại (có chủ đích, để lại cho Sprint 2/3)

- Brand Consistency Agent và Compliance Agent còn là stub (Sprint 2, cần brand guideline + rule-based list).
- Chưa có retry/backoff khi LLM hoặc Drupal API lỗi (`docs/architecture.md` mục 7 mô tả nhưng chưa triển khai).
- Chưa có test tự động (pytest); hiện dùng script test thủ công (`scripts/smoke_test_*.py`).
- Chưa có UI báo cáo hiển thị đẹp trong `/admin/content` (mới hiển thị field thô khi mở từng bài viết) — Sprint 2.
- Trọng số Aggregator (0.25/0.20/0.25/0.30) và ngưỡng quyết định (80/50) hiện là giá trị tạm thời, sẽ hiệu chỉnh từ gold set ở Sprint 3.

## 6. Kết luận

Sprint 1 đã hoàn thành đầy đủ 4 mục tiêu đề ra, có bằng chứng kiểm thử thật (không chỉ dựa vào code chạy được mà đã chạy 8 kịch bản khác nhau, kể cả kịch bản chính "bài chưa publish"). Trong quá trình rà soát đã chủ động phát hiện và khắc phục 3 lỗi thật trước khi bàn giao, nâng cao độ tin cậy của hệ thống. Các hạng mục còn thiếu đều là phạm vi đã được lên kế hoạch rõ ràng cho Sprint 2/3, không phải sai sót ngoài dự kiến.
