"""Test he baseline single-agent cho E3 (evaluation-plan.md muc 4.3).

Chay: .venv\\Scripts\\python.exe scripts\\test_eval_baseline_single.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from agents import brand_voice as bv  # noqa: E402
from agents import compliance as cp  # noqa: E402
from agents import content_quality as cq  # noqa: E402
from agents import fact_check, seo  # noqa: E402
from eval_baseline_single import PROMPT_GOP, SCHEMA_GOP, bo_phat_lai  # noqa: E402

_hong = False


def check(ten, thuc, mong):
    global _hong
    if thuc != mong:
        _hong = True
        print(f"[FAIL] {ten}: mong {mong!r}, thuc {thuc!r}")
    else:
        print(f"[PASS] {ten}")


def kiem(ten, dieu_kien, chi_tiet=""):
    global _hong
    if dieu_kien:
        print(f"[PASS] {ten}")
    else:
        _hong = True
        print(f"[FAIL] {ten}" + (f" - {chi_tiet}" if chi_tiet else ""))


GOP = {
    "cq": {"loi": [{"ma": "CQ1"}], "criteria": [{"id": "CQ6", "muc": "2"}]},
    "seo": {"main_keyword": "sac pin", "criteria": [{"id": "SEO2", "muc": "2"}]},
    "bv6": {"level": 1, "evidence": "abc", "reason": "hoi trang trong"},
    "cp": {"criteria": [{"id": "CP2", "muc": "2"}]},
}


# --- DIEU PHOI SLICE: phuc vu nham slice = ket qua rac ma khong ai thay ---
# Bon agent deu goi call_agent(prompt, noi_dung, schema). Bo phat lai phai
# tra ve DUNG mieng cua agent dang goi, nhan dien bang chinh doi tuong prompt
# chu khong phai bang thu tu goi - thu tu goi doi la sai lang le.

goi_that = []


def _that(prompt, noi_dung, schema, **kw):
    goi_that.append(prompt)
    return {"claims": [], "verdicts": []}


phat = bo_phat_lai(GOP, call_agent_that=_that)

check("prompt CQ -> mieng cq", phat(cq._LLM_PROMPT, "x", cq._LLM_SCHEMA), GOP["cq"])
check("prompt SEO -> mieng seo", phat(seo._LLM_PROMPT, "x", seo._LLM_SCHEMA), GOP["seo"])
check("prompt BV6 -> mieng bv6", phat(bv._BV6_PROMPT, "x", bv._BV6_SCHEMA), GOP["bv6"])
check("prompt CP -> mieng cp", phat(cp._LLM_PROMPT, "x", cp._LLM_SCHEMA), GOP["cp"])

check("khong goi LLM that cho 4 agent", goi_that, [])

# CP3 (fact_check) KHONG gop vao mot lan goi: no can tra KB va co hai prompt
# rieng. Phai cho di tiep toi ham that, neu khong CP3 im lang tra rong va
# fact-check bien mat khoi he baseline ma khong ai biet.
phat(fact_check._EXTRACT_PROMPT, "x", fact_check._EXTRACT_SCHEMA)
phat(fact_check._COMPARE_PROMPT, "x", fact_check._COMPARE_SCHEMA)
check("prompt fact_check di tiep toi ham that", len(goi_that), 2)

# Prompt la -> NEM LOI, tuyet doi khong tra bua mot mieng nao. Them prompt
# thu 5 ma quen khai bao thi phai vo ngay, khong duoc cham tiep bang du lieu
# cua agent khac.
try:
    phat("mot prompt chua tung khai bao", "x", {})
    kiem("prompt la -> nem loi", False, "khong nem gi ca")
except Exception as e:
    kiem("prompt la -> nem loi", True)
    print(f"       ({type(e).__name__}: {str(e)[:60]})")


# --- PROMPT/SCHEMA GOP phai phu du 4 phan --------------------------------
for k in ("cq", "seo", "bv6", "cp"):
    kiem(f"SCHEMA_GOP co phan {k!r}", k in SCHEMA_GOP["properties"])
check("SCHEMA_GOP doi du 4 phan", sorted(SCHEMA_GOP["required"]),
      ["bv6", "cp", "cq", "seo"])

# Prompt gop phai chua NGUYEN VAN dinh nghia tieu chi cua ca 4 agent: neu
# viet lai bang loi khac thi E3 do "prompt viet lai" chu khong do "gop mot
# lan goi", tuc so sanh mat y nghia.
for ten, p in [("CQ", cq._LLM_PROMPT), ("SEO", seo._LLM_PROMPT),
               ("BV6", bv._BV6_PROMPT), ("CP", cp._LLM_PROMPT)]:
    kiem(f"PROMPT_GOP chua nguyen van prompt {ten}", p in PROMPT_GOP)

sys.exit(1 if _hong else 0)
