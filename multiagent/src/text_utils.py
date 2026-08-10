"""Tiện ích xử lý văn bản dùng chung cho MỌI phía đo cùng một bài.

Tách riêng vì script offline (sinh brand guideline), agent runtime (chấm bài)
và script gán nhãn (`scripts/label_helper.py`) đều phải bóc HTML và tách câu
theo ĐÚNG một cách - nếu hai bên đo khác nhau thì con số hai bên nói về cùng
một bài lại không so được với nhau.

**Đó không phải rủi ro lý thuyết - nó đã xảy ra.** Trước 2026-08-10 tồn tại
HAI bản `strip_html`: bản ở đây và một bản riêng trong `label_helper.py`. Mỗi
bản đúng một nửa:

    text_utils    giải mã thực thể HTML (&gt; &nbsp;)   thiếu: gộp ". ."
    label_helper  gộp dấu chấm nhân đôi ". " -> "."     thiếu: giải mã entity

Hệ quả đo được trên 8 bài gold set: số câu lệch nhau tới **62 câu trên
G-007** (266 so với 328, tức 23%). Vì rubric CQ3/CQ4 đếm câu dài và đoạn dài,
còn mã C4/C5 lúc gán nhãn cũng đếm đúng thứ đó, hai bên sẽ nói hai con số
khác nhau về cùng một bài. Nay hợp nhất: bản dưới đây làm CẢ HAI việc.
"""
import hashlib
import html
import re
import unicodedata

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
    # Gộp dấu chấm bị nhân đôi. Câu vốn đã kết thúc bằng "." nằm trong <p> thì
    # sau khi thay </p> thành ".\n" sẽ thành "..", và split_sentences đếm đó
    # thành một câu rỗng thừa. Bước này trước ở label_helper, nay dùng chung.
    text = re.sub(r"\.\s*\.", ".", text)
    return re.sub(r"[ \t]+", " ", text)


# --------------------------------------------------- tách câu / tách đoạn
#
# Chuyển từ `scripts/label_helper.py` vào đây 2026-08-10 để rubric CQ3/CQ4 của
# agent và mã C4/C5 của người gán nhãn dùng CHUNG một phép đếm. Ngưỡng thì vẫn
# tách bạch (họ `scoring` và họ `labelling` trong scoring.yaml, cố ý khác nhau
# - `config-spec.md` mục 2); chỉ **cách đo** là dùng chung.

# Viết tắt tiếng Việt hay gặp - không được cắt câu sau dấu chấm của chúng.
# Không có "st." (Street/Saint): văn bản cẩm nang tiếng Việt không dùng, và khi
# so khớp theo hậu tố chuỗi nó khớp nhầm cả "VinFast.".
_VIET_TAT = ("tp.", "tt.", "vd.", "vs.", "tr.", "q.", "p.")


def split_sentences(text: str) -> list:
    """Tách câu tiếng Việt.

    Không cắt ở: số thập phân ("3.5 giây"), viết tắt ("TP.HCM"), dấu chấm theo
    sau bởi chữ thường (thường là viết tắt bị lọt).
    """
    sentences = []
    current = ""
    for i, ch in enumerate(text):
        current += ch
        if ch not in ".!?":
            continue
        after = text[i + 1:i + 2]
        if ch == "." and text[i - 1:i].isdigit() and after.isdigit():
            continue                                  # 3.5
        # So khớp theo TỪ cuối cùng (ranh giới từ = khoảng trắng), không phải
        # hậu tố chuỗi cố định - tránh khớp nhầm "st." vào cuối "VinFast.".
        # Bỏ ký tự không phải chữ/số ở ĐẦU từ (dấu ngoặc/nháy mở kiểu "(tp."
        # hay "“tp.") trước khi so khớp, nhưng giữ dấu chấm ở CUỐI vì
        # _VIET_TAT gồm cả dấu chấm.
        last_word = re.search(r"(\S+)$", text[:i + 1])
        if last_word:
            candidate = re.sub(r"^\W+", "", last_word.group(1)).lower()
            if candidate in _VIET_TAT:
                continue                              # TP.HCM, (tp. Thủ Đức)
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


def split_paragraphs(raw_html: str) -> list:
    """Ưu tiên thẻ <p>; không có thì tách theo dòng trống."""
    paragraphs = re.findall(r"<p[^>]*>(.*?)</p>", raw_html, re.DOTALL | re.IGNORECASE)
    if paragraphs:
        return [strip_html(p).strip() for p in paragraphs if strip_html(p).strip()]
    plain = strip_html(raw_html)
    return [p.strip() for p in re.split(r"\n\s*\n", plain) if p.strip()]


def co_dau_tieng_viet(text: str) -> bool:
    """True nếu có ký tự tiếng Việt có dấu (kể cả đ/Đ). Dùng cho SEO5 và B7."""
    if "đ" in text.lower():
        return True
    return any(
        unicodedata.combining(c) for c in unicodedata.normalize("NFD", text)
    )


