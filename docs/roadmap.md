# PHẦN 3: KẾ HOẠCH TRIỂN KHAI (theo lộ trình mentor giao)

Sau khi review 2 phần nghiên cứu trên, mentor đã duyệt hướng đi và giao lộ trình triển khai cụ thể theo 3 sprint, với sản phẩm bàn giao là một Web App chạy được thật trên Drupal, không chỉ dừng ở tài liệu thiết kế.

## 1. Tiêu chí hoàn thành chung

Chạy được luồng end-to-end trên Drupal: một node ở trạng thái "Needs Review" được các agent tự động chấm điểm, với ngưỡng quyết định được tính toán từ gold set 30-50 mẫu (không phải số áng chừng - xem mục 8.2 trong architecture.md). Kết quả (lỗi/rủi ro theo từng field) hiển thị ngay trong giao diện editor của Drupal, dưới dạng *đề xuất* cho người duyệt - hệ thống không tự động xuất bản. Sản phẩm bàn giao gồm: Web App, slide thuyết trình, và demo.

**Phạm vi nội dung:** bài cẩm nang / hướng dẫn tiếng Việt về xe điện (nguồn công khai vinfastauto.com), không dùng tài liệu nội bộ VF O2O. Đây là phạm vi tập trung có chủ đích, không set cứng - kiến trúc config-driven cho phép mở rộng loại nội dung/ngôn ngữ theo lộ trình phân tầng P0/P1/P2 (architecture.md mục 5.6). Định nghĩa đầy đủ: `docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md`.

## 2. Lộ trình 3 sprint

### Sprint 1

- Nghiên cứu kiến trúc, chốt công nghệ điều phối (đã hoàn thành - xem architecture.md, mục 1: chọn LangGraph).

- Cải tạo Drupal (tạo content type/field cần thiết) + xây dựng AI Core (kết nối LLM, xử lý prompt).

- Dựng khung Orchestrator (node Fetch, Dispatch, State object - xem architecture.md, mục 2-3).

- Xây thử Agent SEO và Content Quality Agent (2 agent không phụ thuộc brand guideline, có thể làm ngay).

### Sprint 2

- Xây Agent Brand Voice dùng kiến trúc RAG, với brand guideline **tự trích xuất từ corpus bài cẩm nang công khai** (không có tài liệu nội bộ - xem architecture.md, mục 5.3).

- Xây Agent Compliance/Fact-check (nguồn đối chiếu: thông số sản phẩm công bố công khai + căn cứ pháp lý Luật Quảng cáo 2012, Luật Cạnh tranh 2018 - xem architecture.md, mục 5.4).

- Hoàn thiện logic tổng hợp điểm của Aggregator (module tất định, không gọi LLM - xem architecture.md, mục 6).

- Bắt đầu thu thập và gán nhãn gold set (30-50 mẫu bài cẩm nang công khai, ~60% bài thật + ~40% chèn lỗi có chủ đích, tự gán nhãn - chuẩn bị cho calibration ở Sprint 3).

- Tự động hóa quy trình: bật Content Moderation ("Needs Review") + polling worker tự phát hiện bài cần chấm (architecture.md mục 9), thay cho chạy script thủ công.

- Dựng UI báo cáo cơ bản (hiển thị kết quả đánh giá ngay trong giao diện editor Drupal).

### Sprint 3

- [x] **Calibration ngưỡng quyết định từ gold set** (architecture.md mục 8.2) — chạy 2026-08-16. ⛔ **Đã đo nhưng KHÔNG chốt được ngưỡng**: `publish_min = 80` đề xuất `publish` cho 9/33 bài người nói cần sửa, và gold set có 0 mẫu `publish` để calibrate. `meta.calibrated` vẫn `false`. Evidence: [`evidence/e5_e6_ban4_report.md`](evidence/e5_e6_ban4_report.md).

- [x] **Shadow-test** (architecture.md mục 8.3) — đã viết lại thành **held-out test bằng k-fold** vì không có quy trình vận hành thật để chạy song song (evaluation-plan mục 4.6.1). Chạy 2026-08-16, selection bias +0,000.

- [x] **Các phép đo còn lại:** E1 đạt (σ 1,60), E3 cho thấy kiến trúc 4 agent thắng (0,406 so với 0,302), E4 có provenance đầy đủ, test–retest nhãn Kappa 1,000, functional-clean `publish_rate` 10/10.

- [ ] **Hai quyết định thiết kế cần mentor** — cùng một câu hỏi *ai được quyền chặn xuất bản?*: (1) có thêm cổng "bất kỳ tiêu chí mức 0 → trần `needs_revision`" để khớp quy tắc dừng sớm của người gán nhãn không; (2) một phán đoán thuần LLM có được phép một mình sinh `critical` không. Cả hai đổi `graph.aggregator_node`/agent nên **phải đo lại E1/E5/E6** sau khi sửa. Chi tiết: `technical-debt.md` mục 8.2, 8.4, 8.6.

