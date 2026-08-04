"""Test logic Brand Voice Agent bang rules GIA - khong doc brand_rules.json
that, khong goi LLM, khong doc KB.

Chay: .venv\\Scripts\\python.exe scripts\\test_brand_voice.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents import brand_voice

RULES = {
    "model_names": ["VF 8"],
    "terms": [{"standard": "ô tô điện", "non_standard": ["xe hơi điện"],
               "docs": [7, 7], "occurrences": [156, 157], "p_value": 0.01562}],
    "excluded_terms": ["xe hơi điện cao cấp"],
    "address_form": {"standard": "bạn", "docs": [9, 10],
                     "occurrences": [120, 140], "p_value": 0.021},
    "title_case": {"standard": "SENTENCE_CASE", "docs": [15, 16], "p_value": 0.00052},
}


def _khong_co_kb(*args, **kwargs):
    """Retriever gia: KB khong tra ve gi. Dung lam mac dinh cho moi test."""
    return []


def _run(fields, **kwargs):
    """Goi brand_voice.run() voi mac dinh AN TOAN cho test.

    Bat buoc phai co helper nay: tu Task 10, judge_bv6 mac dinh la ham THAT
    (goi Claude) va retriever mac dinh doc Chroma that. Goi run() tran trong
    test se ton tien API va phu thuoc KB da dung hay chua.
    """
    kwargs.setdefault("rules", RULES)
    kwargs.setdefault("judge_bv6", None)
    kwargs.setdefault("retriever", _khong_co_kb)
    return brand_voice.run(fields, **kwargs)


def _muc(ket_qua, ma):
    return next(c["level"] for c in ket_qua["criteria"] if c["id"] == ma)


def test_bv1_ba_cho_sai_muc_0():
    kq = _run(
        {"title": "Đánh giá VF8", "body": "VF8 rất tốt. vf8 tiết kiệm.", "summary": ""},
    )
    assert _muc(kq, "BV1") == 0, kq["criteria"]
    print("[PASS] 3 cho viet VF8 -> BV1 muc 0")


def test_bv1_mot_cho_sai_muc_1():
    kq = _run(
        {"title": "Đánh giá xe", "body": "VF8 rất tốt.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV1") == 1, kq["criteria"]
    print("[PASS] 1 cho viet VF8 -> BV1 muc 1")


def test_bv1_viet_dung_muc_2():
    kq = _run(
        {"title": "Đánh giá xe", "body": "VF 8 rất tốt.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV1") == 2, kq["criteria"]
    print("[PASS] viet 'VF 8' dung -> BV1 muc 2")


def test_bv1_khong_nhac_model_la_na():
    kq = _run(
        {"title": "Hướng dẫn sạc pin", "body": "Sạc pin đúng cách.", "summary": ""},
    )
    assert _muc(kq, "BV1") is None, kq["criteria"]
    print("[PASS] khong nhac model -> BV1 = NA (KHONG phai muc 2)")


def test_bv2_bien_the_thieu_so():
    kq = _run(
        {"title": "Xe hơi điện", "body": "xe hơi điện tiết kiệm.", "summary": ""},
    )
    assert _muc(kq, "BV2") == 1, kq["criteria"]
    print("[PASS] 2 cho dung bien the thieu so -> BV2 muc 1")


def test_bv7_tu_bi_loai():
    kq = _run(
        {"title": "Đánh giá", "body": "Đây là xe hơi điện cao cấp.", "summary": ""},
    )
    assert _muc(kq, "BV7") == 0, kq["criteria"]
    print("[PASS] dung tu bi loai -> BV7 muc 0")


def test_bv3_lan_hai_kieu_xung_ho():
    kq = _run(
        {"title": "Hướng dẫn", "body": "bạn nên sạc. quý khách lưu ý.", "summary": ""},
    )
    assert _muc(kq, "BV3") == 1, kq["criteria"]
    print("[PASS] lan 2 kieu xung ho -> BV3 muc 1")


def test_bv5_title_viet_hoa_toan_bo():
    kq = _run(
        {"title": "LƯU Ý SỬ DỤNG PIN LFP", "body": "Nội dung.", "summary": ""},
    )
    assert _muc(kq, "BV5") == 0, kq["criteria"]
    print("[PASS] title VIET HOA TOAN BO -> BV5 muc 0")


def test_bv6_khong_co_judge_la_na():
    kq = _run(
        {"title": "Hướng dẫn", "body": "Nội dung.", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV6") is None, kq["criteria"]
    assert kq["score"] is not None, "6 tieu chi con lai van phai cham duoc"
    print("[PASS] khong co judge BV6 -> NA, agent VAN tra diem")


def test_bai_rong_tra_none():
    kq = _run({"title": "", "body": "", "summary": ""})
    assert kq is None, kq
    print("[PASS] bai rong -> run() tra None")


def test_loi_o_hai_field_sinh_hai_issue():
    kq = _run(
        {"title": "Đánh giá VF8", "body": "VF8 tốt lắm.", "summary": ""}, rules=RULES
    )
    bv1_issues = [i for i in kq["issues"] if "BV1" in i["type"]]
    assert {i["field"] for i in bv1_issues} == {"title", "body"}, bv1_issues
    print("[PASS] loi o 2 field -> 2 issue, moi cai dung field")


def test_trich_dan_de_rieng_khong_gop_vao_type():
    """Trich dan phai o truong `excerpt` rieng, KHONG gop vao `type`.

    Gop vao khien dong tieu de dai le the khi trich dan la ca mot cau (BV6
    trich nguyen cau van), trong khi Compliance von da tach excerpt ra khung
    rieng. De hai agent nhat quan.
    """
    kq = _run(
        {"title": "Đánh giá VF8", "body": "VF8 tốt lắm.", "summary": ""},
    )
    bv1 = next(i for i in kq["issues"] if "BV1" in i["type"])
    assert "tìm thấy" not in bv1["type"], bv1["type"]
    assert bv1["excerpt"] == "VF8", bv1
    print("[PASS] trich dan o truong excerpt rieng, khong gop vao type")


def test_muc_2_va_na_khong_sinh_issue():
    kq = _run(
        {"title": "Hướng dẫn sạc pin", "body": "bạn nên sạc ô tô điện đúng cách.",
         "summary": ""},
    )
    assert kq["issues"] == [], kq["issues"]
    print("[PASS] khong loi -> khong sinh issue nao")


def test_tat_dinh_nam_lan():
    fields = {"title": "Đánh giá VF8", "body": "VF8 và xe hơi điện.", "summary": ""}
    diem = {_run(fields)["score"] for _ in range(5)}
    assert len(diem) == 1, diem
    print(f"[PASS] cham 5 lan ra dung mot diem: {diem.pop()}")


def test_bv7_thoa_man_rong_la_na():
    """HOI QUY - loi that phat hien 2026-08-03 khi chay tren node/7.

    Bai khong noi gi ve khai niem co tu bi loai thi "khong dung tu bi loai"
    la thoa man RONG - khong chung minh duoc gi. Cho muc 2 o day khien moi
    bai ngan/lac chu de duoc cong diem mien phi, dung loi "tieu chi thanh
    hang so" ma rubrics.md muc 2.2 canh bao.
    """
    kq = _run(
        {"title": "test", "body": "<p>test</p>", "summary": ""}, rules=RULES
    )
    assert _muc(kq, "BV7") is None, kq["criteria"]
    print("[PASS] bai khong nhac khai niem -> BV7 = NA (thoa man rong)")


def test_bv7_dat_khi_bai_co_ban_toi_khai_niem():
    """Nguoc lai: bai CO ban toi khai niem va dung dung tu -> muc 2 that."""
    kq = _run(
        {"title": "Hướng dẫn", "body": "ô tô điện rất tiết kiệm.", "summary": ""},
    )
    assert _muc(kq, "BV7") == 2, kq["criteria"]
    print("[PASS] bai co ban toi khai niem, dung dung tu -> BV7 muc 2")


def test_bv6_judge_tra_muc():
    def judge(fields, **kwargs):
        return {"id": "BV6", "level": 1,
                "occurrences": [{"field": "body", "text": "trích nguyên văn"}],
                "suggestion": "Giọng văn hơi lệch.", "reference": ""}

    kq = _run(
        {"title": "Hướng dẫn", "body": "Nội dung.", "summary": ""},
        rules=RULES, judge_bv6=judge,
    )
    assert _muc(kq, "BV6") == 1, kq["criteria"]
    print("[PASS] judge BV6 tra muc -> vao criteria")


def test_bv6_judge_loi_thi_na_khong_phai_0():
    def judge_loi(fields, **kwargs):
        raise RuntimeError("LLM timeout")

    kq = _run(
        {"title": "Hướng dẫn", "body": "bạn nên sạc ô tô điện.", "summary": ""},
        rules=RULES, judge_bv6=judge_loi,
    )
    assert _muc(kq, "BV6") is None, kq["criteria"]
    assert kq["score"] is not None, "6 tieu chi con lai van phai cham duoc"
    print("[PASS] judge BV6 loi -> NA (KHONG phai 0), agent van tra diem")


def test_bang_chung_duoc_dinh_vao_suggestion():
    kq = _run(
        {"title": "Xe hơi điện", "body": "xe hơi điện tiết kiệm.", "summary": ""},
        rules=RULES, judge_bv6=None,
        retriever=lambda *a, **k: [{
            "text": "Trích từ bài X:\nô tô điện rất tiết kiệm chi phí vận hành.",
            "topic_group": "sac_pin", "score": 0.8}],
    )
    bv2 = next(c for c in kq["criteria"] if c["id"] == "BV2")
    assert bv2["reference"], bv2
    assert "<" not in bv2["reference"], "khong duoc dinh ca dong prefix ngu canh"
    assert any("Ví dụ trong bài đã đăng" in i["suggestion"] for i in kq["issues"]), kq["issues"]
    print("[PASS] bang chung tu corpus duoc dinh vao goi y")


def test_retriever_loi_khong_lam_sap_agent():
    def retriever_loi(*a, **k):
        raise RuntimeError("KB chua dung")

    kq = _run(
        {"title": "Xe hơi điện", "body": "xe hơi điện tiết kiệm.", "summary": ""},
        rules=RULES, judge_bv6=None, retriever=retriever_loi,
    )
    assert kq is not None and kq["score"] is not None
    bv2 = next(c for c in kq["criteria"] if c["id"] == "BV2")
    assert bv2["reference"] == "", bv2
    print("[PASS] KB loi -> khong co bang chung nhung agent van cham")


def test_bang_chung_khong_dinh_cho_tieu_chi_dat():
    """Chi tieu chi bi ha muc moi can bang chung - muc 2 va NA thi khong."""
    goi = []

    def retriever(*a, **k):
        goi.append(a)
        return [{"text": "x:\ny", "topic_group": "g", "score": 0.9}]

    _run(
        {"title": "Hướng dẫn sạc pin", "body": "bạn nên sạc ô tô điện đúng cách.",
         "summary": ""},
        rules=RULES, judge_bv6=None, retriever=retriever,
    )
    assert goi == [], f"khong duoc truy van khi khong co loi, da goi {len(goi)} lan"
    print("[PASS] khong co loi -> khong truy van KB")


def test_corpus_khong_co_chuan_xung_ho_thi_bv4_na():
    """Truong hop THAT cua du an: 16 bai BRAND khong thong nhat xung ho nen
    brand_rules.json co address_form = None. BV4 phai tra NA, KHONG phai 0 -
    khong duoc phat bai viet vi corpus khong co chuan."""
    rules = dict(RULES, address_form=None)
    kq = _run(
        {"title": "Hướng dẫn", "body": "bạn nên sạc pin.", "summary": ""}, rules=rules
    )
    assert _muc(kq, "BV4") is None, kq["criteria"]
    print("[PASS] corpus khong co chuan xung ho -> BV4 = NA")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_bv1_ba_cho_sai_muc_0,
        test_bv1_mot_cho_sai_muc_1,
        test_bv1_viet_dung_muc_2,
        test_bv1_khong_nhac_model_la_na,
        test_bv2_bien_the_thieu_so,
        test_bv7_tu_bi_loai,
        test_bv3_lan_hai_kieu_xung_ho,
        test_bv5_title_viet_hoa_toan_bo,
        test_bv6_khong_co_judge_la_na,
        test_bai_rong_tra_none,
        test_loi_o_hai_field_sinh_hai_issue,
        test_trich_dan_de_rieng_khong_gop_vao_type,
        test_muc_2_va_na_khong_sinh_issue,
        test_tat_dinh_nam_lan,
        test_bv7_thoa_man_rong_la_na,
        test_bv7_dat_khi_bai_co_ban_toi_khai_niem,
        test_bv6_judge_tra_muc,
        test_bv6_judge_loi_thi_na_khong_phai_0,
        test_bang_chung_duoc_dinh_vao_suggestion,
        test_retriever_loi_khong_lam_sap_agent,
        test_bang_chung_khong_dinh_cho_tieu_chi_dat,
        test_corpus_khong_co_chuan_xung_ho_thi_bv4_na,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
