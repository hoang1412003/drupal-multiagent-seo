r"""Doi chieu brief Stitch voi hop dong openapi.json.

Vi sao can: brief khong dinh kem anh admin cu, nen prompt la rang buoc duy nhat
len Stitch. Mot ten truong bia ra trong brief se thanh mot cot trong thiet ke,
roi thanh code khong chay duoc ben frontend. Script nay chan dieu do o goc.

Kiem hai chieu:
1. Thieu  - truong co trong hop dong nhung khong duoc nhac trong brief.
2. Thua   - token kieu snake_case trong brief nhung khong co trong hop dong va
            khong nam trong danh sach gia tri hop le.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts	est_console_stitch_briefs.py
Chay tu dong trong nhom `pure` cua run_test_group: brief lech khoi API se
lam do suite thay vi im lang.
"""
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "multiagent" / "console_ui" / "openapi.json"
BRIEFS = ROOT / "docs" / "console-ui" / "stitch-briefs.md"

# Schema ma brief mo ta truc tiep. HTTPValidationError/ValidationError la co
# che loi cua FastAPI, khong xuat hien trong thiet ke.
SCHEMAS_MO_TA = (
    "MeResponse",
    "DashboardResponse",
    "JobListItemModel",
    "JobDetailModel",
    "ReviewListItemModel",
    "ReviewDetailModel",
    "AgentResultModel",
    "CostEstimateModel",
)

# Truong khong can nhac trong brief vi khong hien ra giao dien.
KHONG_CAN_HIEN = {
    "csrf_token",  # co che noi bo, nguoi dung khong bao gio thay
}

# Token snake_case la GIA TRI hoac thuat ngu, khong phai ten truong.
GIA_TRI_HOP_LE = {
    # gia tri cua decision
    "needs_revision",
    # gia tri cua source
    "admin_retry",
    # ten agent
    "content_quality",
    # gia tri cua content_type
    "cam_nang",
    # thuat ngu trong prompt tieng Anh
    "definition_list", "key_value",
}

TOKEN = re.compile(r"\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b")


def doc_hop_dong() -> dict[str, set[str]]:
    schema = json.loads(CONTRACT.read_text(encoding="utf-8"))
    schemas = schema["components"]["schemas"]
    return {
        ten: set(schemas[ten].get("properties", {}))
        for ten in SCHEMAS_MO_TA
        if ten in schemas
    }


def main() -> int:
    if not CONTRACT.exists():
        print(f"[FAIL] chua co {CONTRACT}. Chay scripts\\export_openapi.py truoc.")
        return 1

    hop_dong = doc_hop_dong()
    thieu_schema = set(SCHEMAS_MO_TA) - set(hop_dong)
    if thieu_schema:
        print(f"[FAIL] hop dong thieu schema: {sorted(thieu_schema)}")
        return 1

    # Chi quet trong khoi prompt, khong quet van xuoi: van xuoi co duong dan
    # file (console_ui, check_stitch_briefs) va chung khong phai ten truong.
    khoi = [
        noi_dung
        for noi_dung in re.findall(
            r"^```\n(.*?)^```", BRIEFS.read_text(encoding="utf-8"), re.S | re.M
        )
        # Chi khoi prompt that; tai lieu con co khoi vi du lenh chay.
        if noi_dung.lstrip().startswith("CONTEXT")
    ]
    if len(khoi) != 6:
        print(f"[FAIL] mong doi 6 khoi prompt, tim thay {len(khoi)}")
        return 1
    brief = "\n".join(khoi)
    tat_ca_truong = set().union(*hop_dong.values())

    loi = []

    # Chieu 1: truong trong hop dong phai duoc nhac trong brief.
    for ten_schema, truong in sorted(hop_dong.items()):
        for field in sorted(truong):
            if field in KHONG_CAN_HIEN:
                continue
            if not re.search(rf"\b{re.escape(field)}\b", brief):
                loi.append(f"THIEU  {ten_schema}.{field} khong duoc nhac trong brief")

    # Chieu 2: token snake_case trong brief phai co that.
    for token in sorted(set(TOKEN.findall(brief))):
        if token in tat_ca_truong or token in GIA_TRI_HOP_LE:
            continue
        loi.append(f"THUA   '{token}' khong co trong hop dong va khong phai gia tri")

    if loi:
        for dong in loi:
            print(f"[FAIL] {dong}")
        print(f"\n{len(loi)} sai lech giua brief va hop dong.")
        return 1

    so_truong = sum(len(v) for v in hop_dong.values())
    print(
        f"[PASS] doi chieu {len(hop_dong)} schema / {so_truong} truong: 0 sai lech"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
