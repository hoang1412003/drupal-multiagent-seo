"""Phần "đo bằng máy" của rubric Content Quality (docs/rubrics.md mục 3).

Tách khỏi `agents/content_quality.py` theo đúng cách `compliance_analysis.py`
và `seo_analysis.py` tách khỏi agent của chúng.

DÙNG CHUNG PHÉP TÁCH CÂU VỚI SCRIPT GÁN NHÃN. `split_sentences` và
`split_paragraphs` lấy từ `text_utils`, đúng hàm mà `scripts/label_helper.py`
dùng để sinh mã C4/C5. Trước 2026-08-10 hai bên có hai bản `strip_html` khác
nhau, đo được lệch tới 62 câu trên G-007 - nếu để nguyên thì CQ3 của agent và
C4 của người gán nhãn nói hai con số khác nhau về cùng một bài. Ngưỡng vẫn
tách bạch (họ `scoring` với họ `labelling`), chỉ CÁCH ĐO là chung.
"""
import re

from text_utils import split_paragraphs, split_sentences, strip_html

# CQ5: thứ tự phân cấp heading. Bắt cả h2 lẫn h3 kèm vị trí để biết có h3 nào
# đứng TRƯỚC h2 đầu tiên không.
_HEADING = re.compile(r"<(h[23])[^>]*>", re.IGNORECASE)


def cau_qua_dai(body: str, nguong_tieng: int) -> list:
    """Các câu dài hơn `nguong_tieng` tiếng.

    Đơn vị là TIẾNG chứ không phải TỪ: `len(s.split())` trên tiếng Việt viết
    rời từng âm tiết đếm ra tiếng ("ô tô điện" = 1 từ ghép, 3 tiếng). Ngưỡng
    30 vốn mượn từ quy ước readability tiếng Anh vốn đếm TỪ - ghi nhận ở
    annotation-guideline v1.3 mục 4.3, chưa sửa vì sửa cần một quyết định
    riêng và sẽ làm mọi số C4 cũ không so được nữa.
    """
    return [c for c in split_sentences(strip_html(body or ""))
            if len(c.split()) > nguong_tieng]


def doan_qua_dai(body: str, nguong_cau: int) -> list:
    """Các đoạn có nhiều hơn `nguong_cau` câu."""
    return [p for p in split_paragraphs(body or "")
            if len(split_sentences(p)) > nguong_cau]


def so_tu(body: str) -> int:
    return len(strip_html(body or "").split())


def cau_truc_heading(body: str) -> dict:
    """Có h2 không, và có h3 nào đứng trước h2 đầu tiên không.

    `h3_truoc_h2` là dấu hiệu phân cấp lộn xộn - mức 1 của CQ5. Đo bằng THỨ TỰ
    XUẤT HIỆN trong HTML chứ không đếm số lượng: một bài có 3 h2 và 5 h3 vẫn
    có thể lộn xộn nếu h3 đầu tiên nằm trước h2 đầu tiên.
    """
    the = [m.group(1).lower() for m in _HEADING.finditer(body or "")]
    co_h2 = "h2" in the
    h3_truoc_h2 = bool(the) and the[0] == "h3"
    return {"co_h2": co_h2, "so_h2": the.count("h2"),
            "so_h3": the.count("h3"), "h3_truoc_h2": h3_truoc_h2}
