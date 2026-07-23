# PHẦN 2: NGHIÊN CỨU THIẾT KẾ HỆ THỐNG MULTI-AGENT AI

Tài liệu này trình bày kết quả nghiên cứu bước 2 theo chỉ đạo của mentor: "nghiên cứu xem các agent sẽ có là gì", dựa trên kiến trúc tổng thể đã được mentor cung cấp (Drupal CMS → Orchestrator Agent → 4 agent chuyên biệt → Aggregator/Scoring Agent → Quyết định → cập nhật ngược Drupal CMS). Đây là tài liệu thiết kế ở mức khái niệm, làm cơ sở để mentor review trước khi triển khai code.

## 1. Lựa chọn công nghệ điều phối (Orchestration Framework)

Để triển khai luồng xử lý gồm nhiều agent chạy song song và tổng hợp kết quả, cần một framework điều phối (orchestration framework). Ba lựa chọn được cân nhắc:

| Framework                           | Đặc điểm                                                                                                                                         | Đánh giá                                                                                                                                           |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| LangGraph                           | Xây dựng workflow dạng đồ thị (graph) cố định, hỗ trợ sẵn fan-out/fan-in (chạy song song nhiều nhánh rồi gộp kết quả), quản lý state xuyên suốt. | Khuyến nghị - khớp trực tiếp với sơ đồ kiến trúc dạng cố định, tuần tự của mentor.                                                                 |
| Tự viết orchestrator (Python thuần) | Dùng asyncio gọi song song các agent, tự viết logic gộp kết quả.                                                                                 | Dễ hiểu, kiểm soát hoàn toàn, nhưng phải tự xây lại các cơ chế retry, đồng bộ mà framework có sẵn.                                                 |
| CrewAI                              | Thiết kế cho các "đội" agent tự động ủy quyền công việc cho nhau (autonomous collaboration).                                                     | Không phù hợp - quy trình kiểm duyệt của đề tài là cố định/tuần tự, không cần agent tự quyết định, dùng CrewAI sẽ thừa tính năng và khó kiểm soát. |

**Kết luận:** Chọn LangGraph làm framework điều phối chính cho toàn bộ hệ thống.

## 2. Kiến trúc tổng thể và luồng dữ liệu

### 2.1. State object (đối tượng trạng thái dùng chung)

LangGraph truyền một đối tượng trạng thái duy nhất đi qua toàn bộ đồ thị xử lý, đóng vai trò như một "tờ phiếu theo dõi" đi kèm bài viết - mỗi bước xử lý (node) đọc và ghi thêm thông tin vào đó:

```
ContentReviewState = {
  node_id: str            # UUID bài viết trong Drupal (lấy từ JSON:API)
  title: str
  body: str
  raw_content: dict        # toàn bộ JSON gốc lấy từ Drupal

  content_quality_result: dict | None
  seo_result: dict | None
  brand_result: dict | None
  compliance_result: dict | None

  final_score: float | None
  decision: Literal["publish","needs_revision","rejected"] | None
  report: dict | None
}
```

### 2.2. Đồ thị xử lý (8 node)

Toàn bộ hệ thống gồm 8 bước xử lý (node) nối tiếp nhau:

```
Node 1: Fetch Node                    (lấy nội dung từ Drupal qua JSON:API)
Node 2: Orchestrator/Dispatch         (phát nội dung song song cho 4 agent)
Node 3: Content Quality Agent   ─┐
Node 4: SEO Agent                ├─ chạy song song, độc lập với nhau
Node 5: Brand Consistency Agent  │
Node 6: Compliance Agent        ─┘
Node 7: Aggregator                    (tổng hợp 4 kết quả, tính điểm, ra quyết định)
Node 8: Write-back Node               (ghi kết quả ngược vào Drupal qua PATCH)
```

LangGraph tự động quản lý việc chạy song song 4 node agent và chờ đủ cả 4 kết quả trước khi chuyển sang Aggregator (cơ chế fan-out/fan-in có sẵn), không cần tự viết code đồng bộ thủ công.

### 2.3. Ghi kết quả ngược về Drupal (Write-back Node)

Node cuối cùng trong đồ thị (Node 8) có nhiệm vụ lấy quyết định và báo cáo do Aggregator tạo ra, ghi ngược vào đúng bài viết gốc trong Drupal - để đội content mở lại bài viết là thấy ngay kết quả đánh giá, không cần dùng công cụ nào khác.

Content type "Bài viết" mặc định của Drupal không có sẵn field để lưu kết quả AI, nên cần tạo thêm các field tùy chỉnh sau (qua Cấu trúc > Loại nội dung > Bài viết > Quản lý trường):

