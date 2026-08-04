"""Test dung bao cao JSON ghi vao field_ai_report_json.

Khong goi LLM, khong can Drupal. Chay:
    .venv\\Scripts\\python.exe scripts\\test_report_json.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import _content_hash

# Fixture nam trong drupal/scripts/ chu khong phai canh file nay, vi container
# DDEV chi mount thu muc drupal/ - phia PHP khong doc duoc gi ben ngoai do.
# Python chay tren host nen doc duoc ca hai noi, vay rang buoc quyet dinh vi
# tri la phia PHP.
FIXTURE = os.path.join(
    os.path.dirname(__file__), "..", "..", "drupal", "scripts",
    "content_hash_fixture.json",
)


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


from graph import _build_report_json

STATE_MAU = {
    "node_id": "n1",
    # State that luon co ca decision/final_score o cap ngoai (aggregator_node
    # tra ra) LAN trong report. _build_report_json doc cap ngoai - dung nguon
    # ma write_back() dung, de JSON va field diem khong bao gio lech nhau.
    "decision": "needs_revision",
    "final_score": 76.5,
    "fields": {"title": "Tiêu đề", "body": "<p>Nội dung</p>",
               "summary": "Tóm tắt", "meta_description": "Mô tả"},
    "report": {
        "node_id": "n1",
        "final_score": 76.5,
        "decision": "needs_revision",
        "missing_agents": [],
        "details": {
            "seo": {"score": 75, "issues": [
                {"field": "title", "type": "Độ dài tiêu đề",
                 "suggestion": "Rút xuống 50-60 ký tự"}]},
            "compliance": {"score": 85, "flags": [
                {"field": "body", "severity": "medium",
                 "rule": "Claim thiếu điều kiện đo",
                 "excerpt": "chạy được 420km"}]},
        },
    },
}


def test_cau_truc_co_ban():
    j = _build_report_json(STATE_MAU)
    assert j["version"] == 1
    assert j["decision"] == "needs_revision"
    assert j["final_score"] == 76.5
    assert len(j["content_hash"]) == 64
    assert j["scored_at"], "phai co moc thoi gian"
    print("[PASS] cau truc co ban day du")


def test_issue_gom_dung_field():
    j = _build_report_json(STATE_MAU)
    assert set(j["fields"]) == {"title", "body"}, j["fields"]
    assert len(j["fields"]["title"]) == 1
    assert len(j["fields"]["body"]) == 1
    print("[PASS] moi issue gom dung field cua no")


def test_severity_chi_tu_compliance():
    """3 agent kia KHONG dinh nghia muc nghiem trong -> null.

    Co y khong bia: rubrics.md muc 6.1 chu truong severity phai tra bang tat
    dinh theo ma tieu chi, tu che mot muc o tang hien thi la di nguoc huong do.
    """
    j = _build_report_json(STATE_MAU)
    assert j["fields"]["body"][0]["severity"] == "medium"
    assert j["fields"]["title"][0]["severity"] is None
    print("[PASS] severity chi lay tu Compliance")


def test_compliance_message_la_none():
    """Compliance khong co truong goi y sua. Dat message = rule se khien giao
    dien in cung mot cau hai lan."""
    j = _build_report_json(STATE_MAU)
    muc = j["fields"]["body"][0]
    assert muc["label"] == "Claim thiếu điều kiện đo"
    assert muc["message"] is None, muc
    assert muc["excerpt"] == "chạy được 420km"
    print("[PASS] Compliance: label co, message None, excerpt co")


def test_agent_thuong_khong_co_excerpt():
    j = _build_report_json(STATE_MAU)
    muc = j["fields"]["title"][0]
    assert muc["agent"] == "SEO"
    assert muc["label"] == "Độ dài tiêu đề"
    assert muc["message"] == "Rút xuống 50-60 ký tự"
    assert muc["excerpt"] is None
    print("[PASS] agent thuong: label + message, khong excerpt")


def test_brand_voice_co_excerpt():
    """Brand Voice co trich dan nguyen van (cho no tim thay loi) - phai vao
    truong excerpt de giao dien hien trong khung rieng nhu Compliance, khong
    gop vao label."""
    state = {
        "node_id": "n1", "decision": "needs_revision", "final_score": 80.0,
        "fields": {"title": "T"},
        "report": {"final_score": 80.0, "decision": "needs_revision",
                   "missing_agents": [],
                   "details": {"brand": {"score": 80.0, "issues": [
                       {"field": "body", "type": "Xưng hô không nhất quán (BV3)",
                        "suggestion": "Chọn một kiểu duy nhất.",
                        "excerpt": "khách hàng, người dùng"}]}}},
    }
    muc = _build_report_json(state)["fields"]["body"][0]
    assert muc["label"] == "Xưng hô không nhất quán (BV3)", muc
    assert muc["excerpt"] == "khách hàng, người dùng", muc
    assert muc["severity"] is None, "chi Compliance moi co severity"
    print("[PASS] Brand Voice: trich dan vao excerpt, khong gop vao label")


def test_compliance_loi_thi_score_none():
    state = {
        "node_id": "n1",
        "decision": "needs_revision",
        "final_score": None,
        "fields": {"title": "T"},
        "report": {"final_score": None, "decision": "needs_revision",
                   "missing_agents": ["compliance"],
                   "note": "Không thể xác minh Compliance",
                   "details": {"compliance": None}},
    }
    j = _build_report_json(state)
    assert j["final_score"] is None, "phai giu None, KHONG duoc thanh 0"
    assert j["note"], "phai co note giai thich"
    assert j["missing_agents"] == ["compliance"]
    print("[PASS] Compliance loi -> final_score None, co note")


def test_veto_reason_duoc_giu():
    state = {
        "node_id": "n1", "decision": "rejected", "final_score": 90.0,
        "fields": {"title": "T"},
        "report": {"final_score": 90.0, "decision": "rejected",
                   "missing_agents": [],
                   "veto_reason": "Bị từ chối do vi phạm Compliance",
                   "details": {}},
    }
    j = _build_report_json(state)
    assert "Compliance" in j["veto_reason"]
    print("[PASS] veto_reason duoc giu nguyen")


def test_agent_loi_khong_lam_sap():
    state = {"node_id": "n1", "fields": {"title": "T"},
             "report": {"final_score": 70.0, "decision": "needs_revision",
                        "missing_agents": ["seo"],
                        "details": {"seo": None, "compliance": {"score": 80, "flags": []}}}}
    j = _build_report_json(state)
    assert j["fields"] == {}
    print("[PASS] agent tra None -> bo qua, khong sap")


def test_issue_khong_co_field_thi_bo_qua():
    """Issue khong gan field khong hien duoc duoi widget nao ca."""
    state = {"node_id": "n1", "fields": {"title": "T"},
             "report": {"final_score": 70.0, "decision": "needs_revision",
                        "missing_agents": [],
                        "details": {"seo": {"score": 70, "issues": [
                            {"type": "Loi chung", "suggestion": "x"}]}}}}
    j = _build_report_json(state)
    assert j["fields"] == {}, j["fields"]
    print("[PASS] issue khong co field -> bo qua")


def _bat_patch(report_json=None):
    """Goi write_back() voi _request_with_retry gia, tra ve attributes da gui."""
    import drupal_client

    da_gui = {}

    def patch_gia(method, url, **kwargs):
        da_gui.update(kwargs["json"]["data"]["attributes"])

        class R:
            pass
        return R()

    that = drupal_client._request_with_retry
    drupal_client._request_with_retry = patch_gia
    try:
        kw = {"node_id": "n1", "status": "publish", "score": 80.0,
              "suggestions": "text"}
        if report_json is not None:
            kw["report_json"] = report_json
        drupal_client.write_back(**kw)
    finally:
        drupal_client._request_with_retry = that
    return da_gui


def test_write_back_gui_ca_hai_field():
    """write_back phai PATCH ca field_ai_suggestions lan field_ai_report_json."""
    da_gui = _bat_patch({"version": 1, "fields": {}})
    assert da_gui["field_ai_suggestions"] == "text"
    assert "field_ai_report_json" in da_gui, da_gui
    assert json.loads(da_gui["field_ai_report_json"])["version"] == 1
    print("[PASS] write_back gui ca 2 field")


def test_write_back_khong_co_report_json_van_chay():
    """Loi goi cu (khong truyen report_json) khong duoc doi hanh vi."""
    da_gui = _bat_patch(None)
    assert "field_ai_report_json" not in da_gui, da_gui
    print("[PASS] khong truyen report_json -> khong gui field do")


def test_json_giu_dau_tieng_viet():
    """ensure_ascii=False de JSON trong DB doc duoc bang mat khi debug."""
    da_gui = _bat_patch({"x": "Tiêu đề"})
    assert "Tiêu đề" in da_gui["field_ai_report_json"], da_gui["field_ai_report_json"]
    print("[PASS] JSON giu nguyen dau tieng Viet")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_hash_khop_fixture,
        test_hash_tat_dinh,
        test_doi_mot_ky_tu_thi_hash_doi,
        test_field_thieu_coi_nhu_rong,
        test_field_none_coi_nhu_rong,
        test_cau_truc_co_ban,
        test_issue_gom_dung_field,
        test_severity_chi_tu_compliance,
        test_compliance_message_la_none,
        test_agent_thuong_khong_co_excerpt,
        test_brand_voice_co_excerpt,
        test_compliance_loi_thi_score_none,
        test_veto_reason_duoc_giu,
        test_agent_loi_khong_lam_sap,
        test_issue_khong_co_field_thi_bo_qua,
        test_write_back_gui_ca_hai_field,
        test_write_back_khong_co_report_json_van_chay,
        test_json_giu_dau_tieng_viet,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