- [ ] **Hoàn thiện UI** — thiết kế mới cho khối báo cáo lỗi trong màn soạn bài đã có bundle handoff (`Trang hiển thị lỗi Agent/`), **chưa triển khai**. Hoãn có chủ đích tới khi xong chuỗi đo lường; nay đã xong.

- [ ] Viết tài liệu vận hành.

- [ ] Demo bàn giao sản phẩm.

## 3. Luồng song song: productization nền tảng Multi-Agent

**Đã duyệt thiết kế ngày 2026-08-12; toàn bộ P1→P5 đã triển khai và qua checkpoint ngày 2026-08-14.** Ma trận nghiệm thu 11/11 pass: [`evidence/platform-mvp-acceptance.md`](evidence/platform-mvp-acceptance.md). Luồng này không thay thế và không tự mở rộng tiêu chí hoàn thành Sprint 3 do mentor giao.

⚠️ **Nền tảng xong KHÔNG có nghĩa là đã có kết quả chấm điểm.** Mọi run sinh ra trong P1→P5 đều `is_fixture=true` do engine giả đặt điểm. E1/E3/E5/E6 vẫn chưa chạy. Mục tiêu là tách Multi-Agent thành service độc lập có API, connector Drupal, site/profile, trang quản trị và phân quyền để có thể tái sử dụng sau này. Phạm vi MVP vẫn chỉ là Việt Nam, tiếng Việt, bài `cam_nang` và một Drupal site.

Thiết kế chuẩn: [`superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`](superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md). Kế hoạch triển khai tổng và 5 plan con: [`superpowers/plans/2026-08-12-standalone-multiagent-platform.md`](superpowers/plans/2026-08-12-standalone-multiagent-platform.md). Có plan không có nghĩa code đã được triển khai.

| Pha | Kết quả |
|---|---|
| P1 — Nền dữ liệu — ✅ xong | Migration có version/checksum; site/profile mặc định; scoped queue/audit; nâng schema cũ không mất dữ liệu. Evidence: `docs/evidence/platform-foundation-verification.txt` |
| P2 — Auth + admin shell — ✅ xong | Local account, session, CSRF, RBAC, bootstrap admin, audit nền. Evidence: `docs/evidence/platform-admin-auth-verification.txt` |
| P3 — Vận hành — ✅ xong | Dashboard, jobs/history, retry có cảnh báo chi phí, users, config/KB/evaluation chỉ đọc và audit. Evidence: `docs/evidence/platform-admin-operations-verification.txt` |
| P4 — API/connector — ✅ xong | `/api/v1`, credential/config theo site, Drupal connector đọc đúng revision, result callback CAS/idempotent, legacy hash-v1 rollback, dedup, pause/resume. Evidence: `docs/evidence/platform-api-cutover-verification.txt` và `platform-api-connector-verification.txt` |
| P5 — Hardening/rollout — ✅ xong | Worker heartbeat thật, `llm_usage_event` bền vững, redaction + security header, usage theo từng agent, ba role Drupal least-privilege, E2E + ma trận 14 case lỗi + quét rò rỉ, test runner một lệnh + CI, diễn tập backup/restore. Evidence: `docs/evidence/platform-backup-restore-rehearsal.txt`, `platform-rollout-smoke.txt`, `platform-mvp-acceptance.md` |

*(Kế hoạch chỉ có **5** pha. Bản trước của bảng này ghi "P6 — Hardening" là sai: nội dung đó nằm trong P5.)*

**Hàng rào với Sprint 3:** productization chỉ thay lớp bao quanh. Không sửa 4 agent, prompt, `fact_check.py`, `scoring.py`, Aggregator, rule, KB hoặc `scoring.yaml` trong lúc E1/E5 đang khóa. Nếu `prompt_version` khác `020738e209017213`, dừng luồng productization và đánh giá lại phép đo trước khi tiếp tục.

## 4. Ghi chú quan trọng từ mentor

"Mặc dù dùng AI, nhưng các phần lõi em cũng cần research sâu hơn để hiểu thật sự" - mentor nhấn mạnh việc dùng công cụ AI hỗ trợ không thay thế việc tự nghiên cứu và hiểu sâu các khái niệm kỹ thuật cốt lõi (kiến trúc multi-agent, RAG, phương pháp luận calibration thống kê, shadow-testing) trước khi triển khai. Tài liệu ở research.md và architecture.md là nền tảng nghiên cứu; các khái niệm mới (RAG, Cohen's Kappa, shadow-test) cần được hiểu rõ bản chất, không chỉ áp dụng theo hướng dẫn.
