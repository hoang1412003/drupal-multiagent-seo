r"""Security test cho `admin/read_only_sources.py` - 330 dong Console dung.

Truoc 2026-08-21 hai phep kiem nay nam trong `test_admin_read_only.py`, cung
file voi test route HTML. Khi xoa admin Jinja2, ca file do se di theo - nen
chung duoc tach ra day. Neu khong, 330 dong code CON DUOC DUNG se mat het lop
kiem tra an toan ma khong ai nhan ra.

Hai tinh chat can khoa, ca hai deu la tinh chat AN TOAN chu khong phai hanh vi
hien thi:

1. Bo nap policy chi doc dung mot allowlist va tu choi duong dan thoat ra
   ngoai (`../.env`). Khong co no, mot tham so duong dan tu ngoai vao co the
   doc bat ky file nao trong may.
2. Cau SQL cua KB khong bao gio doc `document` hay `embedding`, va doan
   metadata tra ve da duoc loc. Man Cau hinh/KB hien cho nguoi VAN HANH xem;
   noi dung bai va vector khong thuoc ve do, con token thi tuyet doi khong.

Khong can Postgres: ca hai deu chay tren du lieu gia.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_read_only_sources.py
"""
import inspect
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from review_platform.admin import read_only_sources


EXPECTED_FILES = {
    "config/scoring.yaml",
    "src/agents/compliance_rules.json",
    "src/agents/brand_rules.json",
    "src/kb/specs.json",
}
EXPECTED_POLICY_HASHES = {
    "config/scoring.yaml": "6ca88fc2ad60e72fcdd162bbc0e55441d32841160db9563bf13ffdb7d81ebd49",
    "src/agents/compliance_rules.json": "edfd49d48e144f7e491ff8527650125370af72219e518222c4421c263ae4c6f6",
    "src/agents/brand_rules.json": "f4c9d489363c1471dafd99335d91cb0c44427c01a24789de0fa7f119ef443f9a",
    "src/kb/specs.json": "fe2185e06d64dcb237b8b49b683d42d4d3487f2bc7d1187de81e3b6ab05e6d61",
}


def test_policy_loader_chi_doc_allowlist_va_metadata():
    # Khong nhan tham so nao: khong co cho de mot duong dan tu ngoai di vao.
    assert not inspect.signature(read_only_sources.load_policy_files).parameters

    files = read_only_sources.load_policy_files()
    assert {item.relative_path for item in files} == EXPECTED_FILES
    assert all(re.fullmatch(r"[0-9a-f]{64}", item.sha256) for item in files)
    assert {item.relative_path: item.sha256 for item in files} == EXPECTED_POLICY_HASHES
    assert all(item.modified_at.utcoffset().total_seconds() == 0 for item in files)

    # Chi tra METADATA, khong tra noi dung file. Ba chuoi duoi day co that
    # trong corpus; chung lot ra nghia la loader dang tra ca noi dung.
    rendered = json.dumps(
        [item.metadata for item in files], ensure_ascii=False, default=str
    )
    for cam in ("tốt nhất", "438km", "nguon_kiem"):
        assert cam not in rendered, f"loader lam lo noi dung: {cam!r}"

    try:
        read_only_sources._resolve_allowed_path("../.env")
    except read_only_sources.UnsafePolicyPathError:
        pass
    else:
        raise AssertionError("loader chap nhan duong dan thoat khoi multiagent root")
    print("[PASS] policy loader chi doc allowlist va khong tra full corpus")


class _CursorGhiLai:
    """Ghi lai cau SQL that su duoc gui di, de kiem no KHONG doc gi."""

    def __init__(self):
        self.sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, sql, _params=None):
        self.sql = str(sql)

    def fetchall(self):
        return [
            (
                "kb_factcheck",
                "cam_nang",
                "vi",
                2,
                {
                    "model": "VF 9",
                    "verified": True,
                    "token": "KHONG-DUOC-LO",
                    "note": "Bearer cung-khong-duoc-lo",
                },
            )
        ]


class _KetNoiGhiLai:
    def __init__(self):
        self.recording_cursor = _CursorGhiLai()

    def cursor(self):
        return self.recording_cursor


def test_kb_query_khong_doc_document_vector_va_sanitize_excerpt():
    gia = _KetNoiGhiLai()
    rows = read_only_sources.load_kb_summary(gia)

    sql = " ".join(gia.recording_cursor.sql.casefold().split())
    assert "document" not in sql, "cau SQL doc noi dung bai"
    assert not re.search(r"\b(?:k\.)?embedding\b", sql), "cau SQL doc vector"

    assert rows[0].chunk_count == 2
    assert len(rows[0].metadata_excerpt) <= 500
    # Token va header Bearer nam trong metadata cua du lieu that; chung phai bi
    # loc truoc khi hien cho nguoi van hanh.
    assert "KHONG-DUOC-LO" not in rows[0].metadata_excerpt
    assert "cung-khong-duoc-lo" not in rows[0].metadata_excerpt
    assert rows[0].embedding_model is None
    assert rows[0].embedding_dimension is None
    print("[PASS] KB query chi aggregate metadata da loc, khong doc noi dung/vector")


if __name__ == "__main__":
    failed = False
    for fn in (
        test_policy_loader_chi_doc_allowlist_va_metadata,
        test_kb_query_khong_doc_document_vector_va_sanitize_excerpt,
    ):
        try:
            fn()
        except Exception as exc:
            failed = True
            print(f"[FAIL] {fn.__name__}: {exc}")

    print("OK" if not failed else "CO TEST DO")
    sys.exit(1 if failed else 0)
