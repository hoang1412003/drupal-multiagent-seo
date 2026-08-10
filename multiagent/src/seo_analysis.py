"""Phần "đo bằng máy" của rubric SEO (docs/rubrics.md mục 4).

Tách khỏi `agents/seo.py` theo đúng cách `compliance_analysis.py` tách khỏi
`agents/compliance.py`: phần đếm được bằng regex nằm riêng, agent chỉ còn việc
ghép mức.

7 trong 10 tiêu chí SEO đo được hoàn toàn bằng máy (SEO1, SEO3, SEO7, SEO10)
hoặc đo được PHẦN mức 0 của nó (SEO5, SEO8, SEO9) - cao hơn hẳn tỉ lệ của
Compliance (3/8) hay Content Quality (3/8). Đó là lý do SEO được chuyển sang
rubric trước: nó là ca ít rủi ro nhất về mặt dao động điểm.

MỌI NGƯỠNG ĐỌC TỪ khối `scoring` của config/scoring.yaml, không hằng số nào
viết cứng ở đây. Trước 2026-08-10 các ngưỡng này nằm trong CHUỖI system prompt
của agent, và đã trôi lệch một lần (nợ B4: prompt ghi meta 150-160 trong khi
config và rubric đều ghi 140-170). `scripts/test_seo_prompt.py` được dựng để
khoá bản chép đó lại; nay bản chép biến mất nên test đó cũng bỏ được.
"""
import re

from text_utils import co_dau_tieng_viet, strip_html

# --- SEO8: cấu trúc heading ------------------------------------------------
_H2 = re.compile(r"<h2[^>]*>", re.IGNORECASE)
_HEADING = re.compile(r"<(h[23])[^>]*>(.*?)</\1\s*>", re.DOTALL | re.IGNORECASE)

# --- SEO10: internal link --------------------------------------------------
# Chỉ đếm thẻ <a> CÓ href. Link rỗng (<a name="...">) không phải internal link.
_LINK = re.compile(r"<a\s[^>]*href\s*=", re.IGNORECASE)

# --- SEO9: alt text --------------------------------------------------------
# `fields["image_alt"]` do drupal_client._extract_image_alt() dựng: mỗi ảnh một
# dòng, alt nằm sau dấu hai chấm ĐẦU TIÊN. Dòng trống sau dấu hai chấm nghĩa là
# ảnh đó thiếu alt. Chuỗi rỗng nghĩa là bài không có ảnh nào -> SEO9 trả NA,
# không phải mức 0 (bài không ảnh không thể "thiếu alt").
_DONG_ANH = re.compile(r"^(.*?):(.*)$")


def do_title(title: str) -> dict:
    return {"so_ky_tu": len(title or "")}


def do_meta(meta: str) -> dict:
    return {"so_ky_tu": len(meta or ""), "trong": not (meta or "").strip()}


def do_url(url: str) -> dict:
    url = url or ""
    return {
        "trong": not url.strip(),
        "co_dau": co_dau_tieng_viet(url),
        "so_ky_tu": len(url),
    }


def do_body(body: str) -> dict:
    """Số từ, số h2, số internal link, và danh sách heading để LLM soi từ khoá.

    Đếm từ trên bản đã bóc HTML - đếm trên HTML thô sẽ tính cả tên thẻ và URL
    trong href thành từ, thổi số lên nhiều lần với bài nhiều link.
    """
    body = body or ""
    plain = strip_html(body)
    return {
        "so_tu": len(plain.split()),
        "so_h2": len(_H2.findall(body)),
        "so_link": len(_LINK.findall(body)),
        "heading": [strip_html(t).strip() for _, t in _HEADING.findall(body)],
    }


def do_anh(image_alt: str) -> dict:
    """Đếm ảnh và ảnh thiếu alt từ chuỗi nhiều dòng của drupal_client.

    Trả `co_anh=False` khi bài không có ảnh nào - người gọi phải phân biệt
    trường hợp đó với "có ảnh nhưng thiếu alt", vì cái đầu là NA còn cái sau
    là mức 0.
    """
    dong = [d for d in (image_alt or "").splitlines() if d.strip()]
    thieu = []
    for d in dong:
        m = _DONG_ANH.match(d)
        if m and not m.group(2).strip():
            thieu.append(m.group(1).strip())
    return {"co_anh": bool(dong), "so_anh": len(dong),
            "thieu_alt": thieu, "so_thieu": len(thieu)}


def dau_body(body: str, so_tu: int = 100) -> str:
    """`so_tu` từ đầu của body, để LLM kiểm SEO6 (từ khoá trong đoạn mở đầu).

    Cắt sẵn ở đây thay vì dặn LLM "xét 100 từ đầu": đếm từ là việc máy làm
    chính xác và miễn phí, còn LLM ước lượng thì mỗi lần một khác - đúng chủ
    trương docs/rubrics.md mục 2.4.
    """
    return " ".join(strip_html(body or "").split()[:so_tu])
