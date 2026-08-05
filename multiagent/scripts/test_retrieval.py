"""Test retrieval tren Postgres + pgvector, dung ket noi GIA.

VI SAO KHONG DUNG POSTGRES THAT: ca bo test cua du an chay duoc "khong can API
key, khong can Drupal, khong can KB" (docs/pre-demo-checklist.md muc 5). Ban
Chroma giu duoc tinh chat do vi Chroma nhung duoc vao tien trinh; Postgres thi
khong. Neu de test doi mot server that thi ai clone repo ve cung khong chay
duoc test - mat dung thu dang gia nhat cua bo test nay.

Doi lai, tiem ket noi gia con do DUNG phan code cua minh (cau SQL, quy doi
distance -> similarity, loc nguong, doc metadata phong thu) thay vi do
Postgres co chay dung khong - Postgres thi khong can minh kiem.

Phan "chay that co ra dung khong" do bang scripts/eval_retrieval.py (E2).
Chay: .venv\\Scripts\\python.exe scripts\\test_retrieval.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import db
import retrieval
from retrieval import retrieve


class _FakeCursor:
    def __init__(self, rows, nhat_ky):
        self._rows = rows
        self._nhat_ky = nhat_ky

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def execute(self, sql, params=None):
        self._nhat_ky.append((sql, params))

    def fetchall(self):
        return self._rows


class FakeConn:
    """Ket noi gia: tra ve dung cac dong duoc dat truoc, ghi lai cau SQL."""

    def __init__(self, rows):
        self.rows = rows
        self.nhat_ky = []

    def cursor(self):
        return _FakeCursor(self.rows, self.nhat_ky)


class FakeEmbedder:
    def embed(self, texts):
        return [[0.1, 0.2, 0.3] for _ in texts]

    @property
    def dim(self):
        return 3


# (document, meta, similarity) - dung thu tu cot cua cau SELECT trong retrieval
_ROWS = [
    ("thông số VF 8: 420km",
     {"model": "VF 8", "source_url": "u1", "verified": True}, 0.91),
    ("thông số VF 9: 438km",
     {"model": "VF 9", "source_url": "u2", "verified": True}, 0.62),
]


def test_loc_dung_collection_va_khoa():
    """Cau SQL phai loc theo ca collection LAN (content_type, langcode).

    Day dung la cho no B6 tung hong o tang tren: hai truy van RAG loc bang
    hang so trong khi Aggregator tra config theo state. Khoa xuong toi day thi
    phai di vao menh de WHERE, khong duoc roi rung giua duong.
    """
    conn = FakeConn(_ROWS)
    retrieve("VF 8", "cam_nang", "vi", embedder=FakeEmbedder(), conn=conn,
             top_k=5, collection_name=retrieval.COLLECTION_BRAND)

    sql, params = conn.nhat_ky[0]
    assert "WHERE collection = %s" in sql, sql
    assert "content_type = %s" in sql and "langcode = %s" in sql, sql
    assert params[1] == "kb_brand", params
    assert params[2] == "cam_nang" and params[3] == "vi", params
    assert params[5] == 5, f"top_k phai xuong LIMIT, got {params}"
    print("[PASS] SQL loc dung collection + content_type + langcode + top_k")


def test_hinh_dang_hit_giu_nguyen():
    """Hinh dang tra ve phai y het ban Chroma - 4 agent doc theo hinh dang do."""
    hits = retrieve("VF 8", "cam_nang", "vi", embedder=FakeEmbedder(),
                    conn=FakeConn(_ROWS))
    assert len(hits) == 2, hits
    assert hits[0]["text"] == "thông số VF 8: 420km", hits[0]
    assert hits[0]["model"] == "VF 8", hits[0]
    assert hits[0]["score"] == 0.91, hits[0]
    assert hits[0]["source_url"] == "u1", hits[0]
    assert set(hits[0]) == {"text", "model", "topic_group", "score", "source_url"}
    print("[PASS] hinh dang hit giu nguyen nhu ban Chroma")


def test_min_similarity_loc():
    hits = retrieve("VF 8", "cam_nang", "vi", embedder=FakeEmbedder(),
                    conn=FakeConn(_ROWS), min_similarity=0.9)
    assert len(hits) == 1, hits
    assert hits[0]["model"] == "VF 8", hits
    print("[PASS] min_similarity loai dong duoi nguong")


def test_min_similarity_none_thi_khong_loc_gi():
    """Mac dinh None = chua chot nguong -> KHONG duoc am tham loc bot."""
    hits = retrieve("VF 8", "cam_nang", "vi", embedder=FakeEmbedder(),
                    conn=FakeConn(_ROWS))
    assert len(hits) == 2, hits
    print("[PASS] min_similarity=None khong loc gi")


def test_meta_thieu_khoa_khong_sap():
    """KB brand khong co khoa 'model', KB fact-check khong co 'topic_group'."""
    rows = [("doan mau", {"sample_id": "B-001", "topic_group": "sac_pin"}, 0.8)]
    hits = retrieve("sạc pin", "cam_nang", "vi", embedder=FakeEmbedder(),
                    conn=FakeConn(rows))
    assert hits[0]["model"] == "", hits
    assert hits[0]["topic_group"] == "sac_pin", hits
    print("[PASS] metadata thieu khoa -> chuoi rong, khong loi")


def test_meta_null_khong_sap():
    """jsonb NULL tu DB -> None. Khong duoc nem AttributeError."""
    hits = retrieve("x", "cam_nang", "vi", embedder=FakeEmbedder(),
                    conn=FakeConn([("doan", None, 0.5)]))
    assert hits[0]["model"] == "" and hits[0]["topic_group"] == "", hits
    print("[PASS] meta = None khong lam sap")


def test_ket_noi_cache_theo_dsn():
    """`db.get_conn` phai cache theo DSN, khong phai mot bien toan cuc duy nhat.

    Giu lai phep kiem cua no B11 sau khi doi tu Chroma sang Postgres: ban cu
    cua retrieval._get_collection bo qua tham so `chroma_path` nen mo KB thu
    hai van ra KB thu nhat. Loi do khong duoc phep tai sinh duoi hinh dang moi.

    Thay psycopg.connect bang ham gia de khong can server that.
    """
    that = db.psycopg.connect
    da_mo = []

    class _ConnGia:
        closed = False

        def __init__(self, dsn):
            self.dsn = dsn

    db.psycopg.connect = lambda d, **kw: (da_mo.append(d), _ConnGia(d))[1]
    cu = dict(db._conns)
    try:
        db._conns.clear()
        a = db.get_conn("postgresql://x/mot")
        b = db.get_conn("postgresql://x/hai")
        assert a.dsn.endswith("mot") and b.dsn.endswith("hai"), (a.dsn, b.dsn)
        # DSN thu hai KHONG duoc de len DSN thu nhat
        assert db.get_conn("postgresql://x/mot") is a, "DSN dau bi de mat"
        assert len(da_mo) == 2, da_mo
    finally:
        db.psycopg.connect = that
        db._conns.clear()
        db._conns.update(cu)
    print("[PASS] ket noi cache theo DSN, hai DSN khong lan nhau")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_loc_dung_collection_va_khoa,
        test_hinh_dang_hit_giu_nguyen,
        test_min_similarity_loc,
        test_min_similarity_none_thi_khong_loc_gi,
        test_meta_thieu_khoa_khong_sap,
        test_meta_null_khong_sap,
        test_ket_noi_cache_theo_dsn,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
