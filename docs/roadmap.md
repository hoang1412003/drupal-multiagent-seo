# PHẦN 3: KẾ HOẠCH TRIỂN KHAI (theo lộ trình mentor giao)

Sau khi review 2 phần nghiên cứu trên, mentor đã duyệt hướng đi và giao lộ trình triển khai cụ thể theo 3 sprint, với sản phẩm bàn giao là một Web App chạy được thật trên Drupal, không chỉ dừng ở tài liệu thiết kế.

## 1. Tiêu chí hoàn thành chung

Chạy được luồng end-to-end trên Drupal: một node ở trạng thái "Needs Review" được các agent tự động chấm điểm, với ngưỡng quyết định được tính toán từ gold set 30-50 mẫu (không phải số áng chừng - xem mục 8.2 trong architecture.md). Kết quả (lỗi/rủi ro theo từng field) hiển thị ngay trong giao diện editor của Drupal. Sản phẩm bàn giao gồm: Web App, slide thuyết trình, và demo.

## 2. Lộ trình 3 sprint

### Sprint 1

- Nghiên cứu kiến trúc, chốt công nghệ điều phối (đã hoàn thành - xem architecture.md, mục 1: chọn LangGraph).

- Cải tạo Drupal (tạo content type/field cần thiết) + xây dựng AI Core (kết nối LLM, xử lý prompt).

- Dựng khung Orchestrator (node Fetch, Dispatch, State object - xem architecture.md, mục 2-3).

- Xây thử Agent SEO và Content Quality Agent (2 agent không phụ thuộc brand guideline, có thể làm ngay).

### Sprint 2

- Xây Agent Brand Voice dùng kiến trúc RAG (cần có brand guideline từ mentor/phòng marketing - xem architecture.md, mục 5.3).

- Xây Agent Compliance/Fact-check.

- Hoàn thiện logic tổng hợp điểm của Orchestrator (Aggregator - xem architecture.md, mục 6).

- Bắt đầu thu thập và gán nhãn gold set (30-50 mẫu, chuẩn bị cho calibration ở Sprint 3).

- Dựng UI báo cáo cơ bản (hiển thị kết quả đánh giá ngay trong giao diện editor Drupal).

### Sprint 3

- Calibration ngưỡng quyết định từ gold set, dùng F1/Recall và Cohen's Kappa (quy trình chi tiết tại architecture.md, mục 8.2).

- Chạy shadow-test toàn hệ thống trước khi trao quyền quyết định thật (quy trình chi tiết tại architecture.md, mục 8.3).

- Hoàn thiện UI, viết tài liệu vận hành.

- Demo bàn giao sản phẩm.

## 3. Ghi chú quan trọng từ mentor

"Mặc dù dùng AI, nhưng các phần lõi em cũng cần research sâu hơn để hiểu thật sự" - mentor nhấn mạnh việc dùng công cụ AI hỗ trợ không thay thế việc tự nghiên cứu và hiểu sâu các khái niệm kỹ thuật cốt lõi (kiến trúc multi-agent, RAG, phương pháp luận calibration thống kê, shadow-testing) trước khi triển khai. Tài liệu ở research.md và architecture.md là nền tảng nghiên cứu; các khái niệm mới (RAG, Cohen's Kappa, shadow-test) cần được hiểu rõ bản chất, không chỉ áp dụng theo hướng dẫn.
