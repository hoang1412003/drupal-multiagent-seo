"""Test thủ công cho script bóc tách gold set, chạy trên fixture thật G-001.html.

Không gọi mạng, không gọi LLM - chỉ đọc file HTML đã lưu sẵn trong repo.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_extract_gold_sample.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup

from extract_gold_sample import ExtractError, extract_fields, _clean_text

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


def test_clean_text_with_nbsp() -> None:
    """Test _clean_text trực tiếp với chuỗi chứa ký tự \xa0 (&nbsp;).

    Ca test này xác minh _clean_text thật sự thay \xa0 bằng dấu cách thường
    và gộp mọi chuỗi khoảng trắng, không chỉ dựa trên fixture G-001.
    """
    # Input: chuỗi có \xa0 (non-breaking space) và nhiều whitespace liên tiếp
    input_str = "Tiêu\xa0đề   có\n\nnbsp"
    result = _clean_text(input_str)
    # Kỳ vọng: \xa0 → dấu cách, whitespace gộp → 1 dấu cách
    expected = "Tiêu đề có nbsp"
    check("_clean_text xoá \\xa0 và gộp whitespace", result, expected)


def test_extract_fields_with_nbsp() -> None:
    """Test extract_fields với HTML tối giản có &nbsp; thật trong h1.field-title.

    Ca test này xác minh đường đi extract_fields -> _clean_text xử lý được nbsp,
    không chỉ dựa trên fixture G-001 (fixture không chứa nbsp trong title).
    """
    # HTML tối giản có đúng cấu trúc, với &nbsp; trong h1
    html = """
    <html>
    <body>
    <div class="node-detail">
        <h1 class="field-title">Kinh nghiệm&nbsp;chạy&nbsp;xe</h1>
        <div class="field-desc">Thử nghiệm thực tế</div>
    </div>
    </body>
    </html>
    """
    soup = BeautifulSoup(html, "html.parser")
    fields = extract_fields(soup)

    # Kỳ vọng: &nbsp; đã được thay → "Kinh nghiệm chạy xe"
    expected_title = "Kinh nghiệm chạy xe"
    check("extract_fields xoá \\xa0 trong h1.field-title", fields["title"], expected_title)
    check("title không còn \\xa0 (qua extract_fields)", "\xa0" in fields["title"], False)


if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_clean_text_with_nbsp()
    test_extract_fields_with_nbsp()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
