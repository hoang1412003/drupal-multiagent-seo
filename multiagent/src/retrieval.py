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

# Hai KB, hai collection. Đổi tên từ COLLECTION (bản một collection) vì tên
# trần không còn nghĩa xác định khi có hai cái.
COLLECTION_FACTCHECK = "kb_factcheck"
COLLECTION_BRAND = "kb_brand"

# Cache khoá theo ĐƯỜNG DẪN, cùng lý do với config._cache: bản cũ giữ một
# client duy nhất và bỏ qua `chroma_path`, nên KB thứ hai mở ra vẫn là KB thứ
# nhất.
_clients: dict = {}


def _get_collection(collection_name: str, chroma_path: str = _CHROMA_PATH):
    if chroma_path not in _clients:
        _clients[chroma_path] = chromadb.PersistentClient(path=chroma_path)
    return _clients[chroma_path].get_collection(collection_name)


def retrieve(query: str, content_type: str, langcode: str, *, top_k: int = 3,
             min_similarity: "float | None" = None, embedder=None,
             collection=None,
             collection_name: str = COLLECTION_FACTCHECK) -> list[dict]:
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    col = collection if collection is not None else _get_collection(collection_name)

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
                # Đọc phòng thủ: KB brand không có khoá "model" (chỉ KB
                # fact-check mới cắt theo đơn vị model xe), và ngược lại KB
                # fact-check không có "topic_group".
                "model": meta.get("model", ""),
                "topic_group": meta.get("topic_group", ""),
                "score": similarity,
                "source_url": meta.get("source_url", ""),
            }
        )
    return hits
