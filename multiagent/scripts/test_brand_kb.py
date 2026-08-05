"""Test cat doan KB brand + tham so collection_name cua retrieval.

Dung embedder GIA va ket noi GIA - khong tai model 2GB, khong can Postgres
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


class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        pass

    def fetchall(self):
        return self._rows


class _FakeConn:
    """Ket noi Postgres gia. Doi tu _FakeCollection (Chroma) ngay 2026-08-05."""

    _ROWS = [("doan mau", {"sample_id": "B-001", "topic_group": "sac_pin"}, 0.9)]

    def cursor(self):
        return _FakeCursor(self._ROWS)


class _FakeEmbedder:
    def embed(self, texts):
        return [[0.0, 1.0] for _ in texts]


def test_retrieve_chay_voi_conn_tiem_vao():
    hits = retrieval.retrieve(
        "VF 8 tầm hoạt động", "cam_nang", "vi",
        embedder=_FakeEmbedder(), conn=_FakeConn(),
    )
    assert len(hits) == 1, hits
    assert hits[0]["text"] == "doan mau"
    print("[PASS] retrieve chay voi conn tiem vao")


def test_retrieve_tra_them_topic_group():
    """Task 9 (do E2) can topic_group de biet doan lay ve co cung chu de."""
    hits = retrieval.retrieve(
        "sạc pin", "cam_nang", "vi",
        embedder=_FakeEmbedder(), conn=_FakeConn(),
    )
    assert hits[0]["topic_group"] == "sac_pin", hits
    print("[PASS] retrieve tra them topic_group")


def test_metadata_thieu_model_khong_lam_sap():
    """KB brand khong co khoa 'model' (chi KB fact-check moi co)."""
    hits = retrieval.retrieve(
        "sạc pin", "cam_nang", "vi",
        embedder=_FakeEmbedder(), conn=_FakeConn(),
    )
    assert hits[0]["model"] == "", hits
    print("[PASS] metadata thieu 'model' -> chuoi rong, khong loi")


def test_chuan_bi_rows_moi_doan_mot_dong():
    """chunk_doc -> chuan_bi_rows giu dung so doan, va gan dung topic_group."""
    from kb.build_brand_kb import chuan_bi_rows

    rows = chuan_bi_rows([DOC], _FakeEmbedder())
    assert len(rows) == 3, rows
    collection, cid, _doc, _vec, content_type, langcode, meta = rows[0]
    assert collection == "kb_brand", collection
    assert cid.startswith("B-001:"), cid
    assert content_type == "cam_nang" and langcode == "vi", (content_type, langcode)
    assert "lai_xe_an_toan" in meta, meta
    print("[PASS] chuan_bi_rows: moi doan mot dong, co topic_group")


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
        test_chuan_bi_rows_moi_doan_mot_dong,
        test_retrieve_chay_voi_conn_tiem_vao,
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
