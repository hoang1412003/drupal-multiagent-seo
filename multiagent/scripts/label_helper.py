"""Trợ giúp gán nhãn gold set: tính sẵn các mã lỗi ĐO ĐƯỢC BẰNG MÁY.

Mục đích: cắt bớt thời gian gán nhãn thủ công (docs/goldset/annotation-guideline.md).
Script chỉ tính các mã lỗi đếm được một cách khách quan - B3, B4, B6, B7, B9
(đổi nhãn) và C4, C5 (KHÔNG đổi nhãn). Mọi mã còn lại (toàn bộ nhóm A, B1, B2,
B5, B8, B10) CẦN NGƯỜI ĐỌC và script cố ý KHÔNG đoán hộ.

HAI NHÓM MÃ TRẢ VỀ RIÊNG, KHÔNG GỘP MỘT LIST (guideline v1.3):
mã B quyết định nhãn, mã C thì không - `analyze()` trả chúng ở hai vị trí khác
nhau để việc đó là ràng buộc cấu trúc chứ không phải quy ước đặt tên mà người
gọi phải nhớ. Trước v1.3 câu dài/đoạn dài nằm trong B9 và kích hoạt 33/33 bài,
làm mọi bài thành `needs_revision` và xoá sạch lớp `publish` khỏi gold set.

Script KHÔNG gọi LLM và KHÔNG đọc kết quả AI - gán nhãn phải mù với kết quả AI
(annotation-guideline mục 2).

Định dạng file đầu vào (docs/goldset/raw/<sample_id>.txt), UTF-8:

    title: Hướng dẫn sạc pin ô tô điện VinFast đúng cách
    url_alias: /vn_vi/huong-dan-sac-pin-o-to-dien-vinfast
    meta_description: ?
    summary: Bài viết hướng dẫn các bước sạc pin an toàn...
    ---
    <nội dung thân bài, PHẢI là HTML - xem lưu ý dưới>

Body phải giữ nguyên HTML (thẻ <h2>, <img alt>, <a href>). Nếu dán text
thuần thì script đếm h2 = 0 và kết luận sai mã B9 cho mọi bài dài. Dùng
scripts/extract_gold_sample.py để sinh file này thay vì gõ tay.

Quy ước 2 giá trị đặc biệt cho các field ngoài body:
    ?        = CHƯA THU (chưa lấy về) -> script báo "chưa thu", không kết luận
    (bỏ trống) = ĐÃ KIỂM TRA VÀ KHÔNG CÓ  -> script kết luận là lỗi

Phân biệt này quan trọng: bỏ trống vì lười sẽ tạo ra lỗi B3 giả.

Cách chạy:
    .venv\\Scripts\\python.exe scripts\\label_helper.py ..\\docs\\goldset\\raw\\G-001.txt
    .venv\\Scripts\\python.exe scripts\\label_helper.py ..\\docs\\goldset\\raw\\*.txt
"""
import glob
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

import config
# Bóc HTML và tách câu dùng CHUNG với agent (text_utils). Trước 2026-08-10
# file này có bản `strip_html` riêng, lệch với bản của agent ở hai chỗ: bản
# kia giải mã thực thể HTML, bản này gộp dấu chấm nhân đôi. Đo được trên 8 bài
# gold set: số câu lệch tới 62 câu ở G-007 (266 so với 328). Vì rubric CQ3/CQ4
# đếm đúng thứ mã C4/C5 ở đây đếm, hai bên phải đo bằng một hàm.
from text_utils import (  # noqa: E402
    co_dau_tieng_viet,
    split_paragraphs,
    split_sentences,
    strip_html,
)

# Giữ tên cũ để không phải sửa mọi chỗ gọi trong file này và trong
# scripts/quet_ung_vien.py (nó import `strip_html`, `split_sentences` từ đây).
has_vietnamese_diacritics = co_dau_tieng_viet

NOT_COLLECTED = "?"

# Ngưỡng lấy từ khối `labelling` của config/scoring.yaml (diễn giải ở
# annotation-guideline.md v1.1 mục 4.2). Đều là giá trị TẠM, chờ calibrate ở
# Sprint 3 - script in ra số đo thô bên cạnh kết luận để khi ngưỡng đổi thì
# không phải đo lại.
#
# Trước đây đây là bản CHÉP thứ hai của cùng bộ số nằm trong graph.py và hai
# tài liệu. Bản chép đó đã trôi lệch một lần (mã B3 ghi 150-160 ở guideline
# trong khi rubric ghi 140-170) - đọc từ config để chuyện đó không lặp lại.
_LB = config.load()["labelling"]
TITLE_MIN, TITLE_MAX = _LB["title_ok"]          # B4
META_MIN, META_MAX = _LB["meta_ok"]             # B3
URL_MAX = _LB["url_max_chars"]                  # B7
# C4/C5 KHÔNG đổi nhãn, nên hai ngưỡng dưới không cần calibrate - chúng chỉ
# là bộ đếm ghi vào `notes`. Đơn vị là TIẾNG (len(s.split()) trên tiếng Việt
# viết rời từng âm tiết), không phải TỪ - guideline v1.3 mục 4.3.
LONG_SENTENCE_WORDS = _LB["long_sentence_words"]        # C4
LONG_PARAGRAPH_SENTENCES = _LB["long_paragraph_sentences"]  # C5
REPEAT_THRESHOLD = _LB["repeat_threshold"]      # C4/C5: "từ 3 lần trở lên"
HEADING_REQUIRED_WORDS = _LB["heading_required_words"]  # B9

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


