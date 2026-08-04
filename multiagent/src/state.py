from typing import Literal, Optional, TypedDict


class ContentReviewState(TypedDict):
    node_id: str
    # Khóa tra config trọng số/ngưỡng (docs/config-spec.md mục 4). Không
    # hard-code "vi" ở đâu trong logic agent - đây là một trong ba điểm giữ
    # sẵn để mở rộng ngôn ngữ/loại nội dung mà không đập đi làm lại
    # (docs/architecture.md mục 5.6). Thiếu chúng thì không tra config được.
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
