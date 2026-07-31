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
    # Chạy trực tiếp: thêm src/ vào path để import được 'embeddings' (khi
    # import qua 'from kb import build_kb' thì caller đã thêm src/ sẵn).
    import sys

    sys.path.insert(0, os.path.dirname(_KB_DIR))
    n = build()
    print(f"Đã nạp {n} chunk vào KB fact-check ({CHROMA_PATH})")
