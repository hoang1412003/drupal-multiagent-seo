"""Regression tests for E1 resumable-result prompt-version guard."""
import json
import os
import tempfile

from eval_calibration import prompt_version
from eval_stability import ghi_ket_qua, nap_ket_qua


def check(name: str, got, want) -> None:
    if got != want:
        raise AssertionError(f"{name}: got {got!r}, want {want!r}")


def path_chua_ton_tai() -> str:
    path = os.path.join(tempfile.gettempdir(), "e1-ket-qua-khong-ton-tai.json")
    if os.path.exists(path):
        os.unlink(path)
    return path


def write_json(data: dict) -> str:
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return path


def assert_system_exit_contains(action, expected: str) -> None:
    try:
        action()
    except SystemExit as error:
        if expected not in str(error):
            raise AssertionError(f"expected {expected!r} in {str(error)!r}")
        return
    raise AssertionError("expected SystemExit")


def test_file_moi_tra_dict_rong() -> None:
    check("file chua co", nap_ket_qua(path_chua_ton_tai()), {})


def test_file_cu_thieu_meta_bi_tu_choi() -> None:
    path = write_json({"G-001": []})
    assert_system_exit_contains(lambda: nap_ket_qua(path), "--ket-qua")


def test_file_sai_prompt_bi_tu_choi() -> None:
    path = write_json({"_meta": {"prompt_version": "sai"}, "G-001": []})
    assert_system_exit_contains(lambda: nap_ket_qua(path), "Tron hai ban")


def test_file_dung_prompt_duoc_resume() -> None:
    path = write_json({"_meta": {"prompt_version": prompt_version()}, "G-001": []})
    check("bo metadata khi tra du lieu", nap_ket_qua(path), {"G-001": []})


def test_ghi_ket_qua_luu_prompt_version() -> None:
    path = path_chua_ton_tai()
    ghi_ket_qua({"G-001": []}, path)
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    check("metadata prompt version", payload["_meta"], {"prompt_version": prompt_version()})


if __name__ == "__main__":
    for test in (
        test_file_moi_tra_dict_rong,
        test_file_cu_thieu_meta_bi_tu_choi,
        test_file_sai_prompt_bi_tu_choi,
        test_file_dung_prompt_duoc_resume,
        test_ghi_ket_qua_luu_prompt_version,
    ):
        test()
    print("PASS: E1 resume prompt-version guard")
