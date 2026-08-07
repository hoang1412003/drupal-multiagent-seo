# Tự động hoá "Needs Review" — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Editor chuyển một bài sang trạng thái "Needs Review" thì hệ thống tự chấm trong vài giây và báo cáo hiện ngay trong giao diện soạn bài, không ai phải chạy lệnh tay.

**Architecture:** Drupal bắn job qua HTTP khi node được lưu ở trạng thái `needs_review`; service Python nhận và ghi vào một hàng đợi bền trong Postgres đang có; worker nhận job bằng `SELECT ... FOR UPDATE SKIP LOCKED`, gọi pipeline LangGraph sẵn có, ghi nhật ký truy vết rồi PATCH kết quả ngược về Drupal. Một vòng đối soát chạy mỗi 5 phút bắt các bài lọt khi đường HTTP thất bại.

**Tech Stack:** Python 3.12, FastAPI + uvicorn, psycopg 3 (đã có), PostgreSQL 17 + pgvector (container `vf-agent-db` đang chạy), Drupal 10.6 + DDEV, PHP 8.4.

**Spec:** `docs/superpowers/specs/2026-08-07-needs-review-automation-design.md` — đọc trước khi bắt đầu.

## Global Constraints

- **Ngôn ngữ:** comment và tên hàm nghiệp vụ bằng tiếng Việt **không dấu** trong file `.py` mới (khớp `db.py`, `retrieval.py`); tài liệu `.md` có dấu. Commit message tiếng Việt **không dấu**, **không** có trailer `Co-Authored-By`.
- **`node_id` LUÔN là UUID của node**, không bao giờ là `nid`. Pipeline gọi `/jsonapi/node/article/{uuid}`.
- **Không đụng:** 4 agent, `scoring.py`, `retrieval.py`, `config.py`, `state.py`, `embeddings.py`, `db.py`. `src/graph.py` chỉ đụng ở **Task 2** và chỉ để chuyển `_content_hash` sang `text_utils` — không sửa logic node nào.
- **Hệ thống không bao giờ tự đổi moderation state của node.** Chỉ ghi 4 field AI.
- **Test:** script Python thuần trong `multiagent/scripts/`, tên `test_*.py`, in `[PASS]` / `[FAIL]`, kết thúc bằng `sys.exit(1 if failed else 0)`. Không dùng pytest. Chạy bằng `.venv/Scripts/python.exe scripts/test_x.py` từ thư mục `multiagent/`.
- **Trạng thái job:** đúng 5 giá trị `queued` / `running` / `done` / `failed` / `superseded`.
- **Không đặt tên file trong `src/` trùng module chuẩn Python.** Repo chèn `src/` vào `sys.path[0]` nên file trùng tên sẽ che module chuẩn — đã xảy ra thật với `queue.py` (xem hộp cảnh báo ở Task 3), làm sập cả tầng DB vì `psycopg` cần `queue` chuẩn.
- **Backoff:** 60s → 300s, rồi dead-letter ở lần thất bại thứ 3 (`MAX_ATTEMPTS = 3`). *(Bản đầu ghi "60s → 300s → 900s" — sai: với `MAX_ATTEMPTS = 3` thì giá trị thứ ba không bao giờ tới lượt, vì lần fail thứ 3 rơi thẳng vào dead-letter. Sửa tài liệu cho khớp hành vi mà test đã khoá, không đổi hành vi.)*
- **Thu hồi job kẹt:** sau 15 phút ở `running`.
- **Chu kỳ đối soát:** 300 giây.
- **Cổng service:** `127.0.0.1:8900`.

---

## File Structure

| File | Trách nhiệm |
|---|---|
| `multiagent/src/text_utils.py` *(sửa)* | Thêm `content_hash()` — dùng chung graph / reconcile / worker |
| `multiagent/src/job_queue.py` *(mới)* | Bảng `review_job`; enqueue / claim / complete / fail / reclaim. Thuần SQL, không biết gì về LLM |
| `multiagent/src/audit.py` *(mới)* | Bảng `run_log`; ghi bản ghi append-only; tra bản ghi đã có |
| `multiagent/src/drupal_client.py` *(sửa)* | `write_back()` trả `bool`; thêm `liet_ke_can_cham()`; tách `_fields_tu_resource()` |
| `multiagent/src/worker.py` *(mới)* | Vòng lặp: claim → chấm → ghi log → đóng job |
| `multiagent/src/reconcile.py` *(mới)* | Quét JSON:API, enqueue bù, không hồi sinh job dead-letter |
| `multiagent/src/api.py` *(mới)* | FastAPI: `POST /jobs`, `GET /jobs/by-node/{id}`, `GET /health` |
| `drupal/web/modules/custom/vf_ai_trigger/` *(mới)* | Hook bắn job, 2 route, khối "đang chấm" + JS, permission, config |
| `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module` *(sửa)* | Tách `vf_ai_review_hash_fields()` dùng chung |

---

### Task 1: Bật Content Moderation và kiểm chứng JSON:API

Đây là task **rủi ro cao nhất** nên làm đầu tiên: cả đường đối soát phụ thuộc vào một giả định về môi trường chưa được kiểm. Dự án này đã sai về môi trường nhiều lần vì tin tài liệu thay vì thử trên hệ thống đang chạy.

**Files:**
- Create: `drupal/scripts/create_workflow.php`
- Create: `docs/evidence/needs_review_jsonapi_kiem_chung.txt`

**Interfaces:**
- Produces: workflow `kiem_duyet_noi_dung` với state `needs_review` trên content type Article; kết luận JSON:API có lọc được `moderation_state` hay không (Task 5 và 7 phụ thuộc).

- [ ] **Step 1: Bật hai module core**

```bash
cd drupal
ddev drush en workflows content_moderation -y
ddev drush pm:list --status=enabled --format=list | grep -E "workflows|content_moderation"
```

Expected: in ra cả `workflows` và `content_moderation`.

- [ ] **Step 2: Tạo workflow bằng script, KHÔNG bấm qua giao diện**

Theo đúng khuôn mẫu `drupal/scripts/create_ai_fields.php` đã có: chạy được lại nhiều lần, tái lập được trên máy khác, và người chấm đọc file là biết cấu hình gì — bấm tay thì cấu hình chỉ tồn tại trong CSDL của một máy.

Tạo `drupal/scripts/create_workflow.php`:

```php
<?php

/**
 * Tạo workflow "Kiểm duyệt nội dung" với state needs_review cho Article.
 *
 * State `needs_review` là tín hiệu DUY NHẤT kích hoạt hệ Multi-Agent chấm bài
 * (spec 2026-08-07 mục 4). Hệ thống AI không nằm trong bất kỳ transition nào:
 * chấm xong node vẫn ở needs_review, người duyệt tự quyết.
 *
 * Chạy lại được nhiều lần (idempotent).
 *
 * Chạy: ddev drush php:script scripts/create_workflow.php
 */

use Drupal\workflows\Entity\Workflow;

$id = 'kiem_duyet_noi_dung';

$workflow = Workflow::load($id);
if (!$workflow) {
  $workflow = Workflow::create([
    'id' => $id,
    'label' => 'Kiem duyet noi dung',
    'type' => 'content_moderation',
  ]);
  echo "Da tao workflow: $id\n";
}
else {
  echo "Workflow da ton tai, cap nhat lai: $id\n";
}

$type_plugin = $workflow->getTypePlugin();

// weight: thu tu hien thi trong dropdown, khong phai thu tu chuyen tiep.
$states = [
  'draft' => ['label' => 'Draft', 'published' => FALSE, 'default_revision' => FALSE, 'weight' => 0],
  'needs_review' => ['label' => 'Needs Review', 'published' => FALSE, 'default_revision' => FALSE, 'weight' => 1],
  'published' => ['label' => 'Published', 'published' => TRUE, 'default_revision' => TRUE, 'weight' => 2],
  'archived' => ['label' => 'Archived', 'published' => FALSE, 'default_revision' => TRUE, 'weight' => 3],
];
foreach ($states as $state_id => $cfg) {
  if (!$workflow->getTypePlugin()->hasState($state_id)) {
    $type_plugin->addState($state_id, $cfg['label']);
  }
  $type_plugin->setStateTypeConfiguration($state_id, [
    'published' => $cfg['published'],
    'default_revision' => $cfg['default_revision'],
  ]);
  $workflow->getTypePlugin()->setStateWeight($state_id, $cfg['weight']);
  echo "  state: $state_id\n";
}

$transitions = [
  'create_new_draft' => ['Create New Draft', ['draft', 'needs_review', 'published'], 'draft'],
  'gui_duyet' => ['Gui duyet', ['draft'], 'needs_review'],
  'publish' => ['Publish', ['needs_review', 'published'], 'published'],
  'archive' => ['Archive', ['published'], 'archived'],
  'khoi_phuc_draft' => ['Khoi phuc ve Draft', ['archived'], 'draft'],
];
foreach ($transitions as $tid => [$label, $from, $to]) {
  if ($type_plugin->hasTransition($tid)) {
    $type_plugin->setTransitionFromStates($tid, $from);
  }
  else {
    $type_plugin->addTransition($tid, $label, $from, $to);
  }
  echo "  transition: $tid\n";
}

// Ap workflow cho content type Article.
$type_plugin->addEntityTypeAndBundle('node', 'article');

$workflow->save();
echo "Da luu workflow. Article gio co state needs_review.\n";
```

Chạy:

```bash
cd drupal
ddev drush php:script scripts/create_workflow.php
```

Expected: in ra 4 dòng `state:`, 5 dòng `transition:` và dòng cuối `Da luu workflow`.

- [ ] **Step 3: Kiểm workflow đã áp đúng**

```bash
cd drupal
ddev drush config:get workflows.workflow.kiem_duyet_noi_dung type_settings.entity_types
ddev drush config:get workflows.workflow.kiem_duyet_noi_dung type_settings.states.needs_review
```

Expected: lệnh đầu có `node: [article]`; lệnh sau có `published: false` và `default_revision: false`.

Chạy lại script lần thứ hai để xác nhận idempotent:

```bash
ddev drush php:script scripts/create_workflow.php
```

Expected: in `Workflow da ton tai, cap nhat lai`, không lỗi.

- [ ] **Step 4: Kiểm chứng JSON:API — ĐÂY LÀ BƯỚC QUYẾT ĐỊNH**

Chuyển một bài bất kỳ sang "Needs Review" trong giao diện admin, rồi:

```bash
cd drupal
ddev drush uinf 1 --fields=uid
curl -s -u "$DRUPAL_USER:$DRUPAL_PASSWORD" \
  "http://drupal.ddev.site/jsonapi/node/article?filter%5Bmoderation_state%5D=needs_review&page%5Blimit%5D=5" \
  | python -m json.tool | head -40
```

Ba kết cục có thể, và mỗi cái dẫn tới một đường khác nhau ở Task 5:

| Kết quả | Nghĩa | Làm gì |
|---|---|---|
| Trả về đúng bài vừa chuyển | Lọc được | Task 5 dùng đúng filter này |
| Trả về **mọi** bài (filter bị bỏ qua) | Không lọc được | Task 5 lọc `filter[status]=0` rồi lọc `moderation_state` phía Python |
| HTTP 400 kèm lỗi về filter | Không lọc được | Như trên |

- [ ] **Step 5: Ghi bằng chứng vào file**

Tạo `docs/evidence/needs_review_jsonapi_kiem_chung.txt` với nội dung thật (không phải chép mẫu):

```
Ngay kiem: 2026-08-07
Lenh: curl ... filter[moderation_state]=needs_review
Ket qua: <dan nguyen van 20 dong dau cua response>
Ket luan: JSON:API CO / KHONG loc duoc moderation_state
Anh huong: reconcile.py dung filter truc tiep / phai loc phia Python
```

- [ ] **Step 6: Commit**

```bash
git add drupal/scripts/create_workflow.php docs/evidence/needs_review_jsonapi_kiem_chung.txt
git commit -m "chore: bat content_moderation, tao workflow needs_review bang script"
```

---

### Task 2: Tách `content_hash` ra `text_utils`

**Files:**
- Modify: `multiagent/src/text_utils.py`
- Modify: `multiagent/src/graph.py:204-220`
- Modify: `multiagent/scripts/test_report_json.py:12`

**Interfaces:**
- Produces: `text_utils.content_hash(fields: dict) -> str` — Task 5, 6, 7 đều gọi.

**Vì sao:** hàm này sắp có **ba** người dùng (graph, reconcile, worker). Để nó là `_content_hash` private trong `graph.py` thì hai chỗ kia phải hoặc import private, hoặc chép lại công thức. `text_utils.py` tồn tại đúng vì lý do này — docstring của nó viết: *"nếu hai bên bóc khác nhau thì tần suất thống kê được sẽ không khớp"*.

- [ ] **Step 1: Chạy test hiện có để có mốc so sánh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_report_json.py
```

Expected: PASS toàn bộ. Ghi lại số dòng `[PASS]`.

- [ ] **Step 2: Thêm hàm vào `text_utils.py`**

Thêm `import hashlib` vào đầu file (sau `import html`), và thêm vào cuối file:

```python
# Cac field tham gia content_hash, DUNG THU TU NAY. Phia PHP
# (AiReportRenderer::HASH_FIELDS) phai ghep y het, neu lech thi bang canh bao
# "noi dung da thay doi" hien sai vinh vien. Co test hop dong dung chung file
# drupal/scripts/content_hash_fixture.json de bat sai lech nay.
_HASH_FIELDS = ("title", "body", "summary", "meta_description")


def content_hash(fields: dict) -> str:
    """Bam noi dung da cham, de biet bai co bi sua sau khi cham khong.

    Dung hash chu KHONG dung moc thoi gian `changed` cua node: chinh lenh
    PATCH cua write_back() lam `changed` nhay, nen so moc do se luon bao
    "noi dung da doi" ngay sau khi cham. Hash chi doi khi noi dung that su doi.

    O day chu khong o graph.py vi tu 2026-08-07 co BA nguoi dung: graph
    (dung bao cao), reconcile (so voi hash da cham), worker (tra run_log).
    De private trong graph thi hai cho kia phai chep lai cong thuc - dung loai
    trung lap ma config-spec.md muc 1 ghi lai nhu mot loi da tra gia.
    """
    ghep = "\n".join(str(fields.get(k) or "") for k in _HASH_FIELDS)
    return hashlib.sha256(ghep.encode("utf-8")).hexdigest()
```

- [ ] **Step 3: Sửa `graph.py` dùng hàm mới**

Xoá khối `_HASH_FIELDS` + `def _content_hash(...)` (dòng 204–220). Sửa import ở đầu file: xoá `import hashlib`, và đổi dòng

```python
from text_utils import strip_html, trich_dan_co_that
```

Chú ý: `graph.py` hiện **không** import `text_utils`. Thêm dòng mới sau `from state import ContentReviewState`:

```python
from text_utils import content_hash
```

Sửa chỗ gọi trong `_build_report_json` (dòng ~279):

```python
        "content_hash": content_hash(state.get("fields") or {}),
