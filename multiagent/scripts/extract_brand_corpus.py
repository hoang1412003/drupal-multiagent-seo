"""Bóc tách corpus BRAND thành file .txt để thống kê brand guideline.

Dùng LẠI nguyên các hàm bóc tách của scripts/extract_gold_sample.py - cùng
nguồn vinfastauto.com, cùng cấu trúc HTML, nên không viết lại logic. Khác 2
điểm: ghi sang docs/brand/corpus/ (tập BRAND phải rời hẳn gold set - xem
docs/goldset/sources.md mục 1.6) và đối chiếu canonical với corpus_index.csv
thay vì labels.csv.

Cách chạy (từ multiagent/):
    .venv\\Scripts\\python.exe scripts\\extract_brand_corpus.py ..\\docs\\brand\\raw_html\\*.html
"""
import csv
import glob
import os
import sys

from bs4 import BeautifulSoup

from extract_gold_sample import ExtractError, clean_body, extract_fields, render_txt

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "brand", "corpus")
INDEX_CSV = os.path.join(REPO_ROOT, "docs", "brand", "corpus_index.csv")


def load_index() -> dict[str, str]:
    """sample_id -> source_url, để phát hiện lưu nhầm bài."""
    if not os.path.isfile(INDEX_CSV):
        return {}
    with open(INDEX_CSV, encoding="utf-8-sig") as f:
        return {row["sample_id"]: row["source_url"] for row in csv.DictReader(f)}


def process(path: str, index: dict) -> bool:
    """Bóc tách 1 file, ghi .txt. Trả True nếu thành công.

    Bắt mọi exception để một file hỏng không làm dừng cả lô 10 file.
    """
    sample_id = os.path.splitext(os.path.basename(path))[0]
    try:
        with open(path, encoding="utf-8") as f:
            soup = BeautifulSoup(f.read(), "html.parser")

        fields = extract_fields(soup)
        body_html, removed, kept, unwrapped, alts = clean_body(soup)

        warnings = []
        expected = index.get(sample_id)
        if expected is None:
            warnings.append(f"{sample_id} khong co trong corpus_index.csv")
        elif fields["url_alias"] and fields["url_alias"] != expected:
            warnings.append(
                f"canonical khac corpus_index.csv: {fields['url_alias']} != {expected}"
            )

        os.makedirs(CORPUS_DIR, exist_ok=True)
        out = os.path.join(CORPUS_DIR, f"{sample_id}.txt")
        with open(out, "w", encoding="utf-8") as f:
            f.write(render_txt(fields, body_html))
    except ExtractError as error:
        print(f"{sample_id}.html\n  [LOI] {error} - KHONG ghi file")
        return False
    except Exception as error:
        print(f"{sample_id}.html\n  [LOI] {type(error).__name__}: {error} - KHONG ghi file")
        return False

    print(f"{sample_id}.txt")
    for item in removed:
        print(f"  [xoa] {item}")
    print(f"  [giu] {kept['p']} doan, {kept['h2']} h2, {kept['h3']} h3")
    for warning in warnings:
        print(f"  [CANH BAO] {warning}")
    return True


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    paths = []
    for arg in sys.argv[1:]:
        paths.extend(sorted(glob.glob(arg)) or [arg])

    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print(f"Khong tim thay file: {', '.join(missing)}")
        sys.exit(1)

    index = load_index()
    written = sum(process(path, index) for path in paths)
    print(f"\nDa ghi {written}/{len(paths)} file vao {CORPUS_DIR}")
    sys.exit(0 if written == len(paths) else 1)
