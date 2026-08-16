"""E3 - he baseline single-agent: GOP 4 lan goi LLM thanh MOT.

Cau hoi nghien cuu (evaluation-plan.md muc 4.3): kien truc 4 agent co that
su hon 1 agent lam tat khong? Khong co tieu chi dat/truot - single-agent
thang cung la mot phat hien dang bao cao.

THIET KE DA CHON (2026-08-16): gop dung 16 tieu chi VON DO LLM CHAM thanh
mot lan goi. 17 tieu chi do bang may (dem ky tu, regex, internal link) giu
NGUYEN Y HET o ca hai he. Nho vay bien so duy nhat la SO LAN GOI LLM, khong
tron voi "may do hay LLM do". Day cung la thiet ke thuc te hon: khong ky su
nao bat LLM dem ky tu tieu de khi regex lam duoc.

CACH TIEM - vi sao khong tiem o tang `danh_gia_llm`:
moi agent tu hop thuc hoa output LLM (loai trich dan bia, ep enum, chan mo
ta rong). Tiem o tang `danh_gia_llm` la BO QUA het khau do, cho he baseline
mot loi the khong cong bang. Nen tiem sau hon: thay `call_agent` trong TUNG
module agent, phuc vu tu ket qua da gop. Agent van chay nguyen ven duong
hop thuc hoa cua no, chi khac la khong con goi mang.

Khong sua mot dong nao trong duong cham diem -> E1/E5/E6 van hop le.

⚠️ CP3 (fact-check) KHONG gop: no tra KB va co hai prompt rieng. He baseline
vi vay goi 1 (gop) + 2 (CP3) = 3 lan/bai, so voi 5,6 lan do duoc o E1. Phai
neu dung con so nay khi bao cao, khong duoc noi "1 so voi 4".

Chay (tu multiagent/):
    HF_HUB_OFFLINE=1 .venv\\Scripts\\python.exe scripts\\eval_baseline_single.py
"""
import os

from agents import brand_voice as _bv
from agents import compliance as _cp
from agents import content_quality as _cq
from agents import seo as _seo

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Prompt gop = NOI NGUYEN VAN bon prompt hien hanh. Co y khong viet lai bang
# loi khac: viet lai thi E3 do "prompt moi viet the nao" chu khong do "gop
# mot lan goi", va so sanh mat y nghia.
PROMPT_GOP = (
    "Bạn chấm MỘT bài viết trên BỐN khía cạnh trong CÙNG một lần trả lời.\n"
    "Bốn bộ tiêu chí dưới đây độc lập nhau; áp dụng đúng từng bộ, không trộn.\n"
    "Trả về object có đúng bốn khoá: `cq`, `seo`, `bv6`, `cp`.\n\n"
    "════════ PHẦN 1/4 → khoá `cq` ════════\n" + _cq._LLM_PROMPT + "\n\n"
    "════════ PHẦN 2/4 → khoá `seo` ════════\n" + _seo._LLM_PROMPT + "\n\n"
    "════════ PHẦN 3/4 → khoá `bv6` ════════\n" + _bv._BV6_PROMPT + "\n\n"
    "════════ PHẦN 4/4 → khoá `cp` ════════\n" + _cp._LLM_PROMPT
)

SCHEMA_GOP = {
    "type": "object",
    "properties": {
        "cq": _cq._LLM_SCHEMA,
        "seo": _seo._LLM_SCHEMA,
        "bv6": _bv._BV6_SCHEMA,
        "cp": _cp._LLM_SCHEMA,
    },
    "required": ["cq", "seo", "bv6", "cp"],
    "additionalProperties": False,
}

# Prompt -> khoa trong ket qua gop. Nhan dien bang CHINH DOI TUONG prompt,
# khong phai bang thu tu goi: thu tu goi doi la sai lang le.
_THEO_PROMPT = {
    id(_cq._LLM_PROMPT): "cq",
    id(_seo._LLM_PROMPT): "seo",
    id(_bv._BV6_PROMPT): "bv6",
    id(_cp._LLM_PROMPT): "cp",
}


def bo_phat_lai(gop: dict, call_agent_that=None):
    """Tra ve ham thay `call_agent`, phuc vu tu ket qua da gop.

    Prompt cua fact_check (CP3) di tiep toi ham that: CP3 khong gop duoc vi
    no tra KB. Prompt la thi NEM LOI - them prompt thu nam ma quen khai bao
    phai vo ngay, tuyet doi khong duoc cham tiep bang du lieu cua agent khac.
    """
    from ai_core import call_agent as _mac_dinh

    that = call_agent_that or _mac_dinh

    def phat(system_prompt, noi_dung, schema, **kw):
        khoa = _THEO_PROMPT.get(id(system_prompt))
        if khoa is not None:
            return gop[khoa]
        from agents import fact_check
        if system_prompt in (fact_check._EXTRACT_PROMPT,
                             fact_check._COMPARE_PROMPT):
            return that(system_prompt, noi_dung, schema, **kw)
        raise ValueError(
            "eval_baseline_single: prompt chua khai bao trong _THEO_PROMPT. "
            "Them prompt moi thi phai them o day, neu khong he baseline se "
            "cham bang du lieu sai."
        )

    return phat


