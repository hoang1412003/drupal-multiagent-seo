"""Test rubric CP1-CP8 cua Compliance Agent (docs/rubrics.md muc 6).

Khong goi LLM, khong doc KB - tiem danh_gia_llm/danh_gia_cp3 gia.

Trong tam la ngu nghia NA, vi do la cho phat sinh loi "diem mien phi" ma
rubrics.md muc 2.2 va 8.1 canh bao: NA bi tinh thanh DAT thi moi bai khong
nhac toi chu de deu duoc cong diem.

Chay: .venv\\Scripts\\python.exe scripts\\test_compliance_rubric.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import text_utils
from agents import compliance
from scoring import score_from_criteria, severity_for
from text_utils import strip_html

# Bai co so lieu: kich hoat CP5 (km), CP8 (so + don vi). Khong kich hoat CP6
# vi khong co moc thoi gian nao di kem "sac".
BODY = "VF 8 chạy được 420 km mỗi lần sạc theo chuẩn NEDC."

# Bai khong co con so nao: CP5, CP6, CP8 deu NA do MAY ket luan.
BODY_KHONG_SO = "Hướng dẫn sạc pin an toàn cho xe điện đúng cách."


def _llm(muc_theo_ma: dict, evidence: str = BODY):
    """Gia lap LLM: tra mot muc co san cho moi ma."""
    def fn(fields, text_theo_field):
        return {
            ma: compliance._tieu_chi(
                ma,
                compliance._hop_thuc_hoa(ma, muc, evidence, text_theo_field),
                ([{"field": "body", "text": evidence}] if muc in (0, 1) else []),
                "ly do",
            )
            for ma, muc in muc_theo_ma.items()
        }
    return fn


def _cp3_na(fields, **k):
    return {"level": None, "occurrences": [], "reason": ""}


def _muc(result, ma):
    return next(c["level"] for c in result["criteria"] if c["id"] == ma)


# --------------------------------------------------------------- bang severity


def test_bang_severity_tra_dung():
    assert severity_for("CP1", 0) == "critical"
    assert severity_for("CP4", 0) == "critical"
    assert severity_for("CP5", 0) == "medium"
    assert severity_for("CP8", 0) == "low"
    print("[PASS] muc 0 -> severity tra dung bang")


def test_cp3_muc_1_khong_bao_gio_critical():
    """rubrics.md muc 6.2: 'khong kiem chung duoc' != 'sai'. KB chi co thong
    so mot so model; coi muc 1 la critical se tu choi oan moi bai nhac model
    ngoai KB - loi he thong, khong phai loi noi dung."""
    assert severity_for("CP3", 0) == "critical", "so lieu LECH thi van critical"
    assert severity_for("CP3", 1) == "low", "khong tra duoc thi KHONG duoc veto"
    print("[PASS] CP3 muc 1 -> low, khong kich hoat veto")


def test_moi_muc_1_deu_la_low():
    for ma in ("CP1", "CP2", "CP3", "CP4", "CP5", "CP6", "CP7", "CP8"):
        assert severity_for(ma, 1) == "low", ma
    print("[PASS] moi tieu chi o muc 1 -> low (dat mot phan khong chan xuat ban)")


# ------------------------------------------------------------------ ngu nghia NA


def test_na_khong_duoc_tinh_la_dat():
    """Bai khong nhac khuyen mai -> CP4 la NA -> bi loai khoi CA tu so LAN mau
    so. Neu tinh thanh dat thi diem cua bai nay bang diem bai co khuyen mai
    ghi day du - tieu chi thanh hang so."""
    chi_cp1 = [{"id": "CP1", "level": 2}, {"id": "CP4", "level": None}]
    ca_hai_dat = [{"id": "CP1", "level": 2}, {"id": "CP4", "level": 2}]
    assert score_from_criteria(chi_cp1) == 100.0
    assert score_from_criteria(ca_hai_dat) == 100.0
    # Diem bang nhau la dung. Cho khac nhau la MAU SO:
    mot_loi_voi_na = [{"id": "CP1", "level": 0}, {"id": "CP4", "level": None}]
    mot_loi_voi_dat = [{"id": "CP1", "level": 0}, {"id": "CP4", "level": 2}]
    assert score_from_criteria(mot_loi_voi_na) == 0.0, "NA bi loai khoi mau so"
    assert score_from_criteria(mot_loi_voi_dat) == 50.0, "muc 2 nam trong mau so"
    print("[PASS] NA bi loai khoi mau so, khong duoc cong diem mien phi")


def test_khong_trich_dan_duoc_thi_tieu_chi_co_dieu_kien_thanh_na():
    """Quy tac chong bia (rubrics.md muc 2.5) + chong diem mien phi (muc 8.1).

    LLM cham CP5 = 2 nhung trich mot cau KHONG co trong bai -> khong chung
    minh duoc bai co ban toi tam hoat dong -> NA, TUYET DOI khong phai muc 2.
    """
    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": 2},
                          evidence="cau nay hoan toan khong co trong bai"),
        danh_gia_cp3=_cp3_na,
    )
    for ma in ("CP4", "CP7"):
        assert _muc(result, ma) is None, f"{ma} phai la NA, dang la {_muc(result, ma)}"
    print("[PASS] muc 2 khong trich dan duoc -> NA (khong phai muc 2)")


def test_cp2_khong_trich_dan_duoc_thi_ve_muc_2():
    """CP2 la ngoai le: muc 2 cua no nghia la 'khong tim thay vi pham', khong
    co gi de trich. Nguoc lai, ha muc ma khong trich duoc thi khong duoc ha."""
    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 0, "CP4": 2, "CP7": 2},
                          evidence="Tesla thua xa VinFast"),   # khong co trong bai
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP2") == 2, "bia vi pham -> phai quay ve muc 2"
    print("[PASS] CP2 ha muc ma khong trich duoc -> quay ve muc 2")


def test_trich_dan_co_that_thi_giu_nguyen_muc():
    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP4": 2, "CP7": 1},
                          evidence="chạy được 420 km"),        # co that trong bai
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP7") == 1, "trich dan co that thi giu nguyen muc"
    assert _muc(result, "CP4") == 2
    print("[PASS] trich dan nguyen van co that -> giu nguyen muc LLM cham")


# ----------------------------------------------------------------- CP1 (may)


def test_cp1_bat_tu_cam_va_sinh_flag_critical():
    result = compliance.run(
        {"title": "VF 3 tốt nhất phân khúc", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({ma: None for ma in compliance._MA_LLM}),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP1") == 0
    cp1 = [f for f in result["flags"] if "tuyệt đối" in f["rule"]]
    assert cp1 and cp1[0]["severity"] == "critical", result["flags"]
    assert cp1[0]["field"] == "title", cp1[0]
    print("[PASS] CP1 bat tu cam -> muc 0 -> flag critical dung field")


def test_cp1_sach_thi_muc_2():
    result = compliance.run(
        {"title": "Huong dan sac pin", "body": BODY_KHONG_SO, "meta_description": ""},
        danh_gia_llm=_llm({ma: None for ma in compliance._MA_LLM}),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP1") == 2
    assert result["score"] == 100.0, f"chi CP1 ap dung, dat -> 100, got {result['score']}"
    print("[PASS] CP1 sach -> muc 2")


# ------------------------------------------- CP5, CP6, CP8: may quyet dinh NA
#
# Ba tieu chi nay chuyen sang may ngay 2026-08-04 vi E1 do duoc chung la nguon
# dao dong chinh: cau hoi "bai co ban toi chu de nay khong" do LLM tra loi thi
# moi lan mot khac -> mau so nhay -> diem nhay
# (docs/evidence/cp_phan_bo_muc.txt).


def _chay(body, title="", **k):
    return compliance.run(
        {"title": title, "body": body, "meta_description": ""},
        danh_gia_llm=_llm({ma: None for ma in compliance._MA_LLM}),
        danh_gia_cp3=_cp3_na, **k)


def test_cp5_theo_ba_muc():
    assert _muc(_chay("VF 8 đi được 420 km theo chuẩn WLTP."), "CP5") == 2
    assert _muc(_chay("VF 8 đi được 420 km, thực tế có thể khác."), "CP5") == 1
    assert _muc(_chay("VF 8 đi được 420 km một lần sạc."), "CP5") == 0
    print("[PASS] CP5 chuan do -> 2, luu y chung -> 1, khong gi -> 0")


def test_cp5_na_khi_bai_khong_co_claim_km():
    assert _muc(_chay(BODY_KHONG_SO), "CP5") is None
    print("[PASS] CP5 khong co claim km -> NA (may ket luan, khong doi giua cac lan)")


def test_cp6_theo_ba_muc():
    assert _muc(_chay("Sạc DC từ 10% lên 70% mất 30 phút."), "CP6") == 2
    assert _muc(_chay("Sạc bằng trụ DC mất 30 phút."), "CP6") == 1
    assert _muc(_chay("Sạc đầy pin mất 30 phút."), "CP6") == 0
    print("[PASS] CP6 du tru+dai% -> 2, mot trong hai -> 1, khong gi -> 0")


def test_cp6_moc_thoi_gian_xa_chu_sac_thi_khong_tinh():
    """Moc thoi gian phai nam gan chu 'sac'. Bai noi 'bao duong moi 12 thang'
    khong phai claim thoi gian sac."""
    xa = "Bảo dưỡng định kỳ mỗi 12 tháng. " + "x " * 200 + "Trạm sạc phủ toàn quốc."
    assert _muc(_chay(xa), "CP6") is None
    print("[PASS] CP6 moc thoi gian xa chu 'sac' -> khong tinh la claim")


def test_cp8_may_chot_ap_dung_hay_na():
    """Hai chieu ghi de. Bai khong co so lieu -> NA du LLM cham gi. Bai co so
    lieu ma LLM tra NA -> muc 0, vi muc 0 cua CP8 dinh nghia dung la 'co so
    lieu nhung khong neu nguon nao'. G-007 co 66 so lieu ma LLM cham NA."""
    assert _muc(_chay(BODY_KHONG_SO), "CP8") is None, "khong co so lieu -> NA"
    assert _muc(_chay(BODY), "CP8") == 0, "co so lieu ma LLM tra NA -> muc 0"
    print("[PASS] CP8 may chot ap dung; LLM tra NA tren bai co so lieu -> muc 0")


