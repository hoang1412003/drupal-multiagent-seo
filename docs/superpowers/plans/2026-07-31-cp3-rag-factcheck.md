# CP3 – RAG Fact-check cho Compliance Agent — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thêm nguồn flag thứ 3 cho Compliance Agent — RAG fact-check đối chiếu claim định lượng trong bài với thông số VinFast công bố, sinh flag `critical` (mã A3) khi số liệu sai lệch.

**Architecture:** KB thông số (JSON, một entry / model) → nạp offline vào Chroma (một collection, lọc metadata `(content_type, langcode)`) qua embedding đa ngôn ngữ BGE-M3 self-host (tách sau interface `Embedder`). Khi chấm: LLM trích claim định lượng → truy vấn KB → LLM so sánh khớp/lệch (chỉ khi *cùng model*) → lệch thì sinh flag critical. Tích hợp vào `compliance.py` như nguồn flag độc lập thứ 3 (bên cạnh LLM tự do + blacklist), **không** phụ thuộc việc viết lại rubric hay thêm field vào `state.py`.

**Tech Stack:** Python 3.12, `chromadb`, `sentence-transformers` (BGE-M3), `anthropic` (structured output qua `ai_core.call_agent`).

## Global Constraints

- Chạy trên Windows; venv tại `multiagent/.venv`. Chạy test/script: `.venv\Scripts\python.exe scripts\<file>.py` (từ thư mục `multiagent/`).
- Test là **script thuần** khớp style hiện có (`sys.path.insert(0, ...src)` + `assert` + `sys.exit(1 if failed else 0)` + in `[PASS]`/`[FAIL]`). **KHÔNG** dùng pytest.
- Comment/chuỗi tiếng Việt, khớp mật độ và văn phong code hiện có (xem `compliance.py`, `drupal_client.py`).
- Commit **KHÔNG** kèm trailer `Co-Authored-By: Claude` (quy ước repo này).
- Mọi lần gọi LLM qua `ai_core.call_agent` (đã có `temperature=0` + structured output). Không gọi Claude trực tiếp.
- Embedding tách sau interface `Embedder`; mặc định BGE-M3; **inject được** để test không tải model 2GB.
- Chroma: một collection `kb_factcheck`, `hnsw:space="cosine"`, lọc metadata `(content_type, langcode)`.
- KB seed đánh dấu `"verified": false`. Thu số liệu thật là **task song song của người dùng** (mở URL `docs/goldset/sources.md` mục 2, verify từng số) — không thuộc plan này.
- **An toàn CP3:** claim không tra được, hoặc thông số tra về thuộc **model khác** → **KHÔNG** sinh flag critical (mức "không kiểm chứng được", `docs/rubrics.md` mục 6.2) — tránh veto oan bài nhắc model ngoài KB.
- Phạm vi hiện tại một `(content_type, langcode)` duy nhất: mặc định `content_type="cam_nang"`, `langcode="vi"` (chờ `state.py` bổ sung 2 field này ở việc config-spec riêng, `docs/config-spec.md` mục 8).

---

## File Structure

- Create: `multiagent/src/embeddings.py` — interface `Embedder` + `BGEM3Embedder` + `get_default_embedder()`.
- Create: `multiagent/src/kb/__init__.py` — đánh dấu package.
- Create: `multiagent/src/kb/specs.json` — dữ liệu KB seed (thông số/model), người dùng verify sau.
- Create: `multiagent/src/kb/build_kb.py` — nạp offline: `specs.json` → chunk → embed → Chroma.
- Create: `multiagent/src/retrieval.py` — truy vấn Chroma theo `(content_type, langcode)`, trả top-k + similarity.
- Create: `multiagent/src/agents/fact_check.py` — CP3: trích claim → truy vấn → so sánh → flag.
- Modify: `multiagent/src/agents/compliance.py` — gộp flag fact-check vào `run()`.
- Modify: `multiagent/requirements.txt` — thêm `chromadb`, `sentence-transformers`.
- Create tests: `scripts/test_embeddings.py`, `scripts/test_kb_build.py`, `scripts/test_retrieval.py`, `scripts/test_fact_check.py`, `scripts/eval_retrieval.py`, `scripts/retrieval_eval_pairs.json`.
- Modify: `scripts/smoke_test_compliance.py` — xác nhận fact-check không phá cấu trúc `run()`.
- Modify docs: `docs/rag-design.md` (mục 4.1), `docs/architecture.md` (mục 5.4), `README.md` (trạng thái Sprint 2).

Ghi chú `.gitignore`: KB Chroma sinh ra tại `multiagent/src/kb/chroma/` là dữ liệu build lại được — thêm vào `.gitignore` (Task 4).

---

## Task 1: Thêm dependency + scaffold package `kb`

**Files:**
- Modify: `multiagent/requirements.txt`
- Create: `multiagent/src/kb/__init__.py`

**Interfaces:**
- Produces: `chromadb`, `sentence_transformers` import được trong venv; package `src/kb`.

- [ ] **Step 1: Thêm dependency vào `requirements.txt`**

Thêm 2 dòng (giữ nguyên các dòng cũ):

```
chromadb>=0.5.0
sentence-transformers>=3.0.0
```

- [ ] **Step 2: Cài đặt**

Run (từ `multiagent/`): `.venv\Scripts\pip.exe install -r requirements.txt`
Expected: cài thành công (kéo theo `torch` — vài trăm MB, có thể mất vài phút).

- [ ] **Step 3: Tạo package `kb`**

Tạo file rỗng `multiagent/src/kb/__init__.py`.

- [ ] **Step 4: Xác nhận import được**

Run: `.venv\Scripts\python.exe -c "import chromadb, sentence_transformers; print('ok')"`
Expected: in `ok`, không lỗi.

- [ ] **Step 5: Commit**

```bash
git add multiagent/requirements.txt multiagent/src/kb/__init__.py
git commit -m "build: them chromadb + sentence-transformers cho CP3 RAG fact-check"
```

---

## Task 2: KB seed data + kiểm tra định dạng

**Files:**
- Create: `multiagent/src/kb/specs.json`
- Create test: `scripts/test_kb_specs.py`

**Interfaces:**
- Produces: `specs.json` — list các entry `{model, content_type, langcode, specs: {..}, source_url, verified}`.

- [ ] **Step 1: Viết test kiểm tra schema `specs.json`**

Create `scripts/test_kb_specs.py`:

