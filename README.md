# VF O2O Multi-Agent Content Review

Hệ thống Multi-Agent AI hỗ trợ kiểm duyệt, đánh giá và tối ưu nội dung Marketing trước khi xuất bản trên Drupal CMS.

Tài liệu (cập nhật song song với code, xem trực tiếp trên GitHub):
- [`docs/research.md`](docs/research.md) — nghiên cứu Drupal CMS (kiến trúc, SEO, JSON:API)
- [`docs/architecture.md`](docs/architecture.md) — thiết kế hệ thống Multi-Agent (LangGraph, 4 agent, Aggregator, calibration, shadow-test)
- [`docs/roadmap.md`](docs/roadmap.md) — lộ trình 3 sprint theo kế hoạch mentor giao

## Cấu trúc project

```
VF_O2O/
├── docker-compose.yml          # Drupal + MySQL local instance
├── requirements.txt            # Python dependencies
├── .env.example                 # copy thành .env và điền ANTHROPIC_API_KEY
├── src/
│   ├── ai_core.py               # gọi Claude API dùng chung cho cả 4 agent (structured output)
│   ├── state.py                # ContentReviewState (đối tượng trạng thái dùng chung)
│   ├── drupal_client.py        # gọi JSON:API Drupal (fetch/patch nội dung)
│   ├── agents/
│   │   ├── content_quality.py  # đã triển khai
│   │   └── seo.py              # đã triển khai (Brand + Compliance: Sprint 2, hiện là stub trong graph.py)
│   └── graph.py                # đồ thị LangGraph (Orchestrator, fan-out/fan-in, Aggregator)
└── docs/
    ├── research.md             # nghiên cứu Drupal CMS
    ├── architecture.md         # thiết kế hệ thống Multi-Agent
    └── roadmap.md              # lộ trình 3 sprint
```

## Setup

```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp .env.example .env   # rồi điền ANTHROPIC_API_KEY, DRUPAL_USER, DRUPAL_PASSWORD
docker compose up -d   # khởi động Drupal + MySQL
```

Trong Drupal admin, cần bật thêm 2 thứ (tắt mặc định):
- `/admin/config/services/jsonapi` — tick "Accept all JSON:API create, read, update, and delete operations"
- `/admin/modules` — bật module "HTTP Basic Authentication"

## Trạng thái Sprint 1

- [x] Nghiên cứu kiến trúc, chốt công nghệ điều phối (LangGraph)
- [x] Dựng Drupal local, bật JSON:API
- [x] Tạo field tùy chỉnh trên Drupal (field_ai_status, field_ai_score, field_ai_suggestions)
- [x] AI Core (gọi Claude API, model claude-haiku-4-5-20251001, structured output)
- [x] Khung Orchestrator (LangGraph, 8 node, 4 agent còn là stub)
- [x] Agent SEO & Content Quality (thử nghiệm, chạy thật end-to-end)

**Sprint 1 hoàn thành.** Tiếp theo: Sprint 2 (Brand Voice Agent với RAG, Compliance Agent, hoàn thiện Aggregator, thu thập gold set) — xem [`docs/roadmap.md`](docs/roadmap.md).
