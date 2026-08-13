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
- [`docs/config-spec.md`](docs/config-spec.md) — đặc tả `scoring.yaml`: trọng số và ngưỡng theo `(content_type, langcode)`, là đầu ra của calibration
- [`docs/operations.md`](docs/operations.md) — nhật ký truy vết mỗi lần chấm và vòng phản hồi người duyệt
- [`docs/goldset/annotation-guideline.md`](docs/goldset/annotation-guideline.md) — quy tắc gán nhãn gold set và cách đo độ tin cậy của nhãn
- [`docs/goldset/sources.md`](docs/goldset/sources.md) — nguồn dữ liệu thật + phân chia `BRAND`/`GOLD`/`PERT`
- [`docs/brand/brand_guideline.md`](docs/brand/brand_guideline.md) — brand guideline **sinh tự động** từ corpus 16 bài `BRAND`, mỗi quy tắc kèm số liệu và p-value chứng minh
- [`docs/roadmap.md`](docs/roadmap.md) — lộ trình 3 sprint theo kế hoạch mentor giao
- [`docs/technical-debt.md`](docs/technical-debt.md) — nợ kỹ thuật và giới hạn đã biết, kèm bằng chứng và thứ tự xử lý đề xuất
- [`docs/pre-demo-checklist.md`](docs/pre-demo-checklist.md) — việc phải làm trước khi demo/bàn giao: cấu hình dev quên tắt, KB phải dựng lại trên máy mới, và cách nói đúng về ngưỡng chưa calibrate
- [`docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`](docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md) — thiết kế đã duyệt để tách Multi-Agent thành service độc lập và thêm trang quản trị; **chưa triển khai code**
- [`docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md`](docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md) — implementation plan tổng và 5 plan con; **mới là kế hoạch, chưa phải module đang tồn tại**

### Dành cho AI/model tiếp nhận dự án

Không suy trạng thái hiện hành từ ngày sửa file hoặc từ các báo cáo lịch sử. Trước khi đề xuất việc tiếp theo, model phải đọc theo thứ tự:

