"""Kiem tra moi ham def test_* trong scripts/test_*.py deu duoc goi trong
khoi `if __name__ == "__main__":` cua chinh file do.

Vi sao script nay ton tai: repo khong dung pytest/unittest de tu dong gom
test - moi file test_*.py tu liet ke TAY danh sach ham can goi trong khoi
__main__. Khuon mau do lam viec quen them ham moi vao danh sach tro thanh
loi im lang: ham test van chay DUNG neu goi rieng, nhung khi chay ca file
(cach duy nhat CI/nguoi kiem thuc te dung) no khong bao gio duoc goi, nen
bo test bao xanh gia trong khi khong he kiem tra dieu no tuong da kiem. Da
xay ra that 3 lan truoc khi co script nay:
  - test_drupal_client_worker.py: thieu test_loai_node_khong_o_needs_review
    va test_url_khong_dung_filter_moderation_state (hai test khoa dung
    logic loc needs_review va tranh filter[moderation_state]).
  - test_brand_analysis.py: thieu test_strip_html_giai_ma_thuc_the.

Chay: .venv\\Scripts\\python.exe scripts\\test_moi_test_deu_chay.py
"""
import ast
import glob
import os
import sys


def _cac_ham_test(cay: ast.Module) -> list:
    """Ten cac ham def test_* o cap module (khong dem ham long trong class/ham khac)."""
    return [
        node.name for node in cay.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test")
    ]


def _khoi_main(cay: ast.Module):
    """Tim khoi `if __name__ == "__main__":` o cap module. Khong co -> None."""
    for node in cay.body:
        if (isinstance(node, ast.If)
                and isinstance(node.test, ast.Compare)
                and isinstance(node.test.left, ast.Name)
                and node.test.left.id == "__name__"):
            return node
    return None


def _ten_duoc_dung_trong(node) -> set:
    """Moi ten (ast.Name) xuat hien trong node, ke ca long trong vong for/
    tuple/list - vi co file goi truc tiep `fn()`, co file lai duyet
    `for fn in (a, b, c):`."""
    return {n.id for n in ast.walk(node) if isinstance(n, ast.Name)}


def _test_chet_trong_file(duong_dan: str) -> list:
    with open(duong_dan, "r", encoding="utf-8") as f:
        nguon = f.read()
    cay = ast.parse(nguon, filename=duong_dan)
    ham_test = _cac_ham_test(cay)
    if not ham_test:
        return []
    main = _khoi_main(cay)
    if main is None:
        # Co ham test_* cap module nhung khong co khoi __main__ -> chay file
        # nay khong goi ham nao ca, coi nhu tat ca deu chet.
        return ham_test
    da_dung = _ten_duoc_dung_trong(main)
    return [ten for ten in ham_test if ten not in da_dung]


def main() -> int:
    thu_muc = os.path.dirname(__file__)
    co_test_chet = False
    for duong_dan in sorted(glob.glob(os.path.join(thu_muc, "test_*.py"))):
        ten_file = os.path.basename(duong_dan)
        chet = _test_chet_trong_file(duong_dan)
        if chet:
            co_test_chet = True
            print(f"[FAIL] {ten_file}: khong chay {', '.join(chet)}")
        else:
            print(f"[PASS] {ten_file}")
    return 1 if co_test_chet else 0


if __name__ == "__main__":
    sys.exit(main())
