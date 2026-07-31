"""Kiem tra specs.json dung dinh dang truoc khi build KB.
Chay: .venv\\Scripts\\python.exe scripts\\test_kb_specs.py
"""
import json
import os
import sys

SPECS = os.path.join(os.path.dirname(__file__), "..", "src", "kb", "specs.json")
REQUIRED = {"model", "content_type", "langcode", "specs", "source_url", "verified"}

if __name__ == "__main__":
    failed = False
    with open(SPECS, encoding="utf-8") as f:
        entries = json.load(f)

    if not isinstance(entries, list) or not entries:
        print("[FAIL] specs.json phai la list khong rong")
        sys.exit(1)

    ids = set()
    for i, e in enumerate(entries):
        missing = REQUIRED - set(e)
        if missing:
            print(f"[FAIL] entry {i} thieu khoa: {missing}")
            failed = True
        if not isinstance(e.get("specs"), dict) or not e["specs"]:
            print(f"[FAIL] entry {i} 'specs' phai la dict khong rong")
            failed = True
        key = (e.get("content_type"), e.get("langcode"), e.get("model"))
        if key in ids:
            print(f"[FAIL] trung id: {key}")
            failed = True
        ids.add(key)

    print(f"[{'FAIL' if failed else 'PASS'}] {len(entries)} entry")
    sys.exit(1 if failed else 0)