```python
"""Kiem tra specs.json dung dinh dang truoc khi build KB.
Chay: .venv\\Scripts\\python.exe scripts\\test_kb_specs.py
"""
import json
import os
import sys

SPECS = os.path.join(os.path.dirname(__file__), "..", "src", "kb", "specs.json")
REQUIRED = {"model", "content_type", "langcode", "specs", "source_url", "verified"}

if __name__ == "__main__":
    failed = False
    with open(SPECS, encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list) or not entries:
        print("[FAIL] specs.json phai la list khong rong")
        sys.exit(1)

    ids = set()
    for i, e in enumerate(entries):
        missing = REQUIRED - set(e)
        if missing:
            print(f"[FAIL] entry {i} thieu khoa: {missing}")
            failed = True
        if not isinstance(e.get("specs"), dict) or not e["specs"]:
            print(f"[FAIL] entry {i} 'specs' phai la dict khong rong")
            failed = True
        key = (e.get("content_type"), e.get("langcode"), e.get("model"))
        if key in ids:
            print(f"[FAIL] trung id: {key}")
            failed = True
        ids.add(key)

    print(f"[{'FAIL' if failed else 'PASS'}] {len(entries)} entry")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 2: Chạy test để thấy nó fail**

Run: `.venv\Scripts\python.exe scripts\test_kb_specs.py`
Expected: FAIL (`FileNotFoundError` vì `specs.json` chưa có).

- [ ] **Step 3: Tạo `specs.json` với dữ liệu seed từ `sources.md` mục 2.1**

Create `multiagent/src/kb/specs.json`:

```json
[
  {
    "model": "VF 9",
    "content_type": "cam_nang",
    "langcode": "vi",
    "specs": {
      "tam_hoat_dong": "438km (Eco) / 423km (Plus)",
      "tieu_chuan_do": "cần xác nhận (NEDC/WLTP)"
    },
    "source_url": "/vn_vi/thong-so-ky-thuat-vinfast-vf9",
    "verified": false
  },
  {
    "model": "VF 8",
    "content_type": "cam_nang",
    "langcode": "vi",
    "specs": {
      "tam_hoat_dong": "420km (Eco) / 400km (Plus)",
      "tieu_chuan_do": "cần xác nhận (NEDC/WLTP)"
    },
    "source_url": "/vn_vi/thong-so-ky-thuat-vf8-kich-thuoc-va-thiet-ke",
    "verified": false
  },
  {
    "model": "VF 5",
    "content_type": "cam_nang",
    "langcode": "vi",
    "specs": {
      "tam_hoat_dong": "326km",
      "tieu_chuan_do": "NEDC"
    },
    "source_url": "/vn_vi/thong-so-vf-7",
    "verified": false
  },
  {
    "model": "Bảo dưỡng định kỳ",
    "content_type": "cam_nang",
    "langcode": "vi",
    "specs": {
      "chu_ky": "mỗi 12.000km hoặc 1 năm"
    },
    "source_url": "/vn_vi/lich-bao-duong-xe-vinfast",
    "verified": false
  }
]
```

- [ ] **Step 4: Chạy test để thấy nó pass**

Run: `.venv\Scripts\python.exe scripts\test_kb_specs.py`
Expected: `[PASS] 4 entry`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/kb/specs.json multiagent/scripts/test_kb_specs.py
git commit -m "data: KB seed thong so VinFast (VF5/8/9 + bao duong) cho CP3, verified=false"
```

---

## Task 3: Interface `Embedder` + `BGEM3Embedder`

**Files:**
- Create: `multiagent/src/embeddings.py`
- Create test: `scripts/test_embeddings.py`

**Interfaces:**
- Produces:
  - `class Embedder(Protocol)`: `embed(texts: list[str]) -> list[list[float]]`, property `dim: int`.
  - `class BGEM3Embedder` (mặc định, `model_name="BAAI/bge-m3"`, `dim==1024`).
  - `get_default_embedder() -> Embedder` (singleton lười, nạp model một lần).
- Consumes: (không).

- [ ] **Step 1: Viết test — dùng `FakeEmbedder` cho logic, đánh dấu integration cho model thật**

Create `scripts/test_embeddings.py`:

```python
"""Test interface Embedder. Logic dung FakeEmbedder (khong tai model 2GB).
Integration voi BGE-M3 that chay rieng khi truyen doi so 'real'.
Chay logic:      .venv\\Scripts\\python.exe scripts\\test_embeddings.py
Chay integration:.venv\\Scripts\\python.exe scripts\\test_embeddings.py real
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class FakeEmbedder:
    """Vector one-hot theo token model xuat hien trong text - du de test
    logic truy xuat (cung model -> cung vector) ma khong can model that."""
    _VOCAB = ["VF 5", "VF 8", "VF 9", "bảo dưỡng"]

    def embed(self, texts):
        out = []
        for t in texts:
            v = [1.0 if term.lower() in t.lower() else 0.0 for term in self._VOCAB]
            if sum(v) == 0:
                v = [1.0] + [0.0] * (len(self._VOCAB) - 1)  # tránh vector 0
            out.append(v)
        return out

    @property
    def dim(self):
        return len(self._VOCAB)


def test_fake():
    e = FakeEmbedder()
    vecs = e.embed(["VF 8 tầm hoạt động", "VF 8"])
    assert len(vecs) == 2, "phai tra dung so vector"
    assert len(vecs[0]) == e.dim, "vector dung so chieu"
    assert vecs[0] == vecs[1], "cung model -> cung vector"
    print("[PASS] FakeEmbedder logic")


def test_real():
    from embeddings import BGEM3Embedder
    e = BGEM3Embedder()
    vecs = e.embed(["VF 8 đi được bao nhiêu km"])
    assert e.dim == 1024, f"BGE-M3 phai 1024 chieu, thuc te {e.dim}"
    assert len(vecs[0]) == 1024
    print("[PASS] BGEM3Embedder integration (dim=1024)")


if __name__ == "__main__":
    test_fake()
    if len(sys.argv) > 1 and sys.argv[1] == "real":
        test_real()
    print("OK")
```

- [ ] **Step 2: Chạy phần logic để thấy fail**

Run: `.venv\Scripts\python.exe scripts\test_embeddings.py`
Expected: hiện tại `test_fake` PASS (FakeEmbedder tự chứa trong test), nhưng test này chưa kiểm `embeddings.py`. Chuyển sang Step 3 để tạo module, integration test là phần kiểm thật.

- [ ] **Step 3: Viết `embeddings.py`**

Create `multiagent/src/embeddings.py`:

