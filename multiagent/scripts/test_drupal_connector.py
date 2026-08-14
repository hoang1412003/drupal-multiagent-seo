"""Test connector Drupal: secret theo env, fetch dung revision, callback CAS.

Toan bo chay offline bang transport gia. Diem quan trong nhat duoc khoa o
day: MOI method chi goi transport DUNG MOT LAN. Retry thuoc ve hang doi
(q.fail co backoff va tran 3 lan); neu connector cung retry thi mot job loi
se thanh 3x3 = 9 lan goi Drupal.

Chay: .venv\\Scripts\\python.exe scripts\\test_drupal_connector.py
"""
from contextlib import contextmanager
from datetime import datetime, timezone
import os
import sys
from uuid import UUID

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import requests
from review_platform.connectors import base, runtime, secrets as connector_secrets
from review_platform.connectors.drupal import DrupalConnector
from review_platform.context import SiteContext


SITE = SiteContext(
    id=UUID("00000000-0000-4000-8000-000000000001"),
    slug="drupal-vn-primary",
    connector_type="drupal",
    base_url="http://drupal.ddev.site",
    secret_ref="DRUPAL",
    active=True,
    intake_paused=False,
)
CREDENTIALS = connector_secrets.ConnectorCredentials(
    username="ai_service", password="mat-khau"
)
NODE_UUID = "11111111-2222-4333-8444-555555555555"


@contextmanager
def expect(exc_type, message: str):
    try:
        yield
    except exc_type as exc:
        assert message in str(exc), (message, str(exc))
    else:
        raise AssertionError(f"khong nem {exc_type.__name__}")


class FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.text = "" if payload is None else str(payload)

    def json(self):
        if self._payload is None:
            raise ValueError("khong phai JSON")
        return self._payload


class FakeTransport:
    def __init__(self, *ket_qua):
        self.ket_qua = list(ket_qua)
        self.calls = []

    def __call__(self, method, url, **kwargs):
        self.calls.append({"method": method, "url": url, **kwargs})
        if not self.ket_qua:
            raise AssertionError(f"goi transport ngoai du kien: {method} {url}")
        tiep = self.ket_qua.pop(0)
        if isinstance(tiep, Exception):
            raise tiep
        return tiep


def _connector(*ket_qua):
    transport = FakeTransport(*ket_qua)
    return DrupalConnector(SITE, CREDENTIALS, request_fn=transport), transport


def _resource(**thay_doi):
    resource = {
        "id": NODE_UUID,
        "attributes": {
            "title": "Huong dan sac pin",
            "body": {
                "value": "<p>Noi dung</p><img src='a.jpg' alt='Cong sac'>",
                "summary": "Tom tat",
            },
            "path": {"alias": "/huong-dan-sac-pin"},
            "field_meta_description": "Mo ta SEO",
            "langcode": "vi",
            "drupal_internal__nid": 7,
            "drupal_internal__vid": 123,
        },
        "relationships": {
            "field_image": {"data": {"meta": {"alt": "Xe dien"}}},
        },
    }
    resource["attributes"].update(thay_doi)
    return resource


# ---------------------------------------------------------------- secrets


def test_secret_resolver_doc_dung_hai_bien_theo_prefix():
    creds = connector_secrets.resolve(
        "DRUPAL",
        environ={"DRUPAL_USER": "ai_service", "DRUPAL_PASSWORD": "mat-khau"},
    )
    assert creds.username == "ai_service"
    assert creds.password == "mat-khau"

    creds = connector_secrets.resolve(
        "DRUPAL_STAGING",
        environ={"DRUPAL_STAGING_USER": "u", "DRUPAL_STAGING_PASSWORD": "p"},
    )
    assert creds.username == "u"
    print("[PASS] secret resolver doc dung <PREFIX>_USER va <PREFIX>_PASSWORD")


def test_secret_resolver_bao_ten_bien_thieu_nhung_khong_bao_gia_tri():
    with expect(base.ConnectorSecretError, "DRUPAL_PASSWORD"):
        connector_secrets.resolve("DRUPAL", environ={"DRUPAL_USER": "ai_service"})

    try:
        connector_secrets.resolve(
            "DRUPAL", environ={"DRUPAL_PASSWORD": "tuyet-mat-khong-duoc-lo"}
        )
    except base.ConnectorSecretError as exc:
        assert "DRUPAL_USER" in str(exc)
        assert "tuyet-mat-khong-duoc-lo" not in str(exc), str(exc)
    else:
        raise AssertionError("phai nem ConnectorSecretError")
    print("[PASS] secret resolver bao ten bien thieu, khong bao gio in gia tri")


