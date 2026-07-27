"""Test thu cong xac nhan write_back() KHONG raise khi Drupal khong the
ket noi (sau khi da het MAX_ATTEMPTS retry) - chi ghi log canh bao.

Cach chay:
    .venv\\Scripts\\python.exe scripts\\test_write_back_failure.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

logging.basicConfig(level=logging.WARNING)

import drupal_client

# Dia chi khong co gi lang nghe -> connection refused ngay, khong can cho
# timeout that (nhanh hon nhieu so voi tro toi 1 IP khong ton tai).
drupal_client.BASE_URL = "http://127.0.0.1:1"

if __name__ == "__main__":
    try:
        result = drupal_client.write_back(
            node_id="fake-node-id",
            status="needs_revision",
            score=50,
            suggestions="test",
        )
        ok = result is None
    except Exception as e:
        ok = False
        print(f"    loi khong mong doi (le ra khong duoc raise): {e}")

    status = "PASS" if ok else "FAIL"
    print(f"[{status}] write_back() voi Drupal khong ket noi duoc -> khong raise, chi log canh bao")
    print("    (kiem tra bang mat: phia tren phai co dong 'WARNING:root:Write-back that bai...')")
    sys.exit(0 if ok else 1)