```

- [ ] **Step 4: Sửa import trong test hợp đồng**

Trong `multiagent/scripts/test_report_json.py`, đổi dòng 12:

```python
from text_utils import content_hash
```

rồi thay mọi chỗ `_content_hash(` thành `content_hash(` trong file đó (5 chỗ: dòng 33 hai lần, 39, 46 hai lần, 51, 59 hai lần).

- [ ] **Step 5: Chạy lại test — phải xanh y như Step 1**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_report_json.py
```

Expected: PASS y hệt Step 1, đặc biệt `[PASS] hash khop fixture (hop dong voi phia PHP)`. Đây là bằng chứng đây là refactor thuần, không đổi giá trị hash.

- [ ] **Step 6: Chạy toàn bộ bộ test**

```bash
cd multiagent
for f in scripts/test_*.py; do .venv/Scripts/python.exe "$f" > /dev/null || echo "FAIL $f"; done
```

Expected: không in dòng FAIL nào.

- [ ] **Step 7: Commit**

```bash
git add multiagent/src/text_utils.py multiagent/src/graph.py multiagent/scripts/test_report_json.py
git commit -m "refactor: chuyen content_hash sang text_utils de dung chung 3 noi"
```

---

### Task 3: `src/job_queue.py` — hàng đợi trên Postgres

**Files:**
- Create: `multiagent/src/job_queue.py`
- Test: `multiagent/scripts/test_job_queue.py`

**Interfaces:**
- Consumes: `db.dsn()`, `db.get_conn()` (đã có)
- Produces:
  - `job_queue.dam_bao_bang(conn) -> None`
  - `job_queue.enqueue(conn, node_id: str, content_hash: str, source: str, force: bool = False) -> dict` → `{"status": "queued"|"duplicate", "job_id": int}`
  - `job_queue.claim(conn, worker_id: str) -> dict | None` → `{"id", "node_id", "content_hash", "attempts"}`
  - `job_queue.complete(conn, job_id: int) -> None`
  - `job_queue.fail(conn, job_id: int, loi: str, attempts: int) -> str` → trạng thái mới (`"queued"` hoặc `"failed"`)
  - `job_queue.reclaim_stuck(conn) -> int` → số job đã thu hồi
  - `job_queue.co_job_that_bai(conn, node_id: str, content_hash: str) -> bool`
  - `job_queue.job_moi_nhat(conn, node_id: str) -> dict | None`
  - `job_queue.thong_ke(conn) -> dict` → `{"queued", "running", "failed"}`

- [ ] **Step 1: Viết test — chạy trước khi có code**

Tạo `multiagent/scripts/test_job_queue.py`:

```python
"""Test hang doi review_job (spec 2026-08-07 muc 5.1, 6.2).

CAN POSTGRES THAT, khac voi cac bo test khac cua du an. Ly do: `FOR UPDATE
SKIP LOCKED` la thu dang kiem nhat o day va no KHONG gia lap duoc - mot
FakeConn se cho qua ca mot ban cai dat khong he co SKIP LOCKED.

Khong ket noi duoc -> in [SKIP] va thoat 0, de bo test van "chay duoc o bat cu
dau". NHUNG [SKIP] KHONG PHAI [PASS] - xem docs/pre-demo-checklist.md muc 5.

Chay: .venv\\Scripts\\python.exe scripts\\test_job_queue.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
import job_queue as q

SCHEMA = "vf_test_job_queue"


def _mo_conn():
    """Mot ket noi RIENG (khong dung db.get_conn cache) tro vao schema tam."""
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"SET search_path TO {SCHEMA}")
    return conn


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
    return conn


def test_enqueue_va_claim(conn):
    kq = q.enqueue(conn, "uuid-1", "hash-a", "event")
    assert kq["status"] == "queued", kq
    job = q.claim(conn, "w1")
    assert job["node_id"] == "uuid-1" and job["content_hash"] == "hash-a", job
    assert job["attempts"] == 1, job
    assert q.claim(conn, "w1") is None, "khong con job nao ma van claim duoc"
    print("[PASS] enqueue roi claim ra dung job, claim lan hai tra None")


def test_dedup_chan_job_trung(conn):
    q.enqueue(conn, "uuid-2", "hash-b", "event")
    kq = q.enqueue(conn, "uuid-2", "hash-b", "reconcile")
    assert kq["status"] == "duplicate", kq
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM review_job WHERE node_id='uuid-2'")
        assert cur.fetchone()[0] == 1, "dedup khong chan"
    print("[PASS] cung (node_id, content_hash) -> chi mot job")


def test_noi_dung_doi_thi_tao_job_moi(conn):
    q.enqueue(conn, "uuid-3", "hash-c", "event")
    kq = q.enqueue(conn, "uuid-3", "hash-KHAC", "event")
    assert kq["status"] == "queued", kq
    print("[PASS] content_hash khac -> job moi")


def test_skip_locked_hai_worker_khong_giam_chan(conn):
    """Phep kiem QUAN TRONG NHAT cua file nay.

    Mo mot giao dich tren conn A va giu no, roi cho conn B claim. Neu cau
    UPDATE thieu SKIP LOCKED thi B se DOI khoa cua A - va vi B dat
    lock_timeout = 2s nen no nem loi thay vi treo mai. Treo mai la kieu that
    bai te nhat cho mot bo test.
    """
    q.enqueue(conn, "uuid-4a", "h4a", "event")
    q.enqueue(conn, "uuid-4b", "h4b", "event")

    conn_b = _mo_conn()
    with conn_b.cursor() as cur:
        cur.execute("SET lock_timeout = '2s'")
    try:
        with conn.transaction():
            job_a = q.claim(conn, "wA")
            job_b = q.claim(conn_b, "wB")
            assert job_a is not None and job_b is not None, (job_a, job_b)
            assert job_a["id"] != job_b["id"], "hai worker claim trung mot job"
        print("[PASS] SKIP LOCKED: hai worker nhan hai job khac nhau")
    finally:
        conn_b.close()


def test_fail_backoff_roi_dead_letter(conn):
    q.enqueue(conn, "uuid-5", "h5", "event")
    job = q.claim(conn, "w1")
    assert q.fail(conn, job["id"], "loi 1", job["attempts"]) == "queued"
    with conn.cursor() as cur:
        cur.execute("SELECT run_after > now() FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] is True, "backoff khong day run_after ra sau"
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s", (job["id"],))

    job = q.claim(conn, "w1")
    assert job["attempts"] == 2, job
    assert q.fail(conn, job["id"], "loi 2", job["attempts"]) == "queued"
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s", (job["id"],))

    job = q.claim(conn, "w1")
    assert job["attempts"] == 3, job
    assert q.fail(conn, job["id"], "loi 3", job["attempts"]) == "failed"
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s", (job["id"],))
        status, loi = cur.fetchone()
    assert status == "failed" and loi == "loi 3", (status, loi)
    print("[PASS] 3 lan that bai -> dead-letter, giu last_error")


def test_job_failed_khong_bi_dedup_chan(conn):
    """Dedup CO Y loai `failed` - job hong phai xep hang lai duoc."""
    kq = q.enqueue(conn, "uuid-5", "h5", "manual")
    assert kq["status"] == "queued", kq
    print("[PASS] job da failed khong chan job moi cung hash")


def test_co_job_that_bai(conn):
    assert q.co_job_that_bai(conn, "uuid-5", "h5") is True
    assert q.co_job_that_bai(conn, "uuid-5", "hash-khong-co") is False
    print("[PASS] co_job_that_bai tra dung ca hai chieu")


def test_thu_hoi_job_ket(conn):
    q.enqueue(conn, "uuid-6", "h6", "event")
    job = q.claim(conn, "w-chet")
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE review_job SET claimed_at = now() - interval '20 minutes' "
            "WHERE id=%s", (job["id"],))
    assert q.reclaim_stuck(conn) == 1
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "queued"
    print("[PASS] job ket qua 15 phut duoc thu hoi ve queued")


def test_force_dat_superseded_va_tao_job_moi(conn):
    q.enqueue(conn, "uuid-7", "h7", "event")
    job = q.claim(conn, "w1")
    q.complete(conn, job["id"])
    assert q.enqueue(conn, "uuid-7", "h7", "event")["status"] == "duplicate"

    kq = q.enqueue(conn, "uuid-7", "h7", "manual", force=True)
    assert kq["status"] == "queued", kq
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "superseded"
    print("[PASS] force -> job cu superseded, job moi tao duoc")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"Chay `docker compose up -d` roi thu lai. LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_enqueue_va_claim,
        test_dedup_chan_job_trung,
        test_noi_dung_doi_thi_tao_job_moi,
        test_skip_locked_hai_worker_khong_giam_chan,
        test_fail_backoff_roi_dead_letter,
        test_job_failed_khong_bi_dedup_chan,
        test_co_job_that_bai,
        test_thu_hoi_job_ket,
        test_force_dat_superseded_va_tao_job_moi,
    ):
        try:
            fn(conn)
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy test để xác nhận nó đỏ đúng lý do**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_job_queue.py
```

Expected: `ModuleNotFoundError: No module named 'job_queue'`.

> **VÌ SAO TÊN LÀ `job_queue.py` CHỨ KHÔNG PHẢI `queue.py` — đã trả giá một lần, ghi lại để không ai "sửa cho gọn".**
>
> Bản đầu của kế hoạch đặt tên `src/queue.py`. Khi triển khai thật (2026-08-07) nó **làm sập toàn bộ tầng DB của dự án**, không riêng module này:
>
> ```
> File ".venv\Lib\site-packages\psycopg\_acompat.py", line 29
>     class Queue(queue.Queue[T]):
> AttributeError: module 'queue' has no attribute 'Queue'
> ```
>
> Nguyên nhân: mọi script trong `scripts/` chèn `src/` vào **`sys.path[0]`**, nên `src/queue.py` che module chuẩn `queue` của Python — mà `psycopg` lại `import queue` để dựng connection pool. Hệ quả: `import db` chết, tức mọi thứ chạm Postgres đều chết.
>
> **Bài học rộng hơn tên một file:** quy ước "chèn `src/` vào `sys.path[0]`" của repo này biến **mọi** file trong `src/` trùng tên module chuẩn (`queue`, `types`, `io`, `json`, `logging`...) thành một quả mìn. Đặt tên module mới trong `src/` phải kiểm chéo với thư viện chuẩn trước.

- [ ] **Step 3: Viết `src/job_queue.py`**

```python
"""Hang doi cham diem, dat tren Postgres dang co.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md

VI SAO POSTGRES CHU KHONG PHAI REDIS/RABBITMQ (spec muc 2, quyet dinh Q1):
`FOR UPDATE SKIP LOCKED` cho dung nhung thu mot broker cho o quy mo nay -
nhieu worker khong giam chan nhau, job khong mat khi worker chet, retry co
backoff, dead-letter - ma khong them mot container phai van hanh, backup va
giai thich. Day la mau dung trong san pham that (pgmq, Oban, River,
Solid Queue). Khac biet chi xuat hien o quy mo hang nghin job/giay.
"""
import db

TEN_BANG = "review_job"

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
FAILED = "failed"
SUPERSEDED = "superseded"

MAX_ATTEMPTS = 3
BACKOFF_GIAY = (60, 300, 900)
KET_SAU_PHUT = 15


def dam_bao_bang(conn) -> None:
    """Tao bang neu chua co. Cung mau voi db.dam_bao_bang cho kb_chunk -
    khong dung framework migration, o hai bang thi do la ha tang thua."""
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {TEN_BANG} ("
            "  id           bigserial PRIMARY KEY,"
            "  node_id      text        NOT NULL,"
            "  content_hash text        NOT NULL,"
            "  status       text        NOT NULL,"
            "  attempts     int         NOT NULL DEFAULT 0,"
            "  run_after    timestamptz NOT NULL DEFAULT now(),"
            "  claimed_at   timestamptz,"
            "  claimed_by   text,"
            "  last_error   text,"
            "  source       text        NOT NULL,"
            "  created_at   timestamptz NOT NULL DEFAULT now(),"
            "  updated_at   timestamptz NOT NULL DEFAULT now()"
            ")"
        )
        # Index BO PHAN: chi rang buoc tren job chua ket thuc. Co y loai
        # `failed` (job hong phai xep hang lai duoc) va `superseded` (danh
        # rieng cho nut "Cham lai" thu cong).
        cur.execute(
            f"CREATE UNIQUE INDEX IF NOT EXISTS {TEN_BANG}_dedup "
            f"ON {TEN_BANG} (node_id, content_hash) "
            f"WHERE status IN ('{QUEUED}', '{RUNNING}', '{DONE}')"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {TEN_BANG}_claim "
            f"ON {TEN_BANG} (status, run_after)"
        )


def enqueue(conn, node_id: str, content_hash: str, source: str,
            force: bool = False) -> dict:
    """Xep mot job. Trung dedup -> khong tao gi, tra status='duplicate'.

    `force=True` (nut "Cham lai" thu cong): danh dau job `done` cua dung cap
    (node_id, content_hash) thanh `superseded` de no roi khoi index dedup,
    roi chen job moi. KHONG xoa ban ghi cu - lich su van tra duoc.
    """
    if force:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() "
                f"WHERE node_id=%s AND content_hash=%s AND status=%s",
                (SUPERSEDED, node_id, content_hash, DONE),
            )
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} (node_id, content_hash, status, source) "
            f"VALUES (%s, %s, %s, %s) ON CONFLICT DO NOTHING RETURNING id",
            (node_id, content_hash, QUEUED, source),
        )
        row = cur.fetchone()
    if row is None:
        cu = job_moi_nhat(conn, node_id)
        return {"status": "duplicate", "job_id": cu["id"] if cu else None}
    return {"status": QUEUED, "job_id": row[0]}


def claim(conn, worker_id: str):
    """Nhan mot job. Tra None khi khong co viec.

    SKIP LOCKED: worker A khoa dong no lay, worker B thay dong dang khoa thi
    BO QUA va lay dong ke tiep - khong khoa toan bang, khong can khoa phan tan.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, claimed_at=now(), claimed_by=%s, "
            f"attempts=attempts+1, updated_at=now() "
            f"WHERE id = (SELECT id FROM {TEN_BANG} "
            f"            WHERE status=%s AND run_after <= now() "
            f"            ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1) "
            f"RETURNING id, node_id, content_hash, attempts",
            (RUNNING, worker_id, QUEUED),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "node_id": row[1], "content_hash": row[2],
            "attempts": row[3]}


def complete(conn, job_id: int) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, updated_at=now() WHERE id=%s",
            (DONE, job_id),
        )


def fail(conn, job_id: int, loi: str, attempts: int) -> str:
    """That bai mot lan. Chua het luot -> xep lai voi backoff; het -> dead-letter.

    `attempts` la so lan DA thu (claim() tang truoc khi chay), nen lan dau
    that bai co attempts = 1 va dung BACKOFF_GIAY[0].
    """
    if attempts >= MAX_ATTEMPTS:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, updated_at=now() "
                f"WHERE id=%s",
                (FAILED, loi, job_id),
            )
        return FAILED

    giay = BACKOFF_GIAY[min(attempts - 1, len(BACKOFF_GIAY) - 1)]
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, last_error=%s, "
            f"run_after = now() + (%s * interval '1 second'), updated_at=now() "
            f"WHERE id=%s",
            (QUEUED, loi, giay, job_id),
        )
    return QUEUED


def reclaim_stuck(conn) -> int:
    """Thu hoi job ket o `running` vi worker chet giua chung."""
    with conn.cursor() as cur:
        cur.execute(
            f"UPDATE {TEN_BANG} SET status=%s, run_after=now(), updated_at=now() "
            f"WHERE status=%s AND claimed_at < now() - interval '{KET_SAU_PHUT} minutes'",
            (QUEUED, RUNNING),
        )
        return cur.rowcount


def co_job_that_bai(conn, node_id: str, content_hash: str) -> bool:
    """Da co job dead-letter cho dung cap nay chua?

    Vong doi soat PHAI hoi cau nay truoc khi enqueue. Khong hoi thi no se
    hoi sinh job da dead-letter moi 5 phut, va co che dead-letter bi vo hieu
    hoan toan - thanh vong lap tieu tien API vo han (spec muc 6.3.1).
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT 1 FROM {TEN_BANG} "
            f"WHERE node_id=%s AND content_hash=%s AND status=%s LIMIT 1",
            (node_id, content_hash, FAILED),
        )
        return cur.fetchone() is not None


def job_moi_nhat(conn, node_id: str):
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, status, attempts, last_error, created_at, updated_at "
            f"FROM {TEN_BANG} WHERE node_id=%s ORDER BY created_at DESC LIMIT 1",
            (node_id,),
        )
        row = cur.fetchone()
    if row is None:
        return None
    return {"id": row[0], "status": row[1], "attempts": row[2],
            "last_error": row[3], "created_at": row[4], "updated_at": row[5]}


def thong_ke(conn) -> dict:
    with conn.cursor() as cur:
        cur.execute(f"SELECT status, count(*) FROM {TEN_BANG} GROUP BY status")
        dem = dict(cur.fetchall())
    return {QUEUED: dem.get(QUEUED, 0), RUNNING: dem.get(RUNNING, 0),
            FAILED: dem.get(FAILED, 0)}
```

- [ ] **Step 4: Chạy test — phải xanh hết**

```bash
cd multiagent
docker compose up -d
.venv/Scripts/python.exe scripts/test_job_queue.py
```

Expected: 9 dòng `[PASS]` rồi `OK`.

- [ ] **Step 5: Kiểm test thật sự bắt được lỗi (không xanh vì không kiểm gì)**

Tạm xoá chữ `SKIP LOCKED` khỏi câu SQL trong `claim()`, chạy lại test.

Expected: `test_skip_locked_hai_worker_khong_giam_chan` **đỏ** với lỗi lock timeout (không phải treo). Khôi phục lại `SKIP LOCKED` rồi chạy lại cho xanh.

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/job_queue.py multiagent/scripts/test_job_queue.py
git commit -m "feat: hang doi review_job tren Postgres voi FOR UPDATE SKIP LOCKED"
```

---

### Task 4: `src/audit.py` — nhật ký truy vết

**Files:**
- Create: `multiagent/src/audit.py`
- Test: `multiagent/scripts/test_audit.py`

**Interfaces:**
- Produces:
  - `audit.dam_bao_bang(conn) -> None`
  - `audit.ghi(conn, *, job_id, node_id, content_hash, duration_ms, report: dict, config_meta: dict, usage: list, model: str, payload: dict) -> int`
  - `audit.da_cham(conn, node_id: str, content_hash: str) -> dict | None` → `{"id", "payload"}`

- [ ] **Step 1: Viết test**

Tạo `multiagent/scripts/test_audit.py`:

```python
"""Test nhat ky truy vet run_log (spec 2026-08-07 muc 5.2).

Can Postgres that, cung ly do va cung cach xu ly [SKIP] nhu test_job_queue.py.
Chay: .venv\\Scripts\\python.exe scripts\\test_audit.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db

SCHEMA = "vf_test_audit"

_REPORT = {
    "node_id": "uuid-1",
    "final_score": 76.5,
    "decision": "needs_revision",
    "missing_agents": ["seo"],
    "note": "Diem so chua day du",
    "details": {"compliance": {"score": 80.0, "flags": []}, "seo": None},
}
_CONFIG_META = {"calibrated": False, "model": None, "rubric_version": None}
_USAGE = [{"model": "claude-haiku-4-5-20251001", "input_tokens": 100,
           "output_tokens": 20}]
_PAYLOAD = {"status": "needs_revision", "score": 76.5,
            "suggestions": "day la goi y", "report_json": {"version": 1}}


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    audit.dam_bao_bang(conn)
    return conn


def _ghi_mau(conn, node_id="uuid-1", content_hash="hash-a"):
    return audit.ghi(conn, job_id=1, node_id=node_id, content_hash=content_hash,
                     duration_ms=42000, report=_REPORT, config_meta=_CONFIG_META,
                     usage=_USAGE, model="claude-haiku-4-5-20251001",
                     payload=_PAYLOAD)


def test_ghi_du_truong(conn):
    rid = _ghi_mau(conn)
    with conn.cursor() as cur:
        cur.execute(
            "SELECT node_id, decision, final_score, missing_agents, note, "
            "agent_results, config_meta, usage, model, payload, duration_ms "
            "FROM run_log WHERE id=%s", (rid,))
        r = cur.fetchone()
    assert r[0] == "uuid-1" and r[1] == "needs_revision", r
    assert float(r[2]) == 76.5, r
    assert r[3] == ["seo"], r
    assert r[5]["compliance"]["score"] == 80.0, r[5]
    assert r[6]["calibrated"] is False, r[6]
    assert r[7][0]["input_tokens"] == 100, r[7]
    assert r[9]["suggestions"] == "day la goi y", r[9]
    assert r[10] == 42000, r
    print("[PASS] ban ghi run_log co du truong, jsonb doc lai dung kieu")


def test_final_score_none_khong_thanh_0(conn):
    """Compliance loi -> final_score = None nghia la CHUA cham duoc.

    Ghi 0 vao day se khien moi phan tich ve sau hieu nham la bai cuc te -
    dung nguyen tac architecture.md muc 6.4.
    """
    bao_cao = dict(_REPORT, final_score=None, decision="needs_revision")
    rid = audit.ghi(conn, job_id=2, node_id="uuid-2", content_hash="h2",
                    duration_ms=100, report=bao_cao, config_meta=_CONFIG_META,
                    usage=[], model="m", payload=_PAYLOAD)
    with conn.cursor() as cur:
        cur.execute("SELECT final_score FROM run_log WHERE id=%s", (rid,))
        assert cur.fetchone()[0] is None
    print("[PASS] final_score None duoc giu la NULL, khong quy thanh 0")


def test_da_cham_tra_payload(conn):
    _ghi_mau(conn, "uuid-3", "h3")
    kq = audit.da_cham(conn, "uuid-3", "h3")
    assert kq is not None and kq["payload"]["status"] == "needs_revision", kq
    print("[PASS] da_cham tra ve payload da PATCH lan truoc")


def test_da_cham_khac_hash_tra_none(conn):
    """Noi dung doi -> phai cham lai that, khong duoc dung ket qua cu."""
    _ghi_mau(conn, "uuid-4", "h4")
    assert audit.da_cham(conn, "uuid-4", "hash-moi") is None
    print("[PASS] hash khac -> khong tai su dung ket qua cu")


def test_khong_luu_bi_mat(conn):
    """operations.md muc 2.5: khong ghi API key, khong ghi toan van system prompt."""
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM information_schema.columns "
                    "WHERE table_name='run_log' AND table_schema=%s "
                    "AND column_name IN ('api_key','system_prompt','body')",
                    (SCHEMA,))
        assert cur.fetchone()[0] == 0
    print("[PASS] schema khong co cot cho bi mat/toan van bai")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_ghi_du_truong,
        test_final_score_none_khong_thanh_0,
        test_da_cham_tra_payload,
        test_da_cham_khac_hash_tra_none,
        test_khong_luu_bi_mat,
    ):
        try:
            fn(conn)
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy test để xác nhận đỏ**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_audit.py
```

Expected: `ModuleNotFoundError: No module named 'audit'`.

- [ ] **Step 3: Viết `src/audit.py`**

```python
"""Nhat ky truy vet: mot ban ghi append-only cho moi lan cham.

Thiet ke: docs/operations.md muc 2 (ghi cai gi, khong ghi cai gi).
Cho luu: Postgres thay vi JSONL - ly do doi ket luan o spec 2026-08-07 muc 2.1
(tien de da doi: luc operations.md viet thi phia Multi-Agent chua co CSDL nao).

Tra loi duoc cau "bai nay bi chan hoi thang truoc, vi sao" - Drupal giu duoc
DIEM BAO NHIEU qua revision, nhung khong giu BOI CANH sinh ra no.
"""
import json

TEN_BANG = "run_log"


def dam_bao_bang(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {TEN_BANG} ("
            "  id             bigserial PRIMARY KEY,"
            "  job_id         bigint,"
            "  node_id        text        NOT NULL,"
            "  content_hash   text        NOT NULL,"
            "  scored_at      timestamptz NOT NULL DEFAULT now(),"
            "  duration_ms    int,"
            "  decision       text,"
            "  final_score    numeric,"
            "  missing_agents jsonb NOT NULL DEFAULT '[]'::jsonb,"
            "  veto_reason    text,"
            "  note           text,"
            "  agent_results  jsonb NOT NULL,"
            "  config_meta    jsonb NOT NULL,"
            "  usage          jsonb NOT NULL,"
            "  model          text  NOT NULL,"
            "  payload        jsonb NOT NULL"
            ")"
        )
        cur.execute(
            f"CREATE INDEX IF NOT EXISTS {TEN_BANG}_tra_cuu "
            f"ON {TEN_BANG} (node_id, content_hash)"
        )


def _js(x) -> str:
    return json.dumps(x, ensure_ascii=False, default=str)


def ghi(conn, *, job_id, node_id: str, content_hash: str, duration_ms: int,
        report: dict, config_meta: dict, usage: list, model: str,
        payload: dict) -> int:
    """Ghi mot ban ghi. CHI INSERT - khong bao gio UPDATE hay DELETE.

    `final_score = None` duoc giu nguyen NULL, KHONG quy ve 0: None nghia la
    CHUA cham duoc (Compliance loi), khac han voi 0 diem.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"INSERT INTO {TEN_BANG} "
            "(job_id, node_id, content_hash, duration_ms, decision, final_score,"
            " missing_agents, veto_reason, note, agent_results, config_meta,"
            " usage, model, payload) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s::jsonb,%s::jsonb,"
            "        %s::jsonb,%s,%s::jsonb) RETURNING id",
            (
                job_id, node_id, content_hash, duration_ms,
                report.get("decision"), report.get("final_score"),
                _js(report.get("missing_agents") or []),
                report.get("veto_reason"), report.get("note"),
                _js(report.get("details") or {}),
                _js(config_meta), _js(usage), model, _js(payload),
            ),
        )
        return cur.fetchone()[0]


def da_cham(conn, node_id: str, content_hash: str):
    """Da co ket qua cho dung cap (node_id, content_hash) chua?

    Worker hoi cau nay TRUOC khi goi LLM. Co roi -> chi ghi lai `payload` cu
    sang Drupal, khong chay lai pipeline. Day la cho chan duong mat tien khi
    write_back that bai: cham lai mot bai ton $0,057 that.
    """
    with conn.cursor() as cur:
        cur.execute(
            f"SELECT id, payload FROM {TEN_BANG} "
            f"WHERE node_id=%s AND content_hash=%s ORDER BY scored_at DESC LIMIT 1",
            (node_id, content_hash),
        )
        row = cur.fetchone()
    return None if row is None else {"id": row[0], "payload": row[1]}
```

- [ ] **Step 4: Chạy test — phải xanh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_audit.py
```

Expected: 5 dòng `[PASS]` rồi `OK`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/audit.py multiagent/scripts/test_audit.py
git commit -m "feat: nhat ky truy vet run_log ghi vao Postgres"
```

---

### Task 5: `drupal_client` — `write_back` trả `bool`, thêm `liet_ke_can_cham`

**Files:**
- Modify: `multiagent/src/drupal_client.py:94-175`
- Test: `multiagent/scripts/test_drupal_client_worker.py`

**Interfaces:**
- Consumes: `text_utils.content_hash` (Task 2)
- Produces:
  - `drupal_client.write_back(...) -> bool`
  - `drupal_client.liet_ke_can_cham(limit: int = 50) -> list[dict]` → mỗi phần tử `{"node_id", "content_hash", "hash_da_cham"}`
  - `drupal_client._fields_tu_resource(resource: dict) -> dict`

**KẾT LUẬN CỦA TASK 1 — đã kiểm chứng thật, không còn là giả định:**

`filter[moderation_state]=needs_review` **KHÔNG dùng được**: JSON:API trả **HTTP 500** kèm `QueryException: 'moderation_state' not found`, vì đó là *computed field* nên không có cột để truy vấn. (Task 1 dự đoán 400 hoặc "trả về mọi bài" — thực tế là 500, cùng nhóm "không lọc được".)

**Nhưng `moderation_state` CÓ mặt trong `attributes` của response** (kiểm 2026-08-07: `attributes.moderation_state == 'draft'`). Nên cách làm là:

```
GET /jsonapi/node/article?filter[status]=0&page[limit]=50
rồi lọc phía Python: attributes.moderation_state == 'needs_review'
```

`filter[status]=0` lấy các node **chưa xuất bản** — bao trọn `draft`, `needs_review`, `archived` — rồi Python lọc tiếp. Lọc thô ở tầng HTTP, lọc tinh ở tầng Python.

> **GIỚI HẠN ĐÃ BIẾT của đường đối soát, phải ghi vào tài liệu ở Task 12 chứ không được giấu:**
> Với một bài **đã xuất bản** rồi tạo bản nháp mới đưa sang `needs_review`, revision mặc định vẫn là bản đã xuất bản (`needs_review` có `default_revision = false`). JSON:API trả revision mặc định, nên node đó có `status = 1` và `moderation_state = 'published'` — **đường đối soát không nhìn thấy nó**.
>
> Ảnh hưởng thật: **đường event vẫn bắt được** (hook đọc `moderation_state` của revision vừa lưu), nên bài vẫn được chấm bình thường. Chỉ mất lớp lưới an toàn cho đúng trường hợp *bài đã xuất bản đang được sửa lại*. Với phạm vi hiện tại (bài mới đi `draft → needs_review → published`) thì không chạm tới.
>
> Muốn đóng hẳn thì phải đọc revision mới nhất chứ không phải revision mặc định — JSON:API core không expose sẵn đường đó. Ghi nhận là hướng mở rộng, **không** làm trong task này.

- [ ] **Step 1: Viết test**

Tạo `multiagent/scripts/test_drupal_client_worker.py`:

```python
"""Test hai thay doi cua drupal_client cho worker (spec 2026-08-07 muc 3.4).

Khong can Drupal that: thay requests.get/patch bang ham gia.
Chay: .venv\\Scripts\\python.exe scripts\\test_drupal_client_worker.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import drupal_client as dc
import requests
from text_utils import content_hash


class _Resp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._data


def test_write_back_thanh_cong_tra_true():
    dc.requests.patch = lambda *a, **kw: _Resp({}, 200)
    assert dc.write_back("uuid-1", "publish", 90.0, "goi y") is True
    print("[PASS] write_back thanh cong -> True")


def test_write_back_that_bai_tra_false_va_khong_nem():
    """Van KHONG raise (bai da ton tien API roi), nhung nguoi goi phai biet.

    Ban cu chi logging.warning nen worker se bao job `done` trong khi Drupal
    khong he co ket qua - dung loai bay im lang du an nay danh nhieu cong
    de diet.
    """
    def _patch_loi(*a, **kw):
        raise requests.ConnectionError("Drupal chet")

    dc.requests.patch = _patch_loi
    assert dc.write_back("uuid-1", "publish", 90.0, "goi y") is False
    print("[PASS] write_back that bai -> False, khong nem exception")


_RESOURCE = {
    "id": "uuid-aaa",
    "attributes": {
        "title": "Tieu de",
        "body": {"value": "<p>Noi dung</p>", "summary": "Tom tat"},
        "path": {"alias": "/bai-viet"},
        "field_meta_description": "Mo ta",
        "field_ai_report_json": None,
        "moderation_state": "needs_review",
    },
    "relationships": {},
}


def test_liet_ke_tinh_dung_hash_hien_tai():
    dc.requests.get = lambda *a, **kw: _Resp({"data": [_RESOURCE]})
    ds = dc.liet_ke_can_cham()
    assert len(ds) == 1, ds
    mong_doi = content_hash({
        "title": "Tieu de", "body": "<p>Noi dung</p>",
        "summary": "Tom tat", "meta_description": "Mo ta",
    })
    assert ds[0]["content_hash"] == mong_doi, ds[0]
    assert ds[0]["node_id"] == "uuid-aaa", ds[0]
    assert ds[0]["hash_da_cham"] is None, ds[0]
    print("[PASS] liet_ke_can_cham tinh hash tu dung 4 field")


def test_liet_ke_doc_duoc_hash_da_cham():
    res = dict(_RESOURCE)
    res["attributes"] = dict(_RESOURCE["attributes"],
                             field_ai_report_json='{"content_hash": "cu-123"}')
    dc.requests.get = lambda *a, **kw: _Resp({"data": [res]})
    assert dc.liet_ke_can_cham()[0]["hash_da_cham"] == "cu-123"
    print("[PASS] doc duoc content_hash trong field_ai_report_json")


def test_report_json_hong_khong_lam_sap():
    """Field chua JSON hong -> coi nhu chua cham, KHONG nem exception."""
    res = dict(_RESOURCE)
    res["attributes"] = dict(_RESOURCE["attributes"],
                             field_ai_report_json="{khong phai json")
    dc.requests.get = lambda *a, **kw: _Resp({"data": [res]})
    assert dc.liet_ke_can_cham()[0]["hash_da_cham"] is None
    print("[PASS] JSON hong -> hash_da_cham None, khong sap")


def test_loai_node_khong_o_needs_review():
    """filter[status]=0 con bao ca draft va archived - phai loc tinh phia Python.

    Khong loc thi vong doi soat se cham MOI ban nhap trong site, tuc tieu tien
    API cho nhung bai chua ai gui duyet.
    """
    draft = dict(_RESOURCE)
    draft["attributes"] = dict(_RESOURCE["attributes"], moderation_state="draft")
    dc.requests.get = lambda *a, **kw: _Resp({"data": [draft, _RESOURCE]})
    ds = dc.liet_ke_can_cham()
    assert len(ds) == 1 and ds[0]["node_id"] == "uuid-aaa", ds
    print("[PASS] node o draft/archived bi loai, chi giu needs_review")


def test_url_khong_dung_filter_moderation_state():
    """filter[moderation_state] lam JSON:API tra HTTP 500 (computed field).

    Khoa lai bang test vi day la thu de bi 'sua cho gon' ma khong biet no hong
    - va no hong o dang kho chan doan: ca vong doi soat chet lang le.
    """
    da_goi = []
    dc.requests.get = lambda url, **kw: (da_goi.append(url), _Resp({"data": []}))[1]
    dc.liet_ke_can_cham()
    assert "moderation_state" not in da_goi[0], da_goi[0]
    assert "filter%5Bstatus%5D=0" in da_goi[0], da_goi[0]
    print("[PASS] URL loc bang status=0, khong dung filter moderation_state")


if __name__ == "__main__":
    that_get, that_patch = dc.requests.get, dc.requests.patch
    failed = False
    for fn in (
        test_write_back_thanh_cong_tra_true,
        test_write_back_that_bai_tra_false_va_khong_nem,
        test_liet_ke_tinh_dung_hash_hien_tai,
        test_liet_ke_doc_duoc_hash_da_cham,
        test_report_json_hong_khong_lam_sap,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    dc.requests.get, dc.requests.patch = that_get, that_patch
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy test để xác nhận đỏ**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_drupal_client_worker.py
```

Expected: `[FAIL] test_write_back_thanh_cong_tra_true: assert None is True` và `AttributeError: module 'drupal_client' has no attribute 'liet_ke_can_cham'`.

- [ ] **Step 3: Sửa `drupal_client.py`**

Thêm `from text_utils import content_hash` vào khối import đầu file.

Tách phần dựng `fields` trong `fetch_content` thành hàm riêng — thay đoạn từ `resource = response.json()["data"]` tới `return ...` bằng:

```python
    resource = response.json()["data"]
    return {"fields": _fields_tu_resource(resource), "raw_content": resource}


def _fields_tu_resource(resource: dict) -> dict:
    """JSON:API resource -> 6 field noi dung. Doc phong thu: field nao chua
    cau hinh/de trong -> chuoi rong, khong lam sap pipeline.

    Tach rieng vi `liet_ke_can_cham()` cung phai doc y HET cach nay - hai
    cach doc khac nhau nghia la content_hash hai ben khong khop, va vong doi
    soat se cham lai vo han moi bai.
    """
    attributes = resource["attributes"]
    body = attributes.get("body") or {}
    path = attributes.get("path") or {}
    return {
        "title": attributes.get("title") or "",
        "body": body.get("value") or "",
        "summary": body.get("summary") or "",
        "url_alias": path.get("alias") or "",
        "meta_description": attributes.get("field_meta_description") or "",
        "image_alt": _extract_image_alt(resource, body.get("value") or ""),
    }
```

Đổi chữ ký và phần cuối của `write_back`:

```python
def write_back(
    node_id: str, status: str, score: Optional[float], suggestions: str,
    report_json: Optional[dict] = None,
) -> bool:
```

và thay khối `try/except` cuối hàm bằng:

```python
    try:
        _request_with_retry(
            requests.patch,
            url,
            headers=PATCH_HEADERS,
            json=payload,
            auth=AUTH,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        return True
    except requests.RequestException as e:
        # VAN khong raise: bai da duoc 4 agent cham xong (ton API call that),
        # de loi ghi-nguoc lam sap ca script se lang phi toan bo cong da lam.
        # NHUNG tra ve False, vi im lang o day la bay: worker se bao job
        # `done` trong khi Drupal khong he co ket qua.
        logging.warning("Write-back that bai cho node %s: %s", node_id, e)
        return False
```

Thêm vào cuối file:

```python
# KHONG dung filter[moderation_state]: do la computed field, JSON:API tra
# HTTP 500 "QueryException: 'moderation_state' not found" (kiem chung
# 2026-08-07, docs/evidence/needs_review_jsonapi_kiem_chung.txt).
#
# Thay bang: loc THO o tang HTTP theo status=0 (chua xuat ban - bao tron
# draft/needs_review/archived), roi loc TINH phia Python theo attribute
# `moderation_state` VAN CO trong response.
_LOC_CAN_CHAM = "filter%5Bstatus%5D=0"
_STATE_CAN_CHAM = "needs_review"


def liet_ke_can_cham(limit: int = 50) -> list:
    """Cac bai dang o "Needs Review", kem hash hien tai va hash da cham.

    Dung cho vong doi soat (spec muc 6.3). Tra list
    {node_id, content_hash, hash_da_cham}; `hash_da_cham` = None nghia la
    chua cham bao gio hoac bao cao doc khong duoc.

    GIOI HAN DA BIET: bai DA XUAT BAN roi tao ban nhap moi dua sang
    needs_review se khong hien o day, vi JSON:API tra revision MAC DINH (van
    la ban da xuat ban, do needs_review co default_revision = false). Duong
    event van bat duoc truong hop do, nen chi mat lop luoi an toan chu khong
    mat bai. Chi tiet o ke hoach Task 5.
    """
    url = (f"{BASE_URL}/jsonapi/node/article?{_LOC_CAN_CHAM}"
           f"&page%5Blimit%5D={limit}")
    response = _request_with_retry(
        requests.get, url, headers=JSONAPI_HEADERS, auth=AUTH,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    ra = []
    for resource in response.json().get("data", []):
        if resource["attributes"].get("moderation_state") != _STATE_CAN_CHAM:
            continue      # loc tinh: status=0 con bao ca draft va archived
        fields = _fields_tu_resource(resource)
        tho = resource["attributes"].get("field_ai_report_json")
        try:
            hash_da_cham = (json.loads(tho) or {}).get("content_hash") if tho else None
        except (ValueError, AttributeError):
            # Bao cao hong -> coi nhu chua cham. Khong duoc nem: mot node
            # hong khong duoc lam chet ca vong doi soat.
            hash_da_cham = None
        ra.append({
            "node_id": resource["id"],
            "content_hash": content_hash(fields),
            "hash_da_cham": hash_da_cham,
        })
    return ra
```

- [ ] **Step 4: Chạy test — phải xanh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_drupal_client_worker.py
```

Expected: 5 dòng `[PASS]` rồi `OK`.

- [ ] **Step 5: Chạy toàn bộ bộ test để chắc không vỡ chỗ khác**

```bash
cd multiagent
for f in scripts/test_*.py; do .venv/Scripts/python.exe "$f" > /dev/null || echo "FAIL $f"; done
```

Expected: không có dòng FAIL.

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/drupal_client.py multiagent/scripts/test_drupal_client_worker.py
git commit -m "feat: write_back tra bool va them liet_ke_can_cham cho vong doi soat"
```

---

### Task 6: `src/worker.py` — vòng lặp chấm

**Files:**
- Create: `multiagent/src/worker.py`
- Test: `multiagent/scripts/test_worker.py`

**Interfaces:**
- Consumes: `job_queue.claim/complete/fail/reclaim_stuck`, `audit.ghi/da_cham`, `drupal_client.write_back`, `graph.build_graph`, `config.load`, `ai_core.USAGE_LOG`, `ai_core.MODEL`
- Produces: `worker.chay_mot_job(conn, job, *, invoke=None, write_back_fn=None) -> str` (trả `"done"` hoặc `"queued"`/`"failed"`); `worker.vong_lap(...)`

- [ ] **Step 1: Viết test**

Tạo `multiagent/scripts/test_worker.py`:

```python
"""Test worker: xu ly mot job (spec 2026-08-07 muc 6.1, 7).

KHONG goi LLM, KHONG can Drupal: tiem `invoke` va `write_back_fn` gia.
Can Postgres that cho queue/run_log - [SKIP] neu khong co.
Chay: .venv\\Scripts\\python.exe scripts\\test_worker.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import audit
import db
import job_queue as q
import worker

SCHEMA = "vf_test_worker"

_STATE_XONG = {
    "node_id": "uuid-1",
    "decision": "needs_revision",
    "final_score": 76.5,
    "fields": {"title": "T", "body": "B", "summary": "S", "meta_description": "M"},
    "report": {
        "node_id": "uuid-1", "final_score": 76.5, "decision": "needs_revision",
        "missing_agents": [], "details": {"seo": {"score": 70, "issues": []}},
    },
}


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
    audit.dam_bao_bang(conn)
    return conn


def _job(conn, node_id, content_hash):
    q.enqueue(conn, node_id, content_hash, "event")
    return q.claim(conn, "test")


def test_job_thanh_cong_ghi_run_log_va_dong_job(conn):
    job = _job(conn, "uuid-1", "h1")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status FROM review_job WHERE id=%s", (job["id"],))
        assert cur.fetchone()[0] == "done"
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-1'")
        assert cur.fetchone()[0] == 1
    print("[PASS] job thanh cong -> run_log co ban ghi, job = done")


def test_write_back_that_bai_thi_job_xep_lai(conn):
    job = _job(conn, "uuid-2", "h2")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                              write_back_fn=lambda **kw: False)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT status, last_error FROM review_job WHERE id=%s",
                    (job["id"],))
        status, loi = cur.fetchone()
    assert status == "queued" and "write-back" in loi.lower(), (status, loi)
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-2'")
        assert cur.fetchone()[0] == 1, "run_log phai ghi TRUOC khi write_back"
    print("[PASS] write_back False -> job ve queued, run_log da ghi")


