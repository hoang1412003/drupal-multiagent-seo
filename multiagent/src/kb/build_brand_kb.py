"""Nạp KB brand: corpus BRAND -> chunk theo đoạn -> embed -> Chroma.

Chạy OFFLINE, KHÔNG nằm trong pipeline chấm (docs/rag-design.md mục 8).

Cắt theo ĐOẠN, giữ nguyên câu (docs/rag-design.md mục 4.3) - khác KB
fact-check vốn cắt theo đơn vị "một model xe". Lý do: KB này dùng làm VÍ DỤ
GIỌNG VĂN, nên đơn vị tự nhiên là đoạn văn tác giả viết.

Giữ mọi đoạn, không lọc theo độ dài: bước bóc tách đã loại boilerplate
(menu, CTA, mục lục tự sinh) nên đoạn còn lại đều là chữ tác giả. Đặt ngưỡng
"đoạn phải dài hơn N câu" lúc này là thêm một số ảo; nếu eval_brand_retrieval
cho thấy nhiễu thì mới xử lý, khi đó có căn cứ.

Chạy (từ multiagent/):
    .venv\\Scripts\\python.exe src\\kb\\build_brand_kb.py
"""
import csv
import glob
import os
import re
import sys

import chromadb

_KB_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_KB_DIR)
REPO_ROOT = os.path.normpath(os.path.join(_SRC_DIR, "..", ".."))
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "brand", "corpus")
INDEX_CSV = os.path.join(REPO_ROOT, "docs", "brand", "corpus_index.csv")
CHROMA_PATH = os.path.join(_KB_DIR, "chroma")
COLLECTION = "kb_brand"

_KHOI = re.compile(
    r"<(?:p|h[1-6]|li|blockquote)[^>]*>(.*?)</(?:p|h[1-6]|li|blockquote)\s*>",
    re.DOTALL | re.IGNORECASE,
)


def chunk_doc(doc: dict) -> list[str]:
    """Một đoạn = một chunk, kèm câu ngữ cảnh cố định ở đầu.

    Câu ngữ cảnh dùng prefix TẤT ĐỊNH (không gọi LLM) - giống cách
    kb/build_kb.py làm cho KB fact-check. Đoạn văn trần đứng một mình khó
    truy vấn đúng chủ đề; thêm tiêu đề bài thì truy vấn theo chủ đề khớp hẳn
    lên (Contextual Retrieval bản tất định, docs/rag-design.md mục 4.3).
    """
    from text_utils import strip_html

    chunks = []
    for khoi in _KHOI.findall(doc["body"]):
        text = strip_html(khoi).strip()
        if text:
            chunks.append(f"Trích từ bài '{doc['title']}' trên vinfastauto.com:\n{text}")
    return chunks


def load_docs() -> list[dict]:
    """Đọc corpus + gắn topic_group từ corpus_index.csv (nguồn duy nhất)."""
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


def build(docs: "list[dict] | None" = None, chroma_path: str = CHROMA_PATH,
          embedder=None, content_type: str = "cam_nang", langcode: str = "vi") -> int:
    """Nạp lại KB từ đầu (xoá collection cũ để không lẫn đoạn cũ). Trả số
    chunk đã nạp."""
    if embedder is None:
        from embeddings import get_default_embedder

        embedder = get_default_embedder()
    if docs is None:
        docs = load_docs()

    ids, texts, metas = [], [], []
    for doc in docs:
        for i, chunk in enumerate(chunk_doc(doc)):
            ids.append(f"{doc['sample_id']}:{i}")
            texts.append(chunk)
            metas.append({
                "sample_id": doc["sample_id"],
                "topic_group": doc["topic_group"],
                "content_type": content_type,
                "langcode": langcode,
            })

    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection(COLLECTION)
    except Exception:
        pass      # chưa có -> bỏ qua
    col = client.create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})
    col.add(ids=ids, embeddings=embedder.embed(texts), documents=texts, metadatas=metas)
    return col.count()


if __name__ == "__main__":
    # Chạy trực tiếp: thêm src/ và scripts/ vào path để import được
    # text_utils, embeddings và label_helper.
    sys.path.insert(0, _SRC_DIR)
    sys.path.insert(0, os.path.join(REPO_ROOT, "multiagent", "scripts"))
    n = build()
    print(f"Da nap {n} chunk vao KB brand ({CHROMA_PATH})")
