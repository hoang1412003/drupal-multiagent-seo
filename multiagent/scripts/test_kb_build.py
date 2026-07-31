"""Test build_kb: nap specs.json vao Chroma tam bang FakeEmbedder (khong
tai model that). Chay: .venv\\Scripts\\python.exe scripts\\test_kb_build.py
"""
import os
import shutil
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
    # mkdtemp + rmtree(ignore_errors) thay cho TemporaryDirectory: tren Windows
    # Chroma giu file handle nen auto-cleanup nem PermissionError luc thoat.
    d = tempfile.mkdtemp()
    try:
        n = build_kb.build(chroma_path=d, embedder=FakeEmbedder())
        assert n == 4, f"phai nap 4 chunk (seed), thuc te {n}"
    finally:
        shutil.rmtree(d, ignore_errors=True)
    print("[PASS] build nap dung so chunk")


if __name__ == "__main__":
    test_chunk_has_model_context()
    test_build_counts()
    print("OK")
