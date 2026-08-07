# Thiết kế: Tự động hoá "Needs Review" — event-driven + hàng đợi bền

**Ngày:** 2026-08-07
**Trạng thái:** thiết kế đã duyệt — chưa triển khai
**Phạm vi:** hạng mục "Tự động hóa quy trình" của Sprint 2 (`docs/roadmap.md`), là deliverable bắt buộc còn lại duy nhất không bị chặn bởi mentor.

**Liên quan:** `docs/architecture.md` mục 9 (thiết kế gốc) và mục 5.7 (tiền đề Postgres, phân quyền) · `docs/operations.md` (nhật ký truy vết) · `docs/editor-ui-design.md` · `docs/technical-debt.md` nhóm C

**Tài liệu này thay thế phần nào của `architecture.md` mục 9:** giữ nguyên mục tiêu ("node ở Needs Review tự động được chấm, báo cáo hiện trong editor") và giữ nguyên lập luận rằng phần "bộ não" của worker không đổi giữa polling và production. **Thay** kết luận ở mục 9.2: polling từ *đường kích hoạt chính* trở thành *lưới an toàn*, đường chính là event-driven. **Bổ sung** hàng đợi bền, idempotency, nhật ký truy vết, và phản hồi cho editor trong lúc chờ.

---

## 1. Vì sao đổi khỏi thiết kế polling ban đầu

`architecture.md` mục 9.2 chọn polling worker, và lập luận bảo vệ lựa chọn đó **vẫn đúng nguyên**: worker xử lý trong production giống hệt worker polling, khác biệt duy nhất là *cách job đến với worker*.

Thứ đổi là **yêu cầu**, không phải lập luận: sản phẩm bàn giao cần đúng hình dạng production, không chỉ đạt mục tiêu tự động hoá. Ba hệ quả cụ thể:

1. **Độ trễ.** Polling 30 giây nghĩa là editor bấm Save rồi ngồi chờ tới nửa phút mà màn hình không nói gì. Event-driven đưa xuống ~2 giây.
2. **Trạng thái công việc không tồn tại ở đâu cả.** Polling không có khái niệm "job" — không trả lời được *bài này đã chấm chưa, thất bại mấy lần, vì sao*. Không có khái niệm đó thì không có retry, không có dead-letter, và không hiển thị được "đang chấm" cho editor.
3. **Tiền đề hạ tầng đã sẵn sàng.** `architecture.md` mục 5.7 đã ghi: *"việc chuyển kho vector sang Postgres (2026-08-05) chính là bước hạ tầng của hướng này — `run_log` và `review_state` nằm cùng một DB với `kb_chunk`, nên trang quản lý không cần thêm kho dữ liệu nào nữa."* Tài liệu này chính là chỗ tiêu đến tiền đề đó.

**Nhưng không bỏ polling.** Xem mục 2, quyết định Q2.

---

## 2. Năm quyết định đã chốt

| # | Quyết định | Lý do |
|---|---|---|
| **Q1** | Hàng đợi là **một bảng trong Postgres đang có**, nhận job bằng `SELECT ... FOR UPDATE SKIP LOCKED`. **Không** dựng Redis/RabbitMQ | `SKIP LOCKED` cho đúng những thứ một broker cho: nhiều worker không giẫm chân nhau, job không mất khi worker chết, retry có backoff, dead-letter. Đây là mẫu dùng trong sản phẩm thật (pgmq, Oban, River, Solid Queue). Khác biệt so với broker chỉ xuất hiện ở quy mô hàng nghìn job/giây; ở đây là vài chục bài/ngày. Redis thuần còn **không bền mặc định** — mất điện là mất job trừ khi cấu hình thêm AOF. Thêm một container không giải quyết vấn đề nào là đúng thứ dự án này gọi là số ảo |
| **Q2** | Giữ **cả hai đường**: event là đường chính, quét đối soát định kỳ là lưới an toàn | Event một mình chỉ bảo đảm *at-most-once* nếu bên gửi không retry — một cú POST thất bại là một bài lọt vĩnh viễn và **không ai biết**. Đó đúng là loại bẫy im lặng dự án này dành nhiều công để diệt (B2, B6, B9, B11). Vòng đối soát tốn ~40 dòng, tái dùng chính khoá idempotency đã phải viết cho Q3, và nó **bao trọn deliverable polling worker của roadmap** thay vì bỏ cam kết cũ |
| **Q3** | Idempotency bằng **unique index bộ phận trên `(node_id, content_hash)`** | Một cơ chế giải ba bài toán: chặn Save nhiều lần không tốn tiền, chặn hai đường (event + đối soát) chấm chồng, chặn chấm lại nội dung không đổi. `content_hash` đã tồn tại ở cả hai phía và đã có test hợp đồng khoá — không phải xây mới |
| **Q4** | Tách **module Drupal thứ hai** `vf_ai_trigger`, không nhét vào `vf_ai_review` | `vf_ai_review` có cam kết thành văn: *"Module CHỈ ĐỌC: không tính điểm, không gọi API, không sửa dữ liệu node."* Nhét EventSubscriber gọi HTTP vào là phá vỡ chính câu đó. Tách ra thì hai module **hỏng độc lập và hậu quả khác hẳn nhau** |
| **Q5** | Làm **nhật ký truy vết (`run_log`) luôn trong lần này**, ghi vào Postgres | `operations.md` mục 4: *"nên bật trước khi chạy các thí nghiệm, không phải sau"* — `agent_results`, `config_meta`, `usage` không ai giữ hộ. E1 sắp phải chạy lại (nợ B7) và E5 sẽ chạy khi có nhãn; có log sẵn thì phân tích là đọc dữ liệu |

