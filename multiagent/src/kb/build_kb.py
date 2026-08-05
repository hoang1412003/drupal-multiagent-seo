"""Nap KB fact-check: specs.json -> chunk theo model -> embed -> Postgres.

Chay OFFLINE, KHONG nam trong pipeline cham (docs/rag-design.md muc 8).
Cat theo don vi "mot model xe" (muc 4.3): claim "VF 8 chay 420km" can dung
khoi thong so VF 8, cat theo ky tu se tach so khoi ten model -> retrieve nham.

specs.json van la NGUON SU THAT; bang kb_chunk chi la du lieu dan xuat, dung
lai duoc bat cu luc nao. Doi kho vector tu Chroma sang Postgres khong dung gi
den nguyen tac do.

Chay: .venv\\Scripts\\python.exe src\\kb\\build_kb.py
"""
import json
import os
import sys

_KB_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_KB_DIR)

# Them src/ vao path TRUOC khi import `db`. Phai o day chu khong o trong khoi
# `if __name__ == "__main__"` nhu ban cu: khoi do chay SAU cac import o dau
# file, nen chay truc tiep file nay se van te o dung dong `import db`. Ban cu
# thoat duoc vi no chi import `chromadb` (goi da cai) o dau file.
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

import db  # noqa: E402  (phai dung sau khoi sua sys.path o tren)

SPECS_PATH = os.path.join(_KB_DIR, "specs.json")
COLLECTION = "kb_factcheck"

_SQL_INSERT = (
    f"INSERT INTO {db.TEN_BANG} "
    "(collection, chunk_id, document, embedding, content_type, langcode, meta) "
    "VALUES (%s, %s, %s, %s::vector, %s, %s, %s::jsonb)"
)


def chunk_text(entry: dict) -> str:
    """Mot chunk cho mot model. Them cau ngu canh vao dau (Contextual
    Retrieval ban TAT DINH - docs/rag-design.md muc 4.3): chunk thong so tran
    dung mot minh gan nhu vo nghia voi retrieval, them ten model + nguon thi
    truy van 'VF 8 di bao nhieu km' khop han len. Dung prefix co dinh thay vi
    goi LLM de giu tat dinh + re; ban dung LLM la cai tien sau, do bang E2."""
    lines = [f"Đây là thông số VinFast {entry['model']} công bố trên vinfastauto.com:"]
    for key, value in entry["specs"].items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def chuan_bi_rows(entries: list[dict], embedder) -> list[tuple]:
    """entries -> cac dong san de INSERT. Ham THUAN, khong cham DB.

    Tach ra khoi build() de test dem duoc so chunk va kiem duoc noi dung ma
    KHONG can Postgres - giu dung tinh chat "test khong can ha tang" cua ca bo
    test trong du an.
    """
    docs = [chunk_text(e) for e in entries]
    vecs = embedder.embed(docs)
    return [
        (
            COLLECTION,
            f"{e['content_type']}:{e['langcode']}:{e['model']}",
            doc,
            db.vector_literal(vec),
            e["content_type"],
            e["langcode"],
            json.dumps(
                {
                    "model": e["model"],
                    "source_url": e.get("source_url", ""),
                    "verified": e.get("verified", False),
                },
                ensure_ascii=False,
            ),
        )
        for e, doc, vec in zip(entries, docs, vecs)
    ]


def build(specs_path: str = SPECS_PATH, conn=None, embedder=None) -> int:
    """Nap lai KB tu dau. Tra ve so chunk da nap."""
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    if conn is None:
        conn = db.get_conn()

    with open(specs_path, encoding="utf-8") as f:
        entries = json.load(f)

    rows = chuan_bi_rows(entries, embedder)
    db.dam_bao_bang(conn, embedder.dim)

    # XOA + CHEN trong CUNG mot giao dich. Ban Chroma lam hai buoc roi rac
    # (delete_collection roi create_collection), nen nap loi giua chung se de
    # lai KB RONG - va KB rong thi CP3/BV6 tra NA lang le, dung kieu hong am
    # tham ma du an tranh. O day loi bat ky se hoan nguyen ve KB cu.
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
    print(f"Da nap {n} chunk vao KB fact-check ({db.dsn()})")
