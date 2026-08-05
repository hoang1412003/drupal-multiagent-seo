"""Truy van KB theo (content_type, langcode). Kho vector: Postgres + pgvector.

Tra top-k chunk kem diem similarity; duoi nguong min_similarity -> loai (ket
qua co the RONG). Rong nghia la "khong tra duoc" -> CP3 muc 1, KHONG phai
muc 0 (docs/rag-design.md muc 4.4, docs/rubrics.md muc 6.2).

min_similarity mac dinh None (chua chot) - chot tu bo eval E2
(docs/evaluation-plan.md muc 4.2).

DOI TU CHROMA SANG PGVECTOR (2026-08-05). Chu ky ham va hinh dang ket qua tra
ve GIU NGUYEN, nen 4 agent khong biet ben duoi la gi - do dung la vai tro cua
cai seam nay. Ba diem khac biet ve hanh vi, deu theo huong tot hon:

  1. `ORDER BY embedding <=> ...` khong dung index nao (xem db.dam_bao_bang),
     tuc lang gieng gan nhat CHINH XAC, khong phai xap xi HNSW nhu Chroma.
  2. Loc (content_type, langcode) thanh menh de WHERE thuong, thay cho cu phap
     `where={"$and": [...]}`.
  3. Loc min_similarity van lam O PHIA PYTHON sau khi lay top_k, GIU Y NGUYEN
     thu tu cu - de con so E2 do lai so sanh duoc voi ban Chroma. Day khong
     phai cho de "toi uu" lai: doi sang loc trong SQL se lam top_k va nguong
     tac dong lan nhau theo kieu khac, tuc doi ca phep do.
"""
import db

# Hai KB, hai collection. Gio la hai gia tri trong cot `collection` cua cung
# mot bang, thay vi hai collection Chroma - nho vay trang quan ly sau nay dem
# duoc ca hai bang mot cau SELECT.
COLLECTION_FACTCHECK = "kb_factcheck"
COLLECTION_BRAND = "kb_brand"

_SQL = (
    "SELECT document, meta, 1 - (embedding <=> %s::vector) AS similarity "
    f"FROM {db.TEN_BANG} "
    "WHERE collection = %s AND content_type = %s AND langcode = %s "
    "ORDER BY embedding <=> %s::vector "
    "LIMIT %s"
)


def retrieve(query: str, content_type: str, langcode: str, *, top_k: int = 3,
             min_similarity: "float | None" = None, embedder=None,
             conn=None,
             collection_name: str = COLLECTION_FACTCHECK) -> list[dict]:
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    if conn is None:
        conn = db.get_conn()

    qvec = db.vector_literal(embedder.embed([query])[0])

    with conn.cursor() as cur:
        cur.execute(_SQL, (qvec, collection_name, content_type, langcode, qvec, top_k))
        rows = cur.fetchall()

    hits = []
    for document, meta, similarity in rows:
        if min_similarity is not None and similarity < min_similarity:
            continue
        meta = meta or {}
        hits.append(
            {
                "text": document,
                # Doc phong thu: KB brand khong co khoa "model" (chi KB
                # fact-check moi cat theo don vi model xe), va nguoc lai KB
                # fact-check khong co "topic_group".
                "model": meta.get("model", ""),
                "topic_group": meta.get("topic_group", ""),
                "score": similarity,
                "source_url": meta.get("source_url", ""),
            }
        )
    return hits