| Field mới cần tạo    | Kiểu dữ liệu               | Mục đích                                                   |
| -------------------- | -------------------------- | ---------------------------------------------------------- |
| field_ai_status      | Danh sách chọn (List text) | Lưu 1 trong 3 giá trị: publish / needs_revision / rejected |
| field_ai_score       | Số (Number)                | Lưu điểm tổng (0-100) do Aggregator tính                   |
| field_ai_suggestions | Văn bản dài (Long text)    | Lưu toàn bộ gợi ý sửa tổng hợp từ 4 agent                  |

**Cách ghi ngược - gọi phương thức PATCH của JSON:API:**

```
PATCH http://localhost:8080/jsonapi/node/article/{node_id}
Header: Content-Type: application/vnd.api+json

Body:
{
  "data": {
    "type": "node--article",
    "id": "{node_id}",
    "attributes": {
      "field_ai_status": "needs_revision",
      "field_ai_score": 76.5,
      "field_ai_suggestions": "1. Thiếu meta description...\n2. Câu ở đoạn 1 quá dài..."
    }
  }
}
```

Sau lệnh PATCH này, mở lại bài viết trong giao diện quản trị Drupal, đội content sẽ thấy ngay các field mới hiển thị kết quả đánh giá của hệ Multi-Agent.

## 3. Orchestrator Agent

Orchestrator Agent là thành phần điều phối trung tâm, đứng ngay sau bước lấy nội dung từ Drupal. Nhiệm vụ:

1. Nhận nội dung nháp đã lấy từ Drupal (title, body).

2. Gửi bản sao nội dung đó cho cả 4 agent chuyên biệt để xử lý song song.

3. Theo dõi và đảm bảo đủ 4 kết quả trả về trước khi chuyển tiếp cho Aggregator.

Lưu ý phân biệt với Aggregator: Orchestrator chỉ "gom" kết quả thô lại một chỗ (chưa xử lý), trong khi Aggregator mới là nơi thực hiện tính toán, xử lý các kết quả đó thành điểm số và quyết định cuối cùng.

Về mặt kỹ thuật, LangGraph có khả năng tự động fan-out khi khai báo nhiều cạnh đi ra từ một node, nên có thể triển khai mà không cần một node Orchestrator riêng biệt. Tuy nhiên, đề xuất vẫn giữ Orchestrator như một node riêng để: (1) trung thành với kiến trúc mentor đã cung cấp, thuận tiện khi báo cáo/đối chiếu; (2) tạo sẵn một điểm mở rộng cho các logic tiền xử lý trong tương lai (ví dụ kiểm tra điều kiện tối thiểu của bài viết trước khi gửi cho các agent chấm điểm).

## 4. Phương pháp luận: Cơ sở lựa chọn số lượng và vai trò agent

Theo góp ý của mentor, mục này trình bày căn cứ (không chỉ dựa vào suy luận nội bộ) cho việc kiến trúc gồm đúng 4 agent chuyên biệt, dựa trên khảo sát các thực tiễn và tài liệu ngành hiện có về hệ thống AI xử lý nội dung marketing/SEO.

### 4.1. Khảo sát thực tiễn ngành

Khảo sát các mô hình pipeline nội dung dùng nhiều AI agent hiện đang được áp dụng trong thực tế cho thấy một số điểm chung:

- Các pipeline nội dung dạng agentic phổ biến hiện nay thường tách vai trò theo từng khâu chuyên biệt (researcher, writer, critic, publisher...). Trong đó có một "Optimization Agent" chuyên tối ưu SEO/GEO (mật độ từ khóa, cấu trúc heading, chất lượng meta description), và hệ thống cho phép cấu hình riêng "brand parameters" (thông số thương hiệu) để kiểm soát giọng văn - cho thấy việc tối ưu SEO và kiểm soát thương hiệu được xem là 2 mối quan tâm cần xử lý tách biệt trong một pipeline nội dung.

- Case study thực tế - AWS Marketing & Gradial (Amazon Bedrock, dùng mô hình Claude): đội Marketing của AWS xây dựng hệ thống agentic AI có bước "Quality Validator" kiểm tra đồng thời SEO compliance, accessibility, brand standards, và content health ngay trước khi xuất bản trang - cấu trúc kiểm tra song song nhiều tiêu chí độc lập này tương tự trực tiếp với SEO Agent và Brand Consistency Agent trong đề tài. Kết quả: thời gian dựng trang giảm từ tối đa 4 tiếng xuống còn khoảng 10 phút (giảm 95%), trong khi vẫn duy trì việc kiểm tra chất lượng.

- Case study thực tế - AWS "Scaling content review operations with multi-agent workflow": pipeline gồm 3 agent chuyên biệt nối tiếp - Content Scanner Agent (quét và trích xuất thông tin cần kiểm tra), Content Verification Agent (đối chiếu với nguồn tài liệu chuẩn, phân loại kết quả CURRENT/PARTIALLY_OBSOLETE/FULLY_OBSOLETE), và Recommendation Agent (chuyển kết quả kiểm tra thành gợi ý chỉnh sửa cụ thể) - xác nhận mô hình "mỗi agent phụ trách đúng 1 việc hẹp, chuyển tiếp kết quả cho agent sau" là kiến trúc đã được triển khai thực tế, không chỉ là thiết kế lý thuyết.

