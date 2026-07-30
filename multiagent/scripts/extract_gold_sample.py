"""Bóc tách bài viết đã lưu từ vinfastauto.com thành file raw cho gold set.

Thiết kế: docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md

Đầu vào : docs/goldset/raw_html/<sample_id>.html
          (lưu bằng Ctrl+S trên trình duyệt -> "Webpage, HTML Only")
Đầu ra  : docs/goldset/raw/<sample_id>.txt
          (đúng format scripts/label_helper.py đọc được)

Vì sao phải lưu bằng trình duyệt: vinfastauto.com chặn truy cập tự động
(HTTP 403), xác minh 2026-07-29. Script chỉ xử lý file đã lưu về máy.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\extract_gold_sample.py ..\\docs\\goldset\\raw_html\\G-001.html
    .venv\\Scripts\\python.exe scripts\\extract_gold_sample.py ..\\docs\\goldset\\raw_html\\*.html
"""
import os
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
RAW_DIR = os.path.join(REPO_ROOT, "docs", "goldset", "raw")
LABELS_CSV = os.path.join(REPO_ROOT, "docs", "goldset", "labels.csv")

# Thẻ giữ lại trong body: đều mang ý nghĩa cấu trúc/nội dung mà label_helper.py
# và các agent cần đọc (heading, đoạn văn, danh sách, ảnh, link).
KEEP_TAGS = {
    "h2", "h3", "h4", "p", "ul", "ol", "li", "img", "a",
    "strong", "em", "blockquote", "table", "tr", "td", "th",
}

# Thuộc tính giữ lại theo từng thẻ. Mọi thứ khác (class/style/id/data-*/
# srcset/width/height/src) bị xoá - xem spec mục 4.2.
KEEP_ATTRS = {"img": {"alt"}, "a": {"href"}}


class ExtractError(Exception):
    """Thiếu phần cốt lõi của bài viết -> không ghi file, báo lỗi rõ ràng."""


def _clean_text(value: str) -> str:
    """Thay &nbsp; bằng dấu cách thường và gộp mọi chuỗi khoảng trắng."""
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


def extract_fields(soup: BeautifulSoup) -> dict:
    """Lấy 4 trường ngoài body, scope theo div.node-detail.

    Bắt buộc scope vào div.node-detail: class field--name-body xuất hiện 3 lần
    trong trang (2 lần thuộc menu/custom block), bám vào nó sẽ bóc nhầm.
    """
    node = soup.select_one("div.node-detail")
    if node is None:
        raise ExtractError(
            "không tìm thấy div.node-detail (có thể đã lưu nhầm loại trang)"
        )

    h1 = node.select_one("h1.field-title")
    if h1 is None:
        raise ExtractError("không tìm thấy h1.field-title trong div.node-detail")

    meta = soup.select_one('meta[name="description"]')
    canonical = soup.select_one('link[rel="canonical"]')
    desc = node.select_one("div.field-desc")

    return {
        "title": _clean_text(h1.get_text()),
        # Không có thẻ meta -> chuỗi rỗng, nghĩa là "đã kiểm tra và không có"
        # (chính là lỗi B3), KHÔNG phải "?" (= chưa thu). Xem docstring
        # label_helper.py về quy ước 2 giá trị đặc biệt này.
        "meta_description": _clean_text(meta.get("content", "")) if meta else "",
        "url_alias": (
            urlparse(canonical["href"]).path
            if canonical and canonical.get("href")
            else ""
        ),
        "summary": _clean_text(desc.get_text()) if desc else "",
    }
