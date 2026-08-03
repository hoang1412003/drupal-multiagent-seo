"""Đếm các đặc trưng brand trên một đoạn văn bản + kiểm định thống kê.

Module này DÙNG CHUNG cho hai phía, và đó là lý do nó tồn tại:
  - scripts/build_brand_guideline.py  - đếm trên corpus BRAND để RÚT RA quy tắc
  - src/agents/brand_voice.py         - đếm trên bài đang chấm để ÁP quy tắc

Nếu hai phía đếm bằng hai đoạn code khác nhau thì quy tắc rút ra không áp
đúng lúc chạy, và sai lệch đó rất khó phát hiện.
"""
import re
import unicodedata
from math import comb

# Mức ý nghĩa thống kê. Với n = 10 bài, ngưỡng thành quy tắc TỰ RƠI RA là
# >=9/10 (p = 0.021); 8/10 cho p = 0.109 nên không đạt. Ngưỡng không do ai
# đặt ra - xem spec mục 4.3.
SIGNIFICANCE = 0.05


def binom_two_sided_p(k: int, n: int) -> float:
    """Xác suất hai phía của kiểm định nhị thức, giả thuyết gốc p = 0,5.

    Trả về: nếu hai biến thể thực sự ngang nhau, xác suất quan sát được mức
    lệch khỏi 50-50 ít nhất bằng mức đang có là bao nhiêu. p nhỏ nghĩa là
    mức lệch không giải thích được bằng ngẫu nhiên.

    Dùng mốc 50-50 cả khi có nhiều hơn 2 ứng viên. Đó là lựa chọn BẢO THỦ:
    với 3-4 ứng viên, tỉ lệ ngẫu nhiên thực tế chỉ 1/3-1/4, nên đòi hỏi vượt
    1/2 là đặt thanh cao hơn mức cần thiết.
    """
    if n == 0:
        return 1.0
    lech = abs(k - n / 2)
    duoi = sum(comb(n, i) for i in range(n + 1) if abs(i - n / 2) >= lech)
    return duoi / (2 ** n)


def count_variants(text: str, variants: list[str]) -> dict[str, int]:
    """Đếm số lần xuất hiện của từng biến thể, không phân biệt hoa/thường.

    So khớp biến thể DÀI trước: các biến thể chồng nhau ("xe ô tô điện" chứa
    "ô tô điện"), nếu không ưu tiên dài thì một lần xuất hiện bị đếm cho cả
    hai và tổng số lần vượt quá số lần thật.
    """
    counts = {v: 0 for v in variants}
    if not text or not variants:
        return counts
    theo_do_dai = sorted(variants, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(v) for v in theo_do_dai), re.IGNORECASE)
    tra_cuu = {v.lower(): v for v in variants}
    for match in pattern.finditer(text):
        counts[tra_cuu[match.group(0).lower()]] += 1
    return counts


def count_model_name_usage(text: str, canonical_models: list[str]) -> tuple[int, list[str]]:
    """Đếm cách viết tên model. Trả (số chỗ viết đúng, list chỗ viết sai).

    Biến thể sai KHÔNG liệt kê tay mà sinh từ dạng chuẩn: bắt mọi cách viết
    khớp khi bỏ qua dấu cách và hoa/thường ("VF8", "vf8", "Vf 8"), rồi so
    nguyên văn với dạng chuẩn - khác là sai.
    """
    dung, sai = 0, []
    for canonical in canonical_models:
        hau_to = canonical[2:].strip()          # "VF 8" -> "8";  "VF e34" -> "e34"
        pattern = re.compile(rf"\bVF\s*{re.escape(hau_to)}\b", re.IGNORECASE)
        for match in pattern.finditer(text):
            if match.group(0) == canonical:
                dung += 1
            else:
                sai.append(match.group(0))
    return dung, sai


def _bo_dau(text: str) -> str:
    """Bỏ dấu tiếng Việt để so sánh chữ hoa/thường ổn định."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )


def classify_title_case(title: str) -> str:
    """Phân loại kiểu viết hoa tiêu đề.

    Trả một trong: ALL_CAPS / TITLE_CASE / SENTENCE_CASE / LOWERCASE / UNKNOWN.

    TITLE_CASE = quá nửa số từ viết hoa chữ đầu. Mốc "quá nửa" là điểm giữa
    tự nhiên giữa hai kiểu, không phải ngưỡng chọn tuỳ ý.

    LOWERCASE tách riêng khỏi SENTENCE_CASE: sentence case theo định nghĩa là
    viết hoa chữ cái ĐẦU rồi phần còn lại thường. Tiêu đề toàn chữ thường
    không thoả điều đó. Gộp chung sẽ khiến tiêu đề kiểu "test" được chấm đạt
    quy ước viết hoa - đúng loại điểm miễn phí cần tránh.
    """
    chu_cai = [c for c in title if c.isalpha()]
    if not chu_cai:
        return "UNKNOWN"
    if all(c.isupper() for c in chu_cai):
        return "ALL_CAPS"
    tu = [t for t in re.findall(r"\S+", title) if any(c.isalpha() for c in t)]
    if not tu:
        return "UNKNOWN"
    if not _bo_dau(tu[0])[0].isupper():
        return "LOWERCASE"
    viet_hoa = sum(1 for t in tu if _bo_dau(t)[0].isupper())
    return "TITLE_CASE" if viet_hoa * 2 > len(tu) else "SENTENCE_CASE"