### 2.1. Q5 đổi kết luận của `operations.md` mục 2.4 — ghi rõ vì sao

`operations.md` mục 2.4 chốt **JSONL**, với lý do *"ở quy mô demo và gold set (vài trăm bản ghi) thì bất cứ thứ gì nặng hơn đều là over-engineering"*.

**Lập luận đó đúng ở thời điểm viết (2026-07-27) và tiền đề của nó đã đổi.** Lúc đó phía Multi-Agent chưa có CSDL nào; "bảng riêng trong CSDL" nghĩa là dựng thêm hạ tầng. Từ 2026-08-05 Postgres đã chạy sẵn cho kho vector, nên chi phí biên của một bảng nữa gần bằng không, và lần này dù sao cũng phải tạo bảng cho hàng đợi.

Hai lợi ích cụ thể của việc đổi:

- Hàng đợi và nhật ký nằm cùng một giao dịch được — không có cảnh job báo `done` trong khi bản ghi log thất bại.
- `architecture.md` mục 5.7 đã ghi trang quản lý sau này đọc `run_log` và `kb_chunk` bằng cùng một câu SELECT. Giữ JSONL thì trang đó phải đọc hai nguồn.

Đây là **đổi kết luận, không phải bác bỏ lập luận** — đúng cách `rag-design.md` mục 4.2a đã xử lý khi chuyển Chroma sang pgvector.

---

## 3. Kiến trúc

### 3.1. Sơ đồ

```
┌─────────────── DRUPAL ───────────────┐        ┌────────── SERVICE PYTHON ──────────┐
│                                       │        │                                     │
│  Editor Save → state "needs_review"   │        │  api.py  (FastAPI, 127.0.0.1:8900) │
│         │                             │        │    POST /jobs         ← xếp hàng   │
│         ▼                             │        │    GET  /jobs/by-node ← hỏi t.thái │
│  vf_ai_trigger (module MỚI)           │        │    GET  /health                    │
│    EventSubscriber ──── POST /jobs ───┼───────►│         │                          │
│    route /vf-ai/status/{node} ────────┼───────►│         ▼                          │
│    route /vf-ai/rescore/{node} ───────┼───────►│    review_job  (bảng Postgres)     │
│    permission "dieu khien ai"         │        │         │                          │
│                                       │        │         │ FOR UPDATE SKIP LOCKED   │
│  vf_ai_review (đã có, KHÔNG đổi vai)  │        │         ▼                          │
│    render báo cáo + khối "đang chấm"  │◄───────┤  worker.py (tiến trình riêng)      │
│    JS poll route status mỗi 3s        │ PATCH  │    build_graph().invoke(node_id)   │
│                                       │        │    audit.ghi() → run_log           │
│                                       │◄───────┤  reconcile (trong worker, 5 phút)  │
└───────────────────────────────────────┘ GET    │    quét JSON:API, enqueue bù       │
                                         JSON:API└─────────────────────────────────────┘
```

### 3.2. Hai module Drupal, hai vai trò tách bạch

