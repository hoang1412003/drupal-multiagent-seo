# VF O2O Multi-Agent Content Review

Hệ thống Multi-Agent AI hỗ trợ kiểm duyệt, đánh giá và tối ưu nội dung Marketing trước khi xuất bản trên Drupal CMS.

**Phạm vi:** bài cẩm nang / hướng dẫn tiếng Việt về xe điện (nguồn công khai vinfastauto.com); hệ thống chấm điểm và trả *đề xuất* theo từng field, không tự động xuất bản. Nguồn dữ liệu hoàn toàn công khai, không dùng tài liệu nội bộ VF O2O.

Tài liệu (cập nhật song song với code, xem trực tiếp trên GitHub):
- [`docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md`](docs/superpowers/specs/2026-07-24-marketing-content-scope-design.md) — định nghĩa phạm vi "nội dung Marketing" và kiến trúc đánh giá (tài liệu tham chiếu chuẩn)
- [`docs/research.md`](docs/research.md) — nghiên cứu Drupal CMS (kiến trúc, SEO, JSON:API)
- [`docs/architecture.md`](docs/architecture.md) — thiết kế hệ thống Multi-Agent (LangGraph, 4 agent, Aggregator, calibration, shadow-test)
- [`docs/rubrics.md`](docs/rubrics.md) — rubric chấm điểm 4 agent (mức rời rạc + hàm tất định, thay cho điểm 0-100 do LLM tự đặt)
- [`docs/rag-design.md`](docs/rag-design.md) — thiết kế RAG cho Brand Voice KB và Fact-check KB (embedding tiếng Việt, chunking, cách đo recall@k)
- [`docs/editor-ui-design.md`](docs/editor-ui-design.md) — hiển thị báo cáo theo từng field trong giao diện soạn bài Drupal (module `vf_ai_review`)
- [`docs/evaluation-plan.md`](docs/evaluation-plan.md) — 6 phép đo dự án phải chạy, thứ tự phụ thuộc, tiêu chí đạt và ngân sách
- [`docs/prompt-injection.md`](docs/prompt-injection.md) — mô hình mối đe doạ khi LLM đọc nội dung do người ngoài soạn, và biện pháp giảm thiểu
- [`docs/goldset/annotation-guideline.md`](docs/goldset/annotation-guideline.md) — quy tắc gán nhãn gold set và cách đo độ tin cậy của nhãn
- [`docs/goldset/sources.md`](docs/goldset/sources.md) — nguồn dữ liệu thật + phân chia `BRAND`/`GOLD`/`PERT`
- [`docs/roadmap.md`](docs/roadmap.md) — lộ trình 3 sprint theo kế hoạch mentor giao

## Cấu trúc project

Hai thư mục cấp cao nhất tương ứng đúng 2 phía trong kiến trúc (Drupal CMS ↔ hệ Multi-Agent AI, nối qua JSON:API — xem sơ đồ ở `docs/architecture.md`):

```
drupal-multiagent-seo/
├── drupal/                      # PHÍA DRUPAL - project Drupal 10 chạy qua DDEV
│   ├── .ddev/                    # cấu hình DDEV (project-type=drupal10, docroot=web)
│   └── web/                      # code Drupal (mở trực tiếp bằng VS Code)
│
├── multiagent/                  # PHÍA PYTHON - hệ Multi-Agent AI
│   ├── requirements.txt
│   ├── .venv/
│   ├── src/
│   │   ├── ai_core.py            # gọi Claude API dùng chung cho cả 4 agent (structured output)
│   │   ├── state.py              # ContentReviewState (đối tượng trạng thái dùng chung)
│   │   ├── drupal_client.py      # gọi JSON:API Drupal (fetch/patch nội dung)
│   │   ├── agents/
│   │   │   ├── content_quality.py  # đã triển khai
│   │   │   ├── seo.py              # đã triển khai
│   │   │   ├── compliance.py       # đã triển khai (LLM + rule-based blacklist) - Sprint 2
│   │   │   └── (brand voice)        # Sprint 2 - còn là stub trong graph.py
│   │   └── graph.py              # đồ thị LangGraph (Orchestrator, fan-out/fan-in, Aggregator)
│   └── scripts/                  # seed dữ liệu mẫu + test thủ công
│
├── docs/                         # tài liệu chung, tham chiếu cả 2 phía
│   ├── research.md               # nghiên cứu Drupal CMS
│   ├── architecture.md           # thiết kế hệ thống Multi-Agent
│   └── roadmap.md                # lộ trình 3 sprint
│
└── .env.example                  # copy thành .env và điền ANTHROPIC_API_KEY
```

## Setup

**Phía Drupal** (dùng [DDEV](https://ddev.com) — công cụ local dev được Drupal.org khuyến nghị chính thức từ 6/2024):

```
cd drupal
ddev start
```

Site chạy tại `http://drupal.ddev.site`. Nếu tạo project từ đầu, xem quy trình đầy đủ ở `docs/architecture.md` mục 2 (research.md có link tham khảo DDEV quickstart chính thức).

Trong Drupal admin, cần bật thêm:
- `/admin/config/services/jsonapi` — tick "Accept all JSON:API create, read, update, and delete operations"
- `/admin/modules` — bật module "HTTP Basic Authentication"
- Tạo field `field_meta_description` trên content type Article (`/admin/structure/types/manage/article/fields`) — kiểu "Text (plain, long)"

**Phía Python:**

```
cd multiagent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp ..\.env.example ..\.env   # rồi điền ANTHROPIC_API_KEY, DRUPAL_USER, DRUPAL_PASSWORD, DRUPAL_BASE_URL
```

## Trạng thái Sprint 1

- [x] Nghiên cứu kiến trúc, chốt công nghệ điều phối (LangGraph)
- [x] Dựng Drupal local, bật JSON:API
- [x] Tạo field tùy chỉnh trên Drupal (field_ai_status, field_ai_score, field_ai_suggestions)
- [x] AI Core (gọi Claude API, model claude-haiku-4-5-20251001, structured output)
- [x] Khung Orchestrator (LangGraph, 8 node, 4 agent còn là stub)
- [x] Agent SEO & Content Quality (thử nghiệm, chạy thật end-to-end)

**Sprint 1 hoàn thành.** Tiếp theo: Sprint 2 (Brand Voice Agent với RAG, Compliance Agent, hoàn thiện Aggregator, thu thập gold set) — xem [`docs/roadmap.md`](docs/roadmap.md).
