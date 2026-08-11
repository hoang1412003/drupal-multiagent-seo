"""Khoa lai: ham quyet_dinh() cua E5 phai cho CUNG ket qua voi
graph.aggregator_node o nguong mac dinh.

VI SAO CAN. eval_calibration.quyet_dinh() la BAN SAO logic cua aggregator_node,
chep lai vi aggregator_node doc nguong tu config con quet nguong thi phai
truyen vao duoc. Ban sao la thu da tra gia nhieu lan trong du an nay
(config-spec.md muc 1: cung mot con so tung nam o 5 noi va troi lech hai lan).

Neu hai ban troi lech thi E5 calibrate cho MOT HE THONG KHAC he thong that -
va khong ai phat hien duoc, vi ca hai deu chay khong loi.

Chay: .venv\\Scripts\\python.exe scripts\\test_e5_khop_aggregator.py
"""
import itertools
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config  # noqa: E402
from eval_calibration import quyet_dinh  # noqa: E402

_hong = False


def check(ten, thuc, mong):
    global _hong
    if thuc != mong:
        _hong = True
        print(f"[FAIL] {ten}: mong {mong!r}, thuc {thuc!r}")
    else:
        print(f"[PASS] {ten}")


def _qua_aggregator(diem, co_critical):
    """Chay THAT graph.aggregator_node roi lay decision."""
    import graph
    flags = ([{"field": "body", "severity": "critical", "rule": "x",
               "excerpt": ""}] if co_critical else [])
    state = {
        "node_id": "test",
        "content_quality_result": ({"score": diem["content_quality"], "issues": []}
                                   if diem["content_quality"] is not None else None),
        "seo_result": ({"score": diem["seo"], "issues": []}
                       if diem["seo"] is not None else None),
        "brand_result": ({"score": diem["brand"], "issues": []}
                         if diem["brand"] is not None else None),
        "compliance_result": ({"score": diem["compliance"], "flags": flags}
                              if diem["compliance"] is not None else None),
    }
    return graph.aggregator_node(state)["decision"]


def test_khop_tren_luoi_diem():
    """Quet mot luoi diem, so hai ban tren TUNG diem mot.

    Luoi chon bao trum ca ba vung quyet dinh va ca hai ranh gioi (50, 80), cong
    them diem sat nguong veto - dung cho E1 do duoc la 8/10 bai roi vao."""
    khoi = config.load()
    w = khoi["weights"]
    ng = {"veto": khoi["decision"]["compliance_veto_below"],
          "nr": khoi["decision"]["needs_revision_min"],
          "publish": khoi["decision"]["publish_min"]}

    gia_tri = [0, 30, 48, 49, 50, 51, 66.7, 79, 80, 81, 100]
    lech = 0
    for cq, sv in itertools.product(gia_tri, gia_tri):
        for cp in gia_tri:
            for crit in (False, True):
                diem = {"content_quality": cq, "seo": sv, "brand": 83.3,
                        "compliance": cp}
                a = quyet_dinh(diem, crit, w, ng)
                b = _qua_aggregator(diem, crit)
                if a != b:
                    lech += 1
                    if lech <= 3:
                        print(f"       lech tai {diem} critical={crit}: "
                              f"E5={a} aggregator={b}")
    check(f"khop tren {len(gia_tri)**3 * 2} to hop diem", lech, 0)


def test_khop_khi_agent_loi():
    """Agent loi -> None. Aggregator chia lai trong so; ban sao phai y het.

    Rieng compliance = None thi luon `needs_revision`, khong bao gio publish
    (architecture.md muc 6.4) - day la nhanh de lech nhat neu chep thieu."""
    khoi = config.load()
    w = khoi["weights"]
    ng = {"veto": khoi["decision"]["compliance_veto_below"],
          "nr": khoi["decision"]["needs_revision_min"],
          "publish": khoi["decision"]["publish_min"]}

    ca = [
        {"content_quality": None, "seo": 95.0, "brand": 83.3, "compliance": 100.0},
        {"content_quality": 90.0, "seo": None, "brand": 83.3, "compliance": 100.0},
        {"content_quality": 90.0, "seo": 95.0, "brand": None, "compliance": 100.0},
        {"content_quality": 100.0, "seo": 100.0, "brand": 100.0, "compliance": None},
    ]
    for diem in ca:
        thieu = [k for k, v in diem.items() if v is None][0]
        check(f"agent loi: {thieu}",
              quyet_dinh(diem, False, w, ng), _qua_aggregator(diem, False))


if __name__ == "__main__":
    test_khop_tren_luoi_diem()
    test_khop_khi_agent_loi()
    sys.exit(1 if _hong else 0)