1. [`docs/technical-debt.md` mục 8 — BÀN GIAO](docs/technical-debt.md#8-bàn-giao--việc-còn-lại-cập-nhật-2026-08-12) — **nguồn sự thật cho trạng thái đang làm**, việc kế tiếp, lệnh chạy, cổng chi phí và các việc tuyệt đối chưa được suy đoán là đã xong.
2. [`docs/evaluation-plan.md` mục 3a và 4](docs/evaluation-plan.md#3a-khoá-code-chấm-điểm--2026-08-12-bản-4) — hợp đồng đo lường, bộ code/prompt/model đã khoá và cách phân biệt kết quả hiện hành với số lịch sử.
3. Tài liệu chuyên biệt theo việc đang làm; riêng gán nhãn/test–retest phải đọc [`docs/goldset/annotation-guideline.md` mục 8](docs/goldset/annotation-guideline.md#8-đo-độ-tin-cậy-của-chính-nhãn).

Nếu các tài liệu mâu thuẫn, dừng và đối chiếu bằng commit, `prompt_version` do code tính và file evidence; không tự chọn con số thuận lợi hơn. Những mục có nhãn **hết hiệu lực/lịch sử** chỉ dùng để giải thích quá trình, không được báo cáo như kết quả của code hiện hành.

Với công việc liên quan service độc lập, admin, auth, site/connector hoặc profile thị trường, phải đọc [thiết kế productization đã duyệt](docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md), [implementation plan tổng](docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md), rồi sáu quyết định sau review ở `docs/technical-debt.md` mục 8.9. Đặc biệt không thay result callback CAS bằng JSON:API PATCH, không bỏ legacy hash v1 trong cửa sổ rollback và không coi cấu trúc “planned” là code đã tồn tại; chỉ task có commit/evidence mới được đánh dấu triển khai.

## Cấu trúc project

Hai thư mục cấp cao nhất tương ứng đúng 2 phía trong kiến trúc (Drupal CMS ↔ hệ Multi-Agent AI, nối qua JSON:API **và** qua service HTTP tự động hoá — xem sơ đồ ở `docs/architecture.md` mục 9). Phía Python nay chạy như **ba tiến trình**: service (`api.py`, nhận job), worker (`worker.py`, chấm job) và các script chạy tay (seed dữ liệu, test, dựng KB) — không còn chỉ là script gọi một lần:

```
drupal-multiagent-seo/
├── drupal/                      # PHÍA DRUPAL - project Drupal 10 chạy qua DDEV
│   ├── .ddev/                    # cấu hình DDEV (project-type=drupal10, docroot=web)
│   ├── scripts/                  # tạo field + test lớp render (PHP thuần)
│   └── web/modules/custom/
│       ├── vf_ai_review/         # CHỈ ĐỌC: hiển thị báo cáo AI trong giao diện soạn bài,
│       │                          # không tính điểm, không gọi API, không sửa dữ liệu node
│       └── vf_ai_trigger/        # module thứ hai, tách riêng vì nói chuyện với service:
│                                  # bắt sự kiện Needs Review, gọi service HTTP, route
│                                  # "chấm lại" - đây là module duy nhất phía Drupal được
│                                  # phép tạo hiệu ứng phụ (side effect)
│
├── multiagent/                  # PHÍA PYTHON - hệ Multi-Agent AI
│   ├── requirements.txt
│   ├── docker-compose.yml        # Postgres + pgvector (kho vector + hàng đợi + run_log, tách khỏi Drupal)
│   ├── .venv/
│   ├── src/
│   │   ├── ai_core.py            # gọi Claude API dùng chung cho cả 4 agent (structured output)
│   │   ├── state.py              # ContentReviewState (đối tượng trạng thái dùng chung)
│   │   ├── drupal_client.py      # gọi JSON:API Drupal (fetch/patch nội dung)
│   │   ├── embeddings.py         # interface Embedder + BGE-M3 self-host (cho cả 2 KB RAG)
│   │   ├── db.py                 # kết nối Postgres + pgvector, tạo bảng kb_chunk
│   │   ├── retrieval.py          # truy vấn KB theo (content_type, langcode)
│   │   ├── scoring.py            # quy mức rubric 0/1/2/NA ra điểm 0-100 (tất định)
│   │   ├── brand_analysis.py     # đếm đặc trưng brand + kiểm định nhị thức (dùng chung)
│   │   ├── text_utils.py         # strip_html dùng chung script offline và agent runtime
│   │   ├── kb/                   # KB fact-check (specs.json) + KB brand (build_brand_kb.py)
│   │   ├── agents/
│   │   │   ├── content_quality.py  # đã triển khai
│   │   │   ├── seo.py              # đã triển khai
│   │   │   ├── compliance.py       # đã triển khai (LLM + blacklist + RAG fact-check CP3) - Sprint 2
│   │   │   ├── fact_check.py        # CP3: trích claim định lượng, đối chiếu KB thông số
│   │   │   └── brand_voice.py       # đã triển khai (rubric BV1-BV7 + RAG) - Sprint 2
│   │   ├── graph.py              # đồ thị LangGraph (Orchestrator, fan-out/fan-in, Aggregator)
│   │   ├── api.py                # service HTTP: chỉ nhận job + trả trạng thái, không chấm gì
│   │   ├── job_queue.py          # hàng đợi Postgres (SKIP LOCKED, retry, dead-letter)
│   │   ├── worker.py             # vòng lặp lấy job, gọi graph.py, ghi run_log, write-back
│   │   ├── reconcile.py          # vòng đối soát định kỳ - lưới an toàn cho đường event
│   │   └── audit.py              # nhật ký truy vết, ghi bảng run_log (Postgres)
│   └── scripts/                  # seed dữ liệu mẫu + test thủ công
│
├── docs/                         # tài liệu chung, tham chiếu cả 2 phía
│   ├── research.md               # nghiên cứu Drupal CMS
│   ├── architecture.md           # thiết kế hệ thống Multi-Agent
│   └── roadmap.md                # lộ trình 3 sprint
│
└── .env.example                  # copy thành .env và điền ANTHROPIC_API_KEY, VF_SERVICE_TOKEN
```

### Hướng productization đã duyệt — chưa triển khai

Song song với Sprint 3, phần Python sẽ được tổ chức thành **nền tảng Multi-Agent độc lập** theo modular monolith: `/api/v1` cho Drupal, `/admin` cho người vận hành, worker riêng và PostgreSQL chung. MVP vẫn chỉ có một site Drupal tại Việt Nam; schema sẽ có `site_id` và `review_profile` để không khóa đường mở rộng sau này.

Người viết vẫn chỉ đăng nhập Drupal bằng role `content_editor`. Trang quản trị Multi-Agent dùng tài khoản riêng và ba role `viewer` / `operator` / `admin`; config, KB và evaluation chỉ đọc. Thiết kế này tuyệt đối không được làm thay đổi agent/prompt/rubric/scoring đang khóa cho E1/E5. Chi tiết và tiêu chí hoàn thành nằm trong [design spec ngày 2026-08-12](docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md); thứ tự TDD/checkpoint nằm trong [implementation plan tổng](docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md). Cây thư mục/module trong hai tài liệu là kiến trúc mục tiêu, **không phải trạng thái code hiện tại**.

## Setup

**Phía Drupal** (dùng [DDEV](https://ddev.com) — công cụ local dev được Drupal.org khuyến nghị chính thức từ 6/2024):

```
cd drupal
ddev start
```

Site chạy tại `http://drupal.ddev.site`. Nếu tạo project từ đầu, xem quy trình đầy đủ ở `docs/architecture.md` mục 2 (research.md có link tham khảo DDEV quickstart chính thức).

Rồi chạy đủ 4 lệnh sau — **chạy lại được nhiều lần**, không sợ hỏng nếu lỡ chạy hai lần:

```
cd drupal
ddev drush en jsonapi basic_auth workflows content_moderation -y   # module core
ddev drush php:script scripts/create_ai_fields.php                 # 5 field AI trên Article
ddev drush php:script scripts/create_workflow.php                  # workflow có state needs_review
ddev drush en vf_ai_review vf_ai_trigger -y                        # 2 module tùy chỉnh
ddev drush role:perm:add content_editor 'xem bao cao ai'
ddev drush role:perm:add administrator 'dieu khien ai'
```

Hai việc còn lại phải làm bằng tay trong giao diện admin:
- `/admin/config/services/jsonapi` — tick "Accept all JSON:API create, read, update, and delete operations". Không tick thì Multi-Agent đọc được nội dung nhưng **không ghi ngược kết quả về được**.
- `/admin/config/regional/language` — đảm bảo **tiếng Việt là ngôn ngữ mặc định**. Phạm vi dự án là nội dung tiếng Việt và KB RAG lọc theo `langcode = 'vi'`; site mặc định tiếng Anh sẽ tạo bài sai ngôn ngữ.

Vì sao dùng script thay vì bấm tay: cấu hình bấm tay chỉ tồn tại trong CSDL của một máy, đọc code không biết được gì. Hai script trên là nguồn sự thật cho cấu hình đó — xem `drupal/scripts/`.

**Phía Python:**

```
cd multiagent
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
cp ..\.env.example ..\.env   # rồi điền ANTHROPIC_API_KEY, DRUPAL_USER, DRUPAL_PASSWORD, DRUPAL_BASE_URL, VF_SERVICE_TOKEN

docker compose up -d                                # Postgres + pgvector (kho vector + hàng đợi + run_log)
.venv\Scripts\python.exe scripts\migrate.py apply  # bắt buộc trước API, worker và build KB
.venv\Scripts\python.exe src\kb\build_kb.py         # KB fact-check (4 chunk)
.venv\Scripts\python.exe src\kb\build_brand_kb.py   # KB brand (1128 chunk, vài phút)
```

KB là **dữ liệu dẫn xuất** — không nằm trong git, dựng lại từ `specs.json` và
`docs/brand/corpus/`. Chi tiết: [`docs/pre-demo-checklist.md`](docs/pre-demo-checklist.md) mục 2.

**Chuỗi bí mật phải đặt ở HAI nơi, giống hệt nhau.** Sinh một lần:

```
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

rồi dán **cùng giá trị đó** vào:
1. `.env` — dòng `VF_SERVICE_TOKEN=`
2. `drupal/web/sites/default/settings.php` — thêm `$settings['vf_ai_service_token'] = '<chuỗi vừa sinh>';`

Đặt ở `settings.php` chứ **không** phải config của Drupal: config export ra file YAML là lộ bí mật vào git. Cả hai file đều đã nằm trong `.gitignore`.

⚠️ **Hai nơi lệch nhau là triệu chứng khó chẩn đoán nhất của hệ thống này:** mọi request từ Drupal sang service trả 401, nhưng Drupal **không hiện lỗi gì cho người soạn bài**, và bài vẫn được chấm — chỉ là chậm vài phút vì phải chờ vòng đối soát thay vì chạy ngay. Nhìn bên ngoài giống "hệ thống chạy đúng, chỉ hơi chậm". Kiểm khi nghi ngờ: `ddev drush watchdog:show` tìm dòng 401 từ `vf_ai_trigger`.

**Chạy tự động hoá "Needs Review"** (service nhận job từ Drupal + worker chấm, cần chạy song song, mỗi lệnh một cửa sổ terminal — chi tiết và lệnh kiểm `/health`: [`docs/pre-demo-checklist.md`](docs/pre-demo-checklist.md) mục "Khởi động service và worker trước khi demo"):

```
.venv\Scripts\python.exe -m uvicorn api:app --port 8900 --app-dir src
.venv\Scripts\python.exe src\worker.py
```

## Trạng thái Sprint 1

- [x] Nghiên cứu kiến trúc, chốt công nghệ điều phối (LangGraph)
- [x] Dựng Drupal local, bật JSON:API
- [x] Tạo field tùy chỉnh trên Drupal (field_ai_status, field_ai_score, field_ai_suggestions)
- [x] AI Core (gọi Claude API, model claude-haiku-4-5-20251001, structured output)
- [x] Khung Orchestrator (LangGraph, 8 node, 4 agent còn là stub)
- [x] Agent SEO & Content Quality (thử nghiệm, chạy thật end-to-end)

**Sprint 1 hoàn thành.**

## Trạng thái Sprint 2

- [x] Compliance Agent — chấm theo **rubric CP1–CP8** (`docs/rubrics.md` mục 6): CP1/CP5/CP6 đo bằng máy, CP3 bằng RAG, bốn tiêu chí còn lại gộp vào **một** lần gọi LLM. Điểm do `src/scoring.py` tính **tất định** và `severity` **tra bảng theo mã tiêu chí** — LLM không tự cho điểm, cũng không tự chọn mức nghiêm trọng, vì `critical` là thứ kích hoạt quyền phủ quyết. **RAG fact-check (CP3)**: KB thông số → BGE-M3 self-host → Postgres + pgvector; lệch số (cùng model) → mức 0 → flag `critical`; **không tra được → mức 1 → flag `low`**, cố ý *không* phải `critical` để không từ chối oan mọi bài nhắc model ngoài KB (E2 recall@3=1.00 trên KB seed). KB đã verify: 4/4 mục `verified: true`, tìm ra 3 chỗ sai khi đối chiếu (`docs/goldset/sources.md` mục 2)
- [x] Hoàn thiện Aggregator — veto Compliance, fail-safe khi agent lỗi, chia lại trọng số
- [x] Retry/backoff khi Drupal lỗi mạng/5xx (`docs/architecture.md` mục 7)
- [x] Brand Voice Agent dùng RAG — rubric BV1–BV7 (`docs/rubrics.md` mục 5), 6/7 tiêu chí đo bằng regex đối chiếu `brand_rules.json`, BV6 chấm giọng văn bằng LLM + RAG trên KB `kb_brand` (1128 chunk từ 16 bài `BRAND`). Điểm do `src/scoring.py` tính **tất định**, không để LLM tự cho điểm — agent đầu tiên áp dụng rubric v1. Brand guideline **tự trích xuất** từ corpus bằng kiểm định nhị thức (p < 0,05 → ngưỡng ≥9/10 tự rơi ra, không phải số tự đặt). E2 đo được 78,3% so với mốc ngẫu nhiên 21,7%
- [x] Thu thập & gán nhãn gold set — hoàn tất **33/33** mẫu calibration (`docs/goldset/labels.csv`)
- [x] Tự động hóa — Content Moderation "Needs Review" bật thật, **hai đường song song**: event-driven là đường chính (Drupal → module `vf_ai_trigger` → service HTTP → hàng đợi Postgres, ~2 giây tới lúc job chạy) và vòng đối soát định kỳ 300 giây là lưới an toàn (bắt các job event bị lọt, ví dụ service tắt tạm thời). Chạy thật end-to-end, 8/8 tiêu chí đạt: `docs/architecture.md` mục 9, bằng chứng `docs/evidence/tu_dong_hoa_e2e.txt`
- [x] UI báo cáo trong editor — module `vf_ai_review`: khối tổng quan ở cột phải + **chú thích lỗi ngay dưới từng field** (phần đáp ứng đúng chữ đề bài). Python ghi thêm `field_ai_report_json` (báo cáo có cấu trúc), module chỉ đọc và render. Escape chống XSS theo `docs/prompt-injection.md` M4. Phát hiện nội dung sửa sau khi chấm bằng **hash nội dung**, không phải mốc `changed`

Gold set calibration: 33 mẫu (20 original + 13 perturbed), không có lớp publish.

Functional-clean: 10 mẫu corrected, expected publish, không tham gia E5/Kappa.

Evaluation suite: 43 mẫu, chỉ số phải báo cáo riêng theo lát dữ liệu.

Báo cáo Sprint 2 đầy đủ (kết quả, phép đo, việc còn vướng): [`docs/sprint2-report.md`](docs/sprint2-report.md).

Lộ trình đầy đủ: [`docs/roadmap.md`](docs/roadmap.md).
