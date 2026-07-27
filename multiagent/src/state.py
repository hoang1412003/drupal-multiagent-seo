from typing import Literal, Optional, TypedDict


class ContentReviewState(TypedDict):
    node_id: str
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
