"""Quy các mức rubric ra điểm 0-100 (docs/rubrics.md mục 2.2).

Hàm thuần: không gọi mạng, không gọi LLM. Đây là điều kiện để calibrate
ngưỡng từ gold set ở Sprint 3 - chấm lại cùng bộ mức luôn ra cùng điểm.

Hiện chỉ Brand Voice Agent dùng. Khi 3 agent còn lại chuyển sang rubric thì
dùng lại đúng hàm này (docs/rubrics.md mục 8).
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
