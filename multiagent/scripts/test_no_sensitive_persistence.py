"""Quet ro ri: toan van bai, prompt va secret KHONG duoc luu o dau.

Cach lam: cho chuoi CANARY di xuyen he thong bang duong that (API -> worker ->
connector), roi luc lai MOI noi co the luu: bon bang, log da bat, va HTML
admin. Bat ky canary nao xuat hien ngoai fake connector deu la ro ri.

Test nay co y "khong hieu biet gi": no khong biet field nao duoc phep luu, no
chi biet chuoi nao TUYET DOI khong duoc xuat hien. Nho vay no van bat duoc ro
ri o cho ma nguoi viet no chua nghi toi.

Chay: .venv\\Scripts\\python.exe scripts\\test_no_sensitive_persistence.py
"""
import io
import json
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.dirname(__file__))

from _platform_harness import (
    CANARY,
    ConnectorGia,
    EngineGia,
    co_postgres,
    moi_truong,
)

# Duoc phep xuat hien: hash noi dung, prefix token, TEN bien secret.
DUOC_PHEP = ("content_hash", "token_prefix", "secret_ref", "DRUPAL")


def _quet(ten_noi: str, noi_dung: str) -> list:
    return [
        ten for ten, chuoi in CANARY.items()
        if chuoi in noi_dung
    ]


def test_khong_bang_nao_luu_canary():
    with moi_truong("vf_test_leak_db") as mt:
        mt.post_job()
        mt.chay()

        bang = ("review_job", "run_log", "llm_usage_event", "admin_audit_log",
                "site_api_credential", "worker_heartbeat", "site")
        for ten_bang in bang:
            noi_dung = str(mt.rows(f"SELECT * FROM {ten_bang}"))
            lo = _quet(ten_bang, noi_dung)
            assert not lo, f"bang {ten_bang} lo canary: {lo}"
    print(f"[PASS] {len(CANARY)} canary khong xuat hien trong 7 bang")


def test_log_khong_lo_canary():
    """Bat toan bo log trong mot vong chay that roi luc lai."""
    from review_platform.logging import RedactingFilter

    bo_dem = io.StringIO()
    handler = logging.StreamHandler(bo_dem)
    handler.addFilter(RedactingFilter())
    root = logging.getLogger()
    root.addHandler(handler)
    muc_cu = root.level
    root.setLevel(logging.DEBUG)
    try:
        with moi_truong("vf_test_leak_log") as mt:
            mt.post_job()
            # Ep mot duong loi de worker ghi nhieu log nhat co the.
            mt.chay(engine=EngineGia(loi=RuntimeError(
                f"loi kem secret Authorization: Bearer {CANARY['password']}"
            )))
    finally:
        root.removeHandler(handler)
        root.setLevel(muc_cu)

    log = bo_dem.getvalue()
    lo = _quet("log", log)
    assert not lo, f"log lo canary: {lo}\n--- log ---\n{log[:2000]}"
    print("[PASS] log khong lo canary, ke ca tren duong loi")


def test_json_console_khong_lo_canary():
    """Console doc tu database, nen no la noi ro ri cuoi cung.

    Truoc 2026-08-21 phep kiem nay render template Jinja2 cua admin cu. Admin
    do da bi xoa; thay vao do quet chinh JSON ma Console tra ve - do moi la
    thu nguoi dung nhan duoc bay gio.

    Man chi tiet review duoc chon vi no hien nhieu du lieu run nhat: ket qua
    tung agent, du lieu tho, va ca chuoi loi.
    """
    import json

    from review_platform.admin import queries
    from review_platform.admin_api import models

    with moi_truong("vf_test_leak_json") as mt:
        mt.post_job()
        mt.chay()

        public_id = mt.scalar("SELECT public_id FROM run_log")
        chi_tiet = queries.get_review(mt.conn, public_id)
        assert chi_tiet is not None

        # Serialize DUNG cach Console serialize: qua model Pydantic, khong
        # phai str() cua dataclass. Hai cach cho ra hai chuoi khac nhau, va
        # chi cach dau moi la thu di ra ngoai mang.
        payload = models.ReviewDetailModel.from_view(chi_tiet).model_dump()
        noi_dung = json.dumps(payload, ensure_ascii=False, default=str)

        lo = _quet("review detail JSON", noi_dung)
        assert not lo, f"JSON cua Console lo canary: {lo}"
    print("[PASS] JSON cua Console khong lo canary")


def test_gia_tri_duoc_phep_van_con_dung_duoc():
    """Che qua tay cung la hong: mat kha nang chan doan."""
    with moi_truong("vf_test_leak_allow") as mt:
        mt.post_job()
        mt.chay()

        # So bang GIA TRI cot, khong phai `in` tren chuoi ca hang: `"10" in
        # str(row)` se dung ke ca khi so 10 den tu mot cot khac.
        assert mt.scalar("SELECT external_revision_id FROM run_log") == "10"
        assert len(mt.scalar("SELECT content_hash FROM run_log")) == 64

        prefix = mt.scalar("SELECT token_prefix FROM site_api_credential")
        assert len(prefix) == 12, prefix
        assert mt.scalar("SELECT secret_ref FROM site") == "DRUPAL"
    print("[PASS] hash/revision/prefix/ten bien secret van doc duoc de chan doan")


def test_usage_event_chi_co_so_dem_khong_co_noi_dung():
    with moi_truong("vf_test_leak_usage") as mt:
        cot = [
            r[0] for r in mt.rows(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name='llm_usage_event' AND table_schema=current_schema()"
            )
        ]
        cam = {"prompt", "output", "content", "body", "payload", "text", "response"}
        assert not (set(cot) & cam), f"llm_usage_event co cot noi dung: {set(cot) & cam}"
    print("[PASS] llm_usage_event chi co so dem/nhan, khong co cot noi dung")


if __name__ == "__main__":
    if not co_postgres():
        print("[SKIP] khong ket noi duoc Postgres; [SKIP] khong phai [PASS]")
        sys.exit(0)

    failed = False
    for fn in (
        test_khong_bang_nao_luu_canary,
        test_log_khong_lo_canary,
        test_json_console_khong_lo_canary,
        test_gia_tri_duoc_phep_van_con_dung_duoc,
        test_usage_event_chi_co_so_dem_khong_co_noi_dung,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
