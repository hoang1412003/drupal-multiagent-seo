"""Test cho chinh runner (Plan 5 Task 6).

Runner ma sai thi moi bao cao "test xanh" sau do deu vo nghia. Trong tam:
manifest phai phu DUNG va DU file that, va [SKIP] khong bao gio thanh [PASS].

Chay: .venv\\Scripts\\python.exe scripts\\test_test_group_runner.py
"""
import json
import os
from pathlib import Path
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import run_test_group


def _manifest(pure=(), postgres=(), manual=()):
    return {
        "nhom": {
            "pure": {"mo_ta": "", "files": list(pure)},
            "postgres": {"mo_ta": "", "files": list(postgres)},
            "manual_ddev": {"mo_ta": "", "files": list(manual)},
        }
    }


def _thu_muc(ten_file):
    tmp = tempfile.TemporaryDirectory()
    for ten in ten_file:
        (Path(tmp.name) / ten).write_text("", encoding="utf-8")
    return tmp


def test_manifest_that_phu_dung_moi_file_test():
    """Cong quan trong nhat: khong file test nao bi bo quen."""
    manifest = run_test_group.doc_manifest()
    run_test_group.kiem_manifest(manifest)

    tren_dia = {p.name for p in run_test_group.SCRIPTS.glob("test_*.py")}
    khai_bao = set()
    for nhom in manifest["nhom"].values():
        khai_bao.update(nhom["files"])
    assert khai_bao == tren_dia, khai_bao ^ tren_dia
    print(f"[PASS] manifest phu dung {len(tren_dia)} file test, khong thua khong thieu")


def test_bao_loi_khi_co_file_chua_xep_nhom():
    with _thu_muc(["test_a.py", "test_b.py"]) as _:
        pass
    tmp = _thu_muc(["test_a.py", "test_b.py"])
    try:
        try:
            run_test_group.kiem_manifest(_manifest(pure=["test_a.py"]), Path(tmp.name))
        except run_test_group.ManifestError as exc:
            assert "test_b.py" in str(exc), exc
        else:
            raise AssertionError("phai bao loi khi co file chua xep nhom")
    finally:
        tmp.cleanup()
    print("[PASS] file test moi chua xep nhom -> bao loi, khong im lang bo qua")


def test_bao_loi_khi_khai_bao_trung_hoac_file_khong_ton_tai():
    tmp = _thu_muc(["test_a.py"])
    try:
        try:
            run_test_group.kiem_manifest(
                _manifest(pure=["test_a.py"], postgres=["test_a.py"]), Path(tmp.name)
            )
        except run_test_group.ManifestError as exc:
            assert "nhieu nhom" in str(exc), exc
        else:
            raise AssertionError("phai bao loi khi file o hai nhom")

        try:
            run_test_group.kiem_manifest(
                _manifest(pure=["test_a.py", "test_khong_co.py"]), Path(tmp.name)
            )
        except run_test_group.ManifestError as exc:
            assert "khong ton tai" in str(exc), exc
        else:
            raise AssertionError("phai bao loi khi khai bao file khong co that")
    finally:
        tmp.cleanup()
    print("[PASS] khai bao trung nhom hoac file khong ton tai deu bi chan")


def test_chan_script_tra_phi_vao_nhom():
    tmp = _thu_muc(["eval_stability.py"])
    try:
        try:
            run_test_group.kiem_manifest(
                _manifest(pure=["eval_stability.py"]), Path(tmp.name)
            )
        except run_test_group.ManifestError as exc:
            assert "tra phi" in str(exc), exc
        else:
            raise AssertionError("script tra phi khong duoc vao nhom")
    finally:
        tmp.cleanup()
    print("[PASS] script goi API tra phi khong duoc dua vao runner tu dong")


def test_moi_truong_con_khong_co_api_key():
    goc = os.environ.get("ANTHROPIC_API_KEY")
    os.environ["ANTHROPIC_API_KEY"] = "sk-khong-duoc-truyen-xuong"
    try:
        moi_truong = run_test_group.moi_truong_con()
    finally:
        if goc is None:
            os.environ.pop("ANTHROPIC_API_KEY", None)
        else:
            os.environ["ANTHROPIC_API_KEY"] = goc

    assert "ANTHROPIC_API_KEY" not in moi_truong, "key phai bi xoa khoi tien trinh con"
    assert moi_truong["HF_HUB_OFFLINE"] == "1"
    assert moi_truong["VF_ALLOW_PAID_EVAL"] == "0"
    print("[PASS] tien trinh con khong co API key, offline, cam eval tra phi")


def test_skip_khong_bao_gio_thanh_pass():
    """Chinh sach: thieu dich vu thi phai sua moi truong, khong bao xanh."""
    import inspect

    nguon = inspect.getsource(run_test_group.main)
    assert "cho_phep_skip" in nguon
    assert "KHONG phai [PASS]" in nguon
    # Mac dinh (khong co co) thi skip lam job that bai.
    assert "if bo_qua and not args.cho_phep_skip" in nguon
    print("[PASS] mac dinh [SKIP] lam runner that bai, khong bao xanh gia")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_manifest_that_phu_dung_moi_file_test,
        test_bao_loi_khi_co_file_chua_xep_nhom,
        test_bao_loi_khi_khai_bao_trung_hoac_file_khong_ton_tai,
        test_chan_script_tra_phi_vao_nhom,
        test_moi_truong_con_khong_co_api_key,
        test_skip_khong_bao_gio_thanh_pass,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