def test_da_co_run_log_thi_KHONG_goi_lai_pipeline(conn):
    """Chot chan tien: cham lai mot bai ton $0,057 that."""
    job1 = _job(conn, "uuid-3", "h3")
    worker.chay_mot_job(conn, job1, invoke=lambda s: _STATE_XONG,
                        write_back_fn=lambda **kw: False)
    with conn.cursor() as cur:
        cur.execute("UPDATE review_job SET run_after = now() WHERE id=%s",
                    (job1["id"],))

    da_goi = []

    def _invoke_khong_duoc_goi(state):
        da_goi.append(state)
        return _STATE_XONG

    job2 = q.claim(conn, "test")
    ket = worker.chay_mot_job(conn, job2, invoke=_invoke_khong_duoc_goi,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    assert da_goi == [], "da goi lai pipeline du run_log da co ket qua"
    print("[PASS] da co run_log -> chi write_back lai, khong goi LLM")


def test_pipeline_nem_loi_thi_job_that_bai(conn):
    def _no(state):
        raise RuntimeError("Drupal tra 404")

    job = _job(conn, "uuid-4", "h4")
    ket = worker.chay_mot_job(conn, job, invoke=_no,
                              write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT last_error FROM review_job WHERE id=%s", (job["id"],))
        assert "404" in cur.fetchone()[0]
    print("[PASS] pipeline nem loi -> job xep lai, giu nguyen van loi")


def test_ca_4_agent_loi_thi_KHONG_ghi_log_ma_retry(conn):
    """4/4 agent thieu = hong ha tang, khong phai ket qua danh gia."""
    state = dict(_STATE_XONG, final_score=None, report=dict(
        _STATE_XONG["report"], missing_agents=[
            "content_quality", "seo", "brand", "compliance"]))
    job = _job(conn, "uuid-5", "h5")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              write_back_fn=lambda **kw: True)
    assert ket == "queued", ket
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM run_log WHERE node_id='uuid-5'")
        assert cur.fetchone()[0] == 0, "khong duoc ghi log cho lan hong ha tang"
    print("[PASS] 4/4 agent loi -> retry, khong ghi run_log")


def test_1_agent_loi_van_chap_nhan(conn):
    """1-3 agent loi la dung tinh huong fail-safe architecture.md 6.4."""
    state = dict(_STATE_XONG, report=dict(_STATE_XONG["report"],
                                          missing_agents=["seo"]))
    job = _job(conn, "uuid-6", "h6")
    ket = worker.chay_mot_job(conn, job, invoke=lambda s: state,
                              write_back_fn=lambda **kw: True)
    assert ket == "done", ket
    print("[PASS] 1 agent loi -> chap nhan ket qua, khong tra tien lan hai")


def test_usage_log_duoc_reset(conn):
    """USAGE_LOG la list muc module, co y khong tu xoa - worker chay nen
    vo han thi no phinh mai (technical-debt.md nhom C)."""
    import ai_core
    ai_core.USAGE_LOG.append({"model": "x", "input_tokens": 1, "output_tokens": 1})
    job = _job(conn, "uuid-7", "h7")
    worker.chay_mot_job(conn, job, invoke=lambda s: _STATE_XONG,
                        write_back_fn=lambda **kw: True)
    assert ai_core.USAGE_LOG == [], ai_core.USAGE_LOG
    print("[PASS] USAGE_LOG duoc reset sau moi job")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_job_thanh_cong_ghi_run_log_va_dong_job,
        test_write_back_that_bai_thi_job_xep_lai,
        test_da_co_run_log_thi_KHONG_goi_lai_pipeline,
        test_pipeline_nem_loi_thi_job_that_bai,
        test_ca_4_agent_loi_thi_KHONG_ghi_log_ma_retry,
        test_1_agent_loi_van_chap_nhan,
        test_usage_log_duoc_reset,
    ):
        try:
            fn(conn)
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Tạo `src/reconcile.py` tối thiểu để phá vòng phụ thuộc**

