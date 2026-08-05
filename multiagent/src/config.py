"""Nạp trọng số và ngưỡng từ config/scoring.yaml theo (content_type, langcode).

Đặc tả: docs/config-spec.md

Vì sao tồn tại: cùng một con số từng nằm ở 4 nơi và ĐÃ trôi lệch một lần
(mã B3 ghi 150-160 trong guideline trong khi rubric ghi 140-170). File này
làm con số chỉ tồn tại ở một chỗ.

Không dùng cơ chế kế thừa/gộp từng phần từ `default`: mỗi khoá trong YAML là
một khối ĐẦY ĐỦ, đọc file là biết chắc hệ thống đang chạy bằng số nào
(config-spec.md mục 9). Ở đây `default` chỉ dùng khi không có khoá nào khớp.
"""
import logging
import os

import yaml

_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "scoring.yaml"
)

# Cache khoá theo ĐƯỜNG DẪN. Bản cũ dùng một biến duy nhất và bỏ qua tham số
# `path`, nên lần gọi thứ hai với file khác vẫn trả nội dung file đã nạp trước
# - tham số hứa một đằng, hàm làm một nẻo.
_cache: dict = {}

# Cảnh báo đã in rồi thì không in lại - pipeline gọi load() nhiều lần trong
# một lần chấm, in mỗi lần sẽ thành nhiễu và người ta bắt đầu phớt lờ.
_da_canh_bao: set = set()


def _nap_file(path: str) -> dict:
    if path not in _cache:
        with open(path, encoding="utf-8") as f:
            _cache[path] = yaml.safe_load(f)
    return _cache[path]


def load(content_type: str = "cam_nang", langcode: str = "vi",
         path: str = _CONFIG_PATH) -> dict:
    """Trả khối config cho (content_type, langcode).

    Không có khoá khớp -> dùng khối `default`. Trả bản SAO để người gọi sửa
    tại chỗ không làm hỏng cache dùng chung.
    """
    import copy

    data = _nap_file(path)
    khoa = f"{content_type}:{langcode}"
    khoi = data.get(khoa) or data.get("default")
    if khoi is None:
        raise ValueError(f"scoring.yaml thiếu cả khoá '{khoa}' lẫn 'default'")
    return copy.deepcopy(khoi)


def kiem_tra_meta(khoi: dict, model_dang_dung: str) -> list:
    """Trả danh sách cảnh báo về xuất xứ của bộ ngưỡng đang dùng.

    Hai cảnh báo này là lý do khối `meta` tồn tại (config-spec.md mục 5a) -
    không có chúng thì quy tắc versioning chỉ là câu văn trong tài liệu, có
    chúng thì hệ thống tự kiểm tra được lúc chạy.
    """
    meta = khoi.get("meta") or {}
    canh_bao = []

    if not meta.get("calibrated"):
        canh_bao.append(
            "Đang dùng ngưỡng minh hoạ, chưa calibrate từ gold set. "
            "Không trình bày kết quả chạy bằng bộ ngưỡng này như thể đã calibrate."
        )
    elif meta.get("model") and meta["model"] != model_dang_dung:
        # Bẫy im lặng: ANTHROPIC_MODEL đọc từ biến môi trường, ai đó đổi .env
        # là toàn bộ ngưỡng đã calibrate mất hiệu lực mà không có dấu hiệu gì.
        canh_bao.append(
            f"Ngưỡng calibrate cho model '{meta['model']}', đang chạy "
            f"'{model_dang_dung}'. Ngưỡng có thể không còn đúng - "
            f"docs/rubrics.md mục 10 yêu cầu calibrate lại khi đổi model."
        )

    return canh_bao


def canh_bao_mot_lan(khoi: dict, model_dang_dung: str) -> None:
    """Ghi log các cảnh báo của kiem_tra_meta(), mỗi nội dung chỉ một lần."""
    for w in kiem_tra_meta(khoi, model_dang_dung):
        if w not in _da_canh_bao:
            _da_canh_bao.add(w)
            logging.warning("[config] %s", w)