```python
"""Interface embedding + hiện thực BGE-M3 (đa ngôn ngữ, self-host).

Tách sau interface Embedder để đổi model chỉ là thay 1 class
(docs/rag-design.md mục 4.1). Chọn model ĐA NGÔN NGỮ (BGE-M3) thay vì model
chuyên tiếng Việt để KB không phải nhúng lại khi mở rộng ngôn ngữ - đổi model
embedding buộc re-embed toàn bộ KB (docs/rag-design.md mục 4.2).
"""
from typing import Protocol


class Embedder(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]:
        ...

    @property
    def dim(self) -> int:
        ...


class BGEM3Embedder:
    """BGE-M3 chạy local qua sentence-transformers. Nạp model lần đầu tốn
    vài giây + tải ~2GB (một lần). Vector đã chuẩn hoá (normalize) để dùng
    cosine trong Chroma."""

    def __init__(self, model_name: str = "BAAI/bge-m3"):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(model_name)
        self._dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return [v.tolist() for v in vecs]

    @property
    def dim(self) -> int:
        return self._dim


_default: Embedder | None = None


def get_default_embedder() -> Embedder:
    """Singleton lười - nạp model một lần cho cả process (polling worker phải
    gọi sớm lúc khởi động, không nạp lazy trong lần chấm đầu -
    docs/rag-design.md mục 6)."""
    global _default
    if _default is None:
        _default = BGEM3Embedder()
    return _default
```

- [ ] **Step 4: Chạy integration test với model thật**

Run: `.venv\Scripts\python.exe scripts\test_embeddings.py real`
Expected: lần đầu tải BGE-M3 (~2GB), rồi `[PASS] BGEM3Embedder integration (dim=1024)`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/embeddings.py multiagent/scripts/test_embeddings.py
git commit -m "feat: interface Embedder + BGEM3Embedder (da ngon ngu, self-host)"
```

---

## Task 4: Script nạp KB `build_kb.py`

**Files:**
- Create: `multiagent/src/kb/build_kb.py`
- Modify: `.gitignore` (thêm `multiagent/src/kb/chroma/`)
- Create test: `scripts/test_kb_build.py`

**Interfaces:**
- Consumes: `specs.json` (Task 2), `Embedder` (Task 3).
- Produces:
  - `chunk_text(entry: dict) -> str` — chunk một model (Contextual Retrieval bản tất định).
  - `build(specs_path=..., chroma_path=..., embedder=None) -> int` — số chunk đã nạp.
  - Hằng: `COLLECTION = "kb_factcheck"`, `SPECS_PATH`, `CHROMA_PATH`.

- [ ] **Step 1: Viết test — build vào Chroma tạm bằng FakeEmbedder**

Create `scripts/test_kb_build.py`:

```python
"""Test build_kb: nap specs.json vao Chroma tam bang FakeEmbedder (khong
tai model that). Chay: .venv\\Scripts\\python.exe scripts\\test_kb_build.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from kb import build_kb


class FakeEmbedder:
    _VOCAB = ["VF 5", "VF 8", "VF 9", "bảo dưỡng"]

    def embed(self, texts):
        out = []
        for t in texts:
            v = [1.0 if x.lower() in t.lower() else 0.0 for x in self._VOCAB]
            if sum(v) == 0:
                v = [1.0] + [0.0] * (len(self._VOCAB) - 1)
            out.append(v)
        return out

    @property
    def dim(self):
        return len(self._VOCAB)


def test_chunk_has_model_context():
    entry = {"model": "VF 8", "specs": {"tam_hoat_dong": "420km"}}
    text = build_kb.chunk_text(entry)
    assert "VF 8" in text, "chunk phai chua ten model (Contextual Retrieval)"
    assert "420km" in text, "chunk phai chua gia tri thong so"
    print("[PASS] chunk_text co ngu canh model")


def test_build_counts():
    with tempfile.TemporaryDirectory() as d:
        n = build_kb.build(chroma_path=d, embedder=FakeEmbedder())
        assert n == 4, f"phai nap 4 chunk (seed), thuc te {n}"
    print("[PASS] build nap dung so chunk")


if __name__ == "__main__":
    test_chunk_has_model_context()
    test_build_counts()
    print("OK")
```

- [ ] **Step 2: Chạy để thấy fail**

Run: `.venv\Scripts\python.exe scripts\test_kb_build.py`
Expected: FAIL (`ImportError: cannot import name 'build_kb'`).

- [ ] **Step 3: Viết `build_kb.py`**

Create `multiagent/src/kb/build_kb.py`:

```python
"""Nạp KB fact-check: specs.json -> chunk theo model -> embed -> Chroma.

Chạy OFFLINE, KHÔNG nằm trong pipeline chấm (docs/rag-design.md mục 8).
Cắt theo đơn vị "một model xe" (mục 4.3): claim "VF 8 chạy 420km" cần đúng
khối thông số VF 8, cắt theo ký tự sẽ tách số khỏi tên model -> retrieve nhầm.