- Riêng về SEO, các quy trình SEO chuyên nghiệp hiện nay đã bao gồm nhiều khâu nhỏ (nghiên cứu từ khóa, phân tích đối thủ, tối ưu nội dung, phân tích ý định người dùng...), cho thấy SEO là một mối quan tâm đủ lớn và đặc thù để tách thành 1 agent riêng, không nên gộp chung với việc kiểm tra chất lượng văn bản thông thường.

Tổng hợp: cả 4 mối quan tâm mà tài liệu ngành đề cập - (1) chất lượng nội dung/văn phong, (2) tối ưu SEO, (3) nhất quán thương hiệu, (4) tuân thủ pháp lý - khớp trực tiếp với 4 agent trong sơ đồ mentor cung cấp. Đây là căn cứ đối chiếu bên ngoài cho thấy kiến trúc 4 agent không phải lựa chọn tùy ý, mà phản ánh đúng 4 mối quan tâm độc lập, đã được thực tiễn ngành công nhận là cần xử lý tách biệt.

### 4.2. Đối chiếu: 4 agent hiện tại đã đủ chưa, có cần bổ sung agent nào không

Đối chiếu thêm với tài liệu ngành, có 2 hướng mở rộng khác được một số hệ thống agentic content hiện nay áp dụng nhưng chưa có trong kiến trúc hiện tại:

- GEO Optimizer Agent: một số pipeline hiện đại (2026) bắt đầu bổ sung agent tối ưu nội dung để được các công cụ AI (ChatGPT, Perplexity...) trích dẫn khi trả lời người dùng (Generative Engine Optimization) - đây là nhu cầu mới nổi, khác với SEO truyền thống.

- Visual/Image Consistency Agent: Brand Consistency Agent hiện tại chỉ kiểm tra văn bản (giọng văn, thuật ngữ), chưa kiểm tra tính nhất quán của hình ảnh/logo đính kèm bài viết.

Đề xuất: chưa bổ sung 2 agent này vào phạm vi hiện tại, vì (1) đây là các nhu cầu mở rộng (nice-to-have), không phải yêu cầu cốt lõi theo kiến trúc mentor đã cung cấp; (2) việc thêm agent làm tăng độ phức tạp hệ thống, nên ưu tiên hoàn thiện và kiểm chứng 4 agent cốt lõi trước. Ghi nhận đây là hướng mở rộng tiềm năng cho giai đoạn sau.

### 4.3. So sánh hiệu quả: nhiều agent chuyên biệt so với một agent duy nhất

Các nghiên cứu về hiệu quả multi-agent so với single-agent (2025-2026) cho kết quả không tuyệt đối một chiều, cần phân tích đúng theo đặc điểm bài toán:

- Ủng hộ multi-agent: khi các tác vụ độc lập và có thể chạy song song, dùng nhiều agent thay vì 1 agent xử lý tuần tự giúp giảm thời gian xử lý (wall-clock time) tới 75% (ví dụ: 4 tác vụ độc lập, 1 agent xử lý lần lượt so với 4 agent xử lý song song). Agent dùng công cụ/system prompt tập trung vào 1 lĩnh vực hẹp cũng có xu hướng cho kết quả tốt hơn agent phải xử lý tổng quát nhiều việc cùng lúc trên cùng 1 tác vụ.

- Cần lưu ý (không nên bỏ qua): một số nghiên cứu gần đây chỉ ra rằng khi kiểm soát cùng một mức tài nguyên tính toán (compute/token budget), hệ thống single-agent có thể đạt kết quả tương đương hoặc thậm chí tốt hơn multi-agent trên các tác vụ mang tính suy luận tuần tự (phải chờ bước trước hoàn thành mới thực hiện bước sau) - nghĩa là multi-agent không phải lúc nào cũng tốt hơn, hiệu quả phụ thuộc nhiều vào việc tác vụ có thể chia song song được hay không.

Kết luận áp dụng cho bài toán của đề tài: yếu tố quyết định là cấu trúc tác vụ. Bài toán kiểm duyệt nội dung marketing của đề tài có đặc điểm: 4 khía cạnh đánh giá (chất lượng, SEO, thương hiệu, compliance) hoàn toàn độc lập với nhau, không phụ thuộc lẫn nhau, có thể chấm điểm song song trên cùng 1 nội dung - đúng chính là kịch bản mà các nghiên cứu trên chỉ ra multi-agent phát huy hiệu quả nhất (tác vụ song song, độc lập, mỗi agent chuyên sâu 1 lĩnh vực hẹp). Vì vậy, kiến trúc multi-agent mentor đề xuất được ủng hộ bởi dữ liệu nghiên cứu, không chỉ dựa trên trực giác thiết kế.

