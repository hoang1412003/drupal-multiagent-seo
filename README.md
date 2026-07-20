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
│   ├── state.py                # ContentReviewState (đối tượng trạng thái dùng chung)
│   ├── drupal_client.py        # gọi JSON:API Drupal (fetch/patch nội dung)
│   ├── agents/                 # 4 agent chuyên biệt
│   └── graph.py                # đồ thị LangGraph (Orchestrator, fan-out/fan-in, Aggregator)
└── docs/
    ├── research.md             # nghiên cứu Drupal CMS
    ├── architecture.md         # thiết kế hệ thống Multi-Agent
    └── roadmap.md              # lộ trình 3 sprint
```

## Setup

```
pip install -r requirements.txt
cp .env.example .env   # rồi điền ANTHROPIC_API_KEY
docker compose up -d   # khởi động Drupal + MySQL
```

## Trạng thái Sprint 1

- [x] Nghiên cứu kiến trúc, chốt công nghệ điều phối (LangGraph)
- [x] Dựng Drupal local, bật JSON:API
- [x] Tạo field tùy chỉnh trên Drupal (field_ai_status, field_ai_score, field_ai_suggestions)
- [ ] AI Core (gọi Claude API)
- [ ] Khung Orchestrator (LangGraph)
- [ ] Agent SEO & Content Quality (thử nghiệm)