`worker.py` import `reconcile`, mà `reconcile` là Task 7. Tạo bản tối thiểu ngay bây giờ, Task 7 sẽ thay bằng bản thật:

```python
"""Vong doi soat - ban day du o Task 7."""


def quet(conn) -> int:
    return 0
```

- [ ] **Step 3: Chạy test để xác nhận đỏ**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_worker.py
```

Expected: `ModuleNotFoundError: No module named 'worker'`.

- [ ] **Step 4: Viết `src/worker.py`**

```python
"""Worker: nhan job tu hang doi, goi pipeline, ghi log, PATCH ve Drupal.

Spec: docs/superpowers/specs/2026-08-07-needs-review-automation-design.md

Tien trinh RIENG voi api.py, co y (spec muc 3.3): API phai tra loi trong vai
ms trong khi worker chay 30-60 giay moi job; worker nap BGE-M3 (~2GB) luc
khoi dong con API thi khong can. Worker chet vi het RAM thi API van song va
job van xep hang duoc - do chinh la ly do co hang doi.

Chay (tu multiagent/): .venv\\Scripts\\python.exe src\\worker.py
"""
import logging
import os
import socket
import sys
import time

_SRC = os.path.dirname(os.path.abspath(__file__))
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

import ai_core
import audit
import config
import db
import job_queue as q
import reconcile