| Module | Vai trò | Hỏng thì sao |
|---|---|---|
| `vf_ai_review` *(đã có)* | **Chỉ đọc** — render báo cáo, render khối "đang chấm" | Không thấy báo cáo. Dữ liệu đánh giá vẫn đúng |
| `vf_ai_trigger` *(mới)* | **Chỉ gọi ra ngoài** — EventSubscriber, 2 route, permission, config | Bài không được gửi qua đường event. Đường đối soát vẫn bắt được, chỉ chậm hơn |

Phụ thuộc **một chiều**: `vf_ai_trigger.info.yml` khai `dependencies: vf_ai_review` (cần chỗ gắn khối "đang chấm"). Ngược lại không — tắt `vf_ai_trigger`, `vf_ai_review` vẫn render bình thường, hệ thống quay về chạy tay.

### 3.3. Vì sao API và worker là hai tiến trình riêng

- API phải trả lời trong vài ms (Drupal đang chờ trong lúc editor bấm Save); worker chạy 30–60 giây mỗi job.
- Worker nạp BGE-M3 (~2GB) lúc khởi động, đúng yêu cầu `rag-design.md` mục 6. API không cần model, khởi động tức thì.
- Worker chết vì hết RAM thì API vẫn sống và job vẫn xếp hàng được — **đó chính là lý do có hàng đợi**. Gộp chung là vứt bỏ lợi ích đó.
- Chạy 2 worker song song = mở thêm một tiến trình, không đụng API. `SKIP LOCKED` bảo đảm chúng không giẫm chân nhau.

### 3.4. Ranh giới với phần đã có

**Không đụng:** 4 agent, `graph.py`, Aggregator, cơ chế veto, `scoring.py`, `retrieval.py`, `config.py`, `state.py`.

**Sửa tối thiểu:**

| File | Thay đổi |
|---|---|
| `src/drupal_client.py` | `write_back()` trả `bool` thay vì nuốt lỗi lặng lẽ (mục 6.2); thêm `liet_ke_can_cham()` |
| `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module` | Tách hàm dùng chung `vf_ai_review_hash_fields($node)`; thêm placeholder khối "đang chấm" |
| `multiagent/requirements.txt` | Thêm `fastapi`, `uvicorn` |
| `.env.example` | Thêm `VF_SERVICE_TOKEN`, `VF_API_PORT` |

---

## 4. Workflow trên Drupal

Bật module core `workflows` + `content_moderation`, tạo workflow **"Kiểm duyệt nội dung"** áp cho content type Article:

| State | Published? | Ý nghĩa |
|---|---|---|
| `draft` | không | Đang soạn |
| `needs_review` | không | **Chuyển sang đây là tín hiệu duy nhất kích hoạt hệ thống chấm** |
| `published` | có | Đã đăng |
| `archived` | không | Gỡ xuống |

Transition: `draft → needs_review`, `needs_review → draft`, `needs_review → published`, `published → archived`, `archived → draft`.

**Hệ thống AI không nằm trong bất kỳ transition nào.** Chấm xong node vẫn ở `needs_review`; người duyệt đọc báo cáo rồi tự quyết. Đây là ràng buộc đã chốt ở `architecture.md` mục 2.3, không phải giới hạn kỹ thuật.

### 4.1. Điều kiện bắn sự kiện — bắn theo TRẠNG THÁI SAU KHI LƯU, không theo chuyển tiếp

EventSubscriber bắn khi **state sau khi lưu là `needs_review`**, chứ **không** chỉ khi có chuyển tiếp `draft → needs_review`.

Khác biệt này không phải chi tiết vụn: người viết thường đưa bài sang `needs_review`, đọc báo cáo, **sửa body ngay tại đó rồi lưu tiếp mà không đổi state**. Nếu chỉ bắn khi có chuyển tiếp thì lần sửa đó không bao giờ được chấm lại — trong khi module lại hiện băng *"nội dung đã thay đổi sau lần chấm"*, tức hệ thống tự mâu thuẫn với chính mình.

Bắn theo trạng thái sau khi lưu thì **không phát sinh chi phí**: lưu mà không sửa gì → `content_hash` không đổi → index dedup chặn ở tầng INSERT. Đây là một lợi ích nữa của quyết định Q3.

> ⚠️ **Giả định phải kiểm chứng ở bước đầu tiên của kế hoạch triển khai, không được tin sẵn:** JSON:API có expose `moderation_state` để lọc bằng `filter[moderation_state]=needs_review` hay không. Đây đúng loại khẳng định về môi trường mà dự án đã sai nhiều lần vì tin tài liệu thay vì thử trên hệ thống đang chạy. Nếu không lọc được, đường đối soát chuyển sang lọc `filter[status]=0` rồi lọc tiếp phía Python — đổi ~10 dòng, không đổi kiến trúc.

