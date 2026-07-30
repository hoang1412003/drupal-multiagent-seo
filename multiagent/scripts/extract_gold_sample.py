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
import csv
import glob
import os
import re
import sys
from collections import Counter
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment, NavigableString

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
RAW_DIR = os.path.join(REPO_ROOT, "docs", "goldset", "raw")
LABELS_CSV = os.path.join(REPO_ROOT, "docs", "goldset", "labels.csv")

# Thẻ giữ lại trong body: đều mang ý nghĩa cấu trúc/nội dung mà label_helper.py
# và các agent cần đọc (heading, đoạn văn, danh sách, ảnh, link).
KEEP_TAGS = {
    "h1", "h2", "h3", "h4", "h5", "h6", "p", "ul", "ol", "li", "img", "a",
    "strong", "em", "blockquote", "table", "tr", "td", "th", "br",
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


def _render_body(body) -> str:
    """Mỗi thẻ khối một dòng, gộp khoảng trắng - để dễ đọc khi gán nhãn tay."""
    lines = []
    for child in body.children:
        rendered = _clean_text(str(child))
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def clean_body(soup: BeautifulSoup) -> tuple[str, list[str], dict, Counter, list[str]]:
    """Bóc div.field-body và làm sạch.

    Trả về (html đã sạch, danh sách thứ đã xoá, số đếm thẻ còn lại,
    số đếm thẻ đã unwrap, danh sách alt của từng ảnh còn lại).

    Danh sách thứ đã xoá KHÔNG được bỏ đi: quy tắc nhận diện banner CTA là
    heuristic (thẻ <a> chỉ bọc 1 ảnh, không có chữ), mới xác minh trên 1 bài.
    Bài khác có thể bọc ảnh nội dung trong <a> kiểu lightbox và bị xoá oan -
    in ra để người dùng phát hiện ngay, thay vì lộ ở Sprint 3 khi đã muộn.

    Thẻ bị unwrap (không nằm trong KEEP_TAGS) cũng được đếm lại và trả về
    thay vì âm thầm mất - bài nào có nhiều <h5>/<br>... người dùng cần biết.
    """
    node = soup.select_one("div.node-detail")
    body = node.select_one("div.field-body") if node else None
    if body is None:
        raise ExtractError("không tìm thấy div.field-body trong div.node-detail")

    removed = []

    for tag in body.find_all(["script", "style", "iframe", "noscript"]):
        tag.decompose()
    for comment in body.find_all(string=lambda s: isinstance(s, Comment)):
        comment.extract()

    # Mục lục tự sinh: không phải chữ tác giả viết, và 13 thẻ <a> của nó sẽ bị
    # label_helper.py đếm thành internal link (đẩy tiêu chí SEO10 lên oan).
    for toc in body.select("div.widget-toc"):
        removed.append(f"div.widget-toc ({len(toc.find_all('a'))} link)")
        toc.decompose()

    # Banner CTA: thẻ <a> mà toàn bộ nội dung chỉ là 1 <img>, không có chữ.
    for anchor in body.find_all("a"):
        images = anchor.find_all("img")
        if len(images) == 1 and not anchor.get_text(strip=True):
            removed.append(
                f'<a href="{anchor.get("href", "")}"> bọc '
                f'<img alt="{images[0].get("alt", "")}">'
            )
            parent = anchor.parent
            anchor.decompose()
            # Dọn thẻ cha nếu nó trở nên rỗng (không chữ và không có img)
            while parent and parent is not body and not parent.get_text(strip=True) and not parent.find_all("img"):
                old_parent = parent
                parent = parent.parent
                old_parent.decompose()

    unwrapped = Counter()
    for tag in body.find_all(True):
        if tag.name not in KEEP_TAGS:
            unwrapped[tag.name] += 1
            tag.unwrap()          # bỏ thẻ trình bày, giữ nội dung bên trong
        else:
            allowed = KEEP_ATTRS.get(tag.name, set())
            # alt bị unwrap từ figcaption có thể còn &nbsp; ở biên (D6) -
            # .strip() xoá vì \xa0 cũng được Python coi là whitespace.
            tag.attrs = {
                k: (v.strip() if k == "alt" else v)
                for k, v in tag.attrs.items() if k in allowed
            }

    # Chú thích ảnh (figcaption) vừa bị unwrap ở trên thành text node trần
    # ngay cấp con của body -> bọc lại thành <p> để label_helper.py tính vào
    # "số đoạn" (D5). Bọc TRƯỚC khi đếm kept để kept["p"] phản ánh đúng số
    # <p> có trong output cuối, không phải số trước khi bọc.
    for child in list(body.children):
        if isinstance(child, NavigableString) and _clean_text(str(child)):
            new_p = soup.new_tag("p")
            new_p.string = str(child)
            child.replace_with(new_p)

    kept = {name: len(body.find_all(name)) for name in ("h2", "h3", "p", "img", "a")}
    alts = [img.get("alt", "") for img in body.find_all("img")]
    rendered = _render_body(body)
    if not rendered.strip():
        raise ExtractError(
            "div.field-body rỗng sau khi làm sạch - nhiều khả năng nội dung "
            "do JavaScript chèn nên file HTML lưu tĩnh không có (Ctrl+S chỉ "
            "lưu HTML gốc từ server)"
        )
    return rendered, removed, kept, unwrapped, alts


def render_txt(fields: dict, body_html: str) -> str:
    """Ghép thành format scripts/label_helper.py đọc được.

    Không còn dòng image_alt: site thật không có field ảnh đại diện riêng,
    mọi ảnh nằm trong body (spec mục 3.3), nên mã B6 xét các thẻ <img> trong
    body thay vì một field riêng.
    """
    return (
        f"title: {fields['title']}\n"
        f"url_alias: {fields['url_alias']}\n"
        f"meta_description: {fields['meta_description']}\n"
        f"summary: {fields['summary']}\n"
        "---\n"
        f"{body_html}\n"
    )


def load_expected_urls() -> dict[str, str]:
    """sample_id -> source_url lấy từ labels.csv, để phát hiện lưu nhầm bài."""
    if not os.path.isfile(LABELS_CSV):
        return {}
    with open(LABELS_CSV, encoding="utf-8-sig") as f:
        return {row["sample_id"]: row["source_url"] for row in csv.DictReader(f)}


def expected_url_for(sample_id: str, table: dict[str, str]) -> str | None:
    """Khớp sample_id với labels.csv.

    File P-001.html ứng với 2 dòng P-001a/P-001b trong labels.csv (cùng một
    bài gốc, khác nhau ở lỗi sẽ chèn vào sau), nên khớp theo tiền tố kèm hậu tố
    biến thể. Dùng regex thay vì startswith để chống khớp nhầm vào ID dài hơn:
    nếu có P-0010, query P-001 không được trả URL sai.
    """
    if sample_id in table:
        return table[sample_id]
    pattern = re.compile(rf"^{re.escape(sample_id)}[a-z]?$")
    for key, url in table.items():
        if pattern.match(key):
            return url
    return None


def process(path: str, table: dict) -> bool:
    """Bóc tách 1 file HTML và ghi file .txt. Trả về True nếu ghi thành công.

    Bắt cả ExtractError lẫn Exception bất kỳ: một file lệch encoding hay lỗi
    bất ngờ khác không được phép làm hỏng cả lô 30 file (spec mục 4.4 - chạy
    hết mọi file rồi in tổng kết).
    """
    sample_id = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        fields = extract_fields(soup)
        body_html, removed, kept, unwrapped, alts = clean_body(soup)

        warnings = []
        if not fields["url_alias"]:
            warnings.append("khong co <link rel=canonical> - url_alias de trong")
        expected = expected_url_for(sample_id, table)
        if expected is None:
            warnings.append(
                f"{sample_id} khong co trong labels.csv - "
                "KHONG doi chieu duoc canonical"
            )
        elif fields["url_alias"] and fields["url_alias"] != expected:
            warnings.append(
                f"canonical khac labels.csv: {fields['url_alias']} != {expected}"
            )

        os.makedirs(RAW_DIR, exist_ok=True)
        with open(os.path.join(RAW_DIR, f"{sample_id}.txt"), "w", encoding="utf-8") as f:
            f.write(render_txt(fields, body_html))
    except ExtractError as error:
        print(f"{sample_id}.html")
        print(f"  [LOI] {error} - KHONG ghi file")
        return False
    except Exception as error:
        print(f"{sample_id}.html")
        print(f"  [LOI] {type(error).__name__}: {error} - KHONG ghi file")
        return False

    print(f"{sample_id}.txt")
    for item in removed:
        print(f"  [xoa] {item}")
    if unwrapped:
        parts = ", ".join(f"{name} x{count}" for name, count in unwrapped.most_common())
        print(f"  [unwrap] {parts}")
    print(
        f"  [giu] {kept['img']} anh, {kept['a']} link, "
        f"{kept['h2']} h2, {kept['h3']} h3"
    )
    for alt in alts:
        print(f"    [anh] alt=\"{alt}\"")
    for warning in warnings:
        print(f"  [CANH BAO] {warning}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(sorted(glob.glob(arg)) or [arg])

    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print(f"Khong tim thay file: {', '.join(missing)}")
        sys.exit(1)

    table = load_expected_urls()
    written = sum(process(path, table) for path in paths)
    print(f"\nDa ghi {written}/{len(paths)} file vao {RAW_DIR}")
    sys.exit(0 if written == len(paths) else 1)
