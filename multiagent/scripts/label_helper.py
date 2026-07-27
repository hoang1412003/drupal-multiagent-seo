"""Trợ giúp gán nhãn gold set: tính sẵn các mã lỗi ĐO ĐƯỢC BẰNG MÁY.

Mục đích: cắt bớt thời gian gán nhãn thủ công (docs/goldset/annotation-guideline.md).
Script chỉ tính các mã lỗi đếm được một cách khách quan - B3, B4, B6, B7, B9.
Mọi mã còn lại (toàn bộ nhóm A, B1, B2, B5, B8, B10) CẦN NGƯỜI ĐỌC và script
cố ý KHÔNG đoán hộ.

Script KHÔNG gọi LLM và KHÔNG đọc kết quả AI - gán nhãn phải mù với kết quả AI
(annotation-guideline mục 2).

Định dạng file đầu vào (docs/goldset/raw/<sample_id>.txt), UTF-8:

    title: Hướng dẫn sạc pin ô tô điện VinFast đúng cách
    url_alias: /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
    meta_description: ?
    image_alt:
    ---
    <nội dung thân bài, HTML hoặc text thuần>

Quy ước 2 giá trị đặc biệt cho các field ngoài body:
    ?        = CHƯA THU (chưa lấy về) -> script báo "chưa thu", không kết luận
    (bỏ trống) = ĐÃ KIỂM TRA VÀ KHÔNG CÓ  -> script kết luận là lỗi

Phân biệt này quan trọng: bỏ trống vì lười sẽ tạo ra lỗi B3/B6 giả.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\label_helper.py ..\\docs\\goldset\\raw\\G-001.txt
    .venv\\Scripts\\python.exe scripts\\label_helper.py ..\\docs\\goldset\\raw\\*.txt
"""
import glob
import os
import re
import sys
import unicodedata

NOT_COLLECTED = "?"

# Ngưỡng lấy từ annotation-guideline.md v1.1 mục 4.2. Đều là giá trị TẠM,
# chờ calibrate ở Sprint 3 - script in ra số đo thô bên cạnh kết luận để khi
# ngưỡng đổi thì không phải đo lại.
TITLE_MIN, TITLE_MAX = 40, 70          # B4
META_MIN, META_MAX = 140, 170          # B3
URL_MAX = 75                           # B7
LONG_SENTENCE_WORDS = 30               # B9
LONG_PARAGRAPH_SENTENCES = 5           # B9
REPEAT_THRESHOLD = 3                   # B9: "từ 3 lần trở lên"
HEADING_REQUIRED_WORDS = 500           # B9

# Viết tắt tiếng Việt hay gặp - không được cắt câu sau dấu chấm của chúng.
_ABBREVIATIONS = ("tp.", "tt.", "vd.", "vs.", "tr.", "st.", "q.", "p.")


def parse_sample(path: str) -> dict:
    """Đọc file mẫu -> dict các field. Thiếu '---' -> coi toàn bộ là body."""
    with open(path, encoding="utf-8") as f:
        raw = f.read()

    head, sep, body = raw.partition("\n---")
    if not sep:
        return {"body": raw.strip()}

    fields = {"body": body.lstrip("-\n").strip()}
    for line in head.splitlines():
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fields[key.strip().lower()] = value.strip()
    return fields


# Thẻ khối: kết thúc thẻ = kết thúc câu. Không xử lý riêng thì tiêu đề <h2>
# (vốn không có dấu chấm) dính vào câu đầu của đoạn ngay sau, làm số câu dài
# bị thổi lên.
_BLOCK_END = re.compile(
    r"</(?:h[1-6]|p|li|div|blockquote|td|th)\s*>|<br\s*/?>", re.IGNORECASE
)


def strip_html(html: str) -> str:
    text = _BLOCK_END.sub(".\n", html)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\.\s*\.", ".", text)      # gộp dấu chấm bị nhân đôi
    return re.sub(r"[ \t]+", " ", text)