---

## 5. Schema

### 5.1. Bảng `review_job`

```sql
CREATE TABLE review_job (
  id           bigserial PRIMARY KEY,
  node_id      text        NOT NULL,
  content_hash text        NOT NULL,
  status       text        NOT NULL,   -- queued | running | done | failed | superseded
  attempts     int         NOT NULL DEFAULT 0,
  run_after    timestamptz NOT NULL DEFAULT now(),
  claimed_at   timestamptz,
  claimed_by   text,
  last_error   text,
  source       text        NOT NULL,   -- event | reconcile | manual
  created_at   timestamptz NOT NULL DEFAULT now(),
  updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX review_job_dedup
  ON review_job (node_id, content_hash)
  WHERE status IN ('queued', 'running', 'done');

CREATE INDEX review_job_claim ON review_job (status, run_after);
```

**Index bộ phận là trái tim của idempotency.** Điều kiện `WHERE` cố ý loại hai trạng thái:

- Loại `failed` — job thất bại phải xếp hàng lại được.
- Loại `superseded` — trạng thái dành riêng cho nút "Chấm lại" thủ công (mục 6.4).

### 5.2. Bảng `run_log`

```sql
CREATE TABLE run_log (
  id             bigserial PRIMARY KEY,
  job_id         bigint,
  node_id        text        NOT NULL,
  content_hash   text        NOT NULL,
  scored_at      timestamptz NOT NULL DEFAULT now(),
  duration_ms    int,
  decision       text,
  final_score    numeric,
  missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb,
  veto_reason    text,
  note           text,
  agent_results  jsonb NOT NULL,
  config_meta    jsonb NOT NULL,
  usage          jsonb NOT NULL,
  model          text  NOT NULL
);

CREATE INDEX run_log_tra_cuu ON run_log (node_id, content_hash);
```

### 5.3. Ai tạo bảng

Theo đúng mẫu `db.dam_bao_bang()` đang dùng cho `kb_chunk`: `queue.dam_bao_bang(conn)` và `audit.dam_bao_bang(conn)`, gọi **lúc khởi động** của cả API lẫn worker, dùng `CREATE TABLE IF NOT EXISTS`. Không dựng framework migration — ở hai bảng thì đó là hạ tầng thừa, và mẫu này đã có tiền lệ trong repo.

### 5.4. Hợp đồng API

| Endpoint | Vào | Ra |
|---|---|---|
| `POST /jobs` | `{node_id, content_hash, source, force?}` | `202 {job_id, status:"queued"}` · `200 {status:"duplicate", job_id}` · `401` · `422` |
| `GET /jobs/by-node/{node_id}` | — | `200 {status, job_id, scored_at, attempts, last_error}` với `status` ∈ `queued/running/done/failed/none` |
| `GET /health` | — | `200 {ok, queued, running, failed}` |

`GET /jobs/by-node` trả về job **mới nhất theo `created_at`** của node đó; không có job nào thì `status: "none"`. Đây là thứ JS trong khối báo cáo poll để biết khi nào nạp lại.

**Append-only:** chỉ INSERT, không bao giờ UPDATE/DELETE.

`config_meta` là trường quan trọng nhất (`operations.md` mục 2.3): không có nó thì *"bài này 42 điểm, bị từ chối"* vô nghĩa vì không biết tính bằng trọng số nào, ngưỡng nào, model nào, rubric phiên bản nào. Có nó thì mỗi bản ghi tự mang bối cảnh, và câu hỏi *"áp ngưỡng mới lên quyết định cũ thì bao nhiêu cái đổi"* trả lời được bằng cách chạy lại Aggregator trên `agent_results` đã lưu — **không tốn đồng API nào**, đúng lợi ích mà `architecture.md` mục 8.2 nêu cho việc quét ngưỡng.

**Không ghi** (`operations.md` mục 2.5): toàn văn bài viết, API key, system prompt đầy đủ (chỉ `config_meta.prompt_version`).

**Bẫy `USAGE_LOG` phải xử lý đúng.** `technical-debt.md` nhóm C cảnh báo sẵn: `ai_core.USAGE_LOG` là list ở mức module, **cố ý không tự xoá** (E4 cộng cả list để tính chi phí). Script chạy một lần thì vô hại; worker chạy nền vô hạn thì phình mãi. → Worker đọc rồi `clear()` **sau mỗi job**; tuyệt đối **không** chặn cứng kích thước list, vì làm thế là phá phép đo E4.

