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
