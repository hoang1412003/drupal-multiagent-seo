"""Test dung bao cao JSON ghi vao field_ai_report_json.

Khong goi LLM, khong can Drupal. Chay:
    .venv\\Scripts\\python.exe scripts\\test_report_json.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import _content_hash

FIXTURE = os.path.join(os.path.dirname(__file__), "content_hash_fixture.json")


def test_hash_khop_fixture():
    """HOP DONG 2 NGON NGU: PHP doc CUNG file nay va phai ra CUNG gia tri.

    Test nay do la lop bao ve duy nhat chong troi lech quy tac ghep chuoi -
    neu lech, bang canh bao 'noi dung da thay doi' se hien sai mai mai ma
    khong co gi bao.
    """
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    assert _content_hash(fx["fields"]) == fx["expected_sha256"], _content_hash(fx["fields"])
    print("[PASS] hash khop fixture (hop dong voi phia PHP)")


def test_hash_tat_dinh():
    fields = {"title": "A", "body": "B", "summary": "C", "meta_description": "D"}
    assert len({_content_hash(fields) for _ in range(20)}) == 1
    print("[PASS] cung dau vao -> cung hash")


def test_doi_mot_ky_tu_thi_hash_doi():
    a = {"title": "A", "body": "B", "summary": "C", "meta_description": "D"}
    b = {"title": "A", "body": "B.", "summary": "C", "meta_description": "D"}
    assert _content_hash(a) != _content_hash(b)
    print("[PASS] doi 1 ky tu trong body -> hash doi")


def test_field_thieu_coi_nhu_rong():
    assert _content_hash({"title": "A"}) == _content_hash(
        {"title": "A", "body": "", "summary": "", "meta_description": ""}
    )
    print("[PASS] field thieu = chuoi rong, khong loi")


def test_field_none_coi_nhu_rong():
    """fetch_content tra chuoi rong, nhung phong thu voi None de chac chan."""
    assert _content_hash({"title": "A", "body": None}) == _content_hash({"title": "A"})
    print("[PASS] field None = chuoi rong, khong loi")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_hash_khop_fixture,
        test_hash_tat_dinh,
        test_doi_mot_ky_tu_thi_hash_doi,
        test_field_thieu_coi_nhu_rong,
        test_field_none_coi_nhu_rong,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