def test_secret_ref_la_khong_duoc_tra_bien_moi_truong_tuy_y():
    for xau in ("drupal", "2X", "A-B", "A B", "A" * 65, "", "PATH;rm"):
        with expect(base.ConnectorSecretError, "secret_ref"):
            connector_secrets.resolve(xau, environ={})
    print("[PASS] secret_ref sai dinh dang bi chan truoc khi tra os.environ")


# ---------------------------------------------------------------- fetch


def test_fetch_dung_url_exact_revision_va_chuan_hoa_sau_field():
    connector, transport = _connector(FakeResponse(200, {"data": _resource()}))

    doc = connector.fetch_content(NODE_UUID, external_revision_id="123")

    assert len(transport.calls) == 1, transport.calls
    assert transport.calls[0]["url"] == (
        f"http://drupal.ddev.site/jsonapi/node/article/{NODE_UUID}"
        "?resourceVersion=id%3A123"
    ), transport.calls[0]["url"]
    assert transport.calls[0]["method"] == "GET"
    assert transport.calls[0]["auth"] == ("ai_service", "mat-khau")

    assert set(doc.fields) == {
        "title", "body", "summary", "url_alias", "meta_description", "image_alt",
    }
    assert doc.fields["title"] == "Huong dan sac pin"
    assert doc.fields["summary"] == "Tom tat"
    assert doc.fields["url_alias"] == "/huong-dan-sac-pin"
    assert doc.fields["meta_description"] == "Mo ta SEO"
    assert doc.fields["image_alt"] == "Ảnh đại diện: Xe dien\nẢnh 1 trong bài: Cong sac"
    assert doc.external_revision_id == "123"
    assert doc.langcode == "vi"
    assert doc.content_type == "cam_nang"
    assert doc.source_url == "http://drupal.ddev.site/node/7"
    print("[PASS] fetch goi dung exact revision URL va chuan hoa du sau field")


def test_fetch_working_copy_lay_revision_that_tu_response():
    connector, transport = _connector(FakeResponse(200, {"data": _resource()}))

    doc = connector.fetch_content(NODE_UUID, working_copy=True)

    assert transport.calls[0]["url"].endswith(
        "?resourceVersion=rel%3Aworking-copy"
    ), transport.calls[0]["url"]
    # Duong legacy khong biet revision truoc: phai lay tu chinh response.
    assert doc.external_revision_id == "123"
    print("[PASS] fetch working-copy lay revision ID that tu response")


def test_fetch_khong_co_nid_thi_source_url_la_none():
    resource = _resource()
    del resource["attributes"]["drupal_internal__nid"]
    connector, _ = _connector(FakeResponse(200, {"data": resource}))

    doc = connector.fetch_content(NODE_UUID, external_revision_id="123")

    assert doc.source_url is None
    print("[PASS] khong co drupal_internal__nid thi source_url la None")


def test_fetch_khop_y_het_chuan_hoa_cua_drupal_client_legacy():
    """Hai cach doc khac nhau -> hash hai ben khong khop -> cham lai vo han."""
    import drupal_client

    resource = _resource()
    connector, _ = _connector(FakeResponse(200, {"data": resource}))
    doc = connector.fetch_content(NODE_UUID, external_revision_id="123")

    assert doc.fields == drupal_client._fields_tu_resource(resource)
    print("[PASS] connector chuan hoa field y het drupal_client legacy")


# ---------------------------------------------- phan loai loi, mot HTTP call


def test_401_403_la_auth_error_va_chi_goi_mot_lan():
    for ma in (401, 403):
        connector, transport = _connector(FakeResponse(ma))
        with expect(base.ConnectorAuthError, "connector_auth"):
            connector.fetch_content(NODE_UUID, external_revision_id="123")
        assert len(transport.calls) == 1, (ma, transport.calls)
    print("[PASS] 401/403 thanh ConnectorAuthError sau dung mot HTTP call")


