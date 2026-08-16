"""Interface embedding + hiện thực BGE-M3, chạy local hoặc qua HuggingFace Space.

Tách sau interface Embedder để đổi model chỉ là thay 1 class
(docs/rag-design.md mục 4.1). Chọn model ĐA NGÔN NGỮ (BGE-M3) thay vì model
chuyên tiếng Việt để KB không phải nhúng lại khi mở rộng ngôn ngữ - đổi model
embedding buộc re-embed toàn bộ KB (docs/rag-design.md mục 4.2).
"""
import json
import os
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
    cosine (toán tử `<=>` của pgvector)."""

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


class RemoteEmbedder:
    """BGE-M3 chạy trên HuggingFace Space (Gradio), gọi qua HTTP thay vì nạp
    model ~2GB local - dùng cho server nhỏ (vd EC2 t3.micro 1GB RAM). Space
    phải encode + normalize_embeddings=True giống hệt BGEM3Embedder để không
    lệch công thức cosine (docs/rag-design.md mục 4.1)."""

    _DIM = 1024  # BGE-M3 cố định 1024 chiều (scripts/test_embeddings.py)

    def __init__(self, space_url: str, token: str):
        from gradio_client import Client

        self._client = Client(space_url)
        self._token = token

    def embed(self, texts: list[str]) -> list[list[float]]:
        result = self._client.predict(json.dumps(texts), self._token, api_name="/embed")
        return json.loads(result)

    @property
    def dim(self) -> int:
        return self._DIM


_default: "Embedder | None" = None


def get_default_embedder() -> "Embedder":
    """Singleton lười - nạp model một lần cho cả process (polling worker phải
    gọi sớm lúc khởi động, không nạp lazy trong lần chấm đầu -
    docs/rag-design.md mục 6).

    Đặt EMBEDDING_SPACE_URL để dùng RemoteEmbedder (HuggingFace Space) thay vì
    nạp BGE-M3 local - tránh cài torch/sentence-transformers trên server nhỏ.
    """
    global _default
    if _default is None:
        space_url = os.environ.get("EMBEDDING_SPACE_URL")
        if space_url:
            token = os.environ.get("EMBEDDING_API_TOKEN", "")
            _default = RemoteEmbedder(space_url, token)
        else:
            _default = BGEM3Embedder()
    return _default