**Nguồn tham khảo:**

- Case study AWS Marketing & Gradial (Quality Validator: SEO/accessibility/brand/content health): aws.amazon.com/blogs/machine-learning/from-hours-to-minutes-how-agentic-ai-gave-marketers-time-back-for-what-matters/

- Case study AWS - multi-agent content review workflow (Scanner/Verification/Recommendation Agent): aws.amazon.com/blogs/machine-learning/scaling-content-review-operations-with-multi-agent-workflow/

- Optimization Agent (SEO/GEO) và "brand parameters" trong agentic content pipeline: trysight.ai/blog/content-generation-with-specialized-ai-agents

- 8 core SEO workflows: lyzr.ai/blog/ai-agents-for-seo

- Hiệu quả xử lý song song multi-agent (giảm 75% thời gian): thinking.inc/en/blue-ocean/comparisons/single-agent-vs-multi-agent; single-agent đạt hiệu quả tương đương multi-agent khi kiểm soát compute/token budget: arxiv.org/abs/2604.02460

## 5. Các Agent chuyên biệt

Cả 4 agent có chung một cơ chế vận hành: nhận vào title và body, gửi cho LLM (Claude) kèm theo một system prompt (bộ chỉ dẫn/tiêu chí) cố định và riêng biệt cho từng agent, yêu cầu trả về kết quả theo một cấu trúc JSON cố định (structured output) để Aggregator dễ dàng xử lý tiếp. "4 agent" về bản chất là cùng một mô hình LLM được gọi 4 lần với 4 bộ chỉ dẫn khác nhau, không phải 4 mô hình AI riêng biệt.

### 5.1. Content Quality Agent

**Tiêu chí đánh giá:** chính tả, ngữ pháp, văn phong, độ rõ ràng, câu quá dài/tối nghĩa, tính mạch lạc.

**Output:**

```
{ "score": 0-100, "issues": [{"type","location","suggestion"}], "strengths": [] }
```

### 5.2. SEO Agent

**Tiêu chí đánh giá:** mật độ và vị trí từ khóa chính, độ dài title/meta description, cấu trúc heading (H1/H2), độ dài nội dung, alt text ảnh, internal link.

**Output:**

```
{ "score": 0-100, "keyword_analysis": {}, "meta_issues": [], "heading_structure_ok": bool }
```

### 5.3. Brand Consistency Agent

**Tiêu chí đánh giá:** giọng văn có khớp brand voice guideline không, dùng đúng tên sản phẩm/thuật ngữ chuẩn (ví dụ "VF3" thay vì "VF 3" hoặc "vf3"), sử dụng đúng chuẩn logo/tagline.

Vì brand guideline thường dài hàng chục trang, không thể đưa toàn bộ vào system prompt, agent sẽ dùng kiến trúc RAG (Retrieval-Augmented Generation): brand guideline được cắt nhỏ và lưu vào vector database; mỗi lần chấm 1 bài viết, hệ thống tự động truy vấn (retrieve) các đoạn guideline liên quan nhất tới nội dung đang chấm, rồi mới đưa các đoạn đó (không phải toàn bộ tài liệu) vào prompt gửi cho LLM. Cách này giảm chi phí gọi LLM và tăng độ chính xác khi guideline dài.

Lưu ý: agent này cần một tài liệu "quy chuẩn thương hiệu" (brand guideline) làm căn cứ đưa vào system prompt - nếu VF O2O chưa có sẵn tài liệu này ở dạng có thể đưa vào prompt, đây là việc cần chuẩn bị trước khi triển khai agent.

**Output:**

```
{ "score": 0-100, "violations": [{"rule","found_text","expected"}] }
```

### 5.4. Compliance Agent

**Tiêu chí đánh giá:** claim nhạy cảm/thổi phồng thiếu căn cứ, nội dung có nguy cơ vi phạm luật quảng cáo, thông tin giá/khuyến mãi gây hiểu nhầm.

Đây là agent có rủi ro cao nhất (rủi ro pháp lý) nếu bỏ sót lỗi. Đề xuất kết hợp thêm một danh sách từ/cụm từ cấm dạng rule-based (so khớp cứng) bên cạnh đánh giá bằng LLM, để đảm bảo không bỏ sót các trường hợp đã biết trước, thay vì chỉ phụ thuộc hoàn toàn vào khả năng suy luận của LLM.

