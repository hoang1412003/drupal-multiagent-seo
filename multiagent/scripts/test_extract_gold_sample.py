"""Test thủ công cho script bóc tách gold set, chạy trên fixture thật G-001.html.

Không gọi mạng, không gọi LLM - chỉ đọc file HTML đã lưu sẵn trong repo.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_extract_gold_sample.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup

from extract_gold_sample import ExtractError, clean_body, expected_url_for, extract_fields, render_txt, _clean_text

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
    check("5 ảnh còn lại đều có thuộc tính alt", body_html.count('<img alt="'), 5)
    check("không có alt rỗng", 'alt=""' in body_html, False)
    check("không còn thẻ <p> rỗng", "<p></p>" in body_html, False)

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

    # Kiểm tra regex an toàn: không khớp nhầm vào ID dài hơn (P-0010 != P-001)
    table_long = {"P-0010": "/url/P-0010", "P-001a": "/url/P-001"}
    check(
        "chặn khớp nhầm ID dài hơn: P-001 không khớp P-0010",
        expected_url_for("P-001", table_long),
        "/url/P-001",
    )
    check(
        "regex không khớp ký tự số thêm: P-001 không khớp P-00100",
        expected_url_for("P-001", {"P-00100": "/wrong-url"}),
        None,
    )


if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_clean_text_with_nbsp()
    test_extract_fields_with_nbsp()
    test_body()
    test_render()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
