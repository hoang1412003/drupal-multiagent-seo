from typing import Literal, Optional, TypedDict


class ContentReviewState(TypedDict):
    node_id: str
    title: str
    body: str
    raw_content: dict

    content_quality_result: Optional[dict]
    seo_result: Optional[dict]
    brand_result: Optional[dict]
    compliance_result: Optional[dict]

    final_score: Optional[float]
    decision: Optional[Literal["publish", "needs_revision", "rejected"]]
    report: Optional[dict]