---

## 6. Luồng dữ liệu

### 6.1. Đường chính — event

```
1. Editor Save, state → needs_review
2. vf_ai_trigger EventSubscriber:
      hash = AiReportRenderer::contentHash(vf_ai_review_hash_fields($node))
      POST http://127.0.0.1:8900/jobs
           { node_id, content_hash, source: "event" }
           Authorization: Bearer <token>
      timeout 2s, bọc try/catch — LỖI KHÔNG ĐƯỢC LÀM SẬP VIỆC SAVE NODE
3. api.py: xác thực → queue.enqueue()
      trùng dedup → 200 {"status": "duplicate"}
      mới        → 202 {"job_id": N, "status": "queued"}
4. worker.py:
      job = queue.claim()
      đã có run_log cho (node_id, content_hash)? → chỉ write_back, KHÔNG gọi LLM
      ngược lại: USAGE_LOG.clear() → build_graph().invoke({"node_id": ...}) → audit.ghi()
      write_back thành công? → done : queued + backoff
5. vf_ai_review + JS poll /vf-ai/status/{node} mỗi 3s → done → nạp lại khối báo cáo
```

Bước 2 dùng lại `AiReportRenderer::contentHash()` — cùng hàm module đang dùng để hiện băng *"nội dung đã thay đổi"*, đã có test hợp đồng khoá với Python qua `scripts/content_hash_fixture.json`. **Không viết công thức băm thứ hai.**

Đoạn *lấy 4 field ra khỏi node* hiện nằm inline trong `vf_ai_review.module:78-83`. Giờ có hai nơi cần → tách thành `vf_ai_review_hash_fields($node)`. **Không** đưa vào `AiReportRenderer`: class đó cố ý không phụ thuộc Drupal để test được bằng PHP thuần (quyết định Q3 của spec `2026-08-03-vf-ai-review-module-design.md`), đưa vào là mất tính chất đó.

**Worker chỉ truyền `node_id` vào state**, không tự đặt `content_type`/`langcode`. `graph._khoa_cua()` đã là **chỗ duy nhất** suy ra cặp khoá đó và tự rơi về `cam_nang`/`vi` khi state thiếu — đó chính là bài học nợ B6. Worker đặt thêm một đường suy ra thứ hai là dựng lại đúng cái bẫy vừa dẹp. Khi có `(content_type, langcode)` thật (nhiều loại nội dung), nó phải đến từ node trong `fetch_node`, không phải từ worker.

### 6.2. Nhận job bằng `SKIP LOCKED`

```sql
UPDATE review_job SET status='running', claimed_at=now(), claimed_by=%s,
                      attempts=attempts+1, updated_at=now()
WHERE id = (
  SELECT id FROM review_job
  WHERE status='queued' AND run_after <= now()
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1
)
RETURNING *;
```

Worker A khoá dòng nó lấy; worker B thấy dòng đang khoá thì **bỏ qua** và lấy dòng kế tiếp. Không khoá toàn bảng, không cần khoá phân tán.

Thu hồi job kẹt (worker chết giữa chừng):

```sql
UPDATE review_job SET status='queued', run_after=now(), updated_at=now()
WHERE status='running' AND claimed_at < now() - interval '15 minutes';
```

### 6.3. Lưới an toàn — đối soát

Chạy trong chính tiến trình worker, mỗi 5 phút:

```
GET /jsonapi/node/article?filter[moderation_state]=needs_review&page[limit]=50
với mỗi node:
    hash_hien_tai = sha256(title, body, summary, meta_description)
    hash_da_cham  = json(field_ai_report_json).content_hash
    nếu hash_hien_tai == hash_da_cham          -> bỏ qua (đã chấm đúng nội dung này)
    nếu đã có job status='failed' cùng hash    -> bỏ qua (xem 6.3.1)
    ngược lại -> enqueue(node_id, hash_hien_tai, source="reconcile")
                 (dedup tự chặn nếu đường event đã xếp hàng rồi)
```

#### 6.3.1. Đối soát tuyệt đối không được hồi sinh job đã dead-letter

Index dedup ở mục 5.1 **cố ý loại `failed`** để job thất bại xếp hàng lại được. Nhưng vòng đối soát chạy mỗi 5 phút và chỉ nhìn Drupal, nên nếu không chặn riêng thì nó sẽ **enqueue lại vĩnh viễn** một bài luôn thất bại — mỗi 5 phút một job mới, mỗi job thử 3 lần, và cơ chế dead-letter bị vô hiệu hoàn toàn.