def _chuan_hoa(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


# Ranh giới giữa các MẢNH của một đoạn trích. Ba dạng đo được trên dữ liệu
# thật (docs/evidence/cp_lat_muc_raw.json), không phải phòng xa:
#   " và "   LLM nối hai trích dẫn:  "...285km..." và "Hành trình dài hơn..."
#   ;        cùng mục đích, dấu khác
#   ". "     hai câu nằm ở HAI THẺ HTML khác nhau - strip_html chèn ".\n" vào
#            giữa nên chúng KHÔNG BAO GIỜ liền mạch được trong text đã bóc
#
# `(?<=[.%])\s+` cần lookbehind để không cắt nhầm số thập phân ("1.000 km",
# "326,4km"): ở đó sau dấu chấm là chữ số chứ không phải khoảng trắng.
_TACH_MANH = re.compile(r"\s+và\s+|[;\n]|(?<=[.%])\s+")


def trich_dan_co_that(evidence: str, text_theo_field: dict) -> bool:
    """MỌI mảnh của đoạn trích có nằm nguyên văn trong bài không?

    Không có bước này thì quy tắc "bắt buộc trích dẫn" (rubrics.md mục 2.5)
    chỉ là lời dặn trong prompt - LLM bịa một câu nghe hợp lý là qua được.
    E1 đã bắt được đúng kiểu bịa này ở trường `rule` của bản cũ.

    Ở ĐÂY chứ không nằm trong `agents/compliance.py` vì rubrics.md mục 2.5 đặt
    quy tắc trích dẫn cho MỌI tiêu chí, không riêng Compliance. Để nguyên chỗ
    cũ thì Brand Voice phải viết phép kiểm thứ hai, và hai phép kiểm khác nhau
    cho cùng một quy tắc chính là thứ file này tồn tại để tránh (nợ B7).

    So sánh sau khi bỏ HTML, gộp khoảng trắng và hạ chữ thường - đủ lỏng để
    không loại nhầm khi LLM chuẩn hoá khoảng trắng, đủ chặt để loại câu bịa.

    VÌ SAO XÉT THEO MẢNH (sửa 2026-08-04). Bản cũ đòi đoạn trích là MỘT chuỗi
    liền mạch, nhưng LLM trả về bằng chứng THẬT mà không liền mạch. Đo trên
    20 lượt chấm: 10/20 lượt bị loại oan, và kiểm lại từng đoạn thì **không
    có lần nào LLM bịa** - ví dụ G-008:

        đoạn trích bị loại : "Trong khoảng 1 giờ ... từ 0 lên tới 10%.
                              Đây là bộ sạc cho phép người dùng..."
        khớp nguyên khối   : False
        mảnh 1 / mảnh 2    : True / True   <- cả hai đều có nguyên văn

    Hậu quả của việc loại oan không dừng ở một tiêu chí: nó đẩy CP4/CP7 về NA,
    tức rút chúng khỏi MẪU SỐ, mà mẫu số nhỏ đúng là nguyên nhân σ Compliance
    cao (rubrics.md mục 9.1 - mẫu số 4,6/8 thì một bậc là ±16,7 điểm).

    Vẫn là phép kiểm CHẶT, không phải nới lỏng có tính đầu hàng: **mọi** mảnh
    đều phải khớp nguyên văn thì mới đạt. Bịa nửa câu vẫn trượt. Và với đoạn
    trích liền mạch, kết quả không đổi so với bản cũ - một chuỗi đã khớp trọn
    thì từng mảnh của nó cũng khớp, nên phép kiểm mới chỉ nhận THÊM, không
    bao giờ loại đi thứ bản cũ đã chấp nhận.
    """
    kho = [_chuan_hoa(t) for t in text_theo_field.values()]
    manh = [
        _chuan_hoa(m).strip(" \"'“”…-")
        for m in _TACH_MANH.split(evidence or "")
    ]
    manh = [m for m in manh if m]
    if not manh:
        return False
    return all(any(m in t for t in kho) for m in manh)


# Các field tham gia content_hash, ĐÚNG thứ tự này. Phía PHP
# (AiReportRenderer::HASH_FIELDS) phải ghép y hệt, nếu lệch thì bảng cảnh báo
# "nội dung đã thay đổi" hiện sai vĩnh viễn. Có test hợp đồng dùng chung file
# drupal/scripts/content_hash_fixture.json để bắt sai lệch này.
_HASH_FIELDS = ("title", "body", "summary", "meta_description")


def content_hash(fields: dict) -> str:
    """Băm nội dung đã chấm, để biết bài có bị sửa sau khi chấm không.

    Dùng hash chứ KHÔNG dùng mốc thời gian `changed` của node: chính lệnh
    PATCH của write_back() làm `changed` nhảy, nên số mốc đó sẽ luôn báo
    "nội dung đã đổi" ngay sau khi chấm. Hash chỉ đổi khi nội dung thật sự đổi.

    Ở đây chứ không ở graph.py vì từ 2026-08-07 có BA người dùng: graph
    (dùng báo cáo), reconcile (so với hash đã chấm), worker (trả run_log).
    Để private trong graph thì hai chỗ kia phải chép lại công thức - dùng loại
    trùng lặp mà config-spec.md mục 1 ghi lại như một lời đã trả giá.
    """
    ghep = "\n".join(str(fields.get(k) or "") for k in _HASH_FIELDS)
    return hashlib.sha256(ghep.encode("utf-8")).hexdigest()
