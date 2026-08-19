r"""Ghi hop dong API cua Console ra console_ui/openapi.json.

Day la file duy nhat ban giao cho agent viet frontend. Tu no sinh tiep
api-types.ts bang openapi-typescript, nen go sai ten truong se bao loi kieu
thay vi im lang tra undefined.

Chay lai sau MOI lan doi model hoac route Console:
    .venv\\Scripts\\python.exe scripts\\export_openapi.py

Ten file bat dau bang `export_` chu khong phai `test_`, nen run_test_group
bo qua - dung y do.
"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import api as app_module


TARGET = Path(__file__).resolve().parents[1] / "console_ui" / "openapi.json"
PREFIX = "/api/console/"


def _refs(node) -> set[str]:
    """Moi ten schema duoc tham chieu trong mot nhanh JSON bat ky."""
    found = set()
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
            found.add(ref.rsplit("/", 1)[1])
        for value in node.values():
            found |= _refs(value)
    elif isinstance(node, list):
        for value in node:
            found |= _refs(value)
    return found


def _prune_schemas(schema: dict, paths: dict) -> dict:
    """Chi giu schema ma cac duong dan Console thuc su dung toi.

    Loc `paths` thoi la chua du: components giu nguyen se keo theo model cua
    connector API (/api/v1), va agent viet frontend se nhan kieu TypeScript cho
    nhung endpoint no khong duoc phep goi.
    """
    tat_ca = schema.get("components", {}).get("schemas", {})
    can_giu = _refs(paths)
    while True:
        them = set()
        for ten in can_giu:
            them |= _refs(tat_ca.get(ten, {}))
        moi = them - can_giu
        if not moi:
            break
        can_giu |= moi
    return {ten: tat_ca[ten] for ten in sorted(can_giu) if ten in tat_ca}


def build_schema() -> dict:
    schema = app_module.app.openapi()
    paths = {p: v for p, v in schema["paths"].items() if p.startswith(PREFIX)}
    if not paths:
        raise SystemExit("[LOI] khong tim thay duong dan Console nao trong openapi")
    schema["paths"] = paths
    schema.setdefault("components", {})["schemas"] = _prune_schemas(schema, paths)
    schema["info"] = {
        "title": "VF O2O Console API",
        "version": schema.get("info", {}).get("version", "1.0.0"),
        "description": (
            "Hop dong cho frontend Console tai /console. Xac thuc bang cookie "
            "phien HttpOnly (same-origin); moi POST phai gui header X-CSRF-Token "
            "lay tu GET /auth/me."
        ),
    }
    return schema


def main() -> int:
    schema = build_schema()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(
        json.dumps(schema, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    so_schema = len(schema.get("components", {}).get("schemas", {}))
    print(f"[OK] ghi {len(schema['paths'])} duong dan, {so_schema} schema vao {TARGET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