Ngoài đánh giá bằng LLM và rule-based blacklist ở trên, Compliance Agent còn cần một cơ chế thứ ba để kiểm tra tính đúng/sai của các claim có thể kiểm chứng bằng số liệu (ví dụ thông số kỹ thuật: tầm hoạt động, thời gian sạc, giá bán) - gọi là fact-check. LLM tự suy luận một mình không đủ để biết một con số cụ thể trong bài viết có đúng thực tế hay không nếu không có tài liệu chuẩn để đối chiếu, nên cơ chế này dùng kiến trúc RAG tương tự Brand Consistency Agent (mục 5.3), nhưng nguồn tài liệu tham chiếu là tài liệu thông số sản phẩm chính thức (không phải brand guideline): tài liệu được cắt nhỏ và lưu vào vector database; khi chấm 1 bài viết, hệ thống trích ra các claim có thể kiểm chứng, truy vấn (retrieve) đoạn tài liệu thông số liên quan nhất, rồi đưa claim kèm đoạn tài liệu đó vào prompt để LLM so sánh khớp/lệch. Nếu phát hiện sai lệch, tạo một flag mới với rule "Thông tin sai lệch so với tài liệu thông số chính thức" - severity mặc định "critical" vì công bố sai thông số kỹ thuật là rủi ro pháp lý rõ ràng, tương tự các rule blacklist hiện có.

Như vậy Compliance Agent gồm 3 nguồn tạo flag độc lập, gộp chung vào 1 danh sách `flags`: (1) LLM đánh giá claim thổi phồng/nhạy cảm, (2) rule-based blacklist so khớp cứng, (3) RAG fact-check đối chiếu tài liệu thông số sản phẩm.

Lưu ý: giống yêu cầu brand guideline ở mục 5.3, cơ chế fact-check cần có sẵn tài liệu thông số sản phẩm chính thức ở dạng văn bản làm nguồn tham chiếu - đây là việc cần chuẩn bị nguồn tài liệu trước khi triển khai.

**Output:**

```
{ "score": 0-100, "flags": [{"severity","rule","excerpt"}] }
```

Trong đó mỗi "flag" là một lỗi cụ thể được phát hiện, có mức độ nghiêm trọng (severity) phân theo 3 cấp: "low" (nhẹ), "medium" (đáng chú ý), "critical" (nghiêm trọng, có nguy cơ vi phạm pháp lý rõ ràng).

## 6. Aggregator / Scoring Agent

Node cuối cùng nhận đủ 4 kết quả, tổng hợp thành một điểm số tổng và một quyết định duy nhất.

### 6.1. Công thức tính điểm tổng (trung bình có trọng số)

Các agent không có mức độ quan trọng như nhau - Compliance (rủi ro pháp lý) được đề xuất trọng số cao nhất, SEO thấp nhất vì chỉ ảnh hưởng thứ hạng tìm kiếm chứ không gây hậu quả nghiêm trọng:

```
final_score = content_quality.score * 0.25
            + seo.score            * 0.20
            + brand.score          * 0.25
            + compliance.score     * 0.30
```

_(Trọng số và các ngưỡng quyết định ở mục 6.2 - ví dụ "80" và "50" - là giá trị tạm thời để minh họa logic. Theo kế hoạch Sprint 3, các ngưỡng này sẽ được hiệu chỉnh lại dựa trên dữ liệu thực tế (xem mục 8.1 - Calibration ngưỡng từ gold set), không dùng số áng chừng khi triển khai chính thức.)_

**Ý nghĩa và căn cứ của công thức, không chỉ dựa vào suy luận nội bộ:**

Công thức tổng có trọng số này là **Weighted Sum Model (WSM)** - còn gọi là Simple Additive Weighting (SAW), một phương pháp Multi-Criteria Decision Analysis (MCDA) kinh điển từ thập niên 1960, dùng phổ biến trong định giá kinh doanh, quản lý dự án, phát triển sản phẩm - không phải cách tính tự nghĩ ra.

Về lý do Compliance được đề xuất trọng số cao nhất: các hệ thống content moderation thực tế đều ưu tiên rủi ro pháp lý/an toàn lên trên các chỉ số khác - nội dung rủi ro cao thường được ưu tiên xử lý/chặn trước, tương tự cơ chế "phủ quyết" (veto) của Compliance Agent (mục 6.2). Có khung tham chiếu chính thức cho nguyên tắc này: NIST AI Risk Management Framework và EU Digital Services Act đều yêu cầu ưu tiên rủi ro pháp lý/tuân thủ trước các tiêu chí khác khi xử lý nội dung. Google cũng có khái niệm tương tự cho SEO: nhóm nội dung YMYL ("Your Money or Your Life") - liên quan tài chính/quyết định mua hàng, như nội dung giá/khuyến mãi xe - đòi hỏi độ chính xác/đáng tin cậy cao hơn hẳn nội dung thông thường, củng cố lý do Compliance được ưu tiên hơn SEO.