def has_vietnamese_diacritics(text: str) -> bool:
    """True nếu có ký tự tiếng Việt có dấu (kể cả đ/Đ)."""
    if "đ" in text.lower():
        return True
    # Ký tự có dấu tách được thành chữ cái gốc + dấu tổ hợp
    return any(
        unicodedata.combining(c) for c in unicodedata.normalize("NFD", text)
    )


def split_sentences(text: str) -> list[str]:
    """Tách câu tiếng Việt (bản v0 - sẽ thay bằng LanguageAnalyzer).

    Không cắt ở: số thập phân ("3.5 giây"), viết tắt ("TP.HCM"), dấu chấm
    theo sau bởi chữ thường (thường là viết tắt bị lọt).
    """
    sentences = []
    current = ""
    for i, ch in enumerate(text):
        current += ch
        if ch not in ".!?":
            continue
        before = text[max(0, i - 4):i + 1].lower()
        after = text[i + 1:i + 2]
        if ch == "." and text[i - 1:i].isdigit() and after.isdigit():
            continue                                  # 3.5
        if any(before.endswith(a) for a in _ABBREVIATIONS):
            continue                                  # TP.HCM
        if after and after not in " \n":
            continue                                  # dính liền, chưa hết câu
        if after == " " and text[i + 2:i + 3].islower():
            continue                                  # viết tắt lọt lưới
        if current.strip():
            sentences.append(current.strip())
        current = ""
    if current.strip():
        sentences.append(current.strip())
    return sentences


def split_paragraphs(html: str) -> list[str]:
    """Ưu tiên thẻ <p>; không có thì tách theo dòng trống."""
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
    if paragraphs:
        return [strip_html(p).strip() for p in paragraphs if strip_html(p).strip()]
    plain = strip_html(html)
    return [p.strip() for p in re.split(r"\n\s*\n", plain) if p.strip()]


