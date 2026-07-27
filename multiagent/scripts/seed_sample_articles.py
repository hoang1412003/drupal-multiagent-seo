"""Tạo bộ bài cẩm nang mẫu (test chức năng) trên Drupal qua JSON:API.

Bộ mẫu này bám theo đúng phạm vi đề tài: bài CẨM NANG / hướng dẫn xe điện
(không phải tin khuyến mãi), mỗi bài cố ý gài 1 kịch bản lỗi để kiểm tra
từng agent bắt đúng loại lỗi tương ứng (architecture.md mục 8.1).

Tạo ở trạng thái chưa xuất bản (status=false) để mô phỏng bản nháp cần duyệt.
Sau khi tạo, ghi danh sách UUID + nhãn + kỳ vọng vào scripts/sample_articles.json
để run_all_samples.py đọc lại (không hard-code UUID).

Cách chạy (Drupal đang chạy, đã điền DRUPAL_USER/DRUPAL_PASSWORD trong .env,
và đã tạo field_meta_description trên content type Article):
    .venv\\Scripts\\python.exe scripts\\seed_sample_articles.py
"""
import json
import os
import sys

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from drupal_client import AUTH, BASE_URL, REQUEST_TIMEOUT_SECONDS, _request_with_retry

POST_HEADERS = {
    "Content-Type": "application/vnd.api+json",
    "Accept": "application/vnd.api+json",
}

MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "sample_articles.json")


