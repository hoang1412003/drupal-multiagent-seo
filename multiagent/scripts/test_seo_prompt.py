"""Test hop dong: nguong trong system prompt cua SEO Agent phai khop
config/scoring.yaml (no B4 trong docs/technical-debt.md).

VI SAO CAN TEST NAY. config/scoring.yaml sinh ra de "con so chi ton tai o mot
cho". Nhung no bo sot mot ban chep: cac nguong nam TRONG CHUOI system prompt.
Chung khong trong giong hang so nen khong ai di tim o do, va chung DA troi
lech - prompt ghi meta 150-160 trong khi config va rubric deu ghi 140-170.

Hau qua that: label_helper.py sinh ma loi B3 theo dai 140-170, tuc bai co meta
145 hoac 165 ky tu thi GROUND TRUTH noi khong loi, con SEO Agent duoc dan dai
ly tuong la 150-160 nen nhieu kha nang van bao loi. Hai ben do hai thang khac
nhau -> Recall/F1 cua SEO3 lech co he thong khi calibrate (E5).

Test nay lam viec "ra soat ca chuoi prompt" thanh viec cua may, thay vi mot
cau dan trong tai lieu ma lan sau lai quen.

Chay: .venv\\Scripts\\python.exe scripts\\test_seo_prompt.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import config
from agents import seo

_SCORING = config.load()["scoring"]


def test_nguong_meta_khop_config():
    lo, hi = _SCORING["meta_ideal"]
    assert f"{lo}-{hi} ký tự" in seo.SYSTEM_PROMPT, (
        f"prompt phai neu dai meta {lo}-{hi} ky tu theo scoring.meta_ideal"
    )
    print(f"[PASS] meta trong prompt = {lo}-{hi} ky tu, khop scoring.yaml")


def test_nguong_title_khop_config():
    lo, hi = _SCORING["title_ideal"]
    assert f"{lo}-{hi} ký tự" in seo.SYSTEM_PROMPT, (
        f"prompt phai neu dai title {lo}-{hi} ky tu theo scoring.title_ideal"
    )
    print(f"[PASS] title trong prompt = {lo}-{hi} ky tu, khop scoring.yaml")


def test_do_dai_body_khop_config():
    """Rubric SEO7: <300 tu = muc 0, >=600 tu = muc 2. Prompt phai neu moc
    DAT (600), khong phai moc 'qua te' (300) - neu 300 thi LLM duoc dan rang
    mot bai 350 tu la du dai, trong khi rubric xep no o muc 1."""
    n = _SCORING["body_min_words"]
    assert f"{n} từ" in seo.SYSTEM_PROMPT, (
        f"prompt phai neu moc dat {n} tu theo scoring.body_min_words"
    )
    print(f"[PASS] do dai body trong prompt = {n} tu, khop scoring.yaml")


def test_khong_con_nguong_cu_150_160():
    """Chan dung con so da gay ra no B4, de no khong quay lai qua mot lan
    copy-paste tu bang cu."""
    for cu in ("150-160", "~300 từ"):
        assert cu not in seo.SYSTEM_PROMPT, f"nguong cu '{cu}' con trong prompt"
    print("[PASS] khong con nguong cu 150-160 / ~300 tu trong prompt")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_nguong_meta_khop_config,
        test_nguong_title_khop_config,
        test_do_dai_body_khop_config,
        test_khong_con_nguong_cu_150_160,
    ):
        try:
            fn()
        except AssertionError as e:
            failed = True
            print(f"[FAIL] {fn.__name__}: {e}")
    sys.exit(1 if failed else 0)
