"""Nap KB brand: corpus BRAND -> chunk theo doan -> embed -> Postgres.

Chay OFFLINE, KHONG nam trong pipeline cham (docs/rag-design.md muc 8).

Cat theo DOAN, giu nguyen cau (docs/rag-design.md muc 4.3) - khac KB
fact-check von cat theo don vi "mot model xe". Ly do: KB nay dung lam VI DU
GIONG VAN, nen don vi tu nhien la doan van tac gia viet.

Giu moi doan, khong loc theo do dai: buoc boc tach da loai boilerplate
(menu, CTA, muc luc tu sinh) nen doan con lai deu la chu tac gia. Dat nguong
"doan phai dai hon N cau" luc nay la them mot so ao; neu eval_brand_retrieval
cho thay nhieu thi moi xu ly, khi do co can cu.

Chay (tu multiagent/):
    .venv\\Scripts\\python.exe src\\kb\\build_brand_kb.py
"""
import csv
import glob
import json
import os
import re
import sys

_KB_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_KB_DIR)
REPO_ROOT = os.path.normpath(os.path.join(_SRC_DIR, "..", ".."))

# Them src/ va scripts/ vao path TRUOC cac import cua du an (`db` o src/,
# `label_helper` o scripts/). Phai o day chu khong o trong khoi __main__:
# khoi do chay sau cac import o dau file.
for _p in (_SRC_DIR, os.path.join(REPO_ROOT, "multiagent", "scripts")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import db  # noqa: E402  (phai dung sau khoi sua sys.path o tren)

CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "brand", "corpus")
INDEX_CSV = os.path.join(REPO_ROOT, "docs", "brand", "corpus_index.csv")
COLLECTION = "kb_brand"

_KHOI = re.compile(
    r"<(?:p|h[1-6]|li|blockquote)[^>]*>(.*?)</(?:p|h[1-6]|li|blockquote)\s*>",
    re.DOTALL | re.IGNORECASE,
)

_SQL_INSERT = (
    f"INSERT INTO {db.TEN_BANG} "
    "(collection, chunk_id, document, embedding, content_type, langcode, meta) "
    "VALUES (%s, %s, %s, %s::vector, %s, %s, %s::jsonb)"
)


def chunk_doc(doc: dict) -> list[str]:
    """Mot doan = mot chunk, kem cau ngu canh co dinh o dau.

    Cau ngu canh dung prefix TAT DINH (khong goi LLM) - giong cach
    kb/build_kb.py lam cho KB fact-check. Doan van tran dung mot minh kho
    truy van dung chu de; them tieu de bai thi truy van theo chu de khop han
    len (Contextual Retrieval ban tat dinh, docs/rag-design.md muc 4.3).
    """
    from text_utils import strip_html

    chunks = []
    for khoi in _KHOI.findall(doc["body"]):
        text = strip_html(khoi).strip()
        if text:
            chunks.append(f"Trích từ bài '{doc['title']}' trên vinfastauto.com:\n{text}")
    return chunks


def load_docs() -> list[dict]:
    """Doc corpus + gan topic_group tu corpus_index.csv (nguon duy nhat)."""
    from label_helper import parse_sample

    with open(INDEX_CSV, encoding="utf-8-sig") as f:
        nhom = {r["sample_id"]: r["topic_group"] for r in csv.DictReader(f)}

    docs = []
    for path in sorted(glob.glob(os.path.join(CORPUS_DIR, "*.txt"))):
        sample_id = os.path.splitext(os.path.basename(path))[0]
        fields = parse_sample(path)
        docs.append({
            "sample_id": sample_id,
            "title": fields.get("title", ""),
            "body": fields.get("body", ""),
            "topic_group": nhom.get(sample_id, ""),
        })
    return docs


def chuan_bi_rows(docs: list[dict], embedder, content_type: str = "cam_nang",
                  langcode: str = "vi") -> list[tuple]:
    """docs -> cac dong san de INSERT. Ham THUAN, khong cham DB.

    Tach ra khoi build() cung ly do voi build_kb.chuan_bi_rows: test dem duoc
    so chunk ma khong can Postgres.
    """
    ids, texts, metas = [], [], []
    for doc in docs:
        for i, chunk in enumerate(chunk_doc(doc)):
            ids.append(f"{doc['sample_id']}:{i}")
            texts.append(chunk)
            metas.append({"sample_id": doc["sample_id"],
                          "topic_group": doc["topic_group"]})

    vecs = embedder.embed(texts) if texts else []
    return [
        (COLLECTION, cid, text, db.vector_literal(vec), content_type, langcode,
         json.dumps(meta, ensure_ascii=False))
        for cid, text, vec, meta in zip(ids, texts, vecs, metas)
    ]


def build(docs: "list[dict] | None" = None, conn=None, embedder=None,
          content_type: str = "cam_nang", langcode: str = "vi") -> int:
    """Nap lai KB tu dau. Tra so chunk da nap."""
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    if conn is None:
        conn = db.get_conn()
    if docs is None:
        docs = load_docs()

    rows = chuan_bi_rows(docs, embedder, content_type, langcode)
    db.dam_bao_bang(conn, embedder.dim)

    # Xoa + chen trong CUNG mot giao dich - xem ly do o build_kb.build().
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(f"DELETE FROM {db.TEN_BANG} WHERE collection = %s", (COLLECTION,))
            cur.executemany(_SQL_INSERT, rows)

    with conn.cursor() as cur:
        cur.execute(
            f"SELECT count(*) FROM {db.TEN_BANG} WHERE collection = %s", (COLLECTION,)
        )
        return cur.fetchone()[0]


if __name__ == "__main__":
    n = build()
    print(f"Da nap {n} chunk vao KB brand ({db.dsn()})")