Về các con số cụ thể (0.25/0.20/0.25/0.30): chưa có nguồn nào cho ra đúng các con số này, vì đây chỉ là giá trị minh họa được chọn trong quá trình thiết kế ban đầu, chưa qua thẩm định hay quyết định chính thức nào từ phía VF O2O - mức độ coi trọng thật sự giữa các tiêu chí là quyết định kinh doanh nội bộ mà không tài liệu ngành nào biết trước được. Thay vì áng chừng thuần túy, có thể dùng **AHP (Analytic Hierarchy Process)** - phương pháp suy ra trọng số bằng cách so sánh cặp (pairwise comparison) từng 2 tiêu chí một (ví dụ: "Compliance quan trọng hơn SEO bao nhiêu lần: 3x, 5x, 9x?"), rồi tính trọng số toán học từ ma trận so sánh đó thay vì đoán thẳng ra %. Đây là phương pháp dùng rộng rãi trong risk prioritization thực tế. Trọng số suy ra theo cách này vẫn chỉ là giá trị tạm thời, sẽ được thay bằng số liệu thật hiệu chỉnh từ gold set ở Sprint 3 (xem mục 8.2).

**Nguồn tham khảo:**

- Weighted sum model (WSM/SAW), phương pháp MCDA từ thập niên 1960: en.wikipedia.org/wiki/Weighted_sum_model
- Analytic Hierarchy Process (AHP), suy ra trọng số bằng so sánh cặp: sciencedirect.com/topics/social-sciences/analytical-hierarchy-process
- Case study ứng dụng AHP cho risk prioritization thực tế: ijcsrr.org/risk-identification-and-risk-prioritization-using-analytical-hierarchy-process-ahp-case-study-human-capital-management-procurement-and-general-affairs-of-holding-company-pt-abc/
- Content moderation ưu tiên xử lý theo mức độ rủi ro (severity-based triage): arxiv.org/pdf/2108.04401
- NIST AI Risk Management Framework và EU Digital Services Act, ưu tiên rủi ro pháp lý/tuân thủ: prudentpartners.in/content-moderation-services-trust-and-safety-guide/
- Google E-E-A-T/YMYL, độ chính xác cao hơn cho nội dung liên quan tài chính/mua hàng: searchatlas.com/blog/quality-of-content/

### 6.2. Quy tắc ra quyết định

```
if compliance.score < 50 hoặc có flag "severity: critical":
    decision = "rejected"          # bất kể điểm tổng bao nhiêu
elif final_score >= 80:
    decision = "publish"
elif final_score >= 50:
    decision = "needs_revision"
else:
    decision = "rejected"
```

Compliance có "quyền phủ quyết" riêng, độc lập với điểm tổng: một bài viết có thể có văn phong tốt, SEO tốt, đúng thương hiệu, nhưng chỉ cần một câu vi phạm luật quảng cáo (flag "critical") thì vẫn phải chặn lại - tránh trường hợp điểm trung bình cao che lấp một lỗi nghiêm trọng.

"needs_revision" (Cần sửa) áp dụng cho các trường hợp lỗi ở mức có thể sửa nhanh (thiếu field SEO, vài lỗi câu chữ, chưa đúng chuẩn thương hiệu nhẹ) - khác với "rejected" (Từ chối) dành cho lỗi nghiêm trọng cần viết lại hoặc cần con người trực tiếp xem xét.

**Ý nghĩa và căn cứ của ngưỡng 80/50:**

Cấu trúc 3 mức publish/needs_revision/rejected khớp với mô hình **"three-tier moderation"** (auto-approve / human review / auto-reject) đang được dùng phổ biến trong các hệ thống content moderation thực tế: nội dung điểm cao được duyệt tự động, nội dung điểm ở mức giữa (không đủ tự tin để duyệt hẳn, cũng không đủ tệ để từ chối hẳn) được đẩy cho con người xem lại, nội dung điểm quá thấp bị từ chối tự động. Mức 0.7-0.8 (tương đương thang điểm 70-80) được ghi nhận là ngưỡng mặc định phổ biến cho tầng "auto-approve" trong các hệ thống dạng này - khớp với việc chọn "80" làm ngưỡng publish ở đây.

Tuy nhiên, giống như trọng số ở mục 6.1, **không có nguồn nào cho ra đúng 2 con số 80 và 50** cho riêng bài toán - đây vẫn là số minh họa. Điểm khác biệt với trọng số: với ngưỡng quyết định, có sẵn một phương pháp thống kê chuẩn để suy ra số thật từ dữ liệu, gọi là **Youden's Index (chỉ số Youden)** - tính từ đường cong ROC, chọn điểm ngưỡng tối đa hoá (Sensitivity + Specificity - 1) trên tập dữ liệu đã có nhãn thật. Đây chính là nền tảng thống kê cho quy trình "quét nhiều mức ngưỡng, chọn mức cho Recall/F1/Kappa cao nhất" đã mô tả ở mục 8.2 - quy trình đó không phải tự nghĩ ra, mà là một dạng áp dụng của Youden's Index/ROC analysis, phương pháp tiêu chuẩn trong thống kê y tế và học máy để chọn ngưỡng phân loại tối ưu từ dữ liệu thật.

