"""Test retrieval: dung Chroma tam + FakeEmbedder. Kiem loc (content_type,
langcode), top_k, va truy van dung model. Khong tai model that.
Chay: .venv\\Scripts\\python.exe scripts\\test_retrieval.py
"""
import os
import shutil
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
    d = tempfile.mkdtemp()
    try:
        col, emb = _make_collection(d)
        hits = retrieve("VF 8", "cam_nang", "vi", embedder=emb, collection=col)
        assert hits, "phai co ket qua"
        assert hits[0]["model"] == "VF 8", f"top1 phai la VF 8, got {hits[0]['model']}"
        # loc langcode: khong duoc tra ban tieng Anh (en:vf8)
        assert all(h["source_url"] != "u3" for h in hits), "khong duoc tra ban langcode khac"
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("[PASS] truy van dung model + loc langcode")


def test_min_similarity_filters():
    d = tempfile.mkdtemp()
    try:
        col, emb = _make_collection(d)
        # truy van khong khop token nao -> vector [1,0,0,0], similarity thap
        hits = retrieve("xe tay ga", "cam_nang", "vi", embedder=emb,
                        collection=col, min_similarity=0.99)
        assert hits == [], "duoi nguong similarity phai loc het"
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("[PASS] min_similarity loc ket qua duoi nguong")


def test_client_tach_theo_chroma_path():
    """`_get_collection(..., chroma_path=...)` phai mo dung KB duoc chi.

    Ban cu cache PersistentClient vao mot bien global va BO QUA `chroma_path`,
    nen lan goi thu hai voi thu muc khac van tra collection cua KB dau tien.
    Cung loai bay voi config._nap_file."""
    import chromadb

    from retrieval import _get_collection

    d1, d2 = tempfile.mkdtemp(), tempfile.mkdtemp()
    try:
        for d, ten in ((d1, "kb_mot"), (d2, "kb_hai")):
            chromadb.PersistentClient(path=d).create_collection(ten)

        assert _get_collection("kb_mot", chroma_path=d1).name == "kb_mot"
        # KB thu hai: neu client bi cache theo KB dau thi day se ném exception
        # "collection kb_hai does not exist".
        assert _get_collection("kb_hai", chroma_path=d2).name == "kb_hai"
    finally:
        shutil.rmtree(d1, ignore_errors=True)
        shutil.rmtree(d2, ignore_errors=True)
    print("[PASS] client tach theo chroma_path, khong lan giua hai KB")


if __name__ == "__main__":
    test_retrieves_right_model_and_lang()
    test_min_similarity_filters()
    test_client_tach_theo_chroma_path()
    print("OK")
