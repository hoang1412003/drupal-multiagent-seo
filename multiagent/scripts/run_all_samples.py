"""Chạy toàn bộ pipeline LangGraph trên bộ bài cẩm nang mẫu (test chức năng,
xem docs/architecture.md muc 8.1). Moi bai co 1 kich ban loi co y khac nhau -
dung de kiem tra nhanh cac agent co bat dung loi tuong ung khong, va doi chieu
quyet dinh thuc te voi quyet dinh ky vong.

Doc danh sach bai tu scripts/sample_articles.json (do seed_sample_articles.py
tao ra) - khong hard-code UUID.

Cach chay (Drupal dang chay, da chay seed_sample_articles.py truoc):
    .venv\\Scripts\\python.exe scripts\\run_all_samples.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import build_graph

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "sample_articles.json")

if __name__ == "__main__":
    if not os.path.exists(MANIFEST_PATH):
        sys.exit(
            "Chua co sample_articles.json - chay seed_sample_articles.py truoc."
        )
    with open(MANIFEST_PATH, encoding="utf-8") as f:
        samples = json.load(f)

    app = build_graph()

    for item in samples:
        result = app.invoke({"node_id": item["uuid"]})
        report = result["report"]
        cq = report["details"]["content_quality"]
        seo = report["details"]["seo"]
        comp = report["details"]["compliance"]
        match = "OK" if report["decision"] == item["expected"] else "LECH"
        print(
            f"[{match}] {item['label']}\n"
            f"  decision={report['decision']} (ky vong {item['expected']}) "
            f"final_score={report['final_score']}\n"
            f"  CQ={cq['score'] if cq else None} SEO={seo['score'] if seo else None} "
            f"Compliance={comp['score'] if comp else None}"
        )
