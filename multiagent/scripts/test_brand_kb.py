"""Test cat doan KB brand + tham so collection_name cua retrieval.

Dung embedder GIA va collection GIA - khong tai model 2GB, khong dung Chroma
that. Chay: .venv\\Scripts\\python.exe scripts\\test_brand_kb.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import retrieval
from kb.build_brand_kb import chunk_doc

DOC = {
    "sample_id": "B-001",
    "title": "Cách lái xe ô tô điện",
    "topic_group": "lai_xe_an_toan",
    "body": "<h2>Chuẩn bị</h2><p>Kiểm tra pin trước khi đi.</p><p>Đi số chậm.</p>",
}


def test_chunk_moi_doan_mot_chunk():
    chunks = chunk_doc(DOC)
    assert len(chunks) == 3, chunks      # 1 heading + 2 doan
    print("[PASS] moi doan mot chunk")


def test_chunk_co_prefix_ngu_canh():
    chunks = chunk_doc(DOC)
    assert all(DOC["title"] in c for c in chunks), chunks
    print("[PASS] moi chunk co cau ngu canh chua tieu de bai")


def test_chunk_bo_the_html():
    chunks = chunk_doc(DOC)
    assert not any("<p>" in c or "<h2>" in c for c in chunks), chunks
    print("[PASS] chunk khong con the HTML")


def test_chunk_bo_qua_doan_rong():
    doc = dict(DOC, body="<p>Có chữ.</p><p>   </p><p></p>")
    chunks = chunk_doc(doc)
    assert len(chunks) == 1, chunks
    print("[PASS] doan rong khong thanh chunk")


class _FakeCollection:
    def __init__(self):
        self.da_goi = None

    def query(self, **kwargs):
        self.da_goi = kwargs
        return {
            "documents": [["doan mau"]],
            "metadatas": [[{"sample_id": "B-001", "topic_group": "sac_pin"}]],
            "distances": [[0.1]],
        }


class _FakeEmbedder:
    def embed(self, texts):
        return [[0.0, 1.0] for _ in texts]


def test_retrieve_chay_voi_collection_tiem_vao():
    col = _FakeCollection()
    hits = retrieval.retrieve(
        "VF 8 tầm hoạt động", "cam_nang", "vi",
        embedder=_FakeEmbedder(), collection=col,
    )
    assert len(hits) == 1, hits
    assert hits[0]["text"] == "doan mau"
    print("[PASS] retrieve chay voi collection tiem vao")


def test_retrieve_tra_them_topic_group():
    """Task 9 (do E2) can topic_group de biet doan lay ve co cung chu de."""
    hits = retrieval.retrieve(
        "sạc pin", "cam_nang", "vi",
        embedder=_FakeEmbedder(), collection=_FakeCollection(),
    )
    assert hits[0]["topic_group"] == "sac_pin", hits
    print("[PASS] retrieve tra them topic_group")


def test_metadata_thieu_model_khong_lam_sap():
    """KB brand khong co khoa 'model' (chi KB fact-check moi co)."""
    hits = retrieval.retrieve(
        "sạc pin", "cam_nang", "vi",
        embedder=_FakeEmbedder(), collection=_FakeCollection(),
    )
    assert hits[0]["model"] == "", hits
    print("[PASS] metadata thieu 'model' -> chuoi rong, khong loi")


def test_hai_hang_so_collection_ton_tai():
    assert retrieval.COLLECTION_FACTCHECK == "kb_factcheck"
    assert retrieval.COLLECTION_BRAND == "kb_brand"
    print("[PASS] hai hang so collection deu co")


def test_mac_dinh_van_la_factcheck():
    """Doi ten hang so KHONG duoc lam doi hanh vi cua fact-check."""
    import inspect

    mac_dinh = inspect.signature(retrieval.retrieve).parameters["collection_name"].default
    assert mac_dinh == retrieval.COLLECTION_FACTCHECK, mac_dinh
    print("[PASS] mac dinh giu nguyen collection fact-check")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_chunk_moi_doan_mot_chunk,
        test_chunk_co_prefix_ngu_canh,
        test_chunk_bo_the_html,
        test_chunk_bo_qua_doan_rong,
        test_retrieve_chay_voi_collection_tiem_vao,
        test_retrieve_tra_them_topic_group,
        test_metadata_thieu_model_khong_lam_sap,
        test_hai_hang_so_collection_ton_tai,
        test_mac_dinh_van_la_factcheck,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
