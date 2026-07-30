# Kế hoạch triển khai: Thu thập gold set bằng script bóc tách HTML

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Viết script bóc tách file HTML đã lưu từ vinfastauto.com thành file raw đúng format gán nhãn, giữ nguyên `<h2>`/`<img alt>`/`<a href>` để `label_helper.py` không kết luận sai mã lỗi.

**Architecture:** Một script độc lập `scripts/extract_gold_sample.py` dùng BeautifulSoup, scope theo `div.node-detail` để bóc 4 field ngoài body + body đã làm sạch (bỏ mục lục tự sinh và banner CTA, unwrap thẻ trình bày, chỉ giữ `alt`/`href`). Kèm sửa `scripts/label_helper.py` để mã B6 suy từ các thẻ `<img>` trong body thay vì một field `image_alt` riêng.

**Tech Stack:** Python 3.12, BeautifulSoup 4 (`html.parser` builder, không cần lxml), thư viện chuẩn (`csv`, `glob`, `re`, `urllib.parse`).

**Spec:** `docs/superpowers/specs/2026-07-29-goldset-html-extraction-design.md`

## Global Constraints

- Ngôn ngữ comment/docstring/output: **tiếng Việt**, khớp phong cách các script hiện có trong `multiagent/scripts/`.
- Dự án **không dùng pytest**. Test là script độc lập chạy bằng `.venv\Scripts\python.exe`, in `[PASS]`/`[FAIL]` từng ca và `sys.exit(1)` nếu có ca fail — theo đúng mẫu `scripts/test_compliance_rules.py`.
- `beautifulsoup4` đặt ở **`multiagent/requirements-dev.txt`**, tuyệt đối **không** thêm vào `requirements.txt` (hệ chạy thật không phụ thuộc nó).
- Commit message **không** kèm trailer `Co-Authored-By: Claude`.
- Branch làm việc: `feature/goldset-html-extraction` (đã tạo, đang ở commit `c6332c5`).
- Fixture test: `docs/goldset/raw_html/G-001.html` (đã commit).
- Mọi lệnh chạy từ thư mục `multiagent/`.

**Số liệu kỳ vọng trên fixture G-001 (đã đo bằng parser, dùng làm expected value trong test):**

| Đại lượng | Giá trị |
| --- | --- |
| `title` | `Tổng hợp kinh nghiệm chạy ô tô điện VinFast đường dài` |
| `url_alias` | `/vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai` |
| `meta_description` bắt đầu bằng | `Kinh nghiệm chạy ô tô điện VinFast đường dài:` |
| `summary` bắt đầu bằng | `Nhờ trang bị công nghệ pin tiên tiến` |
| body sau làm sạch | `h2=3, h3=10, p=36, img=5, a=16` (p đổi từ 31 → 36 ở đợt làm chắc 2026-07-30, xem `docs/superpowers/specs/2026-07-30-goldset-extraction-hardening-design.md` mục D5) |
| Số thứ bị xoá | 1 khối `div.widget-toc` (13 link) + 1 thẻ `<a>` bọc banner CTA |

---

### Task 1: Dependency + bóc 4 field ngoài body

**Files:**
- Create: `multiagent/requirements-dev.txt`
- Create: `multiagent/scripts/extract_gold_sample.py`
- Test: `multiagent/scripts/test_extract_gold_sample.py`

**Interfaces:**
- Consumes: fixture `docs/goldset/raw_html/G-001.html`
- Produces:
  - `ExtractError(Exception)` — raise khi thiếu phần cốt lõi
  - `_clean_text(value: str) -> str`
  - `extract_fields(soup: BeautifulSoup) -> dict` với 4 khoá `title`, `meta_description`, `url_alias`, `summary` (đều là `str`)
  - Hằng số `KEEP_TAGS: set[str]`, `KEEP_ATTRS: dict[str, set[str]]`, `RAW_DIR: str`, `LABELS_CSV: str`

- [ ] **Step 1: Tạo `requirements-dev.txt`**

