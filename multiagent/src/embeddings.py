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


_default: "Embedder | None" = None


def get_default_embedder() -> "Embedder":
    """Singleton lười - nạp model một lần cho cả process (polling worker phải
    gọi sớm lúc khởi động, không nạp lazy trong lần chấm đầu -
    docs/rag-design.md mục 6)."""
    global _default
    if _default is None:
        _default = BGEM3Embedder()
    return _default