NGU_KHI_RONG_GIAY = 2
CHU_KY_DOI_SOAT_GIAY = 300

# 4/4 agent thieu = hong ha tang, khong phai ket qua danh gia. 1-3 agent thieu
# thi CHAP NHAN: do dung la tinh huong fail-safe architecture.md muc 6.4 duoc
# thiet ke de xu ly (chia lai trong so, ghi note "diem chua day du"). Retry
# luc do la tra tien lan hai cho mot co che dang hoat dong dung.
_SO_AGENT = 4


def _payload_tu_state(state: dict) -> dict:
    """Bon gia tri se PATCH sang Drupal: status, score, suggestions, report_json.

    CACH LAM: chan `graph.write_back` roi goi `graph.write_back_node(state)`.
    Ham do dung san ca bon gia tri va goi write_back(...) voi dung chung; chan
    lai la lay duoc nguyen ven ma KHONG PATCH gi.

    Vi sao khong chep logic dung chuoi goi y sang day: no gom loi theo tung
    field, sap thu tu field, them tien to [LUU Y]/[LY DO TU CHOI]. Chep sang
    worker la tao ban thu hai cua cung mot chuoi - dung loai trung lap ma
    config-spec.md muc 1 ghi lai nhu mot loi da tra gia (cung mot con so nam o
    5 noi va da troi lech hai lan).

    `write_back_node` doc decision/final_score tu STATE chu khong tu `report`,
    va giu nguyen tinh chat do la co y: do dung la nguon ghi vao
    field_ai_status/field_ai_score.
    """
    import graph

    da_bat = {}
    that = graph.write_back
    graph.write_back = lambda **kw: (da_bat.update(kw), True)[1]
    try:
        graph.write_back_node(state)
    finally:
        graph.write_back = that

    da_bat.pop("node_id", None)      # worker tu truyen, khong lay tu day
    return da_bat


def chay_mot_job(conn, job: dict, *, invoke=None, write_back_fn=None) -> str:
    """Xu ly mot job da claim. Tra trang thai cuoi: done / queued / failed."""
    from drupal_client import write_back as _write_back_that

    if write_back_fn is None:
        write_back_fn = _write_back_that

    node_id, chash = job["node_id"], job["content_hash"]

    # CHOT CHAN TIEN: da cham dung noi dung nay roi thi chi ghi lai ket qua,
    # KHONG goi LLM. Duong nay xay ra khi lan truoc pipeline chay xong nhung
    # PATCH that bai. Cham lai ton $0,057 that.
    cu = audit.da_cham(conn, node_id, chash)
    if cu is not None:
        if write_back_fn(node_id=node_id, **cu["payload"]):
            q.complete(conn, job["id"])
            return q.DONE
        return q.fail(conn, job["id"], "write-back that bai (ghi lai ket qua cu)",
                      job["attempts"])

    if invoke is None:
        from graph import build_graph

        invoke = build_graph().invoke

    ai_core.USAGE_LOG.clear()
    bat_dau = time.monotonic()
    try:
        # CHI truyen node_id. content_type/langcode do graph._khoa_cua() suy ra
        # - do la CHO DUY NHAT duoc phep suy ra cap khoa nay (no B6). Worker
        # dat them mot duong thu hai la dung lai dung cai bay vua dep.
        state = invoke({"node_id": node_id})
    except Exception as e:
        return q.fail(conn, job["id"], f"{e.__class__.__name__}: {e}",
                      job["attempts"])
    duration_ms = int((time.monotonic() - bat_dau) * 1000)

    report = state.get("report") or {}
    if len(report.get("missing_agents") or []) >= _SO_AGENT:
        return q.fail(conn, job["id"],
                      "ca 4 agent khong tra ket qua - nghi hong ha tang",
                      job["attempts"])

    payload = _payload_tu_state(state)
    audit.ghi(
        conn, job_id=job["id"], node_id=node_id, content_hash=chash,
        duration_ms=duration_ms, report=report,
        config_meta=config.load().get("meta") or {},
        usage=list(ai_core.USAGE_LOG), model=ai_core.MODEL, payload=payload,
    )
    ai_core.USAGE_LOG.clear()

    if write_back_fn(node_id=node_id, **payload):
        q.complete(conn, job["id"])
        return q.DONE
    return q.fail(conn, job["id"], "write-back that bai", job["attempts"])


def vong_lap(conn=None, ten: str = "") -> None:
    if conn is None:
        conn = db.get_conn()
    ten = ten or f"{socket.gethostname()}:{os.getpid()}"
    q.dam_bao_bang(conn)
    audit.dam_bao_bang(conn)

    # Nap model NGAY luc khoi dong, khong de lazy trong lan cham dau
    # (docs/rag-design.md muc 6): lan cham dau se cham them vai giay va nguoi
    # dung tuong he thong treo.
    from embeddings import get_default_embedder

    get_default_embedder()
    logging.info("[worker %s] san sang", ten)

    lan_doi_soat = 0.0
    while True:
        q.reclaim_stuck(conn)
        if time.monotonic() - lan_doi_soat >= CHU_KY_DOI_SOAT_GIAY:
            lan_doi_soat = time.monotonic()
            try:
                them = reconcile.quet(conn)
                if them:
                    logging.info("[worker %s] doi soat them %d job", ten, them)
            except Exception as e:
                # Doi soat hong KHONG duoc lam chet worker - duong event van chay
                logging.warning("[worker %s] doi soat loi: %s", ten, e)

        job = q.claim(conn, ten)
        if job is None:
            time.sleep(NGU_KHI_RONG_GIAY)
            continue
        logging.info("[worker %s] cham node %s (lan %d)", ten, job["node_id"],
                     job["attempts"])
        ket = chay_mot_job(conn, job)
        logging.info("[worker %s] node %s -> %s", ten, job["node_id"], ket)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    vong_lap()
```

- [ ] **Step 5: Chạy test — phải xanh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_worker.py
```

Expected: 7 dòng `[PASS]` rồi `OK`.

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/worker.py multiagent/scripts/test_worker.py multiagent/src/reconcile.py
git commit -m "feat: worker nhan job, goi pipeline, ghi run_log va PATCH ve Drupal"
```

---

### Task 7: `src/reconcile.py` — vòng đối soát

**Files:**
- Create/Modify: `multiagent/src/reconcile.py`
- Test: `multiagent/scripts/test_reconcile.py`

**Interfaces:**
- Consumes: `drupal_client.liet_ke_can_cham` (Task 5), `job_queue.enqueue`, `job_queue.co_job_that_bai` (Task 3)
- Produces: `reconcile.quet(conn, *, liet_ke=None, enqueue_fn=None, co_that_bai=None) -> int`

- [ ] **Step 1: Viết test**

Tạo `multiagent/scripts/test_reconcile.py`:

```python
"""Test vong doi soat (spec 2026-08-07 muc 6.3 va 6.3.1).

Tiem het phu thuoc -> khong can Postgres, khong can Drupal.
Chay: .venv\\Scripts\\python.exe scripts\\test_reconcile.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import reconcile


def _gom():
    da_xep = []
    return da_xep, lambda conn, node_id, content_hash, source: da_xep.append(
        (node_id, content_hash, source))


def test_hash_khop_thi_khong_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u1", "content_hash": "h1",
                          "hash_da_cham": "h1"}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert da_xep == [], da_xep
    print("[PASS] da cham dung noi dung nay -> khong xep lai")


def test_hash_khac_thi_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u2", "content_hash": "moi",
                          "hash_da_cham": "cu"}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert da_xep == [("u2", "moi", "reconcile")], da_xep
    print("[PASS] noi dung da doi -> xep job bu")


def test_chua_cham_bao_gio_thi_xep():
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u3", "content_hash": "h3",
                          "hash_da_cham": None}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: False)
    assert len(da_xep) == 1, da_xep
    print("[PASS] chua cham bao gio -> xep job")


def test_KHONG_hoi_sinh_job_da_dead_letter():
    """Phep kiem quan trong nhat cua file nay (spec muc 6.3.1).

    Index dedup CO Y loai `failed`. Neu doi soat khong hoi them cau nay thi
    no se xep lai mot bai luon that bai MOI 5 PHUT, moi job thu 3 lan, va co
    che dead-letter bi vo hieu hoan toan - thanh vong lap tieu tien API vo han.
    """
    da_xep, fn = _gom()
    reconcile.quet(
        None,
        liet_ke=lambda: [{"node_id": "u4", "content_hash": "h4",
                          "hash_da_cham": None}],
        enqueue_fn=fn, co_that_bai=lambda c, n, h: True)
    assert da_xep == [], f"da hoi sinh job dead-letter: {da_xep}"
    print("[PASS] job da dead-letter KHONG bi doi soat hoi sinh")


def test_tra_ve_so_job_da_xep():
    _, fn = _gom()
    n = reconcile.quet(
        None,
        liet_ke=lambda: [
            {"node_id": "a", "content_hash": "1", "hash_da_cham": None},
            {"node_id": "b", "content_hash": "2", "hash_da_cham": "2"},
            {"node_id": "c", "content_hash": "3", "hash_da_cham": "cu"},
        ],
        enqueue_fn=fn, co_that_bai=lambda c, n_, h: False)
    assert n == 2, n
    print("[PASS] tra ve dung so job da xep")


if __name__ == "__main__":
    failed = False
    for fn_ in (
        test_hash_khop_thi_khong_xep,
        test_hash_khac_thi_xep,
        test_chua_cham_bao_gio_thi_xep,
        test_KHONG_hoi_sinh_job_da_dead_letter,
        test_tra_ve_so_job_da_xep,
    ):
        try:
            fn_()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn_.__name__}: {e}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy test để xác nhận đỏ**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_reconcile.py
```

Expected: `TypeError: quet() got an unexpected keyword argument 'liet_ke'` (file tạm từ Task 6).

- [ ] **Step 3: Viết `src/reconcile.py`**

```python
"""Vong doi soat: bat cac bai lot khi duong event that bai.

Spec: docs/superpowers/specs/2026-08-07-... muc 6.3

Day la LUOI AN TOAN, khong phai duong chinh. No khong can biet VI SAO mot bai
bi lot (service restart, Drupal mat mang, module bi tat, doi state bang drush)
- no chi so trang thai mong muon voi trang thai that roi bu chenh lech. Cung
nguyen ly reconciliation loop ma Kubernetes dung.

Chu ky 5 phut chu khong phai 30 giay: quet thua thi tiet kiem goi API vo ich,
va do tre xau nhat 5 phut chi xay ra trong tinh huong da hong.
"""
import job_queue as q


def quet(conn, *, liet_ke=None, enqueue_fn=None, co_that_bai=None) -> int:
    """Quet mot vong, tra so job da xep them.

    Ba phu thuoc tiem duoc de test khong can Drupal lan Postgres.
    """
    if liet_ke is None:
        from drupal_client import liet_ke_can_cham

        liet_ke = liet_ke_can_cham
    if enqueue_fn is None:
        enqueue_fn = q.enqueue
    if co_that_bai is None:
        co_that_bai = q.co_job_that_bai

    da_xep = 0
    for bai in liet_ke():
        node_id = bai["node_id"]
        chash = bai["content_hash"]
        if bai["hash_da_cham"] == chash:
            continue      # da cham dung noi dung nay roi
        if co_that_bai(conn, node_id, chash):
            # TUYET DOI khong hoi sinh job da dead-letter (spec muc 6.3.1).
            # Bai do chi chay lai duoc qua nut "Cham lai" thu cong, tuc phai
            # co nguoi quyet dinh - dung tinh than "bam cham lai la tieu tien
            # API that".
            continue
        enqueue_fn(conn, node_id, chash, "reconcile")
        da_xep += 1
    return da_xep
```

- [ ] **Step 4: Chạy test — phải xanh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_reconcile.py
.venv/Scripts/python.exe scripts/test_worker.py
```

Expected: cả hai file đều `OK`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/reconcile.py multiagent/scripts/test_reconcile.py
git commit -m "feat: vong doi soat bat bai lot, khong hoi sinh job dead-letter"
```

---

### Task 8: `src/api.py` — service HTTP

**Files:**
- Create: `multiagent/src/api.py`
- Modify: `multiagent/requirements.txt`
- Modify: `.env.example`
- Test: `multiagent/scripts/test_api.py`

**Interfaces:**
- Consumes: `job_queue.*` (Task 3)
- Produces: `api.app` (FastAPI), `api.kiem_token(authorization: str) -> None`, `api.tao_job(body: JobIn, conn) -> dict`, `api.trang_thai(node_id: str, conn) -> dict`, `api.health(conn) -> dict`

- [ ] **Step 1: Cài phụ thuộc**

```bash
cd multiagent
.venv/Scripts/pip install "fastapi>=0.115" "uvicorn>=0.30"
.venv/Scripts/python.exe -c "import fastapi, uvicorn; print('ok')"
```

Expected: in `ok`.

Thêm vào cuối `multiagent/requirements.txt`:

```
# Service HTTP nhan job tu Drupal (spec 2026-08-07). uvicorn la server ASGI
# chay app cua fastapi - khong co no thi `python -m uvicorn` te ngay.
fastapi>=0.115
uvicorn>=0.30
```

Thêm vào cuối `.env.example`:

```
# Token dung chung giua Drupal va service Multi-Agent (spec 2026-08-07 muc 8).
# Sinh bang: python -c "import secrets; print(secrets.token_urlsafe(32))"
# Phia Drupal dat cung gia tri nay vao $settings['vf_ai_service_token'] trong
# settings.php - KHONG dat vao config entity, vi config export ra YAML la lo
# secret vao git.
VF_SERVICE_TOKEN=
VF_API_PORT=8900
```

- [ ] **Step 2: Viết test**

Tạo `multiagent/scripts/test_api.py`:

```python
"""Test logic cua service HTTP (spec 2026-08-07 muc 5.4, 8).