Chạy: .venv\\Scripts\\python.exe src\\kb\\build_kb.py
"""
import json
import os

import chromadb

_KB_DIR = os.path.dirname(__file__)
SPECS_PATH = os.path.join(_KB_DIR, "specs.json")
CHROMA_PATH = os.path.join(_KB_DIR, "chroma")
COLLECTION = "kb_factcheck"


def chunk_text(entry: dict) -> str:
    """Một chunk cho một model. Thêm câu ngữ cảnh vào đầu (Contextual
    Retrieval bản TẤT ĐỊNH - docs/rag-design.md mục 4.3): chunk thông số trần
    đứng một mình gần như vô nghĩa với retrieval, thêm tên model + nguồn thì
    truy vấn 'VF 8 đi bao nhiêu km' khớp hẳn lên. Dùng prefix cố định thay vì
    gọi LLM để giữ tất định + rẻ; bản dùng LLM là cải tiến sau, đo bằng E2."""
    lines = [f"Đây là thông số VinFast {entry['model']} công bố trên vinfastauto.com:"]
    for key, value in entry["specs"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def build(specs_path: str = SPECS_PATH, chroma_path: str = CHROMA_PATH,
          embedder=None) -> int:
    """Nạp lại KB từ đầu (xoá collection cũ để không lẫn số cũ). Trả về số
    chunk đã nạp."""
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()

    with open(specs_path, encoding="utf-8") as f:
        entries = json.load(f)

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass  # chưa có -> bỏ qua
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})

    docs = [chunk_text(e) for e in entries]
    embeddings = embedder.embed(docs)
    col.add(
        ids=[f"{e['content_type']}:{e['langcode']}:{e['model']}" for e in entries],
        embeddings=embeddings,
        documents=docs,
        metadatas=[
            {
                "model": e["model"],
                "content_type": e["content_type"],
                "langcode": e["langcode"],
                "source_url": e.get("source_url", ""),
                "verified": e.get("verified", False),
            }
            for e in entries
        ],
    )
    return col.count()


if __name__ == "__main__":
    n = build()
    print(f"Đã nạp {n} chunk vào KB fact-check ({CHROMA_PATH})")
```

- [ ] **Step 4: Chạy test để thấy pass**

Run: `.venv\Scripts\python.exe scripts\test_kb_build.py`
Expected: `[PASS] chunk_text ...`, `[PASS] build nap dung so chunk`, `OK`.

- [ ] **Step 5: Thêm thư mục Chroma vào `.gitignore` + build KB thật một lần**

Thêm vào `.gitignore` (tạo file nếu chưa có ở gốc repo):

```
multiagent/src/kb/chroma/
```

Rồi build KB thật: `.venv\Scripts\python.exe src\kb\build_kb.py`
Expected: `Đã nạp 4 chunk vào KB fact-check ...`.

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/kb/build_kb.py multiagent/scripts/test_kb_build.py .gitignore
git commit -m "feat: build_kb nap thong so VinFast vao Chroma (chunk theo model)"
```

---

## Task 5: Module truy xuất `retrieval.py`

**Files:**
- Create: `multiagent/src/retrieval.py`
- Create test: `scripts/test_retrieval.py`

**Interfaces:**
- Consumes: Chroma collection `kb_factcheck`, `Embedder` (Task 3).
- Produces:
  - `retrieve(query, content_type, langcode, *, top_k=3, min_similarity=None, embedder=None, collection=None) -> list[dict]`
  - Mỗi hit: `{"text": str, "model": str, "score": float, "source_url": str}`.

- [ ] **Step 1: Viết test — Chroma tạm + FakeEmbedder, kiểm lọc langcode, top_k, cùng-model**

Create `scripts/test_retrieval.py`:

```python
"""Test retrieval: dung Chroma tam + FakeEmbedder. Kiem loc (content_type,
langcode), top_k, va truy van dung model. Khong tai model that.
Chay: .venv\\Scripts\\python.exe scripts\\test_retrieval.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import chromadb
from retrieval import retrieve


class FakeEmbedder:
    _VOCAB = ["VF 5", "VF 8", "VF 9", "bảo dưỡng"]

    def embed(self, texts):
        out = []
        for t in texts:
            v = [1.0 if x.lower() in t.lower() else 0.0 for x in self._VOCAB]
            if sum(v) == 0:
                v = [1.0] + [0.0] * (len(self._VOCAB) - 1)
            out.append(v)
        return out

    @property
    def dim(self):
        return len(self._VOCAB)


def _make_collection(path):
    emb = FakeEmbedder()
    client = chromadb.PersistentClient(path=path)
    col = client.create_collection("kb_factcheck", metadata={"hnsw:space": "cosine"})
    docs = ["thông số VF 8: 420km", "thông số VF 9: 438km", "thông số VF 8 tiếng Anh"]
    col.add(
        ids=["vi:vf8", "vi:vf9", "en:vf8"],
        embeddings=emb.embed(docs),
        documents=docs,
        metadatas=[
            {"model": "VF 8", "content_type": "cam_nang", "langcode": "vi", "source_url": "u1"},
            {"model": "VF 9", "content_type": "cam_nang", "langcode": "vi", "source_url": "u2"},
            {"model": "VF 8", "content_type": "cam_nang", "langcode": "en", "source_url": "u3"},
        ],
    )
    return col, emb


def test_retrieves_right_model_and_lang():
    with tempfile.TemporaryDirectory() as d:
        col, emb = _make_collection(d)
        hits = retrieve("VF 8", "cam_nang", "vi", embedder=emb, collection=col)
        assert hits, "phai co ket qua"
        assert hits[0]["model"] == "VF 8", f"top1 phai la VF 8, got {hits[0]['model']}"
        # loc langcode: khong duoc tra ban tieng Anh (en:vf8)
        assert all(h["source_url"] != "u3" for h in hits), "khong duoc tra ban langcode khac"
    print("[PASS] truy van dung model + loc langcode")


def test_min_similarity_filters():
    with tempfile.TemporaryDirectory() as d:
        col, emb = _make_collection(d)
        # truy van khong khop token nao -> vector [1,0,0,0], similarity thap
        hits = retrieve("xe tay ga", "cam_nang", "vi", embedder=emb,
                        collection=col, min_similarity=0.99)
        assert hits == [], "duoi nguong similarity phai loc het"
    print("[PASS] min_similarity loc ket qua duoi nguong")


if __name__ == "__main__":
    test_retrieves_right_model_and_lang()
    test_min_similarity_filters()
    print("OK")
```

- [ ] **Step 2: Chạy để thấy fail**

Run: `.venv\Scripts\python.exe scripts\test_retrieval.py`
Expected: FAIL (`ModuleNotFoundError: No module named 'retrieval'`).

- [ ] **Step 3: Viết `retrieval.py`**

Create `multiagent/src/retrieval.py`:

```python
"""Truy vấn KB fact-check theo (content_type, langcode).

Trả top-k chunk kèm điểm similarity; dưới ngưỡng min_similarity -> loại (kết
quả có thể RỖNG). Rỗng nghĩa là "không tra được" -> CP3 mức 1, KHÔNG phải
mức 0 (docs/rag-design.md mục 4.4, docs/rubrics.md mục 6.2).

min_similarity mặc định None (chưa chốt) - chốt từ bộ eval E2
(docs/evaluation-plan.md mục 4.2).
"""
import os

import chromadb

_CHROMA_PATH = os.path.join(os.path.dirname(__file__), "kb", "chroma")
COLLECTION = "kb_factcheck"

_client = None


def _get_collection(chroma_path: str = _CHROMA_PATH):
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=chroma_path)
    return _client.get_collection(COLLECTION)


def retrieve(query: str, content_type: str, langcode: str, *, top_k: int = 3,
             min_similarity: float | None = None, embedder=None,
             collection=None) -> list[dict]:
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    col = collection if collection is not None else _get_collection()

    qvec = embedder.embed([query])[0]
    res = col.query(
        query_embeddings=[qvec],
        n_results=top_k,
        where={"$and": [{"content_type": content_type}, {"langcode": langcode}]},
    )

    hits = []
    for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
        similarity = 1.0 - dist  # cosine distance -> similarity
        if min_similarity is not None and similarity < min_similarity:
            continue
        hits.append(
            {
                "text": doc,
                "model": meta["model"],
                "score": similarity,
                "source_url": meta.get("source_url", ""),
            }
        )
    return hits
