"""Tiện ích xử lý văn bản dùng chung cho phần brand.

Tách riêng vì cả script offline (sinh brand guideline) lẫn agent runtime
(chấm bài) đều phải bóc HTML theo ĐÚNG một cách - nếu hai bên bóc khác nhau
thì tần suất thống kê được sẽ không khớp với tần suất đếm lúc chấm.
"""
import hashlib
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