**Nguồn tham khảo:**

- Youden's Index, phương pháp thống kê chuẩn để chọn ngưỡng phân loại tối ưu từ ROC curve: sciencedirect.com/topics/medicine-and-dentistry/youden-index
- Mô hình three-tier moderation (auto-approve/human-review/auto-reject) và ngưỡng mặc định phổ biến 0.7-0.8: mux.com/articles/ai-content-moderation-ugc-video-pipeline-mux-robots

### 6.3. Output cuối cùng

```
{
  "node_id": "67859e3c-...",
  "final_score": 76.5,
  "decision": "needs_revision",
  "missing_agents": [],
  "veto_reason": "Bị từ chối do vi phạm Compliance (severity: critical), độc lập với điểm tổng.",
  "details": { "content_quality": {...}, "seo": {...}, "brand": {...}, "compliance": {...} }
}
```

`missing_agents` liệt kê tên các agent không trả được kết quả (xem mục 6.4). `veto_reason` chỉ xuất hiện khi Compliance phủ quyết bằng flag `critical` trong khi điểm Compliance riêng vẫn từ 50 trở lên - tránh gây hiểu nhầm "điểm không thấp mà vẫn bị từ chối" (xem mục 6.2); nếu điểm Compliance đã dưới 50 thì tự bản thân điểm số đã giải thích được lý do, không cần field này.

Object này chỉ chứa dữ liệu thô để tính toán, chưa có sẵn 1 câu tóm tắt ngôn ngữ tự nhiên - phần gợi ý sửa hiển thị cho người dùng (dạng liệt kê từng lỗi theo từng agent) được Write-back Node build riêng từ `details` và ghi vào `field_ai_suggestions` (mục 2.3).

### 6.4. Xử lý khi một trong 4 agent chuyên biệt bị lỗi/không trả kết quả

Công thức tính điểm ở mục 6.1 giả định luôn có đủ 4 kết quả. Trên thực tế, một agent có thể không trả về kết quả (LLM timeout, lỗi định dạng output sau khi đã retry theo mục 7). Nguyên tắc xử lý chung: khi thiếu dữ liệu, ưu tiên an toàn (fail-safe) - không để việc thiếu dữ liệu dẫn đến quyết định "publish" tự động mà không ai biết dữ liệu bị thiếu.

**Trường hợp 1: Compliance Agent bị lỗi**

Compliance là agent duy nhất có "quyền phủ quyết" (mục 6.2). Nếu nó không chạy được, hệ thống không có cách nào xác minh bài viết có vi phạm pháp lý hay không, nên bắt buộc:

```
if compliance_result is None:
    decision = "needs_revision"   # không bao giờ tự động "publish"
    report.note = "Không thể xác minh compliance - cần con người review thủ công"
```

Áp dụng bất kể 3 agent còn lại chấm điểm cao thế nào - rủi ro pháp lý không xác minh được luôn được ưu tiên hơn lợi ích tự động hóa.

**Trường hợp 2: Content Quality, SEO, hoặc Brand Consistency Agent bị lỗi**

Rủi ro thấp hơn Compliance. Xử lý bằng cách tính lại điểm trung bình chỉ trên các agent còn dữ liệu, chia lại tỷ trọng theo tổng trọng số còn lại, đồng thời ghi rõ trong báo cáo agent nào bị thiếu để người xem biết điểm số chưa đầy đủ. Ví dụ khi SEO Agent lỗi:

```
final_score = content_quality.score * (0.25/0.80)
            + brand.score          * (0.25/0.80)
            + compliance.score     * (0.30/0.80)
# 0.80 = tổng trọng số 3 agent còn lại (0.25 + 0.25 + 0.30)

report.summary += " (Lưu ý: SEO Agent không trả được kết quả, điểm số chưa bao gồm đánh giá SEO)"
```

## 7. Xử lý lỗi (Error handling)

| Tình huống                                 | Cách xử lý                                                                                                                               |
| ------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Drupal API không phản hồi (Fetch Node)     | Thử lại 2-3 lần (retry với backoff); nếu vẫn lỗi thì dừng, không chạy tiếp các agent.                                                    |
| LLM timeout/lỗi khi 1 agent đang chạy      | Thử lại agent đó; nếu vẫn lỗi, đánh dấu agent_status = "failed" thay vì làm sập cả pipeline, Aggregator sẽ biết thiếu dữ liệu agent nào. |
| LLM trả về JSON sai định dạng              | Validate ngay khi nhận; nếu sai, gửi lại yêu cầu kèm thông báo lỗi để LLM tự sửa (1-2 lần), vẫn sai thì coi là agent lỗi.                |
| Ghi ngược vào Drupal thất bại (Write-back) | Thử lại; nếu vẫn lỗi, ghi log cảnh báo để người quản trị biết bài viết đã được chấm nhưng chưa cập nhật lên CMS.                         |