# ------------------------------------------ trich dan nhieu manh (do 2026-08-04)

# Hai cau nam o HAI THE HTML khac nhau. strip_html chen ".\n" vao giua nen
# chung khong bao gio lien mach trong text da boc - day la truong hop that,
# do duoc tren G-008 (docs/evidence/cp_lat_muc_raw.json).
BODY_HAI_KHOI = "<p>Sạc được từ 0 lên 10% mỗi giờ.</p><p>Đây là bộ sạc chậm.</p>"
_TT_HAI_KHOI = {"title": "", "body": strip_html(BODY_HAI_KHOI), "meta_description": ""}


def test_trich_dan_ghep_hai_cau_khac_khoi_van_duoc_chap_nhan():
    """Loi that: 10/20 luot bi loai oan vi doi trich dan phai LIEN MACH.
    Kiem lai tung manh thi ca hai deu co nguyen van trong bai."""
    ev = "Sạc được từ 0 lên 10% mỗi giờ. Đây là bộ sạc chậm."
    assert text_utils.trich_dan_co_that(ev, _TT_HAI_KHOI), \
        "hai cau that o hai khoi HTML phai duoc chap nhan"
    print("[PASS] trich dan ghep 2 cau khac khoi HTML -> chap nhan")


def test_trich_dan_noi_bang_va_van_duoc_chap_nhan():
    """Dang thu hai do duoc: LLM noi hai trich dan bang ' va ' (G-001)."""
    ev = '"Sạc được từ 0 lên 10% mỗi giờ" và "Đây là bộ sạc chậm"'
    assert text_utils.trich_dan_co_that(ev, _TT_HAI_KHOI)
    print("[PASS] trich dan noi bang ' va ' -> chap nhan")