Tạo `multiagent/requirements-dev.txt`:

```
# Thư viện CHỈ dùng cho script chuẩn bị dữ liệu (chạy một lần), không phải
# phụ thuộc của hệ multi-agent chạy thật - xem requirements.txt cho phần đó.
beautifulsoup4>=4.12.0
```

- [ ] **Step 2: Cài đặt**

Chạy: `.venv\Scripts\pip install -r requirements-dev.txt`
Kỳ vọng: cài thành công `beautifulsoup4` và `soupsieve`.

Xác minh: `.venv\Scripts\python.exe -c "import bs4; print(bs4.__version__)"` → in ra số phiên bản, không lỗi.

- [ ] **Step 3: Viết test thất bại**

Tạo `multiagent/scripts/test_extract_gold_sample.py`:

```python
"""Test thủ công cho script bóc tách gold set, chạy trên fixture thật G-001.html.

Không gọi mạng, không gọi LLM - chỉ đọc file HTML đã lưu sẵn trong repo.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_extract_gold_sample.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup

from extract_gold_sample import ExtractError, extract_fields

FIXTURE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "..", "..", "docs", "goldset", "raw_html", "G-001.html",
)

_results = []


def check(name: str, actual, expected) -> None:
    _results.append((name, actual == expected, actual, expected))


def load_soup() -> BeautifulSoup:
    with open(FIXTURE, encoding="utf-8") as f:
        return BeautifulSoup(f.read(), "html.parser")


def test_fields() -> None:
    fields = extract_fields(load_soup())
    check(
        "title",
        fields["title"],
        "Tổng hợp kinh nghiệm chạy ô tô điện VinFast đường dài",
    )
    check(
        "url_alias",
        fields["url_alias"],
        "/vn_vi/kinh-nghiem-chay-o-to-dien-vinfast-duong-dai",
    )
    check(
        "meta_description bắt đầu đúng",
        fields["meta_description"].startswith(
            "Kinh nghiệm chạy ô tô điện VinFast đường dài:"
        ),
        True,
    )
    check(
        "summary bắt đầu đúng",
        fields["summary"].startswith("Nhờ trang bị công nghệ pin tiên tiến"),
        True,
    )
    # \xa0 (&nbsp;) phải được thay bằng dấu cách thường
    check("title không còn \\xa0", "\xa0" in fields["title"], False)


def test_missing_node_detail() -> None:
    """Lưu nhầm loại trang -> phải raise, KHÔNG được trả dict rỗng âm thầm.

    Ghi ra file raw rỗng nguy hiểm hơn nhiều so với báo lỗi: người gán nhãn
    sẽ tưởng bài thật sự trống và gán nhãn sai.
    """
    soup = BeautifulSoup("<html><body><p>trang khac</p></body></html>", "html.parser")
    try:
        extract_fields(soup)
        raised = False
    except ExtractError:
        raised = True
    check("thiếu div.node-detail -> raise ExtractError", raised, True)


if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
```

- [ ] **Step 4: Chạy test để xác nhận nó fail**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: FAIL với `ModuleNotFoundError: No module named 'extract_gold_sample'`.

- [ ] **Step 5: Viết implementation tối thiểu**

Tạo `multiagent/scripts/extract_gold_sample.py`:

```python
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
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: 6 dòng `[PASS]`, exit code 0.

- [ ] **Step 7: Commit**

```bash
git add multiagent/requirements-dev.txt multiagent/scripts/extract_gold_sample.py multiagent/scripts/test_extract_gold_sample.py
git commit -m "feat: boc tach 4 field ngoai body tu HTML da luu

Scope theo div.node-detail vi class field--name-body xuat hien 3 lan
trong trang (2 lan thuoc menu va custom block).

