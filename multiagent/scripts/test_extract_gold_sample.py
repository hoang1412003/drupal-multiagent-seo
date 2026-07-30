"""Test thủ công cho script bóc tách gold set, chạy trên fixture thật G-001.html.

Không gọi mạng, không gọi LLM - chỉ đọc file HTML đã lưu sẵn trong repo.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\test_extract_gold_sample.py
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from bs4 import BeautifulSoup, NavigableString

from extract_gold_sample import (
    KEEP_TAGS,
    ExtractError,
    clean_body,
    expected_url_for,
    extract_fields,
    render_txt,
    _clean_text,
)
from label_helper import analyze, parse_sample, split_sentences

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


def test_clean_body_errors() -> None:
    """clean_body phải raise ExtractError, không được ghi ra body rỗng/thiếu âm thầm."""
    # Thiếu hẳn div.field-body trong div.node-detail
    soup_missing = BeautifulSoup(
        '<div class="node-detail"><h1 class="field-title">t</h1></div>',
        "html.parser",
    )
    try:
        clean_body(soup_missing)
        raised_missing = False
    except ExtractError:
        raised_missing = True
    check("thiếu div.field-body -> raise ExtractError", raised_missing, True)

    # div.field-body có mặt nhưng render ra rỗng sau khi làm sạch (finding 1a:
    # kịch bản thân bài do JavaScript chèn, HTML lưu tĩnh không có nội dung)
    soup_empty = BeautifulSoup(
        '<div class="node-detail">'
        '<div class="field-body"><div id="lazy"></div></div>'
        "</div>",
        "html.parser",
    )
    try:
        clean_body(soup_empty)
        raised_empty = False
    except ExtractError:
        raised_empty = True
    check("div.field-body rỗng sau khi làm sạch -> raise ExtractError", raised_empty, True)


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
    body_html, removed, kept, unwrapped, alts = clean_body(load_soup())

    # Số đo đã xác minh bằng parser trên fixture thật (spec mục 3.1).
    # p = 36 (không phải 31): D5 bọc 5 chú thích ảnh (figcaption cũ) thành
    # <p> - xem docs/superpowers/specs/2026-07-30-goldset-extraction-hardening-design.md
    check("body h2", kept["h2"], 3)
    check("body h3", kept["h3"], 10)
    check("body p", kept["p"], 36)
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

    # D3: thẻ bị unwrap (div, figure, figcaption, span...) phải được báo cáo,
    # không được mất âm thầm - fixture có figcaption (chú thích ảnh cũ).
    check("có báo cáo thẻ đã unwrap", len(unwrapped) > 0, True)
    check("báo cáo unwrap có figcaption", "figcaption" in unwrapped, True)

    # D4: mỗi ảnh còn lại phải có 1 dòng alt riêng để người dùng liếc phát
    # hiện banner sống sót/ảnh bọc 2 lần - số alt phải khớp số ảnh giữ lại.
    check("số alt trả về khớp số ảnh giữ lại", len(alts), kept["img"])
    # Ca trên chỉ so sánh SỐ LƯỢNG - len(alts) và kept["img"] cùng tính từ
    # body.find_all("img") ngay cạnh nhau nên luôn khớp về số lượng bất kể
    # nội dung alts đúng hay sai. Ca này so khớp NỘI DUNG thật để bảo vệ D4.
    check(
        "nội dung alts đúng thứ tự trên fixture G-001",
        alts,
        [
            "kinh nghiệm chạy ô tô điện VinFast đường dài",
            "kinh nghiệm chạy ô tô điện VinFast đường dài cần chuẩn bị gì",
            "Lưu ý khi chạy ô tô điện VinFast đường dài",
            "kinh nghiệm lái ô tô điện VinFast đường dài sử dụng phanh tái sinh",
            "kinh nghiệm chạy ô tô điện VinFast đường dài VF e34 chinh phục Sa Vĩ",
        ],
    )

    # D5: 5 chú thích ảnh (trước đây là text node trần) giờ phải nằm trong
    # <p>, không còn là text node trần ở cấp cao nhất của body.
    reparsed = BeautifulSoup(body_html, "html.parser")
    bare_text = [
        node for node in reparsed.contents
        if isinstance(node, NavigableString) and node.strip()
    ]
    check("không còn text node trần có chữ ở cấp cao nhất", bare_text, [])
    check(
        "chú thích ảnh đã thành <p>",
        "<p>Ô tô điện VinFast VF e34 tự tin chinh phục Sa Vĩ</p>" in body_html,
        True,
    )

    # D6: alt không còn khoảng trắng ở biên (do &nbsp; cuối chuỗi cũ)
    check("không có alt còn khoảng trắng ở biên", any(a != a.strip() for a in alts), False)


def test_render() -> None:
    soup = load_soup()
    fields = extract_fields(soup)
    body_html, _, _, _, _ = clean_body(soup)
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


def test_render_roundtrip() -> None:
    """render_txt -> label_helper.parse_sample phải đọc lại đúng cả 4 field + body.

    Bẫy nếu không có ca này: đổi thứ tự/tên field trong render_txt vẫn để
    test_render xanh (nó chỉ so khớp thứ tự key), nhưng parse_sample sẽ đọc
    field đó ra None và label_helper báo "CHƯA THU" cho mọi bài - hỏng âm thầm.
    """
    soup = load_soup()
    fields = extract_fields(soup)
    body_html, _, _, _, _ = clean_body(soup)
    text = render_txt(fields, body_html)

    fd, tmp_path = tempfile.mkstemp(suffix=".txt")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
        parsed = parse_sample(tmp_path)
    finally:
        os.remove(tmp_path)

    check("round-trip title", parsed.get("title"), fields["title"])
    check("round-trip url_alias", parsed.get("url_alias"), fields["url_alias"])
    check(
        "round-trip meta_description",
        parsed.get("meta_description"),
        fields["meta_description"],
    )
    check("round-trip summary", parsed.get("summary"), fields["summary"])
    check("round-trip body không rỗng", bool(parsed.get("body", "").strip()), True)


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
    body_html, _, _, _, _ = clean_body(soup)
    check("fixture G-001 không có B6", _b6_codes(body_html), [])

    # alt nháy đơn có nội dung -> KHÔNG tính là thiếu (finding 2a)
    check(
        "alt nháy đơn có nội dung -> không B6",
        _b6_codes("<img alt='mô tả ảnh'>"),
        [],
    )
    # alt không quote có nội dung -> KHÔNG tính là thiếu
    check(
        "alt không quote có nội dung -> không B6",
        _b6_codes("<img alt=mota>"),
        [],
    )
    # alt nháy đơn rỗng -> vẫn tính là thiếu
    check(
        "alt nháy đơn rỗng vẫn tính là thiếu",
        _b6_codes("<img alt=''>"),
        ["B6 (1/1 ảnh thiếu alt text)"],
    )


def test_split_sentences_abbreviations() -> None:
    """D1: khớp viết tắt theo TỪ cuối cùng, không phải hậu tố chuỗi cố định.

    Trước khi sửa, "st." trong _ABBREVIATIONS khớp nhầm hậu tố "...nfast."
    của "VinFast." (do so khớp bằng before.endswith(a) trên cửa sổ 5 ký tự
    cố định), khiến câu bị dán làm một một cách có hệ thống trên toàn bộ
    gold set (mọi bài đều nói về VinFast).
    """
    check(
        "VinFast. không còn bị coi là viết tắt -> tách đúng 3 câu",
        split_sentences("Đây là xe của VinFast. Xe này rất tốt. Giá hợp lý."),
        [
            "Đây là xe của VinFast.",
            "Xe này rất tốt.",
            "Giá hợp lý.",
        ],
    )
    # Ca chốt: sửa D1 không được phá hành vi đúng vốn có - TP.HCM vẫn không
    # bị cắt câu giữa chừng (dấu chấm dính giữa "TP." và "HCM" vẫn được giữ).
    check(
        "TP.HCM. vẫn không bị cắt câu giữa chừng -> đúng 2 câu",
        split_sentences("Tôi ở TP.HCM. Trời hôm nay đẹp."),
        ["Tôi ở TP.HCM.", "Trời hôm nay đẹp."],
    )
    # Ca hồi quy: cách khớp theo "từ cuối" (re.search(r"(\S+)$", ...)) ban đầu
    # không bỏ dấu ngoặc/nháy mở đứng liền trước viết tắt, nên từ cuối lấy
    # được là "(tp." thay vì "tp." -> không khớp danh sách -> cắt câu sai.
    # Đã sửa bằng cách bỏ ký tự không phải chữ/số ở đầu từ trước khi so khớp.
    check(
        "viết tắt liền dấu ngoặc vẫn không cắt câu",
        len(split_sentences("Khu vực (tp. Thủ Đức) có nhiều trạm sạc.")),
        1,
    )


def test_keep_tags_and_br() -> None:
    """D2: KEEP_TAGS phải có br, h1, h5, h6 - phòng ngừa cho 29 bài chưa thu."""
    check("KEEP_TAGS có br", "br" in KEEP_TAGS, True)
    check("KEEP_TAGS có h1", "h1" in KEEP_TAGS, True)
    check("KEEP_TAGS có h5", "h5" in KEEP_TAGS, True)
    check("KEEP_TAGS có h6", "h6" in KEEP_TAGS, True)

    # <br> rỗng: nếu unwrap thì mất hẳn (không có nội dung để giữ lại),
    # hai dòng dính thành một -> phải còn nguyên trong output.
    soup = BeautifulSoup(
        '<div class="node-detail"><div class="field-body">'
        "<h5>Tiêu đề phụ</h5><p>Dòng một<br>Dòng hai</p>"
        "</div></div>",
        "html.parser",
    )
    body_html, _, _, _, _ = clean_body(soup)
    check("giữ nguyên thẻ <h5>", "<h5>" in body_html, True)
    check("giữ nguyên thẻ <br>", "<br" in body_html, True)


if __name__ == "__main__":
    test_fields()
    test_missing_node_detail()
    test_clean_body_errors()
    test_clean_text_with_nbsp()
    test_extract_fields_with_nbsp()
    test_body()
    test_render()
    test_render_roundtrip()
    test_b6()
    test_split_sentences_abbreviations()
    test_keep_tags_and_br()

    failed = False
    for name, ok, actual, expected in _results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name}")
        if not ok:
            failed = True
            print(f"    thực tế : {actual!r}")
            print(f"    kỳ vọng : {expected!r}")
    sys.exit(1 if failed else 0)