def test_mot_manh_bia_thi_ca_doan_trich_bi_loai():
    """Doi trong: noi long theo manh KHONG duoc bien thanh cho qua. MOI manh
    phai khop, bia nua cau van truot."""
    ev = "Sạc được từ 0 lên 10% mỗi giờ. Xe này tốt nhất thị trường."
    assert not text_utils.trich_dan_co_that(ev, _TT_HAI_KHOI), \
        "mot manh bia -> phai loai ca doan trich"
    print("[PASS] mot manh bia -> loai ca doan trich")


def test_so_thap_phan_khong_bi_cat_thanh_hai_manh():
    """`1.000 km` co dau cham nhung sau no la CHU SO, khong phai khoang trang
    - lookbehind trong _TACH_MANH phai giu nguyen no lam mot manh."""
    tt = {"title": "", "body": "Hành trình dài hơn 1.000 km từ Hà Nội.",
          "meta_description": ""}
    assert text_utils.trich_dan_co_that("dài hơn 1.000 km", tt)
    print("[PASS] so thap phan khong bi cat thanh hai manh")


def test_cp8_ha_muc_ma_khong_trich_duoc_thi_khong_thanh_muc_2():
    """B5 (docs/technical-debt.md): bai CO so lieu, LLM cham CP8 = 0, nhung
    trich mot cau khong co trong bai.

    Sai theo huong nguy hiem nhat neu tra muc 2: tieu chi vua bi nghi vi pham
    lai duoc cong DIEM TOI DA, va `occurrences` rong theo nen dau ra trong y
    het mot bai that su dat - nhin `criteria` khong phat hien duoc.

    Muc 0 moi dung, va dung theo chinh lap luan cua _chot_cp8: may da xac nhan
    bai co so lieu, LLM khong chi ra duoc nguon nao -> do la dinh nghia cua
    muc 0. Day KHONG phai truong hop cua CP4/CP7 (-> NA), vi voi CP8 thi cau
    hoi 'bai co ban toi chu de nay khong' da do MAY chot, khong con phu thuoc
    vao viec LLM trich dan duoc hay khong."""
    result = compliance.run(
        {"title": "", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({"CP2": 2, "CP8": 0},
                          evidence="cau nay hoan toan khong co trong bai"),
        danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP8") == 0, (
        f"CP8 ha muc ma khong trich duoc -> phai la muc 0, "
        f"dang la {_muc(result, 'CP8')}"
    )
    print("[PASS] CP8 ha muc ma khong trich duoc -> muc 0 (khong phai muc 2)")


def test_cp8_llm_hong_thi_khong_phat_thanh_muc_0():
    """Ranh gioi quan trong: 'LLM tra NA' khac 'LLM chua chay'. Loi ha tang
    khong duoc bien thanh muc 0."""
    result = compliance.run(
        {"title": "VF 3 tốt nhất phân khúc", "body": BODY, "meta_description": ""},
        danh_gia_llm=_boom, danh_gia_cp3=_cp3_na,
    )
    assert _muc(result, "CP8") is None, f"LLM hong -> CP8 phai NA, got {_muc(result,'CP8')}"
    assert _muc(result, "CP5") == 2, "CP5 la regex nen van cham duoc khi LLM hong"
    print("[PASS] LLM hong -> CP8 NA; CP5/CP6 (regex) van cham duoc")


# --------------------------------------------- M3: khong tu lam mu chinh minh


def test_tu_cam_giau_trong_binh_luan_html_van_bi_bat():
    """Loi that, do duoc truoc khi sua: strip_html khop tron '<!-- tot nhat -->'
    bang regex '<[^>]+>' va xoa luon chu ben trong, nen cum tu cam giau trong
    binh luan HTML di qua blacklist CP1 ma khong bi bat lan nao.

    Nguoi duyet doc bai da render nen KHONG THAY doan nay - do la ly do no
    nguy hiem (docs/prompt-injection.md muc 2)."""
    result = _chay("<p>Nội dung sạch</p><!-- xe này tốt nhất thị trường -->")
    assert _muc(result, "CP1") == 0, "tu cam trong binh luan HTML phai bi bat"
    assert any(f["severity"] == "critical" for f in result["flags"]), result["flags"]
    print("[PASS] tu cam giau trong binh luan HTML van bi CP1 bat")


def test_tu_cam_giau_trong_the_display_none_van_bi_bat():
    """Kiem CA HAI chieu cua duong quet phan an, sau khi CP1 tach muc 0/1
    (2026-08-10).

    Bai cu chi kiem mot payload 'san pham so 1' va doi muc 0. Cum do khong neu
    pham vi so sanh nen nay ra muc 1 - nhung dieu test NAY phai khoa lai la
    'duong quet phan an CO cham toi CP1', khong phai 'cum nay critical'. Nen
    kiem ca hai payload thay vi noi long mot phep khang dinh:

      - giau claim CO pham vi   -> muc 0 + flag critical  (tinh chat an ninh)
      - giau cum KHONG pham vi  -> muc 1, VAN sinh flag   (khong bi nuot im lang)

    Chat hon ban cu: ban cu khong he kiem truong hop thu hai.
    """
    co_pham_vi = _chay(
        '<p>Sạch</p><div style="display:none">sản phẩm số 1 Việt Nam</div>'
    )
    assert _muc(co_pham_vi, "CP1") == 0, "claim an co pham vi phai la muc 0"
    assert any(f["severity"] == "critical" for f in co_pham_vi["flags"]), \
        co_pham_vi["flags"]

    khong_pham_vi = _chay(
        '<p>Sạch</p><div style="display:none">sản phẩm số 1</div>'
    )
    assert _muc(khong_pham_vi, "CP1") == 1, "cum an khong pham vi -> muc 1"
    assert any(f["rule"].startswith("So sánh tuyệt đối")
               for f in khong_pham_vi["flags"]), \
        "van phai sinh flag de nguoi duyet thay, du khong veto"
    print("[PASS] tu cam giau trong the display:none van bi CP1 bat (ca 2 chieu)")


def test_bai_sach_khong_bi_bat_nham():
    """Doi trong cua hai test tren: them duong quet moi khong duoc sinh flag
    gia tren bai binh thuong."""
    result = _chay("<p>Hướng dẫn sạc pin an toàn</p><!-- ghi chú biên tập -->")
    assert _muc(result, "CP1") == 2, result["flags"]
    print("[PASS] binh luan HTML vo hai khong sinh flag gia")


# ------------------------------------------------- diem va flag cung mot nguon


def test_diem_va_flag_khong_con_mau_thuan():
    """Loi cu (rubrics.md muc 6.1 diem 1): score lay tu LLM con flags cong
    them tu blacklist, nen mot bai dinh 3 flag critical van co the mang
    score = 95. Gio ca hai deu sinh tu cung bo criteria."""
    result = compliance.run(
        {"title": "VF 3 tốt nhất, số 1, không đối thủ", "body": BODY_KHONG_SO,
         "meta_description": ""},
        danh_gia_llm=_llm({ma: None for ma in compliance._MA_LLM}),
        danh_gia_cp3=_cp3_na,
    )
    co_critical = any(f["severity"] == "critical" for f in result["flags"])
    assert co_critical, result["flags"]
    assert result["score"] == 0.0, f"co flag critical thi khong the diem cao: {result['score']}"
    print("[PASS] co flag critical -> diem khong the cao (mot nguon duy nhat)")


# --------------------------------------------------------- suy giam co kiem soat


def _boom(fields, text_theo_field):
    raise RuntimeError("het han muc API")


def test_llm_loi_va_khong_thay_vi_pham_thi_tra_none():
    """Loi that, bat duoc luc chay E1 ngay 2026-08-04: API het han muc giua
    chung, 6/8 tieu chi thanh NA, chi con CP1 (regex) chay. Bai sach tu cam
    ra Compliance = 100 - tuc bao 'tuan thu hoan toan' cho mot bai moi chi
    duoc do tu khoa. Phai tra None = CHUA XAC MINH DUOC."""
    result = compliance.run(
        {"title": "Huong dan sac pin", "body": BODY, "meta_description": ""},
        danh_gia_llm=_boom, danh_gia_cp3=_cp3_na,
    )
    assert result is None, f"phai la None (chua xac minh duoc), got {result}"
    print("[PASS] LLM loi + khong thay vi pham -> None, khong phai 100 diem")


def test_llm_loi_nhung_co_vi_pham_cung_thi_van_tra_ket_qua():
    """Huong nguoc lai: da co bang chung cung (CP1 khop tu cam) thi du lieu
    DA du de tu choi. Danh mat mot veto nguy hiem hon han so voi bao 'chua
    xac minh duoc'."""
    result = compliance.run(
        {"title": "VF 3 tốt nhất phân khúc", "body": BODY, "meta_description": ""},
        danh_gia_llm=_boom, danh_gia_cp3=_cp3_na,
    )
    assert result is not None, "co vi pham cung thi phai giu lai ket qua"
    assert any(f["severity"] == "critical" for f in result["flags"]), result["flags"]
    for ma in compliance._MA_LLM:
        assert _muc(result, ma) is None, f"{ma} phai la NA (ha tang hong)"
    print("[PASS] LLM loi nhung CP1 bat duoc vi pham -> van veto duoc")


def test_khong_tieu_chi_nao_ap_dung_thi_tra_none():
    """Tra None = CHUA CHAM DUOC, khac han 0 diem. Aggregator gap None thi
    khong bao gio tu dong publish."""
    def chi_na(fields, text_theo_field):
        return {ma: compliance._tieu_chi(ma, None) for ma in compliance._MA_LLM}

    result = compliance.run(
        {"title": "", "body": "   ", "meta_description": ""},
        danh_gia_llm=chi_na, danh_gia_cp3=_cp3_na,
    )
    assert result is None, result
    print("[PASS] bai rong -> None (chua cham duoc), khong phai 0 diem")


def test_cp3_loi_kb_thanh_na_khong_phai_0():
    def boom(fields, **k):
        raise RuntimeError("KB chua dung")

    result = compliance.run(
        {"title": "Huong dan sac pin", "body": BODY, "meta_description": ""},
        danh_gia_llm=_llm({ma: None for ma in compliance._MA_LLM}),
        danh_gia_cp3=boom,
    )
    assert _muc(result, "CP3") is None, "loi ha tang -> NA, khong phat len noi dung"
    print("[PASS] KB loi -> CP3 NA, khong phai muc 0")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_bang_severity_tra_dung,
        test_cp3_muc_1_khong_bao_gio_critical,
        test_moi_muc_1_deu_la_low,
        test_na_khong_duoc_tinh_la_dat,
        test_khong_trich_dan_duoc_thi_tieu_chi_co_dieu_kien_thanh_na,
        test_cp2_khong_trich_dan_duoc_thi_ve_muc_2,
        test_trich_dan_co_that_thi_giu_nguyen_muc,
        test_cp1_bat_tu_cam_va_sinh_flag_critical,
        test_cp1_sach_thi_muc_2,
        test_cp5_theo_ba_muc,
        test_cp5_na_khi_bai_khong_co_claim_km,
        test_cp6_theo_ba_muc,
        test_cp6_moc_thoi_gian_xa_chu_sac_thi_khong_tinh,
        test_cp8_may_chot_ap_dung_hay_na,
        test_trich_dan_ghep_hai_cau_khac_khoi_van_duoc_chap_nhan,
        test_trich_dan_noi_bang_va_van_duoc_chap_nhan,
        test_mot_manh_bia_thi_ca_doan_trich_bi_loai,
        test_so_thap_phan_khong_bi_cat_thanh_hai_manh,
        test_cp8_ha_muc_ma_khong_trich_duoc_thi_khong_thanh_muc_2,
        test_cp8_llm_hong_thi_khong_phat_thanh_muc_0,
        test_tu_cam_giau_trong_binh_luan_html_van_bi_bat,
        test_tu_cam_giau_trong_the_display_none_van_bi_bat,
        test_bai_sach_khong_bi_bat_nham,
        test_diem_va_flag_khong_con_mau_thuan,
        test_llm_loi_va_khong_thay_vi_pham_thi_tra_none,
        test_llm_loi_nhung_co_vi_pham_cung_thi_van_tra_ket_qua,
        test_khong_tieu_chi_nao_ap_dung_thi_tra_none,
        test_cp3_loi_kb_thanh_na_khong_phai_0,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
