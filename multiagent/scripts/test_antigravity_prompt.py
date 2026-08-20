r"""Kiem tra dac ta giao cho Antigravity khong nhac toi thu khong ton tai.

Vi sao can: dac ta la thu DUY NHAT agent viet UI doc. No khong doc code cua
chung ta. Mot ten truong go sai hay mot ham bia ra trong dac ta se thanh code
sai ma `tsc` khong the bat - vi agent se tu tao ra thu con thieu, hoac im lang
bo qua.

Da xay ra that hai lan:
- Dac ta nhac `formatText` cua lib/format.ts; ham do khong he ton tai
  (2026-08-21, bat duoc bang tay truoc khi gui di).
- openapi.json khong khai bao query param, agent doan `external_content_id`
  va `date_from`; server bo qua IM LANG (2026-08-18).

Hai chieu kiem o day:
1. Moi ten truong snake_case trong dau backtick phai co that trong openapi.json
   (hoac nam trong danh sach gia tri hop le).
2. Moi ham `formatX`/`useX` duoc nhac phai co that trong console_ui/src
   (hoac la ham dung san cua React/TanStack).

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_antigravity_prompt.py
"""
import json
from pathlib import Path
import re
import sys


GOC = Path(__file__).resolve().parents[2]
DAC_TA = GOC / "docs" / "console-ui" / "antigravity-prompt.md"
OPENAPI = GOC / "multiagent" / "console_ui" / "openapi.json"
SRC = GOC / "multiagent" / "console_ui" / "src"

# Token snake_case la GIA TRI enum hoac MA LOI, khong phai ten truong.
GIA_TRI_HOP_LE = {
    "needs_revision",      # gia tri cua decision
    "admin_retry",         # gia tri cua source
    "auth_failed",         # ma loi cua connector
    "cost_not_confirmed",  # ma loi cua Console API
    "login_success",       # action trong so kiem toan
    "password_changed",
    "password_rejected",
    "external_id",         # query param, khong phai truong response
}

# Ham dung san, khong phai cua repo nay.
HAM_DUNG_SAN = {"useEffect", "useMutation", "useQuery", "useState", "useMemo"}


def _truong_trong_openapi() -> set[str]:
    schema = json.loads(OPENAPI.read_text(encoding="utf-8"))
    ten: set[str] = set()

    def di(nut):
        if isinstance(nut, dict):
            for khoa, gia_tri in nut.items():
                if khoa == "properties" and isinstance(gia_tri, dict):
                    ten.update(gia_tri)
                # Query param nam o "parameters", khong phai "properties".
                if khoa == "parameters" and isinstance(gia_tri, list):
                    ten.update(
                        p["name"] for p in gia_tri
                        if isinstance(p, dict) and "name" in p
                    )
                di(gia_tri)
        elif isinstance(nut, list):
            for gia_tri in nut:
                di(gia_tri)

    di(schema)
    return ten


def _export_trong_src() -> set[str]:
    ten: set[str] = set()
    for f in SRC.rglob("*.ts*"):
        ten.update(
            re.findall(
                r"export (?:function|const) ([A-Za-z_][A-Za-z0-9_]*)",
                f.read_text(encoding="utf-8"),
            )
        )
    return ten


def test_moi_ten_truong_deu_co_that_trong_hop_dong():
    doc = DAC_TA.read_text(encoding="utf-8")
    nhac_toi = set(re.findall(r"`([a-z][a-z0-9]*(?:_[a-z0-9]+)+)`", doc))
    la = sorted(nhac_toi - _truong_trong_openapi() - GIA_TRI_HOP_LE)
    assert not la, (
        f"dac ta nhac toi ten truong khong co trong openapi.json: {la}. "
        "Agent viet UI chi doc dac ta, nen ten sai o day thanh code sai ma "
        "tsc khong bat duoc. Neu day la gia tri enum chu khong phai ten "
        "truong, them vao GIA_TRI_HOP_LE kem mot dong giai thich."
    )
    print(f"[PASS] ca {len(nhac_toi)} ten truong trong dac ta deu co that")


def test_moi_ham_dung_chung_deu_co_that():
    doc = DAC_TA.read_text(encoding="utf-8")
    # Quy uoc dat ten cua repo nay: formatX = ham dinh dang, useX = hook.
    nhac_toi = set(
        re.findall(r"`((?:format|use)[A-Z][A-Za-z0-9]*)\(?\)?`", doc)
    )
    la = sorted(nhac_toi - _export_trong_src() - HAM_DUNG_SAN)
    assert not la, (
        f"dac ta nhac toi ham khong ton tai trong console_ui/src: {la}. "
        "Agent se tu viet lai mot ham cung ten - dung thu ma module dung "
        "chung sinh ra de chan."
    )
    print(f"[PASS] ca {len(nhac_toi)} ham dung chung trong dac ta deu co that")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_moi_ten_truong_deu_co_that_trong_hop_dong,
        test_moi_ham_dung_chung_deu_co_that,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
