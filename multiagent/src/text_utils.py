"""Tiện ích xử lý văn bản dùng chung cho phần brand.

Tách riêng vì cả script offline (sinh brand guideline) lẫn agent runtime
(chấm bài) đều phải bóc HTML theo ĐÚNG một cách - nếu hai bên bóc khác nhau
thì tần suất thống kê được sẽ không khớp với tần suất đếm lúc chấm.
"""
import html
import re

# Thẻ khối: kết thúc thẻ = kết thúc câu, nếu không tiêu đề <h2> (không có dấu
# chấm) sẽ dính vào câu đầu của đoạn ngay sau.
_BLOCK_END = re.compile(
    r"</(?:h[1-6]|p|li|div|blockquote|td|th)\s*>|<br\s*/?>", re.IGNORECASE
)


def strip_html(raw: str) -> str:
    """Bỏ thẻ HTML, giữ lại phần chữ hiển thị.

    Quan trọng: nội dung THUỘC TÍNH (alt, href, title) bị bỏ hẳn, không lẫn
    vào chữ của bài - alt text là mô tả ảnh, không phải câu văn tác giả viết,
    tính vào thống kê giọng văn sẽ sai.
    """
    text = _BLOCK_END.sub(".\n", raw)
    text = re.sub(r"<[^>]+>", " ", text)
    # Giải mã thực thể HTML (&gt; &amp; &nbsp;...) SAU khi đã bỏ thẻ - làm
    # trước sẽ biến "&lt;p&gt;" thành thẻ thật rồi bị xoá nhầm. Không giải mã
    # thì đoạn trích làm bằng chứng hiện ra dạng "&gt;&gt;&gt; Tìm hiểu thêm".
    text = html.unescape(text)
    return re.sub(r"[ \t]+", " ", text)
