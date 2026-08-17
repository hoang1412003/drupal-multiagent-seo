from typing import Literal, NotRequired, Optional, TypedDict


class ContentReviewState(TypedDict):
    node_id: str
    # Version duong quyet dinh va ngay danh gia di xuyen graph. NotRequired
    # giu tuong thich voi script legacy: thieu policy_version duoc normalize
    # thanh v1 tai orchestrator, con v2 bat buoc co assessment_as_of.
    policy_version: NotRequired[str]
    assessment_as_of: NotRequired[str]
    # Khóa tra config trọng số/ngưỡng (docs/config-spec.md mục 4). Không
    # hard-code "vi" ở đâu trong logic agent - đây là một trong ba điểm giữ
    # sẵn để mở rộng ngôn ngữ/loại nội dung mà không đập đi làm lại
    # (docs/architecture.md mục 5.6). Thiếu chúng thì không tra config được.
    #
    # Hai field này đi hết đường xuống agent từ 2026-08-05 (nợ B6 đã đóng):
    # graph._khoa_cua() suy ra cặp khoá MỘT lần rồi dùng chung cho Aggregator
    # lẫn hai node agent, nên không còn cảnh Aggregator tra theo state trong
    # khi BV6/CP3 lọc Chroma bằng hằng số.
    content_type: str
    langcode: str
    # 6 trường nội dung để đánh giá theo từng field (docs/architecture.md mục 3):
    # title, body, summary, url_alias, meta_description, image_alt
    fields: dict
    raw_content: dict

    content_quality_result: Optional[dict]
    seo_result: Optional[dict]
    brand_result: Optional[dict]
    compliance_result: Optional[dict]

    final_score: Optional[float]
    decision: Optional[Literal["publish", "needs_revision", "rejected"]]
    report: Optional[dict]