# Mỗi bài: label (mô tả kịch bản), expected (quyết định kỳ vọng), và các field.
# meta/slug để trống ("" / None) là cố ý cho kịch bản thiếu SEO.
ARTICLES = [
    {
        "label": "Huong dan sac pin (bai tot)",
        "expected": "publish",
        "title": "Hướng dẫn sạc pin ô tô điện VinFast đúng cách và an toàn",
        "body": (
            "<h2>Chuẩn bị trước khi sạc</h2>"
            "<p>Trước khi sạc pin ô tô điện VinFast, người dùng nên kiểm tra tình "
            "trạng pin và nhiệt độ xe. Sau khi vận hành, nên đợi khoảng 30 phút để "
            "pin ổn định nhiệt độ trước khi cắm sạc.</p>"
            "<h2>Các bước sạc pin an toàn</h2>"
            "<p>Cắm cổng sạc đúng chuẩn, đảm bảo kết nối chắc chắn giữa trụ sạc và "
            "cổng sạc trên xe. Với sạc thường tại nhà, thời gian sạc đầy dao động "
            "tùy dung lượng pin của từng dòng xe. Người dùng nên duy trì mức pin từ "
            "20% đến 80% để kéo dài tuổi thọ pin.</p>"
            "<h2>Lưu ý khi dùng trạm sạc công cộng</h2>"
            "<p>Tại trạm sạc công cộng, khách hàng có thể tra cứu vị trí trạm sạc "
            "gần nhất qua ứng dụng VinFast. Nên lên kế hoạch sạc cho các chuyến đi "
            "dài để tránh gián đoạn hành trình.</p>"
        ),
        "meta_description": (
            "Hướng dẫn sạc pin ô tô điện VinFast đúng cách: chuẩn bị trước khi sạc, "
            "các bước an toàn và lưu ý khi dùng trạm sạc công cộng để kéo dài tuổi thọ pin."
        ),
        "slug": "/huong-dan-sac-pin-o-to-dien-vinfast-dung-cach",
    },
    {
        "label": "Kinh nghiem lai duong dai (loi chinh ta co y)",
        "expected": "needs_revision",
        "title": "Kinh nghiệm lái ô tô điện đường dài cho ngừoi mới",
        "body": (
            "<h2>Chuẩn bị trước chuyến đi</h2>"
            "<p>Khi lái ô tô điện đường dài, ngừoi lái cần kiểm tra pin và lên kế "
            "hoạch sạc. Nên sạc đầy pin trứoc khi khởi hành và xác định các trạm "
            "sạc trên lộ trình.</p>"
            "<h2>Trong quá trình di chuyển</h2>"
            "<p>Giữ vận tốc ổn định khoảng 60km/h giúp tiết kiệm pin hơn. Khách "
            "hàng nên thừong xuyên theo dõi mức pin và quãng đừong còn lại để chủ "
            "động sạc kịp thời, tránh trừong hợp hết pin giữa đừong.</p>"
        ),
        "meta_description": (
            "Kinh nghiệm lái ô tô điện đường dài cho người mới: chuẩn bị pin, lên "
            "kế hoạch sạc và các lưu ý khi di chuyển."
        ),
        "slug": "/kinh-nghiem-lai-o-to-dien-duong-dai",
    },
    {
        "label": "Bao duong xe (thieu SEO co y)",
        "expected": "needs_revision",
        "title": "Bảo dưỡng xe",
        "body": "<p>Xe điện cần bảo dưỡng định kỳ. Liên hệ để biết thêm.</p>",
        "meta_description": "",
        "slug": None,
    },
    {
        "label": "So sanh chi phi (sai thuat ngu brand co y)",
        # needs_revision: bai co SEO yeu + claim chi phi thieu can cu -> rot duoi
        # nguong. Brand Voice con stub nen loi brand (VF8/VF 8) chua bi bat dung
        # cach (Content Quality bat duoc su khong nhat quan nhung goi y sai chuan
        # "VF8" thay vi "VF 8") - minh hoa vi sao can Brand Voice co guideline that.
        "expected": "needs_revision",
        "title": "So sánh chi phí sử dụng ô tô điện và ô tô xăng",
        "body": (
            "<h2>Chi phí nhiên liệu</h2>"
            "<p>Ô tô điện có chi phí vận hành thấp hơn xe xăng. Ví dụ dòng VF8 tiêu "
            "thụ điện năng tiết kiệm, trong khi vf 8 phiên bản Plus có dung lượng "
            "pin lớn hơn. Nhiều khách hàng chọn VF 8 vì chi phí sạc rẻ.</p>"
            "<h2>Chi phí bảo dưỡng</h2>"
            "<p>Xe hơi điện có ít bộ phận chuyển động hơn nên chi phí bảo dưỡng "
            "thấp. So với xe xăng, xe điện tiết kiệm đáng kể chi phí định kỳ.</p>"
        ),
        "meta_description": (
            "So sánh chi phí sử dụng ô tô điện và ô tô xăng: chi phí nhiên liệu và "
            "bảo dưỡng để giúp khách hàng lựa chọn phù hợp."
        ),
        "slug": "/so-sanh-chi-phi-o-to-dien-va-o-to-xang",
    },
    {
        "label": "Tam hoat dong (vi pham compliance co y)",
        "expected": "rejected",
        "title": "Tầm hoạt động các dòng ô tô điện VinFast tốt nhất thị trường",
        "body": (
            "<h2>Tầm hoạt động ấn tượng</h2>"
            "<p>Các dòng ô tô điện VinFast có tầm hoạt động lên đến 450km cho mỗi "
            "lần sạc đầy, vượt xa mọi đối thủ trên thị trường. VF9 là mẫu xe đi xa "
            "nhất, không đối thủ nào sánh bằng.</p>"
            "<h2>Vượt trội so với đối thủ</h2>"
            "<p>So với Tesla, ô tô điện VinFast có giá tốt hơn và tầm hoạt động "
            "vượt trội hơn hẳn. Đây là lựa chọn số 1 cho khách hàng Việt Nam.</p>"
        ),
        "meta_description": (
            "Tầm hoạt động các dòng ô tô điện VinFast lên đến 450km mỗi lần sạc."
        ),
        "slug": "/tam-hoat-dong-o-to-dien-vinfast",
    },
    {
        "label": "Cac loai pin (bai tot)",
        "expected": "publish",
        "title": "Các loại pin ô tô điện và cách chọn phù hợp",
        "body": (
            "<h2>Pin Lithium-ion</h2>"
            "<p>Pin Lithium-ion được sử dụng phổ biến trên ô tô điện nhờ mật độ "
            "năng lượng cao và thời gian sạc nhanh. Loại pin này phù hợp với người "
            "dùng cần quãng đường di chuyển dài.</p>"
            "<h2>Pin LFP</h2>"
            "<p>Pin LFP có tuổi thọ cao và độ an toàn tốt, chi phí hợp lý. Đây là "
            "lựa chọn phù hợp cho người dùng đô thị di chuyển quãng đường vừa phải.</p>"
            "<h2>Cách chọn pin phù hợp</h2>"
            "<p>Khách hàng nên cân nhắc nhu cầu di chuyển và ngân sách để chọn loại "
            "pin phù hợp. Với nhu cầu đô thị, pin LFP là lựa chọn kinh tế; với di "
            "chuyển đường dài, pin Lithium-ion có ưu thế.</p>"
        ),
        "meta_description": (
            "Các loại pin ô tô điện phổ biến (Lithium-ion, LFP) và cách chọn pin "
            "phù hợp với nhu cầu di chuyển và ngân sách."
        ),
        "slug": "/cac-loai-pin-o-to-dien-va-cach-chon",
    },
]


def create_article(article: dict) -> str:
    """POST 1 bài lên Drupal, trả về UUID."""
    attributes = {
        "title": article["title"],
        "body": {"value": article["body"], "format": "basic_html"},
        "field_meta_description": article["meta_description"],
        "status": False,  # bản nháp chưa xuất bản
    }
    if article["slug"]:
        attributes["path"] = {"alias": article["slug"]}

    payload = {"data": {"type": "node--article", "attributes": attributes}}
    response = _request_with_retry(
        requests.post,
        f"{BASE_URL}/jsonapi/node/article",
        headers=POST_HEADERS,
        json=payload,
        auth=AUTH,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    return response.json()["data"]["id"]


if __name__ == "__main__":
    manifest = []
    for article in ARTICLES:
        uuid = create_article(article)
        manifest.append(
            {"uuid": uuid, "label": article["label"], "expected": article["expected"]}
        )
        print(f"[OK] {article['label']} -> {uuid} (ky vong: {article['expected']})")

    with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"\nDa ghi {len(manifest)} bai vao {MANIFEST_PATH}")