def test_404_revision_la_revision_not_found_khong_retry():
    connector, transport = _connector(FakeResponse(404))
    with expect(base.ConnectorRevisionNotFound, "revision"):
        connector.fetch_content(NODE_UUID, external_revision_id="999")
    assert len(transport.calls) == 1
    print("[PASS] 404 revision thanh ConnectorRevisionNotFound, khong retry")


def test_timeout_429_5xx_la_transient_va_chi_mot_lan_goi():
    for ket_qua in (
        requests.Timeout("qua han"),
        requests.ConnectionError("mat ket noi"),
        FakeResponse(429),
        FakeResponse(500),
        FakeResponse(503),
    ):
        connector, transport = _connector(ket_qua)
        with expect(base.ConnectorTransientError, ""):
            connector.fetch_content(NODE_UUID, external_revision_id="123")
        assert len(transport.calls) == 1, (ket_qua, transport.calls)
    print("[PASS] timeout/429/5xx thanh ConnectorTransientError sau dung mot call")


def test_retry_after_chi_nhan_delta_seconds_va_bi_kep_0_600():
    for header, mong_doi in (
        ({"Retry-After": "30"}, 30.0),
        ({"Retry-After": "0"}, 0.0),
        ({"Retry-After": "99999"}, 600.0),
        ({"Retry-After": "-5"}, 0.0),
        ({"Retry-After": "Wed, 21 Oct 2026 07:28:00 GMT"}, None),
        ({"Retry-After": "khong-phai-so"}, None),
        ({}, None),
    ):
        connector, _ = _connector(FakeResponse(429, headers=header))
        try:
            connector.fetch_content(NODE_UUID, external_revision_id="123")
        except base.ConnectorTransientError as exc:
            assert exc.retry_after_seconds == mong_doi, (header, exc.retry_after_seconds)
        else:
            raise AssertionError("phai nem ConnectorTransientError")
    print("[PASS] Retry-After chi nhan delta-seconds, kep 0-600, bo qua dang date")


def test_response_thieu_key_la_payload_error_khong_retry_mu():
    for payload in ({}, {"data": None}, {"data": {"id": NODE_UUID}}):
        connector, transport = _connector(FakeResponse(200, payload))
        with expect(base.ConnectorPayloadError, ""):
            connector.fetch_content(NODE_UUID, external_revision_id="123")
        assert len(transport.calls) == 1
    print("[PASS] response sai schema thanh ConnectorPayloadError, khong retry mu")


# ---------------------------------------------------------- pending feed


def _pending_payload(**thay_doi):
    payload = {
        "items": [
            {
                "external_content_id": NODE_UUID,
                "external_revision_id": "123",
                "content_type": "cam_nang",
                "langcode": "vi",
                "content_hash": "a" * 64,
                "content_hash_version": 2,
                "source_url": "http://drupal.ddev.site/node/7",
            }
        ],
        "next_after_revision_id": None,
    }
    payload.update(thay_doi)
    return payload


def test_list_pending_dung_url_va_kep_limit():
    connector, transport = _connector(FakeResponse(200, _pending_payload()))

    page = connector.list_pending(after_revision_id=5, limit=50)

    assert transport.calls[0]["url"] == (
        "http://drupal.ddev.site/vf-ai/integration/v1/pending"
        "?after_revision_id=5&limit=50"
    ), transport.calls[0]["url"]
    assert len(page.items) == 1
    assert page.items[0].external_revision_id == "123"
    assert page.next_after_revision_id is None

    for limit, mong_doi in ((0, 1), (999, 50), (-3, 1)):
        connector, transport = _connector(FakeResponse(200, _pending_payload()))
        connector.list_pending(after_revision_id=0, limit=limit)
        assert f"limit={mong_doi}" in transport.calls[0]["url"], transport.calls[0]["url"]
    print("[PASS] list_pending dung URL dung va kep limit ve 1..50")


def test_feed_mang_toan_van_bi_tu_choi():
    """Feed chi duoc mang metadata. Toan van di qua feed la ro ri du lieu."""
    for khoa in ("title", "body", "summary"):
        payload = _pending_payload()
        payload["items"][0][khoa] = "khong duoc phep"
        connector, _ = _connector(FakeResponse(200, payload))
        with expect(base.ConnectorPayloadError, khoa):
            connector.list_pending(after_revision_id=0, limit=50)
    print("[PASS] feed chua title/body/summary bi tu choi la payload error")


