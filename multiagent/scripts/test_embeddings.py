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
