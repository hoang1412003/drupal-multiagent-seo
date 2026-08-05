"""Test chan diem LLM tu dat ra ngoai thang 0-100 (Content Quality, SEO).

VI SAO CAN: hai agent nay chua chuyen sang rubric nen van de LLM tu cho
`score` (no B/A1 trong docs/technical-debt.md). Va khong cho nao noi voi LLM
thang diem la gi - ca hai system prompt deu KHONG nhac "0-100", LLM chi suy
tu ten truong `score`. Structured outputs cung khong chan ho: JSON Schema
`minimum`/`maximum` nam trong danh sach rang buoc Anthropic KHONG ho tro, nen
them vao schema la de cho co.

Diem ngoai dai di thang vao trung binh co trong so cua Aggregator -> vo thang
diem cua ca he thong. Chan ngay khi nhan (architecture.md muc 7).

Chay: .venv\\Scripts\\python.exe scripts\\test_diem_llm.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import content_quality, seo
from scoring import kiem_diem_llm

FIELDS = {"title": "Tiêu đề", "body": "Nội dung bài", "summary": "Tóm tắt",
          "meta_description": "meta", "url_alias": "/slug", "image_alt": ""}


def _gia_lap(agent, ket_qua):
    """Thay call_agent cua agent bang mot ham tra ket qua dung san."""
    goc = agent.call_agent
    agent.call_agent = lambda *a, **k: ket_qua
    try:
        return agent.run(FIELDS)
    finally:
        agent.call_agent = goc


def test_diem_trong_dai_di_qua():
    for diem in (0, 50, 78, 100):
        assert kiem_diem_llm(diem, "seo") == diem
    print("[PASS] diem 0..100 di qua nguyen ven")


def test_diem_vuot_tran_bi_tu_choi():
    for diem in (101, 150, 1000):
        try:
            kiem_diem_llm(diem, "seo")
        except ValueError:
            continue
        raise AssertionError(f"diem {diem} phai bi tu choi")
    print("[PASS] diem > 100 -> ValueError")


def test_diem_am_bi_tu_choi():
    for diem in (-1, -20):
        try:
            kiem_diem_llm(diem, "content_quality")
        except ValueError:
            continue
        raise AssertionError(f"diem {diem} phai bi tu choi")
    print("[PASS] diem am -> ValueError")


def test_thong_bao_loi_neu_ten_agent():
    """Loi phai chi dung agent nao, vi graph.py bat exception roi danh dau
    agent loi - khong con ngu canh nao khac de biet cho nao hong."""
    try:
        kiem_diem_llm(150, "seo")
    except ValueError as e:
        assert "seo" in str(e), str(e)
        assert "150" in str(e), str(e)
        print("[PASS] thong bao loi neu ten agent va gia tri")
        return
    raise AssertionError("phai raise")


def test_seo_tu_choi_diem_ngoai_dai():
    """Agent nem loi -> graph.py danh dau agent loi -> Aggregator chia lai
    trong so va ghi `note`. Nguoi duyet thay diem chua day du, thay vi thay
    mot con so da bi thoi phong am tham."""
    try:
        _gia_lap(seo, {"score": 150, "main_keyword": "xe điện", "issues": []})
    except ValueError:
        print("[PASS] seo.run tu choi diem 150")
        return
    raise AssertionError("seo.run phai tu choi diem 150")


def test_content_quality_tu_choi_diem_ngoai_dai():
    try:
        _gia_lap(content_quality, {"score": -5, "issues": [], "strengths": []})
    except ValueError:
        print("[PASS] content_quality.run tu choi diem -5")
        return
    raise AssertionError("content_quality.run phai tu choi diem -5")


def test_seo_giu_nguyen_ket_qua_hop_le():
    """Chieu nguoc lai: khong duoc lam hong duong chay binh thuong."""
    kq = _gia_lap(seo, {"score": 82, "main_keyword": "xe điện", "issues": []})
    assert kq["score"] == 82, kq
    assert kq["main_keyword"] == "xe điện", kq
    print("[PASS] ket qua hop le di qua nguyen ven")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_diem_trong_dai_di_qua,
        test_diem_vuot_tran_bi_tu_choi,
        test_diem_am_bi_tu_choi,
        test_thong_bao_loi_neu_ten_agent,
        test_seo_tu_choi_diem_ngoai_dai,
        test_content_quality_tu_choi_diem_ngoai_dai,
        test_seo_giu_nguyen_ket_qua_hop_le,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
