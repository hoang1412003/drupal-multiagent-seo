"""Test ai_core bat duoc phan hoi bi cat cut, dung fake client - KHONG goi API.

HOI QUY cho mot loi that gap ngay 2026-08-04: max_tokens dang la 1024, cham
bai G-001 (2234 tu) thi Content Quality tim duoc nhieu loi nen JSON bi cat
dung o token 1024, json.loads() vang ra 'Unterminated string at column 1963'.
graph.py bat exception va danh dau agent loi, Aggregator lang le chia lai
trong so - diem tang tu 79.33 len 81.77 va quyet dinh doi tu needs_revision
thanh publish. Sai theo huong DE DAI ma khong co dau hieu gi.

Chay: .venv\\Scripts\\python.exe scripts\\test_ai_core_truncation.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import ai_core


class _Usage:
    input_tokens = 100
    output_tokens = 4096


class _Block:
    type = "text"
    text = '{"score": 80, "issues": [], "strengths": []}'


class _Response:
    def __init__(self, stop_reason: str):
        self.stop_reason = stop_reason
        self.usage = _Usage()
        self.content = [_Block()]


class _FakeMessages:
    def __init__(self, stop_reason: str):
        self._stop_reason = stop_reason

    def create(self, **kwargs):
        return _Response(self._stop_reason)


class _FakeClient:
    def __init__(self, stop_reason: str):
        self.messages = _FakeMessages(stop_reason)


def _goi_voi(stop_reason: str):
    that = ai_core._client
    ai_core._client = _FakeClient(stop_reason)
    try:
        return ai_core.call_agent("prompt", "noi dung", {"type": "object"})
    finally:
        ai_core._client = that


def test_cat_cut_thi_bao_loi_ro_rang():
    try:
        _goi_voi("max_tokens")
    except ValueError as loi:
        assert "max_tokens" in str(loi), loi
        print("[PASS] stop_reason=max_tokens -> ValueError neu ro nguyen nhan")
        return
    except Exception as loi:
        raise AssertionError(f"phai la ValueError, got {type(loi).__name__}: {loi}")
    raise AssertionError("phai nem loi khi bi cat cut, nhung da tra ve binh thuong")


def test_binh_thuong_thi_tra_ket_qua():
    ket = _goi_voi("end_turn")
    assert ket["score"] == 80, ket
    print("[PASS] stop_reason binh thuong -> tra ket qua nhu cu")


def test_ghi_usage():
    ai_core.USAGE_LOG.clear()
    _goi_voi("end_turn")
    assert len(ai_core.USAGE_LOG) == 1, ai_core.USAGE_LOG
    assert ai_core.USAGE_LOG[0]["input_tokens"] == 100
    print("[PASS] ghi usage de do chi phi that (E4)")


def test_max_tokens_du_lon():
    """1024 da chung minh la khong du cho bai tieng Viet dai."""
    import inspect

    nguon = inspect.getsource(ai_core.call_agent)
    assert "max_tokens=1024" not in nguon, "max_tokens=1024 da gay loi that, khong duoc quay lai"
    print("[PASS] max_tokens khong con la 1024")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_cat_cut_thi_bao_loi_ro_rang,
        test_binh_thuong_thi_tra_ket_qua,
        test_ghi_usage,
        test_max_tokens_du_lon,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
