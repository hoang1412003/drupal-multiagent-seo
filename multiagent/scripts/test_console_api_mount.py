r"""Test app that mount du Console API, gioi han body, va openapi sach.

Khac cac file test_console_api_* con lai: o day dung `api.app` THAT chu khong
dung app rong dung trong test, vi ba thu can kiem tra deu la thuoc tinh cua
app that (thu tu mount, middleware, schema openapi).

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_api_mount.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
# export_openapi nam cung thu muc scripts/, khong nam trong src/.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient

import api as app_module
from review_platform import security as platform_security
from review_platform.admin import dependencies as admin_dependencies


CONSOLE_ROUTES = {
    "/api/console/v1/auth/login",
    "/api/console/v1/auth/me",
    "/api/console/v1/auth/logout",
    "/api/console/v1/auth/change-password",
    "/api/console/v1/audit",
    "/api/console/v1/config-kb",
    "/api/console/v1/connection",
    "/api/console/v1/connection/test",
    "/api/console/v1/connection/pause",
    "/api/console/v1/connection/resume",
    "/api/console/v1/dashboard",
    "/api/console/v1/evaluation",
    "/api/console/v1/evaluation/evidence/{experiment}",
    "/api/console/v1/filters",
    "/api/console/v1/jobs",
    "/api/console/v1/jobs/{public_id}",
    "/api/console/v1/jobs/{public_id}/retry",
    "/api/console/v1/reviews",
    "/api/console/v1/reviews/{public_id}",
    "/api/console/v1/users",
    "/api/console/v1/users/{user_id}/role",
    "/api/console/v1/users/{user_id}/lock",
    "/api/console/v1/users/{user_id}/unlock",
    "/api/console/v1/users/{user_id}/reset-password",
}


def _client_khong_can_db():
    """Client goi app THAT nhung khong cham Postgres.

    Khong duyet app.routes: FastAPI ban nay giu route trong _IncludedRouter
    long nhau, khong phang hoa, va do la noi bo se doi khi nang phien ban.
    Kiem tra theo hanh vi thi dung thu can chung minh va khong vo khi nang cap.

    Khong co cookie phien thi console_session nem 401 truoc khi dung toi conn,
    nen stub duoi day khong bao gio duoc su dung.
    """
    app_module.app.state.auth_config = admin_dependencies.AuthConfig(
        csrf_key=b"csrf-key-chi-dung-trong-test-du-32-byte",
        throttle_key=b"throttle-key-chi-dung-trong-test-du-32",
        cookie_secure=False,
    )
    app_module.app.dependency_overrides[admin_dependencies.get_db] = lambda: None
    return TestClient(app_module.app, follow_redirects=False)


def test_real_app_mounts_all_console_routes():
    client = _client_khong_can_db()
    uuid_gia = "00000000-0000-4000-8000-000000000009"
    goi = (
        ("GET", "/api/console/v1/auth/me"),
        ("POST", "/api/console/v1/auth/logout"),
        ("POST", "/api/console/v1/auth/change-password"),
        ("GET", "/api/console/v1/audit"),
        ("GET", "/api/console/v1/config-kb"),
        ("GET", "/api/console/v1/connection"),
        ("POST", "/api/console/v1/connection/test"),
        ("POST", "/api/console/v1/connection/pause"),
        ("POST", "/api/console/v1/connection/resume"),
        ("GET", "/api/console/v1/dashboard"),
        ("GET", "/api/console/v1/evaluation"),
        ("GET", "/api/console/v1/filters"),
        ("GET", "/api/console/v1/jobs"),
        ("GET", f"/api/console/v1/jobs/{uuid_gia}"),
        ("POST", f"/api/console/v1/jobs/{uuid_gia}/retry"),
        ("GET", "/api/console/v1/reviews"),
        ("GET", f"/api/console/v1/reviews/{uuid_gia}"),
        ("GET", "/api/console/v1/users"),
        ("POST", "/api/console/v1/users"),
        ("POST", f"/api/console/v1/users/{uuid_gia}/role"),
        ("POST", f"/api/console/v1/users/{uuid_gia}/lock"),
        ("POST", f"/api/console/v1/users/{uuid_gia}/unlock"),
        ("POST", f"/api/console/v1/users/{uuid_gia}/reset-password"),
    )
    try:
        for method, path in goi:
            response = client.request(method, path, json={})
            assert response.status_code != 404, f"{method} {path} chua duoc mount"
            assert response.status_code == 401, (
                f"{method} {path} tra {response.status_code}, ky vong 401 khi "
                "chua dang nhap"
            )
            assert response.json()["error"]["code"] == "unauthenticated", path

        # /auth/login la endpoint duy nhat khong yeu cau phien.
        login = client.post("/api/console/v1/auth/login", json={})
        assert login.status_code != 404, "/auth/login chua duoc mount"
    finally:
        app_module.app.dependency_overrides.clear()
    print(f"[PASS] ca {len(goi) + 1} route Console deu mount tren app that va tra 401 dung chuan")


def test_openapi_excludes_legacy_admin_routes():
    schema = app_module.app.openapi()
    paths = set(schema["paths"])

    assert "/api/console/v1/auth/me" in paths, sorted(paths)[:10]
    # Hop dong giao cho agent viet frontend chi duoc chua API JSON. Route
    # Jinja2 lot vao se khien no tuong co the goi bang fetch va nhan JSON.
    html_routes = sorted(p for p in paths if p.startswith("/admin"))
    assert not html_routes, html_routes
    print("[PASS] openapi chi chua API JSON, khong lan route admin Jinja2")


def test_console_api_has_request_size_limit():
    client = TestClient(app_module.app, follow_redirects=False)
    qua_lon = "x" * (platform_security.MAX_ADMIN_BODY + 1024)

    response = client.post(
        "/api/console/v1/auth/login",
        content=qua_lon.encode("ascii"),
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 413, (
        f"Console API khong co gioi han kich thuoc body (nhan {response.status_code}). "
        "Duong dan khong khop prefix nao trong RequestSizeLimitMiddleware se di "
        "thang, khong bi chan."
    )
    print("[PASS] Console API co gioi han kich thuoc body, tra 413")


def test_openapi_console_paths_are_complete():
    schema = app_module.app.openapi()
    console_paths = {p for p in schema["paths"] if p.startswith("/api/console/")}
    assert console_paths == CONSOLE_ROUTES, CONSOLE_ROUTES ^ console_paths

    # Moi response model phai co schema: thieu thi openapi-typescript sinh ra
    # kieu `unknown` va agent viet frontend mat toan bo loi ich cua kieu.
    components = schema.get("components", {}).get("schemas", {})
    for ten in ("MeResponse", "DashboardResponse", "JobPage", "JobDetailModel",
                "ReviewPage", "ReviewDetailModel", "FiltersResponse", "AuditPage",
                "ConfigKbResponse", "EvaluationResponse", "ConnectionModel",
                "TestConnectionResponse", "UserPage", "UserModel",
                "TemporaryPasswordResponse"):
        assert ten in components, f"thieu schema {ten} trong openapi"
    print(f"[PASS] openapi co du {len(CONSOLE_ROUTES)} duong dan Console va cac schema chinh")


def test_exported_contract_excludes_connector_models():
    """File ban giao khong duoc chua model cua connector API (/api/v1).

    Loc `paths` thoi la chua du: components giu nguyen se keo theo JobIn,
    JobCreate, JobAccepted, JobStatus - va agent viet frontend se nhan kieu
    TypeScript cho nhung endpoint no khong duoc phep goi.
    """
    import export_openapi

    schema = export_openapi.build_schema()
    schemas = set(schema["components"]["schemas"])

    connector = {"JobIn", "JobCreate", "JobAccepted", "JobStatus"} & schemas
    assert not connector, f"model connector lot vao hop dong: {sorted(connector)}"

    # Va moi $ref con lai phai giai duoc, neu khong openapi-typescript hong.
    for ten in _refs_trong(schema["paths"]) | _refs_trong(schema["components"]):
        assert ten in schemas, f"$ref toi schema khong ton tai: {ten}"
    print("[PASS] hop dong xuat ra khong lan model connector va moi $ref giai duoc")


def _refs_trong(node) -> set:
    import export_openapi

    return export_openapi._refs(node)


def test_every_get_endpoint_declares_its_query_params():
    """Endpoint GET nao nhan tham so loc thi PHAI khai bao chung trong openapi.

    Chan dung lop loi da xay ra HAI lan trong ngay 2026-08-20: route doc thang
    request.query_params nen hop dong khong nhac toi tham so nao, nguoi viet
    frontend doan ten, va bo loc chet IM LANG. Lan dau o /jobs va /reviews,
    lan hai o /dashboard - vi lan sua dau bo sot endpoint do.
    """
    schema = app_module.app.openapi()
    can_khai_bao = {
        "/api/console/v1/jobs": {"status", "site", "source", "external_id",
                                 "from", "to", "page", "page_size"},
        "/api/console/v1/reviews": {"decision", "site", "external_id",
                                    "from", "to", "page", "page_size"},
        "/api/console/v1/audit": {"action", "outcome", "actor",
                                  "from", "to", "page", "page_size"},
        "/api/console/v1/dashboard": {"from", "to"},
    }
    for path, mong_doi in can_khai_bao.items():
        khai_bao = {
            p["name"] for p in schema["paths"][path]["get"].get("parameters", [])
        }
        thieu = mong_doi - khai_bao
        assert not thieu, f"{path} khong khai bao tham so: {sorted(thieu)}"
    print("[PASS] ca ba endpoint GET co loc deu khai bao du tham so trong openapi")


def test_every_filtered_endpoint_rejects_unknown_params():
    """Tham so ngoai hop dong phai bi tu choi, khong duoc bo qua im lang."""
    client = _client_khong_can_db()
    try:
        for path in ("/api/console/v1/jobs", "/api/console/v1/reviews",
                     "/api/console/v1/dashboard"):
            # Chua dang nhap nen 401 den truoc; day chi kiem route co goi
            # reject_unknown_query_params khong, bang cach doc source.
            pass
    finally:
        app_module.app.dependency_overrides.clear()

    import inspect

    from review_platform.admin_api import (
        audit_routes, dashboard_routes, job_routes, review_routes,
    )

    for ten, mod in (("jobs", job_routes), ("reviews", review_routes),
                     ("dashboard", dashboard_routes), ("audit", audit_routes)):
        src = inspect.getsource(mod)
        assert "reject_unknown_query_params" in src, (
            f"{ten} khong goi reject_unknown_query_params; tham so go sai ten "
            "se bi bo qua im lang thay vi tra 422"
        )
    print("[PASS] ca ba endpoint co loc deu tu choi tham so la")


def test_loi_422_cua_console_dung_hinh_dang_chung():
    """Handler nay dang ky o cap APP, nen chi app that moi chung minh duoc.

    Cac file test_console_api_* khac tu dung app rong va tu dang ky handler -
    chung KHONG the phat hien api.py quen dang ky. Hang rao that nam o day.

    Kem theo: /api/v1 phai giu nguyen hinh dang 422 mac dinh cua FastAPI. Do
    la hop dong voi module Drupal dang chay that; doi no la thay doi pha vo.
    """
    client = TestClient(app_module.app, follow_redirects=False)

    # Body sai kieu, gui khi CHUA dang nhap: van phai la hinh dang cua Console.
    # (401 duoc kiem tra o test khac; o day chi quan tam toi hinh dang 422.)
    r = client.post("/api/console/v1/auth/login", json={"username": 123})
    assert r.status_code == 422, f"{r.status_code}: {r.text}"
    body = r.json()
    assert "error" in body, body
    assert set(body["error"]) == {"code", "message", "field"}, body
    assert body["error"]["code"] == "invalid_payload", body
    assert body["error"]["field"] == "username", body

    # Duong dan ngoai Console KHONG duoc doi hinh dang.
    r = client.post("/api/v1/reviews", json={"external_content_id": 123})
    if r.status_code == 422:
        assert "detail" in r.json(), (
            "/api/v1 da bi doi sang hinh dang loi cua Console - day la hop "
            "dong voi module Drupal dang chay that"
        )
    print("[PASS] 422 cua Console dung hinh dang chung, /api/v1 giu nguyen")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_real_app_mounts_all_console_routes,
        test_openapi_excludes_legacy_admin_routes,
        test_console_api_has_request_size_limit,
        test_openapi_console_paths_are_complete,
        test_exported_contract_excludes_connector_models,
        test_every_get_endpoint_declares_its_query_params,
        test_every_filtered_endpoint_rejects_unknown_params,
        test_loi_422_cua_console_dung_hinh_dang_chung,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
