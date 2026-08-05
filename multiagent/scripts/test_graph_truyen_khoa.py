"""Test graph.py truyen (content_type, langcode) tu state xuong agent (no B6).

VI SAO CAN TEST: hai field nay duoc them vao ContentReviewState dung vi muc
dich do, va ca state.py lan architecture.md muc 5.6 deu KHANG DINH agent nhan
chung qua tham so. Nhung graph.py goi brand_voice.run(state["fields"]) va
compliance.run(state["fields"]) tran, nen ca hai roi ve mac dinh trong chu ky
ham - hai truy van RAG (BV6 va CP3) luon loc Chroma theo hang so.

Chua sai ket qua vi scoring.yaml moi co mot khoa that va ca hai KB deu nap voi
dung cap gia tri do. Them khoa thu hai la loi hien ra ngay, o dang kho chan
doan nhat: diem van tinh duoc, chi la RAG lay ve doan cua sai phan vung.

Khong test thi lan refactor sau lai troi ve nhu cu ma khong ai biet.

Chay: .venv\\Scripts\\python.exe scripts\\test_graph_truyen_khoa.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import graph

FIELDS = {"title": "Tiêu đề", "body": "Nội dung bài", "summary": ""}


def _ghi_lai(node, module, state):
    """Chay `node` voi run() cua `module` thay bang mot ham chi ghi lai kwargs.

    Ghi o dung ranh gioi graph -> agent, tuc dung cho B6 hong. Luu y node bat
    Exception va nuot, nen ham gia KHONG duoc nem loi - neu khong test se xanh
    gia.
    """
    ghi = {}
    goc = module.run
    module.run = lambda fields, **kw: ghi.update(kw) or {"score": 100, "issues": []}
    try:
        node(state)
    finally:
        module.run = goc
    return ghi


def test_brand_nhan_khoa_tu_state():
    ghi = _ghi_lai(graph.brand_node, graph.brand_voice, {
        "node_id": "n1", "fields": FIELDS,
        "content_type": "landing_page", "langcode": "en",
    })
    assert ghi.get("content_type") == "landing_page", ghi
    assert ghi.get("langcode") == "en", ghi
    print("[PASS] brand_node truyen khoa tu state")


def test_compliance_nhan_khoa_tu_state():
    ghi = _ghi_lai(graph.compliance_node, graph.compliance, {
        "node_id": "n1", "fields": FIELDS,
        "content_type": "landing_page", "langcode": "en",
    })
    assert ghi.get("content_type") == "landing_page", ghi
    assert ghi.get("langcode") == "en", ghi
    print("[PASS] compliance_node truyen khoa tu state")


def test_thieu_khoa_thi_dung_mac_dinh():
    """State cu (chua co hai field) van phai chay - day la refactor thuan,
    khong duoc doi hanh vi hien tai."""
    for node, module in ((graph.brand_node, graph.brand_voice),
                         (graph.compliance_node, graph.compliance)):
        ghi = _ghi_lai(node, module, {"node_id": "n1", "fields": FIELDS})
        assert ghi.get("content_type") == "cam_nang", ghi
        assert ghi.get("langcode") == "vi", ghi
    print("[PASS] thieu khoa -> mac dinh cam_nang/vi (hanh vi cu giu nguyen)")


def test_khoa_rong_cung_ve_mac_dinh():
    ghi = _ghi_lai(graph.brand_node, graph.brand_voice, {
        "node_id": "n1", "fields": FIELDS, "content_type": "", "langcode": "",
    })
    assert ghi.get("content_type") == "cam_nang", ghi
    assert ghi.get("langcode") == "vi", ghi
    print("[PASS] khoa rong -> mac dinh")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_brand_nhan_khoa_tu_state,
        test_compliance_nhan_khoa_tu_state,
        test_thieu_khoa_thi_dung_mac_dinh,
        test_khoa_rong_cung_ve_mac_dinh,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