Với một bài hỏng vì lý do không tự khỏi (node bị xoá field, quyền sai), đó là **vòng lặp tiêu tiền API vô hạn**.

Vì vậy đối soát phải hỏi thêm một câu trước khi enqueue: *đã có job `failed` cho đúng cặp `(node_id, content_hash)` này chưa?* Có thì bỏ qua. Bài đó chỉ chạy lại được qua **nút "Chấm lại" thủ công** (mục 6.4) — tức phải có người quyết định, đúng tinh thần "bấm chấm lại là tiêu tiền thật".

Đây là ràng buộc bắt buộc, không phải tối ưu: thiếu nó thì hai cơ chế đúng riêng lẻ (dedup loại `failed` + đối soát định kỳ) **cộng lại thành sai**.

Bắt được **mọi** kiểu lọt: service restart, Drupal mất mạng, module bị tắt, node đổi state bằng `drush` hoặc migration. Nó không cần biết *vì sao* lọt — chỉ so trạng thái mong muốn với trạng thái thật rồi bù chênh lệch. Đây là *reconciliation loop*, cùng nguyên lý Kubernetes dùng để hoà giải desired state với actual state.

**Chu kỳ 5 phút chứ không phải 30 giây:** nó là lưới, không phải đường chính. Quét thưa thì tiết kiệm gọi API vô ích, và độ trễ xấu nhất 5 phút chỉ xảy ra trong tình huống đã hỏng.

### 6.4. "Chấm lại" thủ công

```
Người duyệt (permission "dieu khien ai") bấm nút trong khối báo cáo
   → POST /vf-ai/rescore/{node}   (route Drupal, có CSRF token)
   → vf_ai_trigger gọi POST /jobs với { force: true }
   → api.py: UPDATE review_job SET status='superseded'
              WHERE node_id=? AND content_hash=? AND status='done'
             rồi INSERT job mới source='manual'
```

`superseded` nằm ngoài index dedup nên job mới chèn được. Bản ghi cũ **không bị xoá** — lịch sử vẫn tra được.

Phân quyền tách riêng đúng `architecture.md` mục 5.7: **`xem bao cao ai` khác `dieu khien ai`, vì bấm "chấm lại" là tiêu tiền API thật.**

---

## 7. Xử lý lỗi

| Hỏng ở đâu | Hệ thống làm gì | Vì sao |
|---|---|---|
| Drupal POST thất bại | `try/catch`, ghi `watchdog`, **Save node vẫn thành công** | Editor không bao giờ bị chặn lưu bài vì service phụ trợ. Đối soát bắt lại ≤5 phút |
| Postgres chết | API trả 503; worker log lỗi rồi thử lại | `db.get_conn()` đã tự mở lại khi kết nối đóng |
| `fetch_content` lỗi 4xx | Job `failed` ngay, **không retry** | `drupal_client` đã không retry 4xx — thử lại không giải quyết được gì |
| Drupal 5xx / timeout | `_request_with_retry` retry 3 lần trong pipeline; vẫn lỗi → job retry + backoff | Tái dùng cơ chế có sẵn, không chồng tầng retry thứ hai |
| **1–3 agent lỗi** | **Chấp nhận, job `done`** | Đúng tình huống fail-safe `architecture.md` mục 6.4 được thiết kế để xử lý: chia lại trọng số, `note` ghi "điểm chưa đầy đủ". Retry là trả tiền lần hai cho cơ chế đang hoạt động đúng |
| **Cả 4 agent lỗi** | Job retry + backoff | `len(missing_agents) == 4` = hỏng hạ tầng, không phải kết quả đánh giá. Ranh giới kiểm được bằng code, không phải phán đoán |
| `write_back` thất bại | Ghi `run_log` **trước**, job về `queued` + backoff | Mục 7.1 |
| Worker chết giữa job | Job kẹt `running` → thu hồi sau 15 phút | Mục 6.2 |
| Quá 3 lần thất bại | `status='failed'` + `last_error`, dừng hẳn | Dead-letter. Không thử vô hạn, lỗi vẫn tra được |

Backoff: **1 phút → 5 phút → 15 phút**, rồi dead-letter.

### 7.1. `write_back` đang nuốt lỗi — sửa tối thiểu