def test_item_thieu_revision_bi_tu_choi_tru_khi_danh_dau_legacy():
    payload = _pending_payload()
    payload["items"][0]["external_revision_id"] = None
    connector, _ = _connector(FakeResponse(200, payload))
    with expect(base.ConnectorPayloadError, "external_revision_id"):
        connector.list_pending(after_revision_id=0, limit=50)

    payload = _pending_payload()
    payload["items"][0]["external_revision_id"] = None
    payload["items"][0]["legacy_without_revision"] = True
    connector, _ = _connector(FakeResponse(200, payload))
    page = connector.list_pending(after_revision_id=0, limit=50)
    assert page.items[0].external_revision_id is None
    print("[PASS] item thieu revision chi hop le khi danh dau legacy tuong minh")


# ------------------------------------------------------------- write back


def _write_request(**thay_doi):
    tham_so = {
        "run_id": UUID("99999999-8888-4777-8666-555555555555"),
        "external_content_id": NODE_UUID,
        "expected_revision_id": "123",
        "content_hash": "a" * 64,
        "content_hash_version": 2,
        "status": "needs_revision",
        "score": 76.5,
        "suggestions": "Them meta description",
        "report_json": {"content_hash": "a" * 64},
    }
    tham_so.update(thay_doi)
    return base.WriteBackRequest(**tham_so)


def test_write_back_post_result_callback_chu_khong_patch_jsonapi():
    connector, transport = _connector(
        FakeResponse(200, {"outcome": "applied", "applied_revision_id": "124"})
    )

    ket_qua = connector.write_back(_write_request())

    assert len(transport.calls) == 1
    goi = transport.calls[0]
    assert goi["method"] == "POST"
    assert goi["url"] == "http://drupal.ddev.site/vf-ai/integration/v1/results"
    assert "jsonapi" not in goi["url"]
    body = goi["json"]
    assert body["expected_revision_id"] == "123"
    assert body["content_hash_version"] == 2
    assert body["run_id"] == "99999999-8888-4777-8666-555555555555"
    assert "moderation_state" not in body
    assert "title" not in body and "body" not in body
    assert ket_qua.outcome == "applied"
    assert ket_qua.applied_revision_id == "124"
    print("[PASS] write_back POST result callback, khong PATCH JSON:API, khong gui state")


def test_write_back_khoa_ba_ket_qua_va_409_khong_phai_loi_transport():
    connector, _ = _connector(
        FakeResponse(200, {"outcome": "already_applied", "applied_revision_id": "124"})
    )
    assert connector.write_back(_write_request()).outcome == "already_applied"

    connector, _ = _connector(
        FakeResponse(409, {"code": "content_superseded"})
    )
    ket_qua = connector.write_back(_write_request())
    assert ket_qua.outcome == "content_superseded"
    assert ket_qua.applied_revision_id is None
    print("[PASS] applied/already_applied/content_superseded deu la ket qua co kieu")


def test_write_back_retry_dung_y_nguyen_body_va_run_id():
    dau = _write_request()
    connector, transport_1 = _connector(FakeResponse(500))
    with expect(base.ConnectorTransientError, ""):
        connector.write_back(dau)

    connector_2, transport_2 = _connector(
        FakeResponse(200, {"outcome": "already_applied", "applied_revision_id": "124"})
    )
    connector_2.write_back(dau)

    assert transport_1.calls[0]["json"] == transport_2.calls[0]["json"]
    print("[PASS] retry write_back gui y nguyen body va cung run_id")


# ------------------------------------------------------------------ health


def _capabilities(**thay_doi):
    payload = {
        "version": 1,
        "pending_feed": True,
        "result_callback": True,
        "revision_read": True,
    }
    payload.update(thay_doi)
    return payload


def test_health_ok_khi_du_ba_capability_va_feed_rong():
    connector, transport = _connector(
        FakeResponse(200, _capabilities()),
        FakeResponse(200, {"items": [], "next_after_revision_id": None}),
    )

    health = connector.health()

    assert health.ok is True
    assert health.error_code is None
    urls = [goi["url"] for goi in transport.calls]
    assert any("capabilities" in url for url in urls)
    assert any("pending" in url for url in urls)
    assert not any("results" in url for url in urls), urls
    print("[PASS] feed rong van bao ok neu du ba capability, khong goi result callback")