## 8. Kế hoạch kiểm thử

### 8.1. Kiểm thử từng agent và toàn bộ pipeline

Mục đích: kiểm tra tính đúng đắn về mặt chức năng (agent có phát hiện đúng loại lỗi không), thực hiện với bộ mẫu nhỏ, nhanh - khác với gold set ở mục 8.2 (dùng để hiệu chỉnh ngưỡng điểm bằng số liệu thống kê, cần cỡ mẫu lớn hơn).

1. Bộ dữ liệu mẫu (golden set): tạo khoảng 8-10 bài viết mẫu trong Drupal, cố ý bao gồm bài "tốt" (không lỗi), bài lỗi chính tả, bài thiếu SEO, bài sai thuật ngữ thương hiệu, bài vi phạm compliance - để kiểm tra từng agent có phát hiện đúng loại lỗi tương ứng không.

2. Kiểm tra từng agent riêng lẻ trước khi ghép hệ thống: so sánh kết quả AI trả về với đánh giá thủ công.

3. Kiểm tra toàn bộ pipeline end-to-end: chạy từ Fetch đến Write-back trên môi trường Drupal local đã dựng (xem research.md), xác nhận trạng thái và gợi ý được ghi đúng ngược vào Drupal.

4. Kiểm tra trường hợp biên: bài viết rỗng, bài quá ngắn/quá dài, bài chứa thẻ HTML lạ trong body.

### 8.2. Calibration ngưỡng quyết định từ gold set

Theo yêu cầu Sprint 3 của mentor, các ngưỡng quyết định (mục 6.2) không được đặt tùy ý mà phải tính toán từ dữ liệu thực tế, theo quy trình sau:

1. Thu thập gold set: tập hợp 30-50 bài viết, mời người có chuyên môn (đội content VF O2O) chấm thủ công theo đúng 3 mức: publish / needs_revision / rejected - đây là "đáp án chuẩn" để đối chiếu.

2. Chạy hệ thống AI trên toàn bộ gold set, thu lại kết quả (điểm số + quyết định) của từng bài.

3. Tính Recall và F1: với từng agent (đặc biệt Compliance Agent), đo AI có phát hiện đủ các lỗi mà người chấm đã xác nhận là lỗi thật hay không (Recall), và có báo động giả quá nhiều không (Precision, gộp lại thành F1).

4. Tính Cohen's Kappa: đo mức độ đồng thuận giữa quyết định cuối cùng của AI và của người chấm, đã loại trừ phần trùng khớp ngẫu nhiên do phân bố lệch (ví dụ đa số bài đều "publish").

5. Quét nhiều mức ngưỡng khác nhau (ví dụ final_score từ 70 đến 90, bước nhảy 2 điểm) và chọn ra ngưỡng cho kết quả Recall/F1/Kappa cao nhất khi so với gold set - đây mới là ngưỡng chính thức áp dụng, thay cho các số minh họa 80/50 ở mục 6.2.

### 8.3. Shadow-test trước khi vận hành chính thức

Trước khi cho hệ thống AI có quyền quyết định publish/từ chối thật, chạy giai đoạn shadow-test (đề xuất 2-4 tuần):

- Quy trình duyệt nội dung hiện tại (con người) vẫn giữ nguyên, tiếp tục quyết định publish thật như bình thường, không bị ảnh hưởng bởi hệ thống AI.

- Song song, hệ thống AI cũng chấm toàn bộ các bài viết đó, nhưng kết quả chỉ được ghi lại để theo dõi (không có quyền quyết định thật, không hiển thị cho người duyệt để tránh gây ảnh hưởng tới quyết định của họ).

- Sau giai đoạn shadow-test, so sánh toàn bộ kết quả AI với quyết định thật của người (dùng lại Recall/F1/Kappa như mục 8.2) trên dữ liệu thực tế quy mô lớn hơn gold set ban đầu.

- Chỉ khi kết quả shadow-test đạt mức đồng thuận đủ tin cậy mới cân nhắc giao quyền quyết định thật cho hệ thống AI - tránh rủi ro để AI tự quyết định publish/từ chối ngay từ đầu khi chưa được kiểm chứng trên dữ liệu thực tế.

## 9. Kết luận và bước tiếp theo

Tài liệu đã hoàn thành nghiên cứu bước 2 theo yêu cầu mentor: xác định rõ vai trò, input/output, và công nghệ triển khai (LangGraph) cho từng thành phần trong kiến trúc hệ thống Multi-Agent AI. Kiến trúc tổng thể được giữ nguyên 1:1 theo sơ đồ mentor cung cấp; LangGraph chỉ là công cụ triển khai kỹ thuật, không làm thay đổi bản thiết kế.