`drupal_client.write_back()` hiện không raise khi PATCH thất bại, chỉ `logging.warning`. **Lý do cũ vẫn đúng và giữ nguyên:** *"bài viết đã được 4 agent chấm xong (tốn API call thật); để lỗi ghi-ngược làm sập cả script sẽ lãng phí toàn bộ công việc đã làm."*

Nhưng với worker thì im lặng là bẫy: job báo `done` trong khi Drupal không có kết quả nào.

**Sửa:** `write_back()` trả `bool` — vẫn không raise, nhưng người gọi biết được. Worker nhận `False` → job về `queued`.

**Chốt chặn tiền đi kèm:** trước khi gọi LLM, worker tra `run_log` cho `(node_id, content_hash)`. Đã có bản ghi → **chỉ ghi lại kết quả cũ về Drupal, không chạy lại pipeline**. Lỗi write-back vì thế tốn thêm 0 đồng. Khoảng 10 dòng, chặn đúng một đường mất tiền có thật.

---

## 8. Bảo mật

| Hạng mục | Cách làm |
|---|---|
| Xác thực Drupal → service | `Authorization: Bearer <token>`, so bằng `hmac.compare_digest` (chống timing attack) |
| Nơi cất token | Python: `.env` (`VF_SERVICE_TOKEN`). Drupal: **`$settings['vf_ai_service_token']` trong `settings.php`** |
| Vùng nghe | API bind `127.0.0.1:8900`, không phải `0.0.0.0` |
| Route `rescore` | Permission `dieu khien ai` + CSRF token |
| Route `status` | Permission `xem bao cao ai` |
| Chống lạm dụng chi phí | Index dedup là cơ chế chính; **mỗi** worker chạy tuần tự 1 job/lần; dead-letter chặn vòng lặp thất bại; đối soát không hồi sinh job đã dead-letter (6.3.1) |

**Token cất trong `settings.php` chứ không phải config entity** — config export ra YAML là lộ secret vào git. URL service thì để config bình thường (vô hại).

**Cố ý không đặt trần "N bài/giờ".** Không có căn cứ nào để chọn con số đó, và dự án có nguyên tắc rõ: không đặt ngưỡng ảo. Dedup + chạy tuần tự + dead-letter đã chặn mọi đường tiêu tiền mất kiểm soát tìm được.

**Cố ý không dùng HMAC ký body**, dù nó "production hơn": trên loopback không có mối đe doạ replay đáng kể, và thêm một cơ chế không giải quyết vấn đề nào là đúng thứ `prompt-injection.md` mục 5 M5 gọi là *cảm giác an toàn giả*. Nếu sau này service ra khỏi localhost thì nâng lên HMAC + timestamp chống replay.

---

## 9. Kiểm thử

Giữ phong cách hiện có: script Python thuần, in `[PASS]`, `sys.exit(1)`.

| Test | Kiểm gì |
|---|---|
| `test_queue.py` | dedup chặn job trùng; **`SKIP LOCKED` — hai claim đồng thời phải ra hai job khác nhau**; thu hồi job kẹt; backoff tăng đúng; dead-letter sau 3 lần |
| `test_api.py` | token sai → 401; payload thiếu → 422; enqueue trùng → không sinh job thứ hai; `force:true` → `superseded` + job mới |
| `test_worker.py` | tiêm graph giả (không gọi LLM): job done ghi `run_log`; `write_back` False → job về `queued`; **đã có `run_log` → không gọi lại graph**; `USAGE_LOG` được reset |
| `test_reconcile.py` | hash khớp → không enqueue; hash khác → enqueue; **đã có job `failed` cùng hash → KHÔNG enqueue** (6.3.1); JSON:API lỗi → không làm sập vòng lặp |
| `test_audit.py` | bản ghi đủ trường; không lọt token/API key |
| `test_ai_trigger.php` | EventSubscriber dựng đúng payload; `content_hash` khớp `content_hash_fixture.json` |

### 9.1. Một tính chất của bộ test bị đổi — phải nói thẳng

Hiện 28/28 test chạy *"không cần API key, không cần Drupal, không cần KB"*. Nhóm test hàng đợi **cần Postgres thật**: `SKIP LOCKED` không giả lập được, mà đó chính là thứ đáng kiểm nhất.

Cách xử lý: các test này dùng **schema tạm** trong container đang chạy; không kết nối được thì in `[SKIP]` rồi thoát 0. Tính chất "chạy được ở bất cứ đâu" giữ nguyên.

**Nhưng `[SKIP]` không phải `[PASS]`.** Ghi vào `pre-demo-checklist.md` mục 5 để không ai nhầm hai thứ đó khi báo cáo số test xanh.

