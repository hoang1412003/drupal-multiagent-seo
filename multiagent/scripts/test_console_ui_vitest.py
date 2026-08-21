r"""Chay bo kiem JavaScript cua Console qua runner Python chung.

Vi sao boc lai bang Python thay vi de `npm test` chay rieng: du an co dung mot
lenh kiem tra (`run_test_group.py all-offline`), va manifest bat buoc moi file
`test_*.py` phai duoc xep nhom. De bo kiem JS nam ngoai nghia la no se bi quen
- dung cai ma bo kiem nay sinh ra de chan.

File nay chay HAI thu:
1. `npm run typecheck` - tsc. Truoc day khong lenh tu dong nao chay no.
2. `npm test` - Vitest + Testing Library.

Ca hai deu offline, khong can server va khong goi API tra phi.

Chay: ..\multiagent\.venv\Scripts\python.exe scripts\test_console_ui_vitest.py
"""
from pathlib import Path
import re
import shutil
import subprocess
import sys


CONSOLE_UI = Path(__file__).resolve().parents[1] / "console_ui"
TIMEOUT_GIAY = 240
# Ma mau ANSI. Viet tuong minh bang chr(27) thay vi de ky tu dieu khien
# tran trong ma nguon - trinh soan thao co the lang le xoa mat no, va khi
# do bo loc ngung hoat dong ma khong ai biet.
_BO_MAU = re.compile(chr(27) + r"\[[0-9;]*m")


def _npm() -> str | None:
    """Tren Windows npm la `npm.cmd`; shutil.which tim dung ban thuc thi."""
    return shutil.which("npm") or shutil.which("npm.cmd")


def _chay(npm: str, lenh: list[str], nhan: str) -> bool:
    try:
        ket_qua = subprocess.run(
            [npm, *lenh],
            cwd=str(CONSOLE_UI),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_GIAY,
        )
    except subprocess.TimeoutExpired:
        print(f"[FAIL] {nhan}: qua {TIMEOUT_GIAY}s")
        return False

    dau_ra = (ket_qua.stdout or "") + (ket_qua.stderr or "")
    if ket_qua.returncode != 0:
        print(f"[FAIL] {nhan}:")
        # In nguyen dau ra: nguoi doc can biet test nao hong, khong chi biet
        # rang "co gi do hong".
        for dong in dau_ra.splitlines():
            print(f"       {dong}")
        return False

    # Vitest in "Tests  64 passed (64)" - trich ra de bao cao co so lieu.
    # Bo ma mau ANSI: runner gom dau ra vao mot bao cao chung, ma mau lam
    # dong tom tat kho doc.
    sach = _BO_MAU.sub("", dau_ra)
    tom_tat = next(
        (
            " ".join(d.split())
            for d in reversed(sach.splitlines())
            if "Tests" in d and "passed" in d
        ),
        "",
    )
    print(f"[PASS] {nhan}{(' - ' + tom_tat) if tom_tat else ''}")
    return True


def main() -> int:
    npm = _npm()
    if npm is None:
        print("[SKIP] khong tim thay npm; [SKIP] khong phai [PASS]")
        return 0
    if not (CONSOLE_UI / "node_modules").is_dir():
        print(
            "[SKIP] chua cai phu thuoc cua console_ui. Chay:\n"
            "       cd console_ui && npm install\n"
            "       [SKIP] khong phai [PASS]"
        )
        return 0

    dat = True
    for lenh, nhan in (
        (["run", "typecheck"], "tsc khong loi kieu"),
        (["test"], "vitest"),
    ):
        if not _chay(npm, lenh, nhan):
            dat = False

    print("OK" if dat else "CO TEST DO")
    return 0 if dat else 1


if __name__ == "__main__":
    sys.exit(main())
