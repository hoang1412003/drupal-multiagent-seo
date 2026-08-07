"""Test hai thay doi cua drupal_client cho worker (spec 2026-08-07 muc 3.4).

Khong can Drupal that: thay requests.get/patch bang ham gia.
Chay: .venv\\Scripts\\python.exe scripts\\test_drupal_client_worker.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import drupal_client as dc
import requests
from text_utils import content_hash


class _Resp:
    def __init__(self, data, status=200):
        self._data = data
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(response=self)

    def json(self):
        return self._data


def test_write_back_thanh_cong_tra_true():
    dc.requests.patch = lambda *a, **kw: _Resp({}, 200)
    assert dc.write_back("uuid-1", "publish", 90.0, "goi y") is True
    print("[PASS] write_back thanh cong -> True")


def test_write_back_that_bai_tra_false_va_khong_nem():
    """Van KHONG raise (bai da ton tien API roi), nhung nguoi goi phai biet.

    Ban cu chi logging.warning nen worker se bao job `done` trong khi Drupal
    khong he co ket qua - dung loai bay im lang du an nay danh nhieu cong
    de diet.
    """
    def _patch_loi(*a, **kw):
        raise requests.ConnectionError("Drupal chet")

    dc.requests.patch = _patch_loi
    assert dc.write_back("uuid-1", "publish", 90.0, "goi y") is False
    print("[PASS] write_back that bai -> False, khong nem exception")


_RESOURCE = {
    "id": "uuid-aaa",
    "attributes": {
        "title": "Tieu de",
        "body": {"value": "<p>Noi dung</p>", "summary": "Tom tat"},
        "path": {"alias": "/bai-viet"},
        "field_meta_description": "Mo ta",
        "field_ai_report_json": None,
        "moderation_state": "needs_review",
    },
    "relationships": {},
}


def test_liet_ke_tinh_dung_hash_hien_tai():
    dc.requests.get = lambda *a, **kw: _Resp({"data": [_RESOURCE]})
    ds = dc.liet_ke_can_cham()
    assert len(ds) == 1, ds
    mong_doi = content_hash({
        "title": "Tieu de", "body": "<p>Noi dung</p>",
        "summary": "Tom tat", "meta_description": "Mo ta",
    })
    assert ds[0]["content_hash"] == mong_doi, ds[0]
    assert ds[0]["node_id"] == "uuid-aaa", ds[0]
    assert ds[0]["hash_da_cham"] is None, ds[0]
    print("[PASS] liet_ke_can_cham tinh hash tu dung 4 field")


def test_liet_ke_doc_duoc_hash_da_cham():
    res = dict(_RESOURCE)
    res["attributes"] = dict(_RESOURCE["attributes"],
                             field_ai_report_json='{"content_hash": "cu-123"}')
    dc.requests.get = lambda *a, **kw: _Resp({"data": [res]})
    assert dc.liet_ke_can_cham()[0]["hash_da_cham"] == "cu-123"
    print("[PASS] doc duoc content_hash trong field_ai_report_json")


def test_report_json_hong_khong_lam_sap():
    """Field chua JSON hong -> coi nhu chua cham, KHONG nem exception."""
    res = dict(_RESOURCE)
    res["attributes"] = dict(_RESOURCE["attributes"],
                             field_ai_report_json="{khong phai json")
    dc.requests.get = lambda *a, **kw: _Resp({"data": [res]})
    assert dc.liet_ke_can_cham()[0]["hash_da_cham"] is None
    print("[PASS] JSON hong -> hash_da_cham None, khong sap")


def test_loai_node_khong_o_needs_review():
    """filter[status]=0 con bao ca draft va archived - phai loc tinh phia Python.

    Khong loc thi vong doi soat se cham MOI ban nhap trong site, tuc tieu tien
    API cho nhung bai chua ai gui duyet.
    """
    draft = dict(_RESOURCE)
    draft["attributes"] = dict(_RESOURCE["attributes"], moderation_state="draft")
    dc.requests.get = lambda *a, **kw: _Resp({"data": [draft, _RESOURCE]})
    ds = dc.liet_ke_can_cham()
    assert len(ds) == 1 and ds[0]["node_id"] == "uuid-aaa", ds
    print("[PASS] node o draft/archived bi loai, chi giu needs_review")


def test_url_khong_dung_filter_moderation_state():
    """filter[moderation_state] lam JSON:API tra HTTP 500 (computed field).

    Khoa lai bang test vi day la thu de bi 'sua cho gon' ma khong biet no hong
    - va no hong o dang kho chan doan: ca vong doi soat chet lang le.
    """
    da_goi = []
    dc.requests.get = lambda url, **kw: (da_goi.append(url), _Resp({"data": []}))[1]
    dc.liet_ke_can_cham()
    assert "moderation_state" not in da_goi[0], da_goi[0]
    assert "filter%5Bstatus%5D=0" in da_goi[0], da_goi[0]
    print("[PASS] URL loc bang status=0, khong dung filter moderation_state")


if __name__ == "__main__":
    that_get, that_patch = dc.requests.get, dc.requests.patch
    failed = False
    for fn in (
        test_write_back_thanh_cong_tra_true,
        test_write_back_that_bai_tra_false_va_khong_nem,
        test_liet_ke_tinh_dung_hash_hien_tai,
        test_liet_ke_doc_duoc_hash_da_cham,
        test_report_json_hong_khong_lam_sap,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    dc.requests.get, dc.requests.patch = that_get, that_patch
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