```

- [ ] **Step 4: Chạy để thấy pass**

Run: `.venv\Scripts\python.exe scripts\test_retrieval.py`
Expected: `[PASS] truy van dung model + loc langcode`, `[PASS] min_similarity ...`, `OK`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/retrieval.py multiagent/scripts/test_retrieval.py
git commit -m "feat: retrieval truy van KB theo (content_type, langcode) + nguong similarity"
```

---

## Task 6: Module fact-check `fact_check.py` (CP3)

**Files:**
- Create: `multiagent/src/agents/fact_check.py`
- Create test: `scripts/test_fact_check.py`

**Interfaces:**
- Consumes: `ai_core.call_agent` (LLM), `retrieval.retrieve` (Task 5).
- Produces:
  - `run(fields, *, content_type="cam_nang", langcode="vi", extract_fn=_extract_claims, compare_fn=_compare, retriever=retrieve, embedder=None) -> list[dict]`
  - Mỗi flag: `{"field": str, "severity": "critical", "rule": "Thông tin sai lệch so với thông số công bố chính thức", "excerpt": str}` — **cùng shape** với flag blacklist trong `compliance.py` (để `run()` gộp thẳng).
- Ghi chú: `extract_fn`, `compare_fn`, `retriever` **inject được** để test không cần LLM/KB thật.

- [ ] **Step 1: Viết test — inject fakes, kiểm 3 nhánh (lệch → flag / không tra được → không flag / khác model → không flag)**

Create `scripts/test_fact_check.py`:

```python
"""Test logic fact_check (CP3) bang fake extract/compare/retriever - khong
goi LLM hay KB that. Kiem 3 nhanh quan trong:
  - so lieu lech (cung model) -> flag critical
  - khong tra duoc (retrieve rong) -> KHONG flag
  - thong so tra ve khac model -> compare tra 'unverifiable' -> KHONG flag
Chay: .venv\\Scripts\\python.exe scripts\\test_fact_check.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import fact_check

CLAIM_VF8 = {"model": "VF 8", "metric": "tam_hoat_dong", "value": "500km",
             "field": "body", "excerpt": "VF 8 chạy 500km"}


def test_mismatch_makes_critical_flag():
    flags = fact_check.run(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 8: 420km", "model": "VF 8", "score": 0.9, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "mismatch", "reason": "500 != 420"}],
    )
    assert len(flags) == 1, f"phai co 1 flag, got {len(flags)}"
    assert flags[0]["severity"] == "critical"
    assert flags[0]["field"] == "body"
    assert "sai lệch" in flags[0]["rule"].lower()
    print("[PASS] so lieu lech -> flag critical")


def test_not_found_no_flag():
    flags = fact_check.run(
        {"body": "Model XYZ chạy 999km"},
        extract_fn=lambda f: [{"model": "XYZ", "metric": "tam_hoat_dong",
                               "value": "999km", "field": "body", "excerpt": "XYZ 999km"}],
        retriever=lambda q, ct, lc, **k: [],  # khong tra duoc
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc goi compare khi khong co hit")),
    )
    assert flags == [], "khong tra duoc -> khong flag (muc 'khong kiem chung duoc')"
    print("[PASS] khong tra duoc -> khong flag")


def test_unverifiable_no_flag():
    flags = fact_check.run(
        {"body": "VF 8 chạy 500km"},
        extract_fn=lambda f: [CLAIM_VF8],
        retriever=lambda q, ct, lc, **k: [{"text": "VF 9: 438km", "model": "VF 9", "score": 0.6, "source_url": "u"}],
        compare_fn=lambda pairs: [{"index": 0, "verdict": "unverifiable", "reason": "thong so la VF 9, khong phai VF 8"}],
    )
    assert flags == [], "khac model -> unverifiable -> khong flag"
    print("[PASS] khac model -> unverifiable -> khong flag")


def test_no_claims_no_llm():
    flags = fact_check.run(
        {"body": "bài không có số liệu"},
        extract_fn=lambda f: [],
        retriever=lambda *a, **k: (_ for _ in ()).throw(AssertionError("khong duoc retrieve khi khong co claim")),
        compare_fn=lambda pairs: (_ for _ in ()).throw(AssertionError("khong duoc compare")),
    )
    assert flags == [], "khong co claim -> khong flag, khong goi retrieve/compare"
    print("[PASS] khong co claim -> dung som")


if __name__ == "__main__":
    test_mismatch_makes_critical_flag()
    test_not_found_no_flag()
    test_unverifiable_no_flag()
    test_no_claims_no_llm()
    print("OK")
```

- [ ] **Step 2: Chạy để thấy fail**

Run: `.venv\Scripts\python.exe scripts\test_fact_check.py`
Expected: FAIL (`ImportError: cannot import name 'fact_check'`).

- [ ] **Step 3: Viết `fact_check.py`**

Create `multiagent/src/agents/fact_check.py`:

```python
"""CP3 - RAG fact-check: đối chiếu claim định lượng trong bài với thông số
VinFast công bố công khai (docs/architecture.md mục 5.4, docs/rubrics.md CP3).

Là nguồn flag THỨ 3 của Compliance Agent (bên cạnh LLM tự do + blacklist).
Luồng: trích claim định lượng (LLM) -> truy vấn KB -> so sánh (LLM) -> lệch
thì sinh flag critical (mã A3).

AN TOÀN (quan trọng nhất): claim KHÔNG tra được, hoặc thông số tra về thuộc
MODEL KHÁC -> KHÔNG sinh flag. KB chỉ có thông số một số model; "không tra
được" != "sai" (docs/rubrics.md mục 6.2). Coi nó là sai sẽ chặn oan mọi bài
nhắc model ngoài KB. Hai lớp chặn: (1) retrieve rỗng -> bỏ qua claim;
(2) compare LLM chỉ trả 'mismatch' khi CÙNG model và số mâu thuẫn, còn lại
trả 'unverifiable'.
"""
from ai_core import call_agent
from retrieval import retrieve

_RULE = "Thông tin sai lệch so với thông số công bố chính thức"

_EXTRACT_PROMPT = (
    "Bạn trích các CLAIM ĐỊNH LƯỢNG có thể kiểm chứng bằng thông số kỹ thuật "
    "xe điện VinFast từ nội dung. Chỉ trích claim gắn với một model cụ thể và "
    "một con số kiểm chứng được: tầm hoạt động/quãng đường (km), thời gian sạc, "
    "dung lượng pin, giá, chu kỳ bảo dưỡng. KHÔNG trích câu chung chung không "
    "có số. Với mỗi claim, ghi: model (ví dụ 'VF 8'), metric, value (nguyên "
    "văn con số), field chứa nó (title/body/meta_description), và excerpt "
    "(trích nguyên văn cụm chứa claim). Nếu không có claim định lượng nào, "
    "trả mảng rỗng. Trả lời bằng tiếng Việt."
)

_EXTRACT_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "model": {"type": "string"},
                    "metric": {
                        "type": "string",
                        "enum": ["tam_hoat_dong", "thoi_gian_sac", "pin", "gia", "bao_duong", "khac"],
                    },
                    "value": {"type": "string"},
                    "field": {"type": "string", "enum": ["title", "body", "meta_description"]},
                    "excerpt": {"type": "string"},
                },
                "required": ["model", "metric", "value", "field", "excerpt"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["claims"],
    "additionalProperties": False,
}

_COMPARE_PROMPT = (
    "Bạn đối chiếu từng claim với đoạn thông số công bố tra được. Với mỗi mục "
    "đánh số, trả verdict:\n"
    "- 'mismatch' CHỈ KHI đoạn thông số rõ ràng là của ĐÚNG model trong claim "
    "VÀ con số trong claim MÂU THUẪN với con số công bố.\n"
    "- 'match' khi cùng model và con số khớp.\n"
    "- 'unverifiable' khi đoạn thông số thuộc MODEL KHÁC, không đủ dữ kiện, "
    "hoặc không chắc. Khi nghi ngờ luôn chọn 'unverifiable', TUYỆT ĐỐI không "
    "chọn 'mismatch'.\n"
    "Trả lời bằng tiếng Việt trong trường reason."
)

_COMPARE_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["match", "mismatch", "unverifiable"]},
                    "reason": {"type": "string"},
                },
                "required": ["index", "verdict", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def _extract_claims(fields: dict) -> list[dict]:
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}"
    )
    return call_agent(_EXTRACT_PROMPT, content, _EXTRACT_SCHEMA)["claims"]


def _compare(pairs: list[tuple]) -> list[dict]:
    """pairs: list of (claim, hit). Gộp thành 1 lần gọi LLM."""
    lines = []
    for i, (claim, hit) in enumerate(pairs):
        lines.append(
            f"[{i}] Claim: model={claim['model']}, {claim['metric']}={claim['value']}\n"
            f"    Thông số tra được (model {hit['model']}): {hit['text']}"
        )
    return call_agent(_COMPARE_PROMPT, "\n\n".join(lines), _COMPARE_SCHEMA)["verdicts"]


def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi",
        extract_fn=_extract_claims, compare_fn=_compare, retriever=retrieve,
        embedder=None) -> list[dict]:
    claims = extract_fn(fields)
    if not claims:
        return []

    pairs = []  # (claim, hit) - chỉ giữ claim tra được thông số
    for claim in claims:
        query = f"{claim['model']} {claim['metric']}"
        hits = retriever(query, content_type, langcode, embedder=embedder)
        if hits:
            pairs.append((claim, hits[0]))
    if not pairs:
        return []

    verdicts = compare_fn(pairs)
    flags = []
    for v in verdicts:
        if v.get("verdict") != "mismatch":
            continue
        claim = pairs[v["index"]][0]
        flags.append(
            {
                "field": claim["field"],
                "severity": "critical",
                "rule": _RULE,
                "excerpt": claim["excerpt"],
            }
        )
    return flags
```

- [ ] **Step 4: Chạy để thấy pass**

Run: `.venv\Scripts\python.exe scripts\test_fact_check.py`
Expected: 4 dòng `[PASS]` + `OK`.

- [ ] **Step 5: Commit**

```bash
git add multiagent/src/agents/fact_check.py multiagent/scripts/test_fact_check.py
git commit -m "feat: CP3 fact_check - trich claim + doi chieu KB, khong tra duoc thi khong flag"
```

---

## Task 7: Gộp fact-check vào Compliance Agent

**Files:**
- Modify: `multiagent/src/agents/compliance.py` (hàm `run()`)
- Modify: `scripts/smoke_test_compliance.py`

**Interfaces:**
- Consumes: `fact_check.run` (Task 6).
- Produces: `compliance.run(fields, *, content_type="cam_nang", langcode="vi")` — flags giờ gồm 3 nguồn: LLM + blacklist + fact-check.

- [ ] **Step 1: Viết test — fact-check flag được gộp; lỗi KB không làm sập compliance**

Create `scripts/test_compliance_factcheck_merge.py`:

```python
"""Test compliance.run() gop flag fact-check dung, va khi fact_check loi
(KB chua dung) thi KHONG lam sap compliance. Monkeypatch fact_check + LLM
de khong goi API/KB that.
Chay: .venv\\Scripts\\python.exe scripts\\test_compliance_factcheck_merge.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import compliance, fact_check
import ai_core

# Stub LLM cua compliance: khong flag LLM, score 100
ai_core_call_original = ai_core.call_agent
compliance.call_agent = lambda *a, **k: {"score": 100, "flags": []}


def test_factcheck_flag_merged():
    fact_check.run = lambda fields, **k: [
        {"field": "body", "severity": "critical", "rule": "Thông tin sai lệch so với thông số công bố chính thức", "excerpt": "VF 8 chạy 500km"}
    ]
    # ket noi lai tham chieu ma compliance dung
    compliance.fact_check = fact_check
    result = compliance.run({"title": "", "body": "VF 8 chạy 500km", "meta_description": ""})
    fc = [f for f in result["flags"] if "sai lệch" in f["rule"].lower()]
    assert len(fc) == 1, f"flag fact-check phai duoc gop, got {result['flags']}"
    print("[PASS] flag fact-check duoc gop vao compliance")


def test_factcheck_error_does_not_break():
    def boom(fields, **k):
        raise RuntimeError("KB chua dung")

    compliance.fact_check.run = boom
    result = compliance.run({"title": "", "body": "abc", "meta_description": ""})
    assert isinstance(result["flags"], list), "loi fact-check khong duoc lam sap run()"
    print("[PASS] loi fact-check khong lam sap compliance")


if __name__ == "__main__":
    test_factcheck_flag_merged()
    test_factcheck_error_does_not_break()
    print("OK")
```

- [ ] **Step 2: Chạy để thấy fail**

Run: `.venv\Scripts\python.exe scripts\test_compliance_factcheck_merge.py`
Expected: FAIL (`compliance.run()` chưa nhận `content_type`/chưa gọi fact-check; `AttributeError` hoặc flag không được gộp).

- [ ] **Step 3: Sửa `compliance.py` — import + gọi fact-check trong `run()`**

Trong `multiagent/src/agents/compliance.py`:

Thêm import (cạnh `from ai_core import call_agent`):