Goi THANG cac ham xu ly thay vi dung TestClient: TestClient keo them phu
thuoc `httpx`, va thu dang kiem o day la logic cua minh (so token hang thoi
gian, hinh dang tra ve, dedup) chu khong phai tang HTTP cua FastAPI.

Can Postgres that cho phan hang doi - [SKIP] neu khong co.
Chay: .venv\\Scripts\\python.exe scripts\\test_api.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

os.environ["VF_SERVICE_TOKEN"] = "token-test"

import api
import db
import job_queue as q

SCHEMA = "vf_test_api"


def _dung_schema_sach():
    conn = db.psycopg.connect(db.dsn(), autocommit=True)
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
        cur.execute(f"CREATE SCHEMA {SCHEMA}")
        cur.execute(f"SET search_path TO {SCHEMA}")
    q.dam_bao_bang(conn)
    return conn


def _loi(fn, *a, **kw):
    try:
        fn(*a, **kw)
    except api.HTTPException as e:
        return e.status_code
    return None


def test_thieu_token_thi_401(conn):
    assert _loi(api.kiem_token, "") == 401
    print("[PASS] khong co header Authorization -> 401")


def test_token_sai_thi_401(conn):
    assert _loi(api.kiem_token, "Bearer token-sai") == 401
    print("[PASS] token sai -> 401")


def test_token_dung_thi_qua(conn):
    api.kiem_token("Bearer token-test")
    print("[PASS] token dung -> khong nem gi")


def test_tao_job_moi_tra_queued(conn):
    kq = api.tao_job(api.JobIn(node_id="u1", content_hash="h1"), conn)
    assert kq["status"] == "queued" and kq["job_id"] > 0, kq
    print("[PASS] job moi -> status queued kem job_id")


def test_tao_job_trung_tra_duplicate(conn):
    api.tao_job(api.JobIn(node_id="u2", content_hash="h2"), conn)
    kq = api.tao_job(api.JobIn(node_id="u2", content_hash="h2"), conn)
    assert kq["status"] == "duplicate", kq
    print("[PASS] job trung -> duplicate, khong tao them")


def test_force_tao_duoc_job_moi(conn):
    api.tao_job(api.JobIn(node_id="u3", content_hash="h3"), conn)
    job = q.claim(conn, "t")
    q.complete(conn, job["id"])
    kq = api.tao_job(api.JobIn(node_id="u3", content_hash="h3", force=True), conn)
    assert kq["status"] == "queued", kq
    print("[PASS] force=True -> tao duoc job moi du da done")


def test_trang_thai_node_chua_co_job(conn):
    assert api.trang_thai("khong-ton-tai", conn)["status"] == "none"
    print("[PASS] node chua co job -> status 'none'")


def test_trang_thai_tra_job_moi_nhat(conn):
    api.tao_job(api.JobIn(node_id="u4", content_hash="h4"), conn)
    kq = api.trang_thai("u4", conn)
    assert kq["status"] == "queued" and kq["attempts"] == 0, kq
    print("[PASS] trang thai tra job moi nhat cua node")


def test_health_dem_theo_trang_thai(conn):
    kq = api.health(conn)
    assert kq["ok"] is True and kq["queued"] >= 1, kq
    print("[PASS] health tra so job theo tung trang thai")


if __name__ == "__main__":
    try:
        conn = _dung_schema_sach()
    except Exception as e:
        print(f"[SKIP] khong ket noi duoc Postgres ({e.__class__.__name__}). "
              f"LUU Y: [SKIP] khong phai [PASS].")
        sys.exit(0)

    failed = False
    for fn in (
        test_thieu_token_thi_401,
        test_token_sai_thi_401,
        test_token_dung_thi_qua,
        test_tao_job_moi_tra_queued,
        test_tao_job_trung_tra_duplicate,
        test_force_tao_duoc_job_moi,
        test_trang_thai_node_chua_co_job,
        test_trang_thai_tra_job_moi_nhat,
        test_health_dem_theo_trang_thai,
    ):
        try:
            fn(conn)
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    with conn.cursor() as cur:
        cur.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 3: Chạy test để xác nhận đỏ**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_api.py
```

Expected: `ModuleNotFoundError: No module named 'api'`.

- [ ] **Step 4: Viết `src/api.py`**

```python
"""Service HTTP nhan job tu Drupal va tra trang thai.

Spec: docs/superpowers/specs/2026-08-07-... muc 5.4

CHI nhan va tra trang thai - khong cham gi, khong nap model. Tra loi trong
vai ms vi Drupal dang cho trong luc editor bam Save.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe -m uvicorn api:app --port 8900 --app-dir src
"""
import hmac
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel

import db
import job_queue as q

load_dotenv()

app = FastAPI(title="VF O2O Multi-Agent")


class JobIn(BaseModel):
    node_id: str
    content_hash: str
    source: str = "event"
    force: bool = False


def kiem_token(authorization: str = Header(default="")) -> None:
    """So token bang hmac.compare_digest - so bang `==` tren chuoi bi mat la
    ro ri thoi gian, du o loopback thi day van la thoi quen phai dung."""
    mong_doi = os.environ.get("VF_SERVICE_TOKEN", "")
    if not mong_doi:
        raise HTTPException(500, "VF_SERVICE_TOKEN chua dat trong .env")
    if not authorization.startswith("Bearer "):
        raise HTTPException(401, "thieu Bearer token")
    if not hmac.compare_digest(authorization[7:], mong_doi):
        raise HTTPException(401, "token sai")


def _conn():
    conn = db.get_conn()
    q.dam_bao_bang(conn)
    return conn


def tao_job(body: JobIn, conn) -> dict:
    return q.enqueue(conn, body.node_id, body.content_hash, body.source,
                     force=body.force)


def trang_thai(node_id: str, conn) -> dict:
    job = q.job_moi_nhat(conn, node_id)
    if job is None:
        return {"status": "none", "job_id": None, "attempts": 0,
                "last_error": None, "updated_at": None}
    return {"status": job["status"], "job_id": job["id"],
            "attempts": job["attempts"], "last_error": job["last_error"],
            "updated_at": job["updated_at"].isoformat()}


def health(conn) -> dict:
    return {"ok": True, **q.thong_ke(conn)}


@app.post("/jobs", status_code=202, dependencies=[Depends(kiem_token)])
def post_jobs(body: JobIn):
    return tao_job(body, _conn())


@app.get("/jobs/by-node/{node_id}", dependencies=[Depends(kiem_token)])
def get_trang_thai(node_id: str):
    return trang_thai(node_id, _conn())


@app.get("/health")
def get_health():
    return health(_conn())
```

- [ ] **Step 5: Chạy test — phải xanh**

```bash
cd multiagent
.venv/Scripts/python.exe scripts/test_api.py
```

Expected: 9 dòng `[PASS]` rồi `OK`.

- [ ] **Step 6: Chạy service thật và kiểm bằng curl**

```bash
cd multiagent
.venv/Scripts/python.exe -m uvicorn api:app --port 8900 --app-dir src &
sleep 3
curl -s http://127.0.0.1:8900/health
curl -s -o /dev/null -w "%{http_code}\n" -X POST http://127.0.0.1:8900/jobs \
  -H "Content-Type: application/json" -d '{"node_id":"x","content_hash":"y"}'
```

Expected: `/health` trả JSON có `"ok":true`; POST không kèm token trả `401`.

- [ ] **Step 7: Commit**

```bash
git add multiagent/src/api.py multiagent/scripts/test_api.py multiagent/requirements.txt .env.example
git commit -m "feat: service HTTP nhan job va tra trang thai, xac thuc bearer token"
```

---

### Task 9: Module Drupal `vf_ai_trigger` — bắn job khi node vào Needs Review

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.info.yml`
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.services.yml`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php`
- Test: `drupal/scripts/test_vf_ai_trigger.php`

**Interfaces:**
- Consumes: `AiReportRenderer::contentHash()` (đã có), `vf_ai_review_hash_fields()` (tạo ở Step 1)
- Produces: `Drupal\vf_ai_trigger\ServiceClient::guiJob(string $uuid, string $hash, string $source, bool $force): bool`; `ServiceClient::trangThai(string $uuid): ?array`

**Nhắc lại ràng buộc:** gửi `$node->uuid()`, **không** phải `$node->id()`.

- [ ] **Step 1: Tách hàm hash dùng chung trong `vf_ai_review`**

Trong `drupal/web/modules/custom/vf_ai_review/vf_ai_review.module`, thay đoạn tính `$hien_tai` (dòng 77–85) bằng:

```php
  $stale = FALSE;
  if ($report !== NULL && !empty($report['content_hash'])) {
    $hien_tai = AiReportRenderer::contentHash(vf_ai_review_hash_fields($node));
    $stale = ($hien_tai !== $report['content_hash']);
  }
```

và thêm hàm mới vào cuối file:

```php
/**
 * Bốn field tham gia content_hash, lấy ra khỏi node.
 *
 * Để một chỗ duy nhất vì từ 2026-08-07 có hai nơi cần: khối báo cáo (băng
 * "nội dung đã thay đổi") và module vf_ai_trigger (tính hash gửi kèm job).
 * Hai nơi ghép khác nhau nghĩa là hash lệch, và hệ quả là vòng đối soát
 * chấm lại vô hạn mọi bài.
 *
 * KHÔNG đưa vào AiReportRenderer: class đó cố ý không phụ thuộc Drupal để
 * test được bằng PHP thuần.
 */
function vf_ai_review_hash_fields($node): array {
  return [
    'title' => (string) $node->label(),
    'body' => _vf_ai_review_gia_tri($node, 'body'),
    'summary' => _vf_ai_review_gia_tri($node, 'body', 'summary'),
    'meta_description' => _vf_ai_review_gia_tri($node, 'field_meta_description'),
  ];
}
```

- [ ] **Step 2: Kiểm module cũ vẫn chạy**

```bash
cd drupal
ddev drush cr
ddev exec php scripts/test_ai_report_renderer.php
```

Expected: test PHP xanh như trước; mở một node edit form không lỗi.

- [ ] **Step 3: Viết test PHP cho payload**

Tạo `drupal/scripts/test_vf_ai_trigger.php`:

```php
<?php

/**
 * @file
 * Test hop dong: payload gui sang service phai dung hinh dang va dung hash.
 *
 * Chay bang PHP thuan (khong can bootstrap Drupal), dung phong cach
 * test_ai_report_renderer.php. Chay:
 *   ddev exec php scripts/test_vf_ai_trigger.php
 */

require_once __DIR__ . '/../web/modules/custom/vf_ai_review/src/AiReportRenderer.php';

use Drupal\vf_ai_review\AiReportRenderer;

$that_bai = FALSE;

function kiem(string $ten, bool $dieu_kien, string $chi_tiet = ''): void {
  global $that_bai;
  if ($dieu_kien) {
    echo "[PASS] $ten\n";
  }
  else {
    $that_bai = TRUE;
    echo "[FAIL] $ten $chi_tiet\n";
  }
}

// 1. Hash gui kem job phai khop fixture dung chung voi Python.
$fx = json_decode(file_get_contents(__DIR__ . '/content_hash_fixture.json'), TRUE);
$hash = AiReportRenderer::contentHash($fx['fields']);
kiem('hash gui kem job khop fixture dung chung voi Python',
  $hash === $fx['expected_sha256'], "got $hash");

// 2. Hinh dang payload phai dung 4 khoa service mong doi.
$payload = [
  'node_id' => '11111111-2222-3333-4444-555555555555',
  'content_hash' => $hash,
  'source' => 'event',
  'force' => FALSE,
];
kiem('payload co dung 4 khoa',
  array_keys($payload) === ['node_id', 'content_hash', 'source', 'force']);

// 3. node_id phai la UUID, khong phai nid. Tron hai loai dinh danh la loi
//    im lang: job van tao duoc, chi la fetch_content tra 404.
kiem('node_id la UUID chu khong phai so nguyen',
  (bool) preg_match('/^[0-9a-f-]{36}$/i', $payload['node_id']),
  $payload['node_id']);

exit($that_bai ? 1 : 0);
```

- [ ] **Step 4: Chạy test PHP**

```bash
cd drupal
ddev exec php scripts/test_vf_ai_trigger.php
```

Expected: 3 dòng `[PASS]`, exit 0.

- [ ] **Step 5: Tạo module `vf_ai_trigger`**

`drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.info.yml`:

```yaml
name: 'VF AI Trigger'
type: module
description: 'Bắn job chấm điểm sang service Multi-Agent khi bài vào trạng thái Needs Review.'
core_version_requirement: ^10 || ^11
package: 'VF O2O'
dependencies:
  - drupal:node
  - drupal:content_moderation
  - vf_ai_review:vf_ai_review
```

`drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.services.yml`:

```yaml
services:
  vf_ai_trigger.client:
    class: Drupal\vf_ai_trigger\ServiceClient
    arguments: ['@http_client', '@config.factory', '@logger.factory']
```

`drupal/web/modules/custom/vf_ai_trigger/src/ServiceClient.php`:

```php
<?php

namespace Drupal\vf_ai_trigger;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Logger\LoggerChannelFactoryInterface;
use Drupal\Core\Site\Settings;
use GuzzleHttp\ClientInterface;

/**
 * Gọi service Multi-Agent. Là NƠI DUY NHẤT module này chạm mạng.
 *
 * Mọi phương thức đều nuốt lỗi và trả về giá trị "không có" thay vì ném:
 * service phụ trợ chết TUYỆT ĐỐI không được làm sập việc lưu bài của editor.
 * Bài bị lọt sẽ được vòng đối soát bên Python bắt lại trong ≤5 phút.
 */
class ServiceClient {

  /**
   * Timeout ngắn, cố ý: endpoint bên kia chỉ làm một lệnh INSERT (vài ms).
   * Quá 2 giây nghĩa là service có vấn đề, và lúc đó chờ thêm chỉ làm editor
   * phải đợi lâu hơn chứ không cứu được gì.
   */
  private const TIMEOUT = 2;

  public function __construct(
    private readonly ClientInterface $httpClient,
    private readonly ConfigFactoryInterface $configFactory,
    private readonly LoggerChannelFactoryInterface $loggerFactory,
  ) {}

  private function baseUrl(): string {
    return rtrim((string) $this->configFactory->get('vf_ai_trigger.settings')
      ->get('service_url') ?: 'http://127.0.0.1:8900', '/');
  }

  /**
   * Token đọc từ settings.php, KHÔNG phải config entity.
   *
   * Config export ra file YAML là lộ secret vào git.
   */
  private function token(): string {
    return (string) Settings::get('vf_ai_service_token', '');
  }

  private function logger() {
    return $this->loggerFactory->get('vf_ai_trigger');
  }

  /**
   * Xếp một job. TRUE nghĩa là service đã nhận (kể cả khi nó báo trùng).
   */
  public function guiJob(string $uuid, string $hash, string $source = 'event', bool $force = FALSE): bool {
    try {
      $this->httpClient->request('POST', $this->baseUrl() . '/jobs', [
        'timeout' => self::TIMEOUT,
        'headers' => ['Authorization' => 'Bearer ' . $this->token()],
        'json' => [
          'node_id' => $uuid,
          'content_hash' => $hash,
          'source' => $source,
          'force' => $force,
        ],
      ]);
      return TRUE;
    }
    catch (\Throwable $e) {
      $this->logger()->warning('Khong gui duoc job cho node @uuid: @loi', [
        '@uuid' => $uuid,
        '@loi' => $e->getMessage(),
      ]);
      return FALSE;
    }
  }

  /**
   * Trạng thái job mới nhất của node. NULL khi không hỏi được.
   */
  public function trangThai(string $uuid): ?array {
    try {
      $res = $this->httpClient->request('GET', $this->baseUrl() . '/jobs/by-node/' . $uuid, [
        'timeout' => self::TIMEOUT,
        'headers' => ['Authorization' => 'Bearer ' . $this->token()],
      ]);
      $data = json_decode((string) $res->getBody(), TRUE);
      return is_array($data) ? $data : NULL;
    }
    catch (\Throwable $e) {
      return NULL;
    }
  }

}
```

`drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`:

```php
<?php

/**
 * @file
 * Bắn job chấm điểm khi bài được lưu ở trạng thái "Needs Review".
 *
 * ĐÍNH CHÍNH THUẬT NGỮ (spec mục 3.2.1): Drupal core phát HOOK cho vòng đời
 * entity, không phát sự kiện Symfony. Nên cơ chế ở đây là
 * hook_ENTITY_TYPE_insert/update, không phải một class EventSubscriber.
 */

use Drupal\node\NodeInterface;

/**
 * State kích hoạt chấm điểm. Trùng machine name của workflow đã tạo.
 */
const VF_AI_TRIGGER_STATE = 'needs_review';

/**
 * Implements hook_ENTITY_TYPE_insert() for node.
 */
function vf_ai_trigger_node_insert(NodeInterface $node): void {
  _vf_ai_trigger_ban_job($node);
}

/**
 * Implements hook_ENTITY_TYPE_update() for node.
 */
function vf_ai_trigger_node_update(NodeInterface $node): void {
  _vf_ai_trigger_ban_job($node);
}

/**
 * Bắn job nếu bài vừa lưu đang ở trạng thái cần duyệt.
 *
 * Điều kiện là TRẠNG THÁI SAU KHI LƯU, không phải "vừa có chuyển tiếp"
 * (spec mục 4.1). Người viết thường đưa bài sang needs_review, đọc báo cáo,
 * rồi sửa body ngay tại đó và lưu tiếp mà không đổi state — nếu chỉ bắn khi
 * có chuyển tiếp thì lần sửa đó không bao giờ được chấm lại, trong khi module
 * lại hiện băng "nội dung đã thay đổi". Hệ thống tự mâu thuẫn với chính mình.
 *
 * Lưu mà không sửa gì thì không tốn đồng nào: content_hash không đổi nên
 * index dedup bên service chặn ở tầng INSERT.
 *
 * ĐIỀU KIỆN NGẦM PHẢI GIỮ — đọc trước khi sửa index dedup bên Python.
 * Hook này cũng bắn khi chính hệ Multi-Agent PATCH 4 field AI về (write_back
 * đi qua JSON:API, tức cũng là một lần lưu node). Lúc đó node vẫn ở
 * needs_review nên hook lại gọi POST /jobs.
 *
 * Nó KHÔNG thành vòng lặp tự chấm vô hạn, nhưng chỉ nhờ hai điều cộng lại:
 *   1. write_back chỉ đụng field_ai_*, không nằm trong 4 field của
 *      content_hash -> hash không đổi.
 *   2. Index dedup bên Python phủ cả trạng thái `running`, mà lúc PATCH thì
 *      job đang chính là `running`.
 * Bỏ `running` khỏi index dedup là mở lại vòng lặp đó ngay lập tức.
 */
function _vf_ai_trigger_ban_job(NodeInterface $node): void {
  if ($node->bundle() !== 'article') {
    return;
  }
  if (!$node->hasField('moderation_state')
    || $node->get('moderation_state')->value !== VF_AI_TRIGGER_STATE) {
    return;
  }

  $hash = \Drupal\vf_ai_review\AiReportRenderer::contentHash(
    vf_ai_review_hash_fields($node)
  );
  // uuid() chứ KHÔNG phải id(): pipeline gọi /jsonapi/node/article/{uuid}.
  \Drupal::service('vf_ai_trigger.client')->guiJob($node->uuid(), $hash);
}
```

- [ ] **Step 6: Bật module và cấu hình token**

```bash
cd drupal
ddev drush en vf_ai_trigger -y
```

Sinh token một lần và dán vào **hai** chỗ:

```bash
cd multiagent
.venv/Scripts/python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

1. `.env` (cùng thư mục gốc repo): `VF_SERVICE_TOKEN=<token vừa sinh>`
2. Cuối `drupal/web/sites/default/settings.php`:

```php
// Token nói chuyện với service Multi-Agent. Để ở đây chứ KHÔNG phải config
// entity: config export ra file YAML là lộ secret vào git.
$settings['vf_ai_service_token'] = '<token vua sinh>';
```

Hai giá trị **phải giống hệt nhau**, nếu không mọi cú POST đều trả 401 và bài chỉ được chấm qua đường đối soát (chậm 5 phút, rất khó chẩn đoán vì không có lỗi nào hiện ra ở Drupal).

Lưu ý: DDEV container gọi ra host qua `host.docker.internal`. Đặt config:

```bash
ddev drush config:set vf_ai_trigger.settings service_url http://host.docker.internal:8900 -y
```

Nếu `host.docker.internal` không thông thì thử `ddev exec curl -s http://host.docker.internal:8900/health` và đổi sang IP LAN của máy nếu cần.

- [ ] **Step 7: Kiểm end-to-end đường bắn job**

Bật service Python (Task 8 Step 6) và worker chưa cần chạy. Trong Drupal, chuyển một bài sang "Needs Review" và lưu. Rồi:

```bash
docker exec vf-agent-db psql -U vf_agent -d vf_agent \
  -c "SELECT node_id, status, source FROM review_job ORDER BY id DESC LIMIT 3;"
```

Expected: có đúng 1 dòng `queued`, `source = event`, `node_id` là UUID.

Bấm Save lại 2 lần nữa mà không sửa gì, chạy lại lệnh trên. Expected: **vẫn đúng 1 dòng** cho node đó.

- [ ] **Step 8: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_trigger drupal/scripts/test_vf_ai_trigger.php \
        drupal/web/modules/custom/vf_ai_review/vf_ai_review.module
git commit -m "feat: module vf_ai_trigger ban job khi bai vao Needs Review"
```

---

### Task 10: Khối "đang chấm" tự cập nhật trong editor

**Files:**
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.routing.yml`
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.permissions.yml`
- Create: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.libraries.yml`
- Create: `drupal/web/modules/custom/vf_ai_trigger/js/vf_ai_trigger.js`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/TrangThaiController.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`

**Interfaces:**
- Consumes: `ServiceClient::trangThai()` (Task 9)
- Produces: route `vf_ai_trigger.trang_thai` tại `/vf-ai/status/{node}`; permission `xem bao cao ai`

- [ ] **Step 1: Khai báo permission**

`vf_ai_trigger.permissions.yml`:

```yaml
'xem bao cao ai':
  title: 'Xem báo cáo đánh giá AI'
  description: 'Xem kết quả chấm điểm và trạng thái hàng đợi.'
'dieu khien ai':
  title: 'Điều khiển hệ thống đánh giá AI'
  description: 'Bấm chấm lại một bài. Tách riêng khỏi quyền xem vì thao tác này tiêu tiền API thật.'
  restrict access: true
```

- [ ] **Step 2: Route trạng thái**

`vf_ai_trigger.routing.yml`:

```yaml
vf_ai_trigger.trang_thai:
  path: '/vf-ai/status/{node}'
  defaults:
    _controller: '\Drupal\vf_ai_trigger\Controller\TrangThaiController::trangThai'
  requirements:
    _permission: 'xem bao cao ai'
    node: \d+
  options:
    parameters:
      node:
        type: entity:node
```

- [ ] **Step 3: Controller**

`src/Controller/TrangThaiController.php`:

```php
<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Proxy trạng thái job cho JS trong màn soạn bài.
 *
 * Vì sao qua Drupal chứ không để JS gọi thẳng service: service chỉ nghe trên
 * 127.0.0.1 và cần bearer token — đưa token xuống trình duyệt là phát tán bí
 * mật cho mọi người soạn bài.
 */
class TrangThaiController extends ControllerBase {

  public function trangThai(NodeInterface $node): JsonResponse {
    // Route nhận nid từ URL; service nói chuyện bằng UUID.
    $kq = \Drupal::service('vf_ai_trigger.client')->trangThai($node->uuid());
    if ($kq === NULL) {
      // Không hỏi được service. KHÔNG bịa "none" — đó là nói dối rằng bài
      // chưa từng được xếp hàng.
      return new JsonResponse(['status' => 'khong_ro'], 200);
    }
    return new JsonResponse($kq, 200);
  }

}
```

- [ ] **Step 4: JS và library**

`vf_ai_trigger.libraries.yml`:

```yaml
trang_thai:
  js:
    js/vf_ai_trigger.js: {}
  dependencies:
    - core/drupal
    - core/once
```

`js/vf_ai_trigger.js`:

```js
/**
 * @file
 * Poll trạng thái chấm điểm và tự nạp lại trang khi xong.
 *
 * Không có nó thì editor bấm Save xong sẽ thấy "Chưa được đánh giá" suốt một
 * phút, tưởng hệ thống hỏng rồi bấm Save lại — mỗi lần bấm là tiền API thật.
 */
(function (Drupal, once) {
  'use strict';

  var CHU_KY_MS = 3000;
  var TOI_DA_LAN = 40; // ~2 phút rồi thôi, không poll mãi

  Drupal.behaviors.vfAiTrigger = {
    attach: function (context, settings) {
      var els = once('vf-ai-trang-thai', '[data-vf-ai-status-url]', context);
      els.forEach(function (el) {
        var url = el.getAttribute('data-vf-ai-status-url');
        var lan = 0;
        // CHỈ tải lại trang khi ĐÃ THẤY job đang chạy rồi mới thấy nó xong.
        //
        // Không có cờ này thì bài đã chấm xong từ trước cũng trả 'done' ngay
        // lần poll đầu -> reload -> JS chạy lại -> 'done' -> reload... tức
        // MỌI bài đã có kết quả đều không mở ra sửa được. Đây là lỗi đã bắt
        // được khi rà kế hoạch, không phải phòng xa.
        var da_thay_dang_chay = false;

        function ve(trangThai) {
          if (trangThai === 'queued') {
            el.textContent = '⏳ Đã xếp hàng, đang chờ tới lượt…';
          }
          else if (trangThai === 'running') {
            el.textContent = '⏳ Đang chấm…';
          }
          else if (trangThai === 'failed') {
            el.textContent = '⛔ Chấm thất bại. Xem log của worker.';
          }
          else if (trangThai === 'khong_ro') {
            el.textContent = '⚠ Không liên lạc được với dịch vụ chấm điểm.';
          }
        }

        function hoi() {
          lan += 1;
          fetch(url, { credentials: 'same-origin' })
            .then(function (r) { return r.json(); })
            .then(function (d) {
              if (d.status === 'queued' || d.status === 'running') {
                da_thay_dang_chay = true;
              }
              if (d.status === 'done') {
                // Chỉ nạp lại nếu ta ĐÃ chứng kiến job chạy trong chính lần
                // mở trang này. Bài đã chấm từ trước thì không làm gì cả.
                if (da_thay_dang_chay) {
                  window.location.reload();
                }
                return;
              }
              ve(d.status);
              if (d.status !== 'none' && d.status !== 'failed' && lan < TOI_DA_LAN) {
                window.setTimeout(hoi, CHU_KY_MS);
              }
            })
            .catch(function () {
              el.textContent = '⚠ Không liên lạc được với dịch vụ chấm điểm.';
            });
        }

        hoi();
      });
    }
  };
})(Drupal, once);
```

- [ ] **Step 5: Gắn khối vào form**

Thêm vào cuối `vf_ai_trigger.module`:

```php
use Drupal\Core\Form\FormStateInterface;
use Drupal\Core\Url;

/**
 * Implements hook_form_BASE_FORM_ID_alter() for node_form.
 *
 * Chèn ô trạng thái vào chính khối báo cáo của vf_ai_review. Nếu khối đó
 * không tồn tại (module kia bị tắt) thì không chèn gì — không đổ lỗi, không
 * làm trắng form soạn bài.
 */
function vf_ai_trigger_form_node_form_alter(array &$form, FormStateInterface $form_state, string $form_id): void {
  $node = $form_state->getFormObject()->getEntity();
  if ($node->bundle() !== 'article' || $node->isNew() || !isset($form['vf_ai_review'])) {
    return;
  }
  if (!\Drupal::currentUser()->hasPermission('xem bao cao ai')) {
    return;
  }

  $url = Url::fromRoute('vf_ai_trigger.trang_thai', ['node' => $node->id()])
    ->toString();

  $form['vf_ai_review']['vf_ai_trang_thai'] = [
    '#type' => 'html_tag',
    '#tag' => 'div',
    '#value' => '',
    '#attributes' => [
      'class' => ['vf-ai-trang-thai'],
      'data-vf-ai-status-url' => $url,
    ],
    '#weight' => -100,
  ];
  $form['#attached']['library'][] = 'vf_ai_trigger/trang_thai';
}
```

- [ ] **Step 6: Cấp quyền và xoá cache**

```bash
cd drupal
ddev drush role:perm:add content_editor 'xem bao cao ai'
ddev drush cr
```

Nếu chưa có role `content_editor` thì cấp cho `authenticated`:

```bash
ddev drush role:perm:add authenticated 'xem bao cao ai'
```

- [ ] **Step 7: Kiểm bằng mắt**

Bật cả service lẫn worker, chuyển một bài sang "Needs Review", mở form sửa bài đó ngay.

Expected: khối "Đánh giá AI" ở cột phải hiện `⏳ Đang chấm…` hoặc `⏳ Đã xếp hàng…`, và sau khi worker chấm xong thì trang **tự nạp lại** và hiện báo cáo — không phải bấm F5.

- [ ] **Step 8: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_trigger
git commit -m "feat: khoi trang thai cham diem tu cap nhat trong man soan bai"
```

---

### Task 11: Nút "Chấm lại" thủ công

**Files:**
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.routing.yml`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/vf_ai_trigger.module`
- Create: `drupal/web/modules/custom/vf_ai_trigger/src/Controller/ChamLaiController.php`
- Modify: `drupal/web/modules/custom/vf_ai_trigger/js/vf_ai_trigger.js`

