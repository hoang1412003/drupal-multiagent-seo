"""Tiện ích xử lý văn bản dùng chung cho phần brand.

Tách riêng vì cả script offline (sinh brand guideline) lẫn agent runtime
(chấm bài) đều phải bóc HTML theo ĐÚNG một cách - nếu hai bên bóc khác nhau
thì tần suất thống kê được sẽ không khớp với tần suất đếm lúc chấm.
"""
import re

# Thẻ khối: kết thúc thẻ = kết thúc câu, nếu không tiêu đề <h2> (không có dấu
# chấm) sẽ dính vào câu đầu của đoạn ngay sau.
_BLOCK_END = re.compile(
    r"</(?:h[1-6]|p|li|div|blockquote|td|th)\s*>|<br\s*/?>", re.IGNORECASE
)


def strip_html(html: str) -> str:
    """Bỏ thẻ HTML, giữ lại phần chữ hiển thị.

    Quan trọng: nội dung THUỘC TÍNH (alt, href, title) bị bỏ hẳn, không lẫn
    vào chữ của bài - alt text là mô tả ảnh, không phải câu văn tác giả viết,
    tính vào thống kê giọng văn sẽ sai.
    """
    text = _BLOCK_END.sub(".\n", html)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"[ \t]+", " ", text)
