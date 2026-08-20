r"""Doi chieu brief Stitch voi hop dong openapi.json.

Vi sao can: brief khong dinh kem anh admin cu, nen prompt la rang buoc duy nhat
len Stitch. Mot ten truong bia ra trong brief se thanh mot cot trong thiet ke,
roi thanh code khong chay duoc ben frontend. Script nay chan dieu do o goc.

Kiem ba chieu:
1. Thieu  - truong co trong hop dong nhung khong duoc nhac trong brief.
2. Thua   - token kieu snake_case trong brief nhung khong co trong hop dong va
            khong nam trong danh sach gia tri hop le.
3. Enum   - moi gia tri trang thai that phai xuat hien trong brief.

Chieu 3 them sau khi mot loi that lot qua hai chieu dau: brief ghi trang thai
job la "queued/running/succeeded/failed" trong khi that su la
"queued/running/failed/done/superseded" - nam gia tri, va la `done` chu khong
phai `succeeded`. openapi.json khai bao `status: str` chu khong phai enum nen
doi chieu ten truong khong the bat duoc. Chi lo ra khi nhin anh chup man hinh
that.

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

# Mien tru THEO TUNG MAN HINH, moi dong phai co ly do. Khai bao tuong minh
# thay vi mien tru chung: mien tru chung se lam mot truong bien mat khoi MOI
# man hinh, va do la dung cach lo hong ban dau lot qua.
MIEN_TRU = {
    (2, "site_id"): "bang Jobs hien site_slug cho nguoi doc, khong hien UUID",
    (4, "site_id"): "bang Reviews hien site_slug cho nguoi doc, khong hien UUID",
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

TEN_MAN_HINH = (
    "Login", "Dashboard", "Jobs", "Job detail", "Reviews", "Review detail",
)
# Man hinh nao phai mo ta schema nao.
CAN_SCHEMA = {
    0: ("MeResponse",),
    1: ("DashboardResponse", "CostEstimateModel"),
    2: ("JobListItemModel",),
    3: ("JobDetailModel",),
    4: ("ReviewListItemModel",),
    5: ("ReviewDetailModel", "AgentResultModel", "CostEstimateModel"),
}
# Man hinh nao phai liet ke enum nao. Login khong hien du lieu nghiep vu nen
# khong co rang buoc.
CAN_ENUM = {
    1: ("trang thai job", "quyet dinh review"),
    2: ("trang thai job",),
    3: ("trang thai job", "trang thai ghi nguoc"),
    4: ("quyet dinh review",),
    5: ("quyet dinh review", "trang thai ghi nguoc"),
}


def _enum_that() -> dict[str, tuple[str, ...]]:
    """Gia tri enum doc THANG tu code, khong go tay vao day.

    Go tay se lap lai dung loi ma chieu kiem nay sinh ra de chan.
    """
    import os

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
    from review_platform.admin import queries

    return {
        "trang thai job": queries.QUEUE_STATUSES,
        "quyet dinh review": queries._REVIEW_DECISIONS,
        "trang thai ghi nguoc": queries.WRITEBACK_STATUSES,
    }


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

    # Chieu 1: truong phai duoc nhac trong DUNG man hinh dung no.
    #
    # Khong tim tren toan tai lieu: mot ten truong co the trung giua hai schema
    # (vi du `source` co ca o JobListItemModel lan CostEstimateModel), va khi
    # do man hinh nay se "che" cho man hinh kia. Loi that da lot qua theo dung
    # duong nay: cost_estimate.source khong he duoc mo ta trong brief dashboard
    # nhung van xanh, vi Jobs co nhac `source`.
    for chi_so, schemas in CAN_SCHEMA.items():
        phan_data = khoi[chi_so].split("STYLE")[0]
        for ten_schema in schemas:
            for field in sorted(hop_dong[ten_schema]):
                if field in KHONG_CAN_HIEN or (chi_so, field) in MIEN_TRU:
                    continue
                if not re.search(rf"\b{re.escape(field)}\b", phan_data):
                    loi.append(
                        f"THIEU  brief #{chi_so + 1} ({TEN_MAN_HINH[chi_so]}) "
                        f"khong nhac {ten_schema}.{field}"
                    )

    # Chieu 2: token snake_case trong brief phai co that.
    for token in sorted(set(TOKEN.findall(brief))):
        if token in tat_ca_truong or token in GIA_TRI_HOP_LE:
            continue
        loi.append(f"THUA   '{token}' khong co trong hop dong va khong phai gia tri")

    # Chieu 3: gia tri enum, kiem TUNG MAN HINH.
    #
    # Khong duoc tim tren toan tai lieu: khoi STYLE lap lai 6 lan va co nhac
    # ten trang thai de quy dinh mau, nen mot man hinh bo sot gia tri van se
    # "tim thay" o cho khac. Vi vay cat bo khoi STYLE truoc khi tim.
    enum = _enum_that()
    for chi_so, can_co in CAN_ENUM.items():
        phan_data = khoi[chi_so].split("STYLE")[0]
        for ten_enum in can_co:
            for value in enum[ten_enum]:
                if not re.search(rf"\b{re.escape(value)}\b", phan_data):
                    loi.append(
                        f"ENUM   brief #{chi_so + 1} ({TEN_MAN_HINH[chi_so]}) "
                        f"thieu gia tri '{value}' cua {ten_enum}"
                    )

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
