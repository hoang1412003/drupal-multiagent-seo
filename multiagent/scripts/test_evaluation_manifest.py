r"""Kiem tra bo nap manifest phep do - `admin/evaluation.py`, Console dung.

Truoc 2026-08-21 phep kiem nay nam trong `test_admin_evaluation.py`, cung file
voi test route HTML. Khi xoa admin Jinja2 ca file do se di theo, nen no duoc
tach ra day.

Vi sao no quan trong: manifest la thu QUYET DINH mot ket qua do co con hieu luc
hay khong. Mot manifest sai lech ma van duoc chap nhan nghia la ca du an tin
vao mot phep do khong con dung. Bo nap phai tu choi:

- trung ten phep do, ten phep do la, trang thai la
- duong dan tuyet doi, duong dan thoat ra ngoai (`../`), file .env
- file bang chung khong ton tai
- phep do `pending` ma lai co bang chung hoac co thoi diem chay
- danh dau `metadata_complete` nhung thieu truong bat buoc
- manifest nam ngoai docs/evidence

Khong can Postgres.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_evaluation_manifest.py
"""
from copy import deepcopy
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform.admin import evaluation


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = REPO_ROOT / "docs" / "evidence"


def _pending(experiment: str) -> dict:
    return {
        "experiment": experiment,
        "status": "pending",
        "score_path_snapshot": "04f10e1",
        "head_commit": None,
        "prompt_version": "020738e209017213",
        "model": "claude-haiku-4-5-20251001",
        "run_at": None,
        "evidence_path": None,
        "metadata_complete": False,
        "summary": "Chưa chạy.",
    }


def _valid_entries(relative_evidence: str) -> list[dict]:
    entries = [_pending(f"E{number}") for number in range(1, 7)]
    entries[1] = {
        "experiment": "E2",
        "status": "valid",
        "score_path_snapshot": "04f10e1",
        "head_commit": "a" * 40,
        "prompt_version": "not_applicable",
        "model": "BAAI/bge-m3",
        "run_at": "2026-08-13T16:06:44Z",
        "evidence_path": relative_evidence,
        "metadata_complete": True,
        "summary": "E2 đạt.",
    }
    return entries


def _write_json(path: Path, value) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_manifest_loader_validate_schema_provenance_va_path():
    manifest_path = EVIDENCE_DIR / ".test-evaluation-manifest.json"
    evidence_path = EVIDENCE_DIR / ".test-evaluation-e2.json"
    relative_evidence = "docs/evidence/.test-evaluation-e2.json"
    evidence_path.write_text('{"experiment":"E2"}\n', encoding="utf-8", newline="\n")
    try:
        entries = _valid_entries(relative_evidence)
        _write_json(manifest_path, entries)

        loaded = evaluation.load_manifest(manifest_path)
        assert [item.experiment for item in loaded] == [f"E{i}" for i in range(1, 7)]
        assert loaded[1].metadata_complete is True
        # E1 thieu head_commit -> phai kem canh bao, khong duoc im lang.
        assert loaded[0].provenance_warning is not None
        assert loaded[1].evidence_file == evidence_path.resolve()

        truong_hop_sai: list[tuple[str, list[dict]]] = []

        def them(ten: str, sua):
            ban_sao = deepcopy(entries)
            sua(ban_sao)
            truong_hop_sai.append((ten, ban_sao))

        them("trung ten phep do", lambda e: e.append(deepcopy(e[1])))
        them("trang thai la", lambda e: e[0].__setitem__("status", "running"))
        them("ten phep do la", lambda e: e[0].__setitem__("experiment", "E7"))
        them(
            "duong dan tuyet doi",
            lambda e: e[1].__setitem__("evidence_path", str(evidence_path.resolve())),
        )
        them(
            "duong dan thoat ra ngoai",
            lambda e: e[1].__setitem__("evidence_path", "docs/evidence/../.env"),
        )
        them(
            "file .env",
            lambda e: e[1].__setitem__("evidence_path", "docs/evidence/.env"),
        )
        them(
            "file bang chung khong ton tai",
            lambda e: e[1].__setitem__(
                "evidence_path", "docs/evidence/does-not-exist.json"
            ),
        )
        them(
            "pending nhung co bang chung",
            lambda e: e[0].__setitem__("evidence_path", relative_evidence),
        )
        them(
            "pending nhung co thoi diem chay",
            lambda e: e[0].__setitem__("run_at", "2026-08-13T00:00:00Z"),
        )
        them(
            "metadata_complete nhung thieu model",
            lambda e: e[1].__setitem__("model", None),
        )

        for ten, sai in truong_hop_sai:
            _write_json(manifest_path, sai)
            try:
                evaluation.load_manifest(manifest_path)
            except evaluation.ManifestError:
                pass
            else:
                raise AssertionError(f"khong chan duoc truong hop: {ten}")

        # Manifest nam ngoai docs/evidence cung phai bi tu choi.
        try:
            evaluation.load_manifest(REPO_ROOT / "README.md")
        except evaluation.ManifestError:
            pass
        else:
            raise AssertionError("loader chap nhan manifest ngoai docs/evidence")
    finally:
        manifest_path.unlink(missing_ok=True)
        evidence_path.unlink(missing_ok=True)
    print(
        "[PASS] manifest chan duplicate/status/path/provenance sai "
        f"({len(truong_hop_sai)} truong hop)"
    )


if __name__ == "__main__":
    failed = False
    try:
        test_manifest_loader_validate_schema_provenance_va_path()
    except Exception as exc:
        failed = True
        print(f"[FAIL] test_manifest_loader_validate_schema_provenance_va_path: {exc}")

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