def analyze(fields: dict) -> tuple[list[str], list[str], list[str]]:
    """Trả về (dòng số đo, mã nhóm A/B, mã nhóm C).

    Hai list mã tách riêng vì chúng có ngữ nghĩa khác nhau: nhóm B quy ra nhãn
    (annotation-guideline mục 5), nhóm C chỉ ghi vào `notes`.
    """
    measures, codes, c_codes = [], [], []

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

    # --- B6, B9 + C4/C5: đọc từ body ---------------------------------------
    body = fields.get("body", "")
    if body.strip():
        # --- B6: alt text của MỌI ảnh trong body ------------------------
        # Site thật không có field ảnh đại diện riêng - mọi ảnh nằm trong
        # body (spec 2026-07-29 mục 3.3), nên B6 xét tất cả ảnh thay vì
        # một field image_alt đơn lẻ.
        images = re.findall(r"<img[^>]*>", body, re.IGNORECASE)
        if images:
            # Nhận cả 3 kiểu quote: alt="...", alt='...', alt=khong-quote.
            # alt="" và alt='' (rỗng) vẫn phải tính là THIẾU nên không nằm
            # trong các nhánh trên (mỗi nhánh đều yêu cầu nội dung khác rỗng).
            no_alt = [
                img for img in images
                if not re.search(
                    # (?<![\w-]) chứ KHÔNG phải \b: \b khớp ngay giữa dấu
                    # gạch và chữ nên data-alt="x" bị đọc nhầm thành alt,
                    # khiến ảnh thiếu alt thật bị coi là có alt (bỏ sót B6).
                    # Kiểm 2026-08-04: 0 ảnh trong corpus hiện tại dính lỗi
                    # này, nên báo cáo đã sinh không bị ảnh hưởng.
                    r"""(?<![\w-])alt\s*=\s*(?:"[^"]+"|'[^']+'|[^\s>"']+)""",
                    img,
                    re.IGNORECASE,
                )
            ]
            measures.append(
                f"  số ảnh             {len(images)} (thiếu alt: {len(no_alt)})"
            )
            if no_alt:
                codes.append(f"B6 ({len(no_alt)}/{len(images)} ảnh thiếu alt text)")
            else:
                measures.append("  → B6 phần 'mô tả đúng ảnh không' CẦN NGƯỜI xét")
        else:
            measures.append("  số ảnh             0 (bài không có ảnh - không xét B6)")

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
            f"  câu > {LONG_SENTENCE_WORDS} tiếng      {len(long_sentences)}",
            f"  đoạn > {LONG_PARAGRAPH_SENTENCES} câu        {len(long_paragraphs)}",
            f"  heading            h2={h2} h3={h3}",
            f"  internal link      {links}",
        ]

        # B9 nay CHỈ còn tín hiệu cấu trúc (guideline v1.3). Hai tín hiệu văn
        # phong tách sang C4/C5 và KHÔNG đổi nhãn - lý do đầy đủ ở
        # annotation-guideline.md mục 4.3 và bảng đổi ở mục 11.
        if words > HEADING_REQUIRED_WORDS and h2 == 0:
            codes.append(f"B9 (bài {words} từ nhưng không có h2)")

        if len(long_sentences) >= REPEAT_THRESHOLD:
            c_codes.append(
                f"C4 ({len(long_sentences)} câu > {LONG_SENTENCE_WORDS} tiếng)"
            )
        if len(long_paragraphs) >= REPEAT_THRESHOLD:
            c_codes.append(
                f"C5 ({len(long_paragraphs)} đoạn > {LONG_PARAGRAPH_SENTENCES} câu)"
            )

        if long_sentences:
            measures.append("  Câu dài nhất:")
            longest = max(long_sentences, key=lambda s: len(s.split()))
            measures.append(f'    ({len(longest.split())} tiếng) "{longest[:110]}..."')

    return measures, codes, c_codes


HUMAN_ONLY = (
    "A1 claim tuyệt đối/so sánh nhất   A2 so sánh đối thủ   A3 số liệu sai lệch\n"
    "  A4 khuyến mại thiếu thời hạn      A5 lạc đề >50%       A6 mất an toàn\n"
    "  B1 tầm hoạt động thiếu chuẩn đo   B2 sạc thiếu trụ/%   B5 thuật ngữ brand\n"
    "  B8 chính tả, ngữ pháp             B10 số liệu không nguồn"
)


def report(path: str) -> None:
    fields = parse_sample(path)
    measures, codes, c_codes = analyze(fields)

    print("=" * 72)
    print(os.path.basename(path))
    print("=" * 72)
    print("\n[SỐ ĐO]")
    print("\n".join(measures))

    print("\n[MÃ LỖI MÁY KẾT LUẬN ĐƯỢC - ĐỔI NHÃN]")
    print("\n".join(f"  {c}" for c in codes) if codes else "  (không có)")

    # In khối RIÊNG chứ không gộp vào khối trên: gộp lại thì mã C nằm cạnh mã B
    # trong cùng một danh sách và người gán rất dễ áp nhầm quy tắc mục 5 lên
    # chúng - đúng cái lỗi mà guideline v1.3 vừa sửa.
    print("\n[MÃ NHÓM C - GHI VÀO `notes`, KHÔNG ĐỔI NHÃN]")
    print("\n".join(f"  {c}" for c in c_codes) if c_codes else "  (không có)")

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