def _noi_dung_gop(fields: dict, doan_mau: str) -> str:
    """Noi dung cho lan goi gop = hop cua nhung gi 4 agent von gui rieng.

    ⚠️ Co MOT sai lech co y so voi he 4 agent: SEO goi rieng dung
    `boc_an_o=("body",)` de boc chu an, con CQ/CP thi khong. Lan goi gop chi
    dung duoc mot bien the, va o day chon theo CQ/CP (khong boc) vi do la
    da so. Nghia la SEO o he baseline nhin thay body chua boc chu an. Ghi ra
    day vi day la khac biet ngoai "so lan goi", phai neu khi bao cao.
    """
    from agents import seo as _s
    import prompt_builder
    import seo_analysis as sa

    cac_field = ("title", "body", "summary", "url_alias",
                 "meta_description", "image_alt")
    noi_dung, _ = prompt_builder.boc_noi_dung(fields, cac_field)

    body = fields.get("body", "") or ""
    b = sa.do_body(body)
    noi_dung += (
        f"\n\n<dau_bai>{sa.dau_body(body)}</dau_bai>"
        f"\n<danh_sach_heading>{' | '.join(b['heading'])}</danh_sach_heading>"
        f"\n\nChỉ chấm các mã SEO sau: {', '.join(_s._MA_LLM)}"
    )
    if doan_mau:
        noi_dung += f"\n\n<doan_mau_brand>\n{doan_mau}\n</doan_mau_brand>"
    return noi_dung


def _doan_mau_bv6(fields: dict, content_type: str, langcode: str) -> str:
    """Lay doan mau brand y het `brand_voice._judge_formality` lam.

    Buoc nay KHONG goi LLM (chi truy van vector KB) nen gop duoc vao truoc.
    Phai giu nguyen truy van/top_k/collection, neu khong he baseline cham
    BV6 tren ngu canh khac he 4 agent va so sanh mat y nghia.
    """
    truy_van = fields.get("title") or fields.get("summary") or ""
    if not truy_van.strip():
        return ""
    hits = _bv.retrieve(truy_van, content_type, langcode, top_k=3,
                        collection_name=_bv.COLLECTION_BRAND)
    return "\n\n".join(f"[Đoạn mẫu {i + 1}] {h['text']}"
                       for i, h in enumerate(hits))


def cham_mot_bai(fields: dict, *, content_type: str = "cam_nang",
                 langcode: str = "vi") -> dict:
    """Cham mot bai bang he baseline. Cung hinh dang voi eval_calibration."""
    import ai_core

    ai_core.USAGE_LOG.clear()
    doan_mau = _doan_mau_bv6(fields, content_type, langcode)
    gop = ai_core.call_agent(PROMPT_GOP, _noi_dung_gop(fields, doan_mau),
                             SCHEMA_GOP)

    phat = bo_phat_lai(gop)
    cu = {m: m.call_agent for m in (_cq, _seo, _bv, _cp)}
    for m in cu:
        m.call_agent = phat
    try:
        diem, chi_tiet, co_critical = {}, {}, False
        for ten, ham in (("content_quality", _cq.run), ("seo", _seo.run),
                         ("brand", _bv.run), ("compliance", _cp.run)):
            try:
                r = ham(fields, content_type=content_type, langcode=langcode)
            except Exception as e:
                print(f"      !! {ten}: {type(e).__name__}: {str(e)[:60]}")
                r = None
            diem[ten] = r["score"] if r else None
            chi_tiet[ten] = r
            if ten == "compliance" and r:
                co_critical = any(f.get("severity") == "critical"
                                  for f in r.get("flags", []))
    finally:
        for m, ham in cu.items():
            m.call_agent = ham

    return {"diem": diem, "co_critical": co_critical,
            "usage": list(ai_core.USAGE_LOG), "chi_tiet": chi_tiet}


def cham_bo(path: str) -> dict:
    """Cham gold set bang he baseline, resumable, guard prompt_version."""
    import json

    from eval_calibration import (doc_bai, gold_ids, nap_ket_qua,
                                  prompt_version)

    pv = prompt_version()
    da_co = nap_ket_qua(path) if os.path.isfile(path) else {}
    ids = gold_ids()
    for i, sid in enumerate(ids, 1):
        if sid in da_co:
            continue
        print(f"  [{i}/{len(ids)}] {sid} ...", flush=True)
        da_co[sid] = cham_mot_bai(doc_bai(sid))
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"_meta": {"prompt_version": pv,
                                 "he": "baseline-single-agent"}, **da_co},
                      f, ensure_ascii=False, indent=1)
    return da_co