**Interfaces:**
- Consumes: `ServiceClient::guiJob(..., force: TRUE)` (Task 9), permission `dieu khien ai` (Task 10)

- [ ] **Step 1: Thêm route**

Thêm vào `vf_ai_trigger.routing.yml`:

```yaml
vf_ai_trigger.cham_lai:
  path: '/vf-ai/rescore/{node}'
  defaults:
    _controller: '\Drupal\vf_ai_trigger\Controller\ChamLaiController::chamLai'
  methods: [POST]
  requirements:
    _permission: 'dieu khien ai'
    _csrf_token: 'TRUE'
    node: \d+
  options:
    parameters:
      node:
        type: entity:node
```

- [ ] **Step 2: Controller**

`src/Controller/ChamLaiController.php`:

```php
<?php

namespace Drupal\vf_ai_trigger\Controller;

use Drupal\Core\Controller\ControllerBase;
use Drupal\node\NodeInterface;
use Drupal\vf_ai_review\AiReportRenderer;
use Symfony\Component\HttpFoundation\JsonResponse;

/**
 * Ép chấm lại một bài, kể cả khi nội dung không đổi.
 *
 * Quyền tách riêng ('dieu khien ai', không phải 'xem bao cao ai') vì thao tác
 * này TIÊU TIỀN API THẬT — architecture.md mục 5.7 đã đặt ra ranh giới đó.
 */
class ChamLaiController extends ControllerBase {

  public function chamLai(NodeInterface $node): JsonResponse {
    $hash = AiReportRenderer::contentHash(vf_ai_review_hash_fields($node));
    $ok = \Drupal::service('vf_ai_trigger.client')
      ->guiJob($node->uuid(), $hash, 'manual', TRUE);

    return new JsonResponse(['ok' => $ok], $ok ? 202 : 503);
  }

}
```

- [ ] **Step 3: Thêm nút vào form**

Trong `vf_ai_trigger_form_node_form_alter()`, ngay sau khối `vf_ai_trang_thai`, thêm:

```php
  if (\Drupal::currentUser()->hasPermission('dieu khien ai')) {
    $url_cham_lai = Url::fromRoute('vf_ai_trigger.cham_lai', ['node' => $node->id()])
      ->toString();
    // ltrim BẮT BUỘC: CsrfAccessCheck::access() xác thực token theo
    // `ltrim($route->getPath(), '/')` đã thay tham số, tức "vf-ai/rescore/2"
    // KHÔNG có gạch chéo đầu. Sinh token từ chuỗi có gạch chéo thì token
    // không bao giờ khớp và route luôn trả 403 — mà thông báo lỗi chỉ nói
    // "'csrf_token' URL query argument is invalid", không hề gợi ý nguyên
    // nhân là một ký tự thừa. Kiểm chứng 2026-08-07 tại
    // web/core/lib/Drupal/Core/Access/CsrfAccessCheck.php:59.
    $token = \Drupal::csrfToken()->get(ltrim($url_cham_lai, '/'));
    $form['vf_ai_review']['vf_ai_cham_lai'] = [
      '#type' => 'html_tag',
      '#tag' => 'button',
      '#value' => 'Chấm lại',
      '#attributes' => [
        'type' => 'button',
        'class' => ['button', 'vf-ai-cham-lai'],
        'data-vf-ai-rescore-url' => $url_cham_lai . '?token=' . $token,
      ],
      '#weight' => 100,
    ];
  }
```

- [ ] **Step 4: Nối nút với JS**

Thêm vào trong `Drupal.behaviors.vfAiTrigger.attach`, sau khối `els.forEach(...)`:

```js
      var nut = once('vf-ai-cham-lai', '[data-vf-ai-rescore-url]', context);
      nut.forEach(function (btn) {
        btn.addEventListener('click', function () {
          btn.disabled = true;
          btn.textContent = 'Đang gửi…';
          fetch(btn.getAttribute('data-vf-ai-rescore-url'), {
            method: 'POST',
            credentials: 'same-origin'
          })
            .then(function (r) {
              if (r.status === 202) {
                window.location.reload();
              }
              else {
                btn.textContent = 'Gửi thất bại';
              }
            })
            .catch(function () { btn.textContent = 'Gửi thất bại'; });
        });
      });
```

- [ ] **Step 5: Cấp quyền cho tài khoản quản trị và kiểm**

```bash
cd drupal
ddev drush role:perm:add administrator 'dieu khien ai'
ddev drush cr
```

Mở một bài **đã chấm xong**, bấm "Chấm lại". Rồi:

```bash
docker exec vf-agent-db psql -U vf_agent -d vf_agent \
  -c "SELECT id, status, source FROM review_job ORDER BY id DESC LIMIT 3;"
```

Expected: job cũ chuyển `superseded`, có job mới `queued` với `source = manual`.

- [ ] **Step 6: Kiểm quyền thật sự chặn**

Đăng nhập bằng một tài khoản chỉ có `xem bao cao ai`. Expected: **không thấy nút "Chấm lại"**, và gọi thẳng URL bằng `curl` trả 403.

- [ ] **Step 7: Commit**

```bash
git add drupal/web/modules/custom/vf_ai_trigger
git commit -m "feat: nut cham lai thu cong, tach quyen dieu khien khoi quyen xem"
```

---

### Task 12: Chạy thật end-to-end và cập nhật tài liệu

**Files:**
- Modify: `docs/architecture.md` mục 9
- Modify: `docs/operations.md` mục 2.4 và mục 4
- Modify: `docs/technical-debt.md` nhóm C
- Modify: `README.md`
- Modify: `docs/pre-demo-checklist.md`
- Modify: `docs/sprint2-report.md`
- Modify: `docs/editor-ui-design.md` mục 9
- Create: `docs/evidence/tu_dong_hoa_e2e.txt`

- [ ] **Step 1: Chạy toàn bộ bộ test**

```bash
cd multiagent
docker compose up -d
for f in scripts/test_*.py; do .venv/Scripts/python.exe "$f" > /dev/null || echo "FAIL $f"; done
cd ../drupal
ddev exec php scripts/test_ai_report_renderer.php
ddev exec php scripts/test_vf_ai_trigger.php
```

Expected: không dòng FAIL nào; hai test PHP exit 0. Ghi lại tổng số file test.

- [ ] **Step 2: Chạy 8 tiêu chí hoàn thành của spec mục 13**

Với mỗi tiêu chí, ghi kết quả thật vào `docs/evidence/tu_dong_hoa_e2e.txt`:

```
Ngay chay: <ngay that>
Model: claude-haiku-4-5-20251001

1. Save -> "Dang cham" trong ~2s -> tu hien ket qua:        DAT / KHONG
   (do bang dong ho: <so giay> giay tu luc Save toi luc job chuyen sang running)
2. Tat service, Save, bat lai -> doi soat bat duoc trong <=5 phut:  DAT / KHONG
3. Save 3 lan khong sua gi -> count(review_job) = 1:        <so that>
4. Sua mot chu -> job moi:                                   DAT / KHONG
5. run_log du agent_results / config_meta / usage:           DAT / KHONG
6. Giet worker giua chung -> sau 15 phut job ve queued:      DAT / KHONG
7. Bai luon that bai -> dead-letter, doi soat KHONG tao them: DAT / KHONG
8. Toan bo test xanh:                                        <so file>/<tong>

Chi phi lan chay nay (cong tu run_log.usage): $<so that>
```

Lệnh cho tiêu chí 5 và chi phí:

```bash
docker exec vf-agent-db psql -U vf_agent -d vf_agent -c \
  "SELECT node_id, decision, final_score, jsonb_array_length(usage) AS so_lan_goi,
          config_meta->>'calibrated' AS calibrated FROM run_log ORDER BY id DESC LIMIT 5;"
```

- [ ] **Step 3: Viết lại `architecture.md` mục 9**

Thay toàn bộ mục 9.1 và 9.2 bằng nội dung phản ánh đúng cái đã làm. Giữ nguyên mục 9.3 (lập luận "worker trong production chính là worker này") vì lập luận đó vẫn đúng, nhưng sửa câu mở đầu 9.3 cho khớp: nay đường chính đã là event-driven, phần còn thiếu so với production chỉ là broker và container hoá. Thêm bảng trạng thái:

| Mắt xích | Trạng thái |
|---|---|
| Content Moderation "Needs Review" | Đã bật |
| Đường event (Drupal → service → hàng đợi) | Đã làm |
| Hàng đợi bền + retry + dead-letter | Đã làm, Postgres |
| Vòng đối soát (polling) | Đã làm, vai trò lưới an toàn |
| Nhật ký truy vết | Đã làm, bảng `run_log` |
| Message broker riêng | Cố ý chưa làm, lý do ở spec mục 2 Q1 |
| Container hoá phía Python | Cố ý chưa làm, lý do ở spec mục 11 |

- [ ] **Step 4: Sửa `operations.md`**

Trong mục 2.4, thêm ngay dưới bảng phương án:

> **Đính chính 2026-08-07 — kết luận đã đổi từ JSONL sang bảng Postgres.** Lập luận cũ (*"bất cứ thứ gì nặng hơn đều là over-engineering"*) đúng ở thời điểm viết và **tiền đề của nó đã đổi**: lúc đó phía Multi-Agent chưa có CSDL nào, nên "bảng riêng" nghĩa là dựng thêm hạ tầng. Từ 2026-08-05 Postgres đã chạy sẵn cho kho vector, và bản triển khai tự động hoá dù sao cũng phải tạo bảng cho hàng đợi. Chi tiết: spec `2026-08-07-needs-review-automation-design.md` mục 2.1.

Trong mục 4, đổi trạng thái nhật ký truy vết thành "đã triển khai 2026-08-07", và ghi rằng vòng phản hồi người duyệt nay **hết bị chặn** vì `(node_id, scored_at)` đã có trong `run_log`.

Trong mục 5, thay dòng `src/audit.py (mới)` — bỏ phần JSONL và xoay file theo tháng, thay bằng bảng `run_log`.

- [ ] **Step 5: Sửa `technical-debt.md`**

Trong bảng nhóm C:
- Xoá dòng "Polling worker + Content Moderation", thay bằng dòng đã hoàn thành có gạch ngang, ghi `✅ xong 2026-08-07` và nói rõ cảnh báo `USAGE_LOG` đã được xử lý bằng `clear()` sau mỗi job.
- Dòng "Nhật ký truy vết JSONL" → `✅ xong 2026-08-07`, ghi chú đã đổi sang Postgres.
- Dòng "Vòng phản hồi người duyệt" → gỡ phần "cần nhật ký truy vết xong trước", vì nay đã xong.

- [ ] **Step 6: Sửa `README.md`**

- Mục "Trạng thái Sprint 2": tick ô "Tự động hóa", mô tả đúng hai đường (event + đối soát).
- **Sửa dòng 114**: cụm `→ Chroma` phải thành `→ Postgres + pgvector` (đã đổi từ 2026-08-05 mà README còn sót).
- Mục Setup: thêm hai lệnh chạy service và worker.

- [ ] **Step 7: Sửa `pre-demo-checklist.md`**

Thêm mục mới "Khởi động service và worker trước khi demo" với đủ 3 lệnh (docker compose, uvicorn, worker) và lệnh kiểm `curl http://127.0.0.1:8900/health`.

Trong mục 5, thêm cảnh báo:

> ⚠️ Từ 2026-08-07, bốn bộ test (`test_job_queue`, `test_audit`, `test_worker`, `test_api`) **cần container Postgres đang chạy**. Không có nó chúng in `[SKIP]` và thoát 0 — **`[SKIP]` không phải `[PASS]`**. Trước khi báo cáo số test xanh, chạy `docker compose ps` xác nhận `vf-agent-db` đang chạy.

- [ ] **Step 8: Sửa `sprint2-report.md` và `editor-ui-design.md`**

- `sprint2-report.md` mục 1: đổi "4 mục xong, 2 mục chưa" thành "5 mục xong, 1 mục chưa".
- `sprint2-report.md` mục 3.2: chuyển thành mục 2.5 trong phần "Đã xong", kèm lý do chọn Postgres thay vì Redis (spec mục 2 Q1) và lý do giữ cả hai đường (Q2).
- `sprint2-report.md` mục 6: bỏ dòng polling worker khỏi việc tiếp theo.
- `editor-ui-design.md` mục 9: chuyển nút "chấm lại" và khối trạng thái từ "chưa chốt" sang đã làm, trỏ tới spec mới.

- [ ] **Step 9: Chạy lại toàn bộ test lần cuối**

```bash
cd multiagent
for f in scripts/test_*.py; do .venv/Scripts/python.exe "$f" > /dev/null || echo "FAIL $f"; done
```

Expected: không dòng FAIL.

- [ ] **Step 10: Commit và mở PR**

```bash
git add -A
git commit -m "docs: dong bo tai lieu voi phan tu dong hoa Needs Review"
git push -u origin feature/tu-dong-hoa-needs-review
```

Mở PR bằng URL (repo này chưa cài `gh`):
`https://github.com/hoang1412003/drupal-multiagent-seo/compare/main...feature/tu-dong-hoa-needs-review`

- Tiêu đề PR (tiếng Anh): `Event-driven Needs Review automation with durable Postgres queue`
- Nội dung PR: tiếng Việt không dấu, dẫn tới spec và file bằng chứng `docs/evidence/tu_dong_hoa_e2e.txt`.

---

## Phụ lục: những chỗ dễ sai nhất

| Chỗ | Sai thế nào | Bắt bằng gì |
|---|---|---|
| `node_id` là `nid` thay vì UUID | Job tạo được, `fetch_content` trả 404, job dead-letter sau 3 lần | `test_vf_ai_trigger.php` kiểm định dạng UUID |
| Thiếu `SKIP LOCKED` | Hai worker chặn nhau, hoặc chấm trùng | `test_job_queue.py::test_skip_locked_...` (có `lock_timeout` để đỏ thay vì treo) |
| Đối soát hồi sinh job dead-letter | Vòng lặp tiêu tiền API vô hạn | `test_reconcile.py::test_KHONG_hoi_sinh_job_da_dead_letter` |
| `write_back` vẫn trả `None` | Job báo `done` trong khi Drupal không có kết quả | `test_drupal_client_worker.py` |
| `USAGE_LOG` không reset | Worker chạy nền phình bộ nhớ, chi phí cộng dồn sai | `test_worker.py::test_usage_log_duoc_reset` |
| Hash PHP lệch hash Python | Đối soát chấm lại vô hạn mọi bài | Fixture dùng chung ở cả hai phía |
| Token đặt vào config entity | Lộ secret vào git khi export config | Rà `config:export` trước khi commit |
| JS reload khi thấy `done` mà không nhớ đã thấy `running` | **Mọi bài đã chấm đều tự tải lại vô hạn**, không mở ra sửa được | Mở form một bài đã có báo cáo, trang phải đứng yên |
| Bỏ `running` khỏi index dedup | write_back PATCH → hook bắn lại → job mới → chấm lại → PATCH… vòng lặp tự chấm vô hạn | Chấm một bài, đếm `review_job` của node đó phải đúng 1 |
| Token CSRF sinh từ đường dẫn có `/` đầu | Nút "Chấm lại" **luôn** trả 403, thông báo lỗi không gợi ý nguyên nhân | Bấm nút thật, phải ra 202 |