def test_health_that_bai_khi_thieu_bat_ky_capability_nao():
    for thieu in ("pending_feed", "result_callback", "revision_read"):
        connector, _ = _connector(FakeResponse(200, _capabilities(**{thieu: False})))
        health = connector.health()
        assert health.ok is False, thieu
        assert health.error_code == "capability_missing", (thieu, health.error_code)
    print("[PASS] thieu mot capability bat ky la fail, khong bao ok")


def test_health_co_item_thi_doc_dung_revision_de_chung_minh_quyen():
    connector, transport = _connector(
        FakeResponse(200, _capabilities()),
        FakeResponse(200, _pending_payload()),
        FakeResponse(200, {"data": _resource()}),
    )

    health = connector.health()

    assert health.ok is True
    assert "resourceVersion=id%3A123" in transport.calls[2]["url"], transport.calls[2]
    print("[PASS] feed co item thi health doc dung exact revision de chung minh quyen")


def test_health_auth_that_bai_tra_ma_auth_failed_khong_nem():
    connector, _ = _connector(FakeResponse(403))
    health = connector.health()
    assert health.ok is False
    assert health.error_code == "auth_failed"
    assert health.status_code == 403
    assert isinstance(health.checked_at, datetime)
    print("[PASS] health tra ma loi co kieu thay vi nem exception ra ngoai")


# ----------------------------------------------------------------- runtime


def test_runtime_prepared_document_reset_ke_ca_khi_loi():
    connector, _ = _connector()
    doc = base.ContentDocument(
        fields={"title": "x"},
        raw_content={},
        source_url=None,
        external_revision_id="123",
        content_type="cam_nang",
        langcode="vi",
    )

    assert runtime.prepared_for(NODE_UUID) is None
    with runtime.activate(connector, NODE_UUID, doc):
        assert runtime.prepared_for(NODE_UUID) is doc
        assert runtime.prepared_for("id-khac") is None
    assert runtime.prepared_for(NODE_UUID) is None

    class LoiCoY(RuntimeError):
        pass

    try:
        with runtime.activate(connector, NODE_UUID, doc):
            raise LoiCoY("loi giua chung")
    except LoiCoY:
        pass
    assert runtime.prepared_for(NODE_UUID) is None, "ContextVar phai reset trong finally"
    print("[PASS] runtime prepared document reset ContextVar ke ca khi nem loi")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_secret_resolver_doc_dung_hai_bien_theo_prefix,
        test_secret_resolver_bao_ten_bien_thieu_nhung_khong_bao_gia_tri,
        test_secret_ref_la_khong_duoc_tra_bien_moi_truong_tuy_y,
        test_fetch_dung_url_exact_revision_va_chuan_hoa_sau_field,
        test_fetch_working_copy_lay_revision_that_tu_response,
        test_fetch_khong_co_nid_thi_source_url_la_none,
        test_fetch_khop_y_het_chuan_hoa_cua_drupal_client_legacy,
        test_401_403_la_auth_error_va_chi_goi_mot_lan,
        test_404_revision_la_revision_not_found_khong_retry,
        test_timeout_429_5xx_la_transient_va_chi_mot_lan_goi,
        test_retry_after_chi_nhan_delta_seconds_va_bi_kep_0_600,
        test_response_thieu_key_la_payload_error_khong_retry_mu,
        test_list_pending_dung_url_va_kep_limit,
        test_feed_mang_toan_van_bi_tu_choi,
        test_item_thieu_revision_bi_tu_choi_tru_khi_danh_dau_legacy,
        test_write_back_post_result_callback_chu_khong_patch_jsonapi,
        test_write_back_khoa_ba_ket_qua_va_409_khong_phai_loi_transport,
        test_write_back_retry_dung_y_nguyen_body_va_run_id,
        test_health_ok_khi_du_ba_capability_va_feed_rong,
        test_health_that_bai_khi_thieu_bat_ky_capability_nao,
        test_health_co_item_thi_doc_dung_revision_de_chung_minh_quyen,
        test_health_auth_that_bai_tra_ma_auth_failed_khong_nem,
        test_runtime_prepared_document_reset_ke_ca_khi_loi,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")
    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