beautifulsoup4 dat o requirements-dev.txt, khong phai requirements.txt -
he multi-agent chay that khong phu thuoc no."
```

---

### Task 2: Làm sạch body

**Files:**
- Modify: `multiagent/scripts/extract_gold_sample.py` (thêm hàm mới sau `extract_fields`)
- Test: `multiagent/scripts/test_extract_gold_sample.py` (thêm hàm `test_body`)

**Interfaces:**
- Consumes: `ExtractError`, `_clean_text`, `KEEP_TAGS`, `KEEP_ATTRS` từ Task 1
- Produces:
  - `clean_body(soup: BeautifulSoup) -> tuple[str, list[str], dict]`
    - phần tử 0: HTML body đã làm sạch, mỗi thẻ khối một dòng
    - phần tử 1: danh sách mô tả những thứ đã xoá (để in ra)
    - phần tử 2: dict đếm thẻ còn lại, khoá `h2 h3 p img a`
  - `_render_body(body) -> str`

- [ ] **Step 1: Viết test thất bại**

Thêm vào `multiagent/scripts/test_extract_gold_sample.py` — sửa dòng import và thêm hàm test:

```python
from extract_gold_sample import clean_body, extract_fields
```

```python
def test_body() -> None:
    body_html, removed, kept = clean_body(load_soup())

    # Số đo đã xác minh bằng parser trên fixture thật (spec mục 3.1)
    check("body h2", kept["h2"], 3)
    check("body h3", kept["h3"], 10)
    check("body p", kept["p"], 31)
    check("body img (đã loại banner CTA)", kept["img"], 5)
    check("body a (đã loại 13 link mục lục + 1 thẻ bọc CTA)", kept["a"], 16)

    # Rác phải biến mất khỏi output
    check("không còn widget-toc", "widget-toc" in body_html, False)
    check("không còn alt banner CTA", "dat-coc-xe-o-to-dien-vinfast" in body_html, False)
    check("không còn class=", "class=" in body_html, False)
    check("không còn src=", "src=" in body_html, False)

    # Nội dung thật phải còn nguyên
    check(
        "còn heading mục 1",
        "1. Lên kế hoạch hành trình" in body_html,
        True,
    )
    check("mọi ảnh còn lại đều có alt không rỗng", body_html.count('<img alt="'), 5)

    # Heuristic xoá CTA phải báo cáo được, không xoá âm thầm
    check("báo cáo đúng 2 thứ đã xoá", len(removed), 2)
    check(
        "có báo cáo xoá mục lục",
        any("widget-toc" in item for item in removed),
        True,
    )
    check(
        "có báo cáo xoá banner CTA",
        any("dat-coc-xe-o-to-dien-vinfast" in item for item in removed),
        True,
    )
```

Và thêm lời gọi trong `__main__`:

```python
if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_body()
```

- [ ] **Step 2: Chạy test để xác nhận nó fail**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: FAIL với `ImportError: cannot import name 'clean_body' from 'extract_gold_sample'`.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `multiagent/scripts/extract_gold_sample.py`:

```python
def _render_body(body) -> str:
    """Mỗi thẻ khối một dòng, gộp khoảng trắng - để dễ đọc khi gán nhãn tay."""
    lines = []
    for child in body.children:
        rendered = _clean_text(str(child))
        if rendered:
            lines.append(rendered)
    return "\n".join(lines)


