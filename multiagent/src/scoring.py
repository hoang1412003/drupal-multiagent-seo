"""Quy các mức rubric ra điểm 0-100 (docs/rubrics.md mục 2.2) và tra bảng
severity cho Compliance (mục 6).

Hàm thuần: không gọi mạng, không gọi LLM. Đây là điều kiện để calibrate
ngưỡng từ gold set ở Sprint 3 - chấm lại cùng bộ mức luôn ra cùng điểm.

Brand Voice và Compliance dùng. Content Quality và SEO chưa (docs/rubrics.md
mục 8.1).
"""


def score_from_criteria(criteria: list[dict]) -> float | None:
    """Mức 0/1/2 của từng tiêu chí -> điểm 0-100.

    Tiêu chí NA (level=None) bị loại khỏi CẢ tử số LẪN mẫu số. NA tuyệt đối
    không được tính là "đạt": nếu tính, mọi bài không nhắc tới tiêu chí đó
    đều được cộng điểm miễn phí và tiêu chí thành hằng số.

    Trả None khi không tiêu chí nào áp dụng được - nghĩa là CHƯA chấm được,
    khác hẳn 0 điểm.
    """
    ap_dung = [c for c in criteria if c["level"] is not None]
    if not ap_dung:
        return None
    return round(100 * sum(c["level"] for c in ap_dung) / (2 * len(ap_dung)), 1)


# Thang điểm của hệ thống. score_from_criteria() luôn quy các mức về dải này.
# KHÔNG đưa vào scoring.yaml: đây là định nghĩa thang đo, không phải ngưỡng
# calibrate được - calibration đổi ngưỡng quyết định, không đổi thang.
DIEM_MIN, DIEM_MAX = 0, 100


def kiem_diem_llm(score, ten_agent: str):
    """Kiểm điểm do LLM tự đặt, trước khi nó vào công thức của Aggregator.

    Content Quality và SEO chưa chuyển sang rubric nên vẫn để LLM tự cho
    `score` (nợ A1). Hai điều kiện cộng lại làm chỗ này hở:

    1. KHÔNG chỗ nào nói cho LLM biết thang điểm là gì - cả hai system prompt
       đều không nhắc "0-100", LLM chỉ suy ra từ tên trường `score`.
    2. Structured outputs không chặn hộ: `minimum`/`maximum` nằm trong nhóm
       ràng buộc JSON Schema mà Anthropic **không hỗ trợ**, nên đặt vào schema
       là để cho có. Kiểu `integer` thì có hiệu lực, nên chỉ cần kiểm dải.

    Ném ValueError chứ KHÔNG kẹp về biên: graph.py bắt exception rồi đánh dấu
    agent lỗi, Aggregator chia lại trọng số và ghi `note`, nên người duyệt
    thấy "điểm chưa đầy đủ". Kẹp biên sẽ sửa lặng lẽ một con số bất thường -
    đúng kiểu im lặng mà cả dự án tránh.
    """
    if not DIEM_MIN <= score <= DIEM_MAX:
        raise ValueError(
            f"Agent {ten_agent} trả score = {score}, ngoài thang "
            f"{DIEM_MIN}-{DIEM_MAX}. Không dùng được cho điểm tổng."
        )
    return score


# Severity của flag Compliance, tra theo MÃ tiêu chí (docs/rubrics.md mục 6).
#
# Vì sao là bảng tra chứ không để LLM chọn: `critical` kích hoạt veto của
# Aggregator, tức nó chính là quyết định CHẶN HAY KHÔNG CHẶN xuất bản. E1
# (2026-08-04, docs/evidence/e1_e4_report.txt) đo được cách cũ - để LLM tự
# chọn trong enum - cho σ = 5.48 trên bài G-002: cùng bài, cùng model, cùng
# code, lúc thì 0 flag/95 điểm, lúc thì 2-3 flag mức low/85 điểm.
_SEVERITY_CP = {
    "CP1": "critical",   # claim tuyệt đối/so sánh nhất
    "CP2": "critical",   # so sánh trực tiếp hơn hẳn đối thủ
    "CP3": "critical",   # số liệu sai lệch so với thông số công bố
    "CP4": "critical",   # khuyến mại thiếu thời hạn/điều kiện
    "CP5": "medium",     # tầm hoạt động thiếu chuẩn đo
    "CP6": "medium",     # thời gian sạc thiếu loại trụ/dải %
    "CP7": "medium",     # chính sách pin thiếu điều kiện/phí/thời hạn
    "CP8": "low",        # số liệu không nguồn
}


def severity_for(criterion_id: str, level: int) -> str:
    """Mức 0 -> severity trong bảng. Mức 1 -> luôn `low`.

    Mức 1 nghĩa là "đạt một phần" - đáng ghi chú cho người duyệt, không đáng
    chặn xuất bản. Quy tắc này chính là chỗ hiện thực yêu cầu ở rubrics.md
    mục 6.2: **CP3 mức 1 ("không kiểm chứng được") cố ý KHÔNG phải critical**,
    vì KB fact-check chỉ có thông số của một số model - "không tra được" khác
    "sai". Coi nó là critical sẽ từ chối oan mọi bài nhắc model ngoài KB, đó
    là lỗi hệ thống chứ không phải lỗi nội dung.

    Chỉ gọi với mức 0 hoặc 1; mức 2 và NA không sinh flag nên không có
    severity.
    """
    if level == 0:
        return _SEVERITY_CP[criterion_id]
    return "low"