def analyze(fields: dict) -> tuple[list[str], list[str]]:
    """Trả về (dòng số đo, mã lỗi máy kết luận được)."""
    measures, codes = [], []

    def check(name: str, value):
        """None = chưa thu; chuỗi rỗng = đã kiểm tra và không có."""
        if value is None or value == NOT_COLLECTED:
            measures.append(f"  {name:<18} CHƯA THU - tự kiểm tra")
            return None
        return value

    # --- B4: title ---------------------------------------------------------
    title = check("title", fields.get("title"))
    if title is not None:
        n = len(title)
        flags = []
        if not (TITLE_MIN <= n <= TITLE_MAX):
            flags.append(f"ngoài {TITLE_MIN}-{TITLE_MAX}")
        letters = [c for c in title if c.isalpha()]
        if letters and all(c.isupper() for c in letters):
            flags.append("VIẾT HOA TOÀN BỘ")
        for year in re.findall(r"\b(20\d{2})\b", title):
            flags.append(f"gắn năm {year} - kiểm tra còn hợp lệ không")
        measures.append(f"  title              {n} ký tự")
        if flags:
            codes.append(f"B4 ({'; '.join(flags)})")

    # --- B3: meta_description ---------------------------------------------
    meta = check("meta_description", fields.get("meta_description"))
    if meta is not None:
        n = len(meta)
        measures.append(f"  meta_description   {n} ký tự")
        if n == 0:
            codes.append("B3 (trống)")
        elif not (META_MIN <= n <= META_MAX):
            codes.append(f"B3 ({n} ký tự, ngoài {META_MIN}-{META_MAX})")

    # --- B7: url_alias -----------------------------------------------------
    slug = check("url_alias", fields.get("url_alias"))
    if slug is not None:
        n = len(slug)
        flags = []
        if not slug:
            flags.append("trống")
        else:
            if has_vietnamese_diacritics(slug):
                flags.append("còn dấu tiếng Việt")
            if n > URL_MAX:
                flags.append(f"dài {n} ký tự (> {URL_MAX})")
        measures.append(f"  url_alias          {n} ký tự")
        if flags:
            codes.append(f"B7 ({'; '.join(flags)})")
        measures.append("  → B7 phần 'thiếu từ khóa chính' CẦN NGƯỜI xét")

    # --- B6: image_alt -----------------------------------------------------
    alt = check("image_alt", fields.get("image_alt"))
    if alt is not None:
        if not alt:
            codes.append("B6 (thiếu alt text)")
        else:
            measures.append(f"  image_alt          có ({len(alt)} ký tự)")
            measures.append("  → B6 phần 'mô tả đúng ảnh không' CẦN NGƯỜI xét")

    # --- B9: cấu trúc body -------------------------------------------------
    body = fields.get("body", "")
    if body.strip():
        plain = strip_html(body)
        words = len(plain.split())
        paragraphs = split_paragraphs(body)
        all_sentences = split_sentences(plain)
        long_sentences = [s for s in all_sentences if len(s.split()) > LONG_SENTENCE_WORDS]
        long_paragraphs = [
            p for p in paragraphs
            if len(split_sentences(p)) > LONG_PARAGRAPH_SENTENCES
        ]
        h2 = len(re.findall(r"<h2[^>]*>", body, re.IGNORECASE))
        h3 = len(re.findall(r"<h3[^>]*>", body, re.IGNORECASE))
        links = len(re.findall(r"<a\s[^>]*href=", body, re.IGNORECASE))

        measures += [
            f"  body               {words} từ (đếm theo tiếng, chưa tách từ)",
            f"  số đoạn            {len(paragraphs)}",
            f"  số câu             {len(all_sentences)}",
            f"  câu > {LONG_SENTENCE_WORDS} từ         {len(long_sentences)}",
            f"  đoạn > {LONG_PARAGRAPH_SENTENCES} câu        {len(long_paragraphs)}",
            f"  heading            h2={h2} h3={h3}",
            f"  internal link      {links}",
        ]

        b9 = []
        if len(long_sentences) >= REPEAT_THRESHOLD:
            b9.append(f"{len(long_sentences)} câu > {LONG_SENTENCE_WORDS} từ")
        if len(long_paragraphs) >= REPEAT_THRESHOLD:
            b9.append(f"{len(long_paragraphs)} đoạn > {LONG_PARAGRAPH_SENTENCES} câu")
        if words > HEADING_REQUIRED_WORDS and h2 == 0:
            b9.append(f"bài {words} từ nhưng không có h2")
        if b9:
            codes.append(f"B9 ({'; '.join(b9)})")

        if long_sentences:
            measures.append("  Câu dài nhất:")
            longest = max(long_sentences, key=lambda s: len(s.split()))
            measures.append(f'    ({len(longest.split())} từ) "{longest[:110]}..."')

    return measures, codes


HUMAN_ONLY = (
    "A1 claim tuyệt đối/so sánh nhất   A2 so sánh đối thủ   A3 số liệu sai lệch\n"
    "  A4 khuyến mại thiếu thời hạn      A5 lạc đề >50%       A6 mất an toàn\n"
    "  B1 tầm hoạt động thiếu chuẩn đo   B2 sạc thiếu trụ/%   B5 thuật ngữ brand\n"
    "  B8 chính tả, ngữ pháp             B10 số liệu không nguồn"
)


def report(path: str) -> None:
    fields = parse_sample(path)
    measures, codes = analyze(fields)

    print("=" * 72)
    print(os.path.basename(path))
    print("=" * 72)
    print("\n[SỐ ĐO]")
    print("\n".join(measures))

    print("\n[MÃ LỖI MÁY KẾT LUẬN ĐƯỢC]")
    print("\n".join(f"  {c}" for c in codes) if codes else "  (không có)")

    print("\n[CẦN NGƯỜI ĐỌC - script không đoán hộ]")
    print("  " + HUMAN_ONLY)

    print("\n[NHẮC]")
    print("  - Có bất kỳ mã A nào  -> rejected")
    print("  - Không A, có mã B    -> needs_revision")
    print("  - Không A, không B    -> publish  (mã C không ảnh hưởng)")
    print("  - Gán nhãn MÙ: không mở field_ai_status/field_ai_score trước khi chốt")
    print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(sorted(glob.glob(arg)) or [arg])

    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print(f"Không tìm thấy file: {', '.join(missing)}")
        sys.exit(1)

    for path in paths:
        report(path)