```python
from agents import fact_check
```

Sửa hàm `run()` (cuối file) — thay:

```python
def run(fields: dict) -> dict:
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}"
    )
    llm_result = call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)

    # Rule-based: quét từng field riêng để gắn đúng field vào flag
    rule_flags = []
    for field_name in _RULE_FIELDS:
        for flag in match_blacklist(fields.get(field_name, "")):
            flag["field"] = field_name
            rule_flags.append(flag)

    return {
        "score": llm_result["score"],
        "flags": llm_result["flags"] + rule_flags,
    }
```

thành:

```python
def run(fields: dict, *, content_type: str = "cam_nang", langcode: str = "vi") -> dict:
    content = (
        f"[title] {fields.get('title', '')}\n\n"
        f"[body] {fields.get('body', '')}\n\n"
        f"[meta_description] {fields.get('meta_description', '')}"
    )
    llm_result = call_agent(SYSTEM_PROMPT, content, OUTPUT_SCHEMA)

    # Rule-based: quét từng field riêng để gắn đúng field vào flag
    rule_flags = []
    for field_name in _RULE_FIELDS:
        for flag in match_blacklist(fields.get(field_name, "")):
            flag["field"] = field_name
            rule_flags.append(flag)

    # Nguồn thứ 3: RAG fact-check (CP3). Bọc try/except vì KB có thể chưa
    # dựng (chạy src/kb/build_kb.py) - khi đó fact-check bỏ qua, KHÔNG làm
    # sập cả Compliance Agent.
    try:
        fact_check_flags = fact_check.run(fields, content_type=content_type, langcode=langcode)
    except Exception:
        fact_check_flags = []

    return {
        "score": llm_result["score"],
        "flags": llm_result["flags"] + rule_flags + fact_check_flags,
    }
```

- [ ] **Step 4: Chạy để thấy pass**

Run: `.venv\Scripts\python.exe scripts\test_compliance_factcheck_merge.py`
Expected: `[PASS] flag fact-check duoc gop ...`, `[PASS] loi fact-check ...`, `OK`.

- [ ] **Step 5: Chạy lại test blacklist cũ để chắc không hồi quy**

Run: `.venv\Scripts\python.exe scripts\test_compliance_rules.py`
Expected: tất cả `[PASS]` (không đổi hành vi blacklist).

- [ ] **Step 6: Commit**

```bash
git add multiagent/src/agents/compliance.py multiagent/scripts/test_compliance_factcheck_merge.py
git commit -m "feat: gop CP3 fact-check vao Compliance run() nhu nguon flag thu 3"
```

---

## Task 8: Bộ eval retrieval E2 (recall@k)

**Files:**
- Create: `scripts/retrieval_eval_pairs.json`
- Create: `scripts/eval_retrieval.py`

**Interfaces:**
- Consumes: KB đã dựng (Task 4), `retrieval.retrieve` + BGE-M3 thật.
- Produces: script in recall@1 và recall@3, so với tiêu chí recall@3 ≥ 0.9 (`docs/evaluation-plan.md` mục 4.2).

- [ ] **Step 1: Tạo bộ cặp (truy vấn, model đúng)**

Create `multiagent/scripts/retrieval_eval_pairs.json`:

```json
[
  {"query": "VF 8 đi được bao nhiêu km một lần sạc", "expected_model": "VF 8"},
  {"query": "tầm hoạt động VF 8", "expected_model": "VF 8"},
  {"query": "VF 8 chạy được bao xa", "expected_model": "VF 8"},
  {"query": "VF 9 quãng đường tối đa", "expected_model": "VF 9"},
  {"query": "VF 9 đi được bao nhiêu km", "expected_model": "VF 9"},
  {"query": "phạm vi di chuyển VF 9", "expected_model": "VF 9"},
  {"query": "VF 5 tầm hoạt động theo NEDC", "expected_model": "VF 5"},
  {"query": "VF 5 chạy bao nhiêu km", "expected_model": "VF 5"},
  {"query": "quãng đường một lần sạc VF 5", "expected_model": "VF 5"},
  {"query": "chu kỳ bảo dưỡng định kỳ xe điện", "expected_model": "Bảo dưỡng định kỳ"},
  {"query": "bao lâu bảo dưỡng xe một lần", "expected_model": "Bảo dưỡng định kỳ"},
  {"query": "bao nhiêu km thì bảo dưỡng", "expected_model": "Bảo dưỡng định kỳ"}
]
```

- [ ] **Step 2: Viết script eval**

Create `multiagent/scripts/eval_retrieval.py`:

```python
"""E2 - do recall@k cua KB fact-check (docs/evaluation-plan.md muc 4.2,
docs/rag-design.md muc 5). Can KB da dung: chay src/kb/build_kb.py truoc.

recall@k = ti le truy van co model dung nam trong top-k.
Tieu chi: recall@3 >= 0.9 (KB fact-check noi vao quyen phu quyet).
Chay: .venv\\Scripts\\python.exe scripts\\eval_retrieval.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from retrieval import retrieve

PAIRS = os.path.join(os.path.dirname(__file__), "retrieval_eval_pairs.json")


def recall_at_k(pairs, k):
    hit = 0
    for p in pairs:
        results = retrieve(p["query"], "cam_nang", "vi", top_k=k)
        models = [r["model"] for r in results]
        if p["expected_model"] in models:
            hit += 1
        else:
            print(f"  MISS@{k}: '{p['query']}' -> {models} (mong doi {p['expected_model']})")
    return hit / len(pairs)


if __name__ == "__main__":
    with open(PAIRS, encoding="utf-8") as f:
        pairs = json.load(f)

    r1 = recall_at_k(pairs, 1)
    r3 = recall_at_k(pairs, 3)
    print(f"\nrecall@1 = {r1:.2f}")
    print(f"recall@3 = {r3:.2f}  (tieu chi >= 0.90)")
    print("DAT" if r3 >= 0.9 else "CHUA DAT - sua chunking truoc, doi embedding sau (rag-design muc 5)")
    sys.exit(0 if r3 >= 0.9 else 1)
```

- [ ] **Step 3: Chạy eval trên KB thật**

Run (sau khi đã `build_kb.py` ở Task 4): `.venv\Scripts\python.exe scripts\eval_retrieval.py`
Expected: in recall@1, recall@3. Ghi nhận con số. Nếu recall@3 < 0.9, đây là tín hiệu sửa chunking (không phải lỗi plan) — ghi vào báo cáo E2.

- [ ] **Step 4: Commit**

```bash
git add multiagent/scripts/retrieval_eval_pairs.json multiagent/scripts/eval_retrieval.py
git commit -m "test: bo eval E2 do recall@k cho KB fact-check"
```

