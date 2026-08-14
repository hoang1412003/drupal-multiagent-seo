"""Test fingerprint v2 phia Python, dung chung fixture voi PHP.

Fixture `drupal/scripts/input_fingerprint_v2_fixture.json` la HOP DONG giua
hai ngon ngu. Hai ben cung phai ra dung `expected_sha256` trong do; lech mot
byte la bang stale hien sai vinh vien.

Chay: .venv\\Scripts\\python.exe scripts\\test_platform_fingerprint.py
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform.fingerprint import FIELDS, canonical_bytes, input_fingerprint
from text_utils import content_hash


FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "drupal" / "scripts" / "input_fingerprint_v2_fixture.json"
)


def _fixture() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_khop_dung_hash_trong_fixture_dung_chung_voi_php():
    fixture = _fixture()
    assert fixture["version"] == 2, fixture["version"]
    thuc_te = input_fingerprint(fixture["fields"])
    assert thuc_te == fixture["expected_sha256"], (thuc_te, fixture["expected_sha256"])
    print("[PASS] Python ra dung expected_sha256 cua fixture dung chung")


def test_canonical_bytes_dung_prefix_va_json_compact_unicode_nguyen_ban():
    fixture = _fixture()
    raw = canonical_bytes(fixture["fields"])
    assert raw.startswith(b"v2\n"), raw[:8]
    payload = raw[3:].decode("utf-8")
    # Compact: khong khoang trang sau dau phay hay hai cham.
    assert ", " not in payload and '": ' not in payload, payload[:120]
    # Unicode giu nguyen ban, khong escape \uXXXX; dau gach cheo khong escape.
    assert "Hướng dẫn" in payload, payload[:120]
    assert "\\u" not in payload, payload[:120]
    assert "\\/" not in payload, payload[:120]
    # Xuong dong trong image_alt van phai la escape JSON hop le.
    assert "\\n" in payload, payload[-160:]
    print("[PASS] canonical bytes co prefix v2, JSON compact, unicode/slash nguyen ban")


def test_thu_tu_field_co_dinh_va_thieu_field_thanh_chuoi_rong():
    fixture = _fixture()
    assert FIELDS == (
        "title", "body", "summary", "url_alias", "meta_description", "image_alt",
    ), FIELDS

    dao_thu_tu = {ten: fixture["fields"][ten] for ten in reversed(FIELDS)}
    assert input_fingerprint(dao_thu_tu) == fixture["expected_sha256"]

    assert input_fingerprint({}) == input_fingerprint(
        {ten: "" for ten in FIELDS}
    )
    assert input_fingerprint({"title": None}) == input_fingerprint({"title": ""})
    print("[PASS] thu tu field do code quyet dinh; field thieu/None thanh chuoi rong")


def test_doi_url_alias_hoac_image_alt_LA_doi_hash_dong_no_n2():
    """Day la ly do ton tai cua v2: v1 khong thay hai field nay doi."""
    fixture = _fixture()
    goc = fixture["fields"]
    goc_hash = input_fingerprint(goc)

    for ten in ("url_alias", "image_alt"):
        doi = dict(goc)
        doi[ten] = goc[ten] + " (da sua)"
        assert input_fingerprint(doi) != goc_hash, ten
        # Chung minh dung la lo hong cua v1: v1 KHONG doi khi hai field nay doi.
        assert content_hash(doi) == content_hash(goc), ten
    print("[PASS] v2 bat duoc thay doi url_alias/image_alt ma v1 bo sot (no N2)")


def test_moi_field_deu_tham_gia_hash():
    fixture = _fixture()
    goc = fixture["fields"]
    goc_hash = input_fingerprint(goc)
    for ten in FIELDS:
        doi = dict(goc)
        doi[ten] = str(goc[ten]) + "x"
        assert input_fingerprint(doi) != goc_hash, ten
    print("[PASS] doi bat ky field nao trong sau field deu lam doi hash")


def test_v1_va_v2_khong_bao_gio_cho_cung_mot_hash():
    fixture = _fixture()
    assert input_fingerprint(fixture["fields"]) != content_hash(fixture["fields"])
    print("[PASS] v1 va v2 cho hash khac nhau tren cung du lieu")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_khop_dung_hash_trong_fixture_dung_chung_voi_php,
        test_canonical_bytes_dung_prefix_va_json_compact_unicode_nguyen_ban,
        test_thu_tu_field_co_dinh_va_thieu_field_thanh_chuoi_rong,
        test_doi_url_alias_hoac_image_alt_LA_doi_hash_dong_no_n2,
        test_moi_field_deu_tham_gia_hash,
        test_v1_va_v2_khong_bao_gio_cho_cung_mot_hash,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
