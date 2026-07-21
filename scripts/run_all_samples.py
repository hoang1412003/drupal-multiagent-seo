"""Chạy toàn bộ pipeline LangGraph trên bộ 8 bài viết mẫu (golden set nhỏ,
xem docs/architecture.md muc 8.1), moi bai co 1 loai loi co y khac nhau -
dung de kiem tra nhanh cac agent co bat dung loi tuong ung khong.

Cach chay (tu thu muc goc project, sau khi Drupal local dang chay va da
tao du 8 bai viet mau tren Drupal):
    .venv\\Scripts\\python.exe scripts\\run_all_samples.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from graph import build_graph

SAMPLES = [
    ("3fea90a9-b0cc-422f-bee6-79c2b35aaf0f", "Uu dai VF5 thang 8 (bai tot)"),
    ("e6611bd7-362f-4f24-93d6-041623dfaa94", "Su kien lai thu VF8 (bai tot)"),
    ("176ea2cb-5976-4d25-ac3f-dada7d7c28b0", "VF6 ra mat phien ban moi (bai tot)"),
    ("b4a38180-fc74-42e6-9d5a-aadf8cca9c80", "VF9 (bai tot nhung kha ngan)"),
    ("a59fff1a-f924-4710-9719-b97cbef83b5c", "VF3 thag 7 - loi chinh ta co y"),
    ("03b9ed27-145b-4520-b047-bc3bae3c67c6", "Tin moi - thieu SEO co y"),
    ("b8a6b9c2-d432-4e00-bcb3-cbe1111c7c63", "Vf 3 giam gia thang 8 - sai thuat ngu brand co y"),
    ("fdeeaec6-472a-449e-b007-1ee0e42dd51f", "VF3 tot nhat the gioi - phong dai/compliance co y"),
]

if __name__ == "__main__":
    app = build_graph()

    for node_id, label in SAMPLES:
        result = app.invoke({"node_id": node_id})
        report = result["report"]
        cq = report["details"]["content_quality"]
        seo = report["details"]["seo"]
        print(
            f"{label}\n"
            f"  final_score={report['final_score']} decision={report['decision']} "
            f"CQ={cq['score'] if cq else None} SEO={seo['score'] if seo else None}"
        )