---

## Task 9: Smoke test end-to-end + cập nhật tài liệu

**Files:**
- Modify: `scripts/smoke_test_compliance.py`
- Modify: `docs/rag-design.md` (mục 4.1)
- Modify: `docs/architecture.md` (mục 5.4, đoạn "Trạng thái hiện tại")
- Modify: `README.md` (Trạng thái Sprint 2)

**Interfaces:** (không tạo interface mới — verify + đồng bộ tài liệu.)

- [ ] **Step 1: Bổ sung smoke test — chạy compliance thật trên P-002a (claim VF 8 500km sai)**

Thêm vào cuối `scripts/smoke_test_compliance.py` (giữ nguyên phần cũ), một khối chạy trên nội dung có claim số liệu sai để xác nhận CP3 bắt được (cần KB đã dựng + API key):

```python
    # --- CP3 fact-check: claim VF 8 500km (cong bo that 420km) phai bi bat ---
    print("\n--- CP3 fact-check ---")
    fc_fields = {
        "title": "Đánh giá VF 8",
        "body": "Với một lần sạc đầy, VinFast VF 8 có thể đi tới 500km.",
        "meta_description": "",
    }
    fc_result = run(fc_fields)
    fc_flags = [f for f in fc_result["flags"] if "sai lệch" in f["rule"].lower()]
    print(f"fact-check flags: {fc_flags}")
    # Luu y: can chay src/kb/build_kb.py truoc. Neu KB chua dung, fact-check
    # bo qua (khong flag) - khi do in canh bao thay vi assert cung.
    if fc_flags:
        print("PASS: CP3 bat duoc claim VF 8 500km sai lech")
    else:
        print("LUU Y: khong co flag CP3 - kiem tra da chay build_kb.py chua, "
              "va so lieu KB da verify chua (sources.md muc 2)")
```

- [ ] **Step 2: Chạy smoke test end-to-end**

Run (cần `.env` có `ANTHROPIC_API_KEY` + đã `build_kb.py`): `.venv\Scripts\python.exe scripts\smoke_test_compliance.py`
Expected: phần blacklist cũ vẫn PASS; phần CP3 in flag bắt được claim VF 8 500km (hoặc LƯU Ý nếu KB chưa dựng).

- [ ] **Step 3: Cập nhật `docs/rag-design.md` mục 4.1 — đổi khuyến nghị sang BGE-M3 đa ngôn ngữ**

Trong `docs/rag-design.md`, mục 4.1, thay đoạn khuyến nghị "model tiếng Việt chạy local" bằng đoạn nêu **quyết định đã chốt**: dùng **BGE-M3 (đa ngôn ngữ, self-host)** thay vì model chuyên tiếng Việt, với lý do: (1) đổi model embedding buộc re-embed toàn bộ KB, nên chọn model đã sẵn sàng đa ngôn ngữ từ đầu để mở rộng ngôn ngữ (mục 4.2) không phải di trú; (2) self-host giữ dữ liệu trong hạ tầng (đúng bối cảnh VF O2O production); (3) con số cuối vẫn chốt bằng recall@k đo thật (mục 5), không theo leaderboard. Giữ lại ghi chú model chuyên tiếng Việt (`dangvantuan/...`) như phương án đối chiếu recall@k nếu còn thời gian.

- [ ] **Step 4: Cập nhật `docs/architecture.md` mục 5.4 — CP3 đã triển khai**

Trong `docs/architecture.md` mục 5.4, đoạn "Trạng thái hiện tại (Sprint 2)": sửa câu "Nguồn (3) RAG fact-check **chưa triển khai**" thành đã triển khai — ghi rõ: KB thông số (`src/kb/specs.json`, seed từ `sources.md` mục 2.1, `verified=false` chờ verify số thật), embedding BGE-M3 self-host, Chroma một collection lọc `(content_type, langcode)`, "không tra được / khác model → không flag critical". Nêu E2 recall@k là bước đo tiếp theo.

- [ ] **Step 5: Cập nhật `README.md` — Trạng thái Sprint 2**

Trong `README.md` mục "Trạng thái Sprint 2": đổi dòng Compliance Agent để phản ánh RAG fact-check (CP3) đã có; nếu có mục liệt kê "RAG fact-check chưa triển khai" thì bỏ/di chuyển. Thêm ghi chú KB cần verify số thật là task dữ liệu song song.

- [ ] **Step 6: Commit**

```bash
git add multiagent/scripts/smoke_test_compliance.py docs/rag-design.md docs/architecture.md README.md
git commit -m "docs: dong bo CP3 RAG fact-check da trien khai + smoke test end-to-end"
```

---

## Self-Review

**Spec coverage** (đối chiếu `docs/rag-design.md` + `architecture.md` 5.4 + `rubrics.md` CP3):
- KB fact-check chunk theo "một model xe" → Task 4 `chunk_text`. ✅
- Contextual Retrieval → Task 4 (bản tất định, prefix cố định; bản LLM ghi nhận là cải tiến sau). ✅
- Chroma + metadata filter `(content_type, langcode)` → Task 4/5. ✅
- Embedding đa ngôn ngữ self-host, tách sau interface → Task 3. ✅
- "Không tra được / khác model → mức 1, không flag critical" → Task 6 (2 lớp chặn) + test. ✅
- top-k=3, min_similarity chốt từ E2 → Task 5 (mặc định None, tham số hoá). ✅
- Nguồn flag thứ 3 gộp vào Compliance, không phá veto/Aggregator → Task 7. ✅
- E2 recall@k, tiêu chí ≥0.9 → Task 8. ✅
- Không phụ thuộc rubric rewrite / `state.py` content_type → mặc định `cam_nang`/`vi`, ghi chú rõ. ✅

**Placeholder scan:** không có TBD/TODO; mọi step có code thật hoặc lệnh chạy cụ thể.

**Type consistency:** `retrieve(...)` trả `list[{text,model,score,source_url}]` — dùng nhất quán ở Task 6 (`hits[0]["model"]`, `hit["text"]`) và Task 8 (`r["model"]`). `fact_check.run(...)` trả flag `{field,severity,rule,excerpt}` — khớp shape blacklist, gộp thẳng ở Task 7. `Embedder.embed` trả `list[list[float]]` — dùng nhất quán Task 4/5.

**Điểm cần người dùng làm song song (ngoài plan):** thu số liệu thật cho KB (`sources.md` mục 2, WAF chặn bot → thủ công), verify từng số, đổi `verified=true`. Trước khi verify, kết quả CP3 chỉ đáng tin ở mức seed.