---

## 10. Vận hành

```bash
cd multiagent
docker compose up -d                                    # Postgres (đã có)
.venv/Scripts/python.exe -m uvicorn api:app --port 8900 --app-dir src
.venv/Scripts/python.exe src/worker.py                  # cửa sổ thứ hai
```

`GET /health` → `{"ok": true, "queued": 3, "running": 1, "failed": 0}`. Một dòng biết hàng đợi có tắc không.

---

## 11. Giới hạn cố ý — có thiết kế, chưa làm

| Hạng mục | Lý do hoãn |
|---|---|
| **Container hoá phía Python** | BGE-M3 ~2GB đã nằm trong cache HuggingFace trên máy dev. Đóng gói lại nghĩa là nhồi 2GB vào image hoặc mount cache qua Docker Desktop trên Windows — cả hai là nguồn rủi ro tiến độ thật, đã có tiền lệ (`pre-demo-checklist.md` mục 2: HuggingFace từng ngắt kết nối giữa chừng làm chết script). Container hoá là chuyện **triển khai**, không đổi một dòng kiến trúc |
| Message broker riêng (Redis/RabbitMQ) | Quyết định Q1. Đường nâng cấp: thay `queue.py` bằng bản cài đặt khác sau cùng interface, worker không đổi |
| Vòng phản hồi người duyệt (`operations.md` mục 3) | Hạng mục riêng. Cần `run_log` xong trước — lần này sẽ có, nên nó hết bị chặn |
| Trang quản lý agent (`architecture.md` mục 5.7) | Đã ghi là mở rộng, chưa tới lượt. `run_log` lần này chính là nguồn dữ liệu nó cần |
| Tự động xuất bản | Ràng buộc đã chốt của đề bài, không bao giờ làm |
| Tự động chỉnh ngưỡng theo phản hồi | `operations.md` mục 3.3 đã bác: phản hồi là mẫu thiên lệch và không mù |

---

## 12. Tài liệu phải cập nhật theo

Không phải việc phụ — dự án đã có bài học riêng về tài liệu trôi lệch khỏi code (`technical-debt.md` B4, B6).

| File | Sửa gì |
|---|---|
| `architecture.md` mục 9 | Viết lại: polling từ đường chính thành lưới an toàn; thêm mục event-driven; giữ lập luận "bộ não worker không đổi" |
| `operations.md` mục 2.4 | Đổi kết luận JSONL → Postgres, **ghi rõ tiền đề đã đổi** (mục 2.1 tài liệu này) |
| `technical-debt.md` nhóm C | Gỡ mục polling worker; ghi cảnh báo `USAGE_LOG` đã được xử lý |
| `README.md` | Trạng thái Sprint 2; **sửa chỗ còn ghi "Chroma" ở dòng 114** (đã đổi sang pgvector từ 2026-08-05) |
| `pre-demo-checklist.md` | Thêm mục khởi động service + worker; ghi rõ `[SKIP]` ≠ `[PASS]` |
| `sprint2-report.md` | Mục 3.2 từ "chưa xong" sang xong, kèm lý do chọn Postgres thay vì Redis |
| `editor-ui-design.md` mục 9 | Nút "chấm lại" và khối "đang chấm" từ "chưa chốt" sang đã làm |

---

## 13. Tiêu chí hoàn thành

1. Editor chuyển một bài sang "Needs Review" → trong ~2 giây khối báo cáo hiện "⏳ Đang chấm" → chấm xong tự hiện kết quả, **không phải F5**.
2. Tắt service Python, chuyển một bài sang "Needs Review", bật lại service → trong ≤5 phút bài đó vẫn được chấm (đường đối soát).
3. Bấm Save 3 lần liên tiếp không sửa gì → `SELECT count(*) FROM review_job WHERE node_id=...` trả về **1**.
4. Sửa một chữ trong body rồi Save → job mới được tạo và bài được chấm lại.
5. `SELECT * FROM run_log` có đủ `agent_results`, `config_meta`, `usage` cho mọi lần chấm.
6. Giết worker giữa lúc đang chấm → sau 15 phút job tự về `queued` và chạy lại.
7. Một bài luôn thất bại (ví dụ xoá `field_meta_description` khỏi Article) → sau 3 lần thành `failed`, và **vòng đối soát không tạo thêm job nào nữa** trong 15 phút tiếp theo.
8. Toàn bộ bộ test xanh (nhóm queue chạy với container bật).