def clean_body(soup: BeautifulSoup) -> tuple[str, list[str], dict]:
    """Bóc div.field-body và làm sạch.

    Trả về (html đã sạch, danh sách thứ đã xoá, số đếm thẻ còn lại).

    Danh sách thứ đã xoá KHÔNG được bỏ đi: quy tắc nhận diện banner CTA là
    heuristic (thẻ <a> chỉ bọc 1 ảnh, không có chữ), mới xác minh trên 1 bài.
    Bài khác có thể bọc ảnh nội dung trong <a> kiểu lightbox và bị xoá oan -
    in ra để người dùng phát hiện ngay, thay vì lộ ở Sprint 3 khi đã muộn.
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
            anchor.decompose()

    for tag in body.find_all(True):
        if tag.name not in KEEP_TAGS:
            tag.unwrap()          # bỏ thẻ trình bày, giữ nội dung bên trong
        else:
            allowed = KEEP_ATTRS.get(tag.name, set())
            tag.attrs = {k: v for k, v in tag.attrs.items() if k in allowed}

    kept = {name: len(body.find_all(name)) for name in ("h2", "h3", "p", "img", "a")}
    return _render_body(body), removed, kept
```

Sửa dòng import ở đầu file thành:

```python
from bs4 import BeautifulSoup, Comment
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: toàn bộ `[PASS]`, exit code 0.

- [ ] **Step 5: Commit**

```bash
git add multiagent/scripts/extract_gold_sample.py multiagent/scripts/test_extract_gold_sample.py
git commit -m "feat: lam sach body - bo muc luc tu sinh va banner CTA

Muc luc (div.widget-toc) va banner CTA nam BEN TRONG field body cua
Drupal, khong phai chu tac gia viet. Giu lai se dem nham 13 internal
link va tao ma B6 gia tu alt dang slug.

Quy tac nhan dien CTA la heuristic nen bat buoc in ra thu da xoa."
```

---

### Task 3: Ghi file + CLI + đối chiếu labels.csv

**Files:**
- Modify: `multiagent/scripts/extract_gold_sample.py` (thêm phần ghi file và `__main__`)
- Test: `multiagent/scripts/test_extract_gold_sample.py` (thêm `test_render`)

**Interfaces:**
- Consumes: `extract_fields`, `clean_body`, `RAW_DIR`, `LABELS_CSV`, `ExtractError`
- Produces:
  - `render_txt(fields: dict, body_html: str) -> str`
  - `load_expected_urls() -> dict[str, str]`
  - `expected_url_for(sample_id: str, table: dict) -> str | None`
  - `process(path: str, table: dict) -> bool` (True nếu ghi file thành công)

- [ ] **Step 1: Viết test thất bại**

Sửa dòng import:

```python
from extract_gold_sample import clean_body, expected_url_for, extract_fields, render_txt
```

Thêm hàm test:

```python
def test_render() -> None:
    soup = load_soup()
    fields = extract_fields(soup)
    body_html, _, _ = clean_body(soup)
    text = render_txt(fields, body_html)

    head, sep, body = text.partition("\n---\n")
    check("có dấu phân cách ---", sep, "\n---\n")

    keys = [line.split(":", 1)[0] for line in head.splitlines()]
    check(
        "đúng 4 dòng field theo thứ tự",
        keys,
        ["title", "url_alias", "meta_description", "summary"],
    )
    check("đã bỏ dòng image_alt", "image_alt" in head, False)
    check("body giữ nguyên heading", "<h2>" in body, True)

    # P-001.html ứng với P-001a/P-001b trong labels.csv -> khớp theo tiền tố
    table = {"P-001a": "/vn_vi/cham-soc-xe-dien", "G-001": "/vn_vi/kinh-nghiem"}
    check("khớp sample_id chính xác", expected_url_for("G-001", table), "/vn_vi/kinh-nghiem")
    check(
        "khớp sample_id theo tiền tố",
        expected_url_for("P-001", table),
        "/vn_vi/cham-soc-xe-dien",
    )
    check("không khớp thì trả None", expected_url_for("G-999", table), None)
```

Thêm lời gọi trong `__main__`:

```python
if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_body()
    test_render()
```

- [ ] **Step 2: Chạy test để xác nhận nó fail**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: FAIL với `ImportError: cannot import name 'expected_url_for'`.

- [ ] **Step 3: Viết implementation**

Thêm vào cuối `multiagent/scripts/extract_gold_sample.py`:

```python
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


def load_expected_urls() -> dict:
    """sample_id -> source_url lấy từ labels.csv, để phát hiện lưu nhầm bài."""
    if not os.path.isfile(LABELS_CSV):
        return {}
    with open(LABELS_CSV, encoding="utf-8-sig") as f:
        return {row["sample_id"]: row["source_url"] for row in csv.DictReader(f)}


def expected_url_for(sample_id: str, table: dict):
    """Khớp sample_id với labels.csv.

    File P-001.html ứng với 2 dòng P-001a/P-001b trong labels.csv (cùng một
    bài gốc, khác nhau ở lỗi sẽ chèn vào sau), nên phải khớp theo tiền tố.
    """
    if sample_id in table:
        return table[sample_id]
    for key, url in table.items():
        if key.startswith(sample_id):
            return url
    return None


def process(path: str, table: dict) -> bool:
    """Bóc tách 1 file HTML và ghi file .txt. Trả về True nếu ghi thành công."""
    sample_id = os.path.splitext(os.path.basename(path))[0]
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    try:
        fields = extract_fields(soup)
        body_html, removed, kept = clean_body(soup)
    except ExtractError as error:
        print(f"{sample_id}.html")
        print(f"  [LOI] {error} - KHONG ghi file")
        return False

    warnings = []
    if not fields["url_alias"]:
        warnings.append("khong co <link rel=canonical> - url_alias de trong")
    expected = expected_url_for(sample_id, table)
    if expected and fields["url_alias"] and fields["url_alias"] != expected:
        warnings.append(
            f"canonical khac labels.csv: {fields['url_alias']} != {expected}"
        )

    os.makedirs(RAW_DIR, exist_ok=True)
    with open(os.path.join(RAW_DIR, f"{sample_id}.txt"), "w", encoding="utf-8") as f:
        f.write(render_txt(fields, body_html))

    print(f"{sample_id}.txt")
    for item in removed:
        print(f"  [xoa] {item}")
    print(
        f"  [giu] {kept['img']} anh, {kept['a']} link, "
        f"{kept['h2']} h2, {kept['h3']} h3"
    )
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
```

Sửa phần import ở đầu file thành:

```python
import csv
import glob
import os
import re
import sys
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Comment
```

- [ ] **Step 4: Chạy test để xác nhận nó pass**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: toàn bộ `[PASS]`, exit code 0.

- [ ] **Step 5: Chạy script thật trên fixture**

Chạy: `.venv\Scripts\python.exe scripts\extract_gold_sample.py ..\docs\goldset\raw_html\G-001.html`

Kỳ vọng in ra đúng dạng:

```
G-001.txt
  [xoa] div.widget-toc (13 link)
  [xoa] <a href="https://reserve.vinfastauto.com/"> bọc <img alt="dat-coc-xe-o-to-dien-vinfast">
  [giu] 5 anh, 16 link, 3 h2, 10 h3

Da ghi 1/1 file vao ...\docs\goldset\raw
```

Mở `docs/goldset/raw/G-001.txt` xác nhận bằng mắt: 4 dòng field, dấu `---`, body có `<h2>`/`<img alt=`, không có `class=`.

- [ ] **Step 6: Commit**

```bash
git add multiagent/scripts/extract_gold_sample.py multiagent/scripts/test_extract_gold_sample.py docs/goldset/raw/G-001.txt
git commit -m "feat: ghi file raw + CLI + doi chieu labels.csv

Format moi bo dong image_alt, them summary (field-descripton co that
tren site VinFast). Doi chieu canonical voi labels.csv de phat hien
luu nham bai; P-001.html khop theo tien to voi P-001a/P-001b."
```

---

### Task 4: Sửa `label_helper.py` — mã B6 suy từ ảnh trong body

**Files:**
- Modify: `multiagent/scripts/label_helper.py` (docstring, khối B6, khối body)
- Test: `multiagent/scripts/test_extract_gold_sample.py` (thêm `test_b6`)

**Interfaces:**
- Consumes: `analyze(fields: dict) -> tuple[list[str], list[str]]` (đã có sẵn trong `label_helper.py`)
- Produces: không có API mới — chỉ đổi hành vi của `analyze()` với mã B6

- [ ] **Step 1: Viết test thất bại**

Thêm vào `multiagent/scripts/test_extract_gold_sample.py`:

```python
from label_helper import analyze
```

```python
def _b6_codes(body: str) -> list:
    """Chạy analyze() trên body cho trước, trả về các mã B6 tìm được."""
    _, codes = analyze({"body": body})
    return [c for c in codes if c.startswith("B6")]


def test_b6() -> None:
    # Mọi ảnh có alt -> không có B6
    check(
        "mọi ảnh có alt -> không B6",
        _b6_codes('<p>Nội dung</p><img alt="mô tả ảnh"><img alt="mô tả ảnh 2">'),
        [],
    )
    # Có ảnh thiếu alt -> B6, kèm số lượng
    check(
        "1/2 ảnh thiếu alt -> B6",
        _b6_codes('<img alt="có mô tả"><img src="x.png">'),
        ["B6 (1/2 ảnh thiếu alt text)"],
    )
    # alt rỗng cũng tính là thiếu
    check(
        "alt rỗng tính là thiếu",
        _b6_codes('<img alt="">'),
        ["B6 (1/1 ảnh thiếu alt text)"],
    )
    # Bài không có ảnh -> KHÔNG kết luận B6 (không có ảnh không phải lỗi alt)
    check("bài không ảnh -> không B6", _b6_codes("<p>Chỉ có chữ.</p>"), [])

    # Trên fixture thật: 5 ảnh đều có alt -> không B6
    soup = load_soup()
    body_html, _, _ = clean_body(soup)
    check("fixture G-001 không có B6", _b6_codes(body_html), [])
```

Thêm lời gọi trong `__main__`:

```python
if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_body()
    test_render()
    test_b6()
```

- [ ] **Step 2: Chạy test để xác nhận nó fail**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: FAIL ở ca `1/2 ảnh thiếu alt -> B6` (thực tế `[]`, kỳ vọng `["B6 (1/2 ảnh thiếu alt text)"]`) — vì `analyze()` hiện đọc field `image_alt` chứ chưa đọc body.

- [ ] **Step 3: Xoá khối B6 cũ**

Trong `multiagent/scripts/label_helper.py`, **xoá** khối sau (nằm giữa khối B7 và khối B9):

```python
    # --- B6: image_alt -----------------------------------------------------
    alt = check("image_alt", fields.get("image_alt"))
    if alt is not None:
        if not alt:
            codes.append("B6 (thiếu alt text)")
        else:
            measures.append(f"  image_alt          có ({len(alt)} ký tự)")
            measures.append("  → B6 phần 'mô tả đúng ảnh không' CẦN NGƯỜI xét")
```

- [ ] **Step 4: Thêm khối B6 mới vào phần body**

Trong cùng file, tìm dòng mở đầu khối body:

```python
    # --- B9: cấu trúc body -------------------------------------------------
    body = fields.get("body", "")
    if body.strip():
        plain = strip_html(body)
```

Chèn khối B6 mới ngay sau dòng `if body.strip():`, trước dòng `plain = strip_html(body)`:

```python
        # --- B6: alt text của MỌI ảnh trong body ------------------------
        # Site thật không có field ảnh đại diện riêng - mọi ảnh nằm trong
        # body (spec 2026-07-29 mục 3.3), nên B6 xét tất cả ảnh thay vì
        # một field image_alt đơn lẻ.
        images = re.findall(r"<img[^>]*>", body, re.IGNORECASE)
        if images:
            no_alt = [
                img for img in images
                if not re.search(r'\balt\s*=\s*"[^"]+"', img, re.IGNORECASE)
            ]
            measures.append(
                f"  số ảnh             {len(images)} (thiếu alt: {len(no_alt)})"
            )
            if no_alt:
                codes.append(f"B6 ({len(no_alt)}/{len(images)} ảnh thiếu alt text)")
            else:
                measures.append("  → B6 phần 'mô tả đúng ảnh không' CẦN NGƯỜI xét")
        else:
            measures.append("  số ảnh             0 (bài không có ảnh - không xét B6)")

```

- [ ] **Step 5: Cập nhật docstring của `label_helper.py`**

Trong docstring đầu file, thay khối ví dụ định dạng đầu vào:

```
    title: Hướng dẫn sạc pin ô tô điện VinFast đúng cách
    url_alias: /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
    meta_description: ?
    image_alt:
    ---
    <nội dung thân bài, HTML hoặc text thuần>
```

thành:

```
    title: Hướng dẫn sạc pin ô tô điện VinFast đúng cách
    url_alias: /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
    meta_description: ?
    summary: Bài viết hướng dẫn các bước sạc pin an toàn...
    ---
    <nội dung thân bài, PHẢI là HTML - xem lưu ý dưới>
```

Và thêm ngay sau khối đó:

```
Body phải giữ nguyên HTML (thẻ <h2>, <img alt>, <a href>). Nếu dán text
thuần thì script đếm h2 = 0 và kết luận sai mã B9 cho mọi bài dài. Dùng
scripts/extract_gold_sample.py để sinh file này thay vì gõ tay.
```

- [ ] **Step 6: Chạy test để xác nhận nó pass**

Chạy: `.venv\Scripts\python.exe scripts\test_extract_gold_sample.py`
Kỳ vọng: toàn bộ `[PASS]`, exit code 0.

- [ ] **Step 7: Chạy `label_helper.py` trên file thật (tiêu chí 13 của spec)**

Chạy: `.venv\Scripts\python.exe scripts\label_helper.py ..\docs\goldset\raw\G-001.txt`

Kỳ vọng:
- Phần `[SỐ ĐO]` có dòng `số ảnh 5 (thiếu alt: 0)`, `heading h2=3 h3=10`
- Phần `[MÃ LỖI MÁY KẾT LUẬN ĐƯỢC]` **không** có mã `B6`
- **Không** có mã `B9` với lý do "không có h2" (vì h2 = 3, không phải 0)

Đây chính là mục tiêu cuối của cả plan: ground truth không còn mã lỗi giả.

- [ ] **Step 8: Commit**

```bash
git add multiagent/scripts/label_helper.py multiagent/scripts/test_extract_gold_sample.py
git commit -m "feat: ma B6 suy tu moi anh trong body thay vi field image_alt

Site that khong co field anh dai dien rieng - moi anh nam trong body,
nen xet 1 field image_alt la sai voi du lieu that.

Docstring canh bao ro: body PHAI la HTML, dan text thuan se lam h2 = 0
va sinh ma B9 gia cho moi bai dai."
```

---

## Sau khi hoàn thành plan

Việc còn lại thuộc về người dùng, không phải code (spec mục 9):

1. Lưu 29 file HTML còn lại (`Ctrl+S` → "Webpage, HTML Only" → `docs/goldset/raw_html/`).
   Đặt tên: `G-002.html`…`G-020.html` và `P-001.html`…`P-010.html` (không hậu tố `a`/`b`).
2. Chạy `scripts\extract_gold_sample.py ..\docs\goldset\raw_html\*.html`, đọc kỹ các dòng `[xoa]` và `[CANH BAO]`.
3. Nhân bản `P-001/P-004/P-007` thành biến thể `a`/`b`, chèn lỗi theo `injected_codes` trong `labels.csv`.
4. Gán nhãn theo `docs/goldset/annotation-guideline.md`.

**Hạng mục phát sinh, KHÔNG thuộc plan này** (spec mục 6): mở rộng SEO Agent chấm alt của mọi ảnh trong body. Sau Task 4, nhãn B6 xét mọi ảnh trong body còn `src/agents/seo.py` vẫn chấm tiêu chí SEO9 trên một field `image_alt` — hai bên đo hai tập ảnh khác nhau. Phải xử lý **trước calibration Sprint 3**, nếu không Recall/F1 của tiêu chí alt sẽ lệch có hệ thống. Cần spec riêng.
