"""Thống kê corpus BRAND -> sinh brand guideline (2 file đầu ra).

Chạy OFFLINE, KHÔNG gọi LLM, KHÔNG nằm trong pipeline chấm bài.

Nguyên tắc (spec mục 4.1): người nêu danh sách ỨNG VIÊN biến thể
(variant_candidates.json), DỮ LIỆU quyết định biến thể nào là chuẩn.

Một quy ước chỉ thành quy tắc khi lệch khỏi 50-50 ở mức có ý nghĩa thống kê
(kiểm định nhị thức, p < 0.05). Với 10 bài, ngưỡng tự rơi ra là >=9/10 - đây
là lý do không có con số ngưỡng nào do người đặt ra.

Hai file đầu ra sinh trong CÙNG một lần chạy nên không trôi lệch nhau:
  docs/brand/brand_guideline.md          - người và mentor đọc, kiểm chứng
  multiagent/src/agents/brand_rules.json - code so khớp lúc chấm

Cách chạy (từ multiagent/):
    .venv\\Scripts\\python.exe scripts\\build_brand_guideline.py
"""
import glob
import json
import os
import sys
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src"))

from brand_analysis import (
    SIGNIFICANCE,
    binom_two_sided_p,
    classify_title_case,
    count_model_name_usage,
    count_variants,
)
from text_utils import strip_html

from label_helper import parse_sample

_HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.normpath(os.path.join(_HERE, "..", ".."))
CORPUS_DIR = os.path.join(REPO_ROOT, "docs", "brand", "corpus")
CANDIDATES_PATH = os.path.join(REPO_ROOT, "docs", "brand", "variant_candidates.json")
GUIDELINE_PATH = os.path.join(REPO_ROOT, "docs", "brand", "brand_guideline.md")
RULES_PATH = os.path.join(REPO_ROOT, "multiagent", "src", "agents", "brand_rules.json")


def load_corpus(corpus_dir: str = CORPUS_DIR) -> list[dict]:
    """Đọc corpus -> list {sample_id, title, text}. text đã bóc hết thẻ HTML."""
    docs = []
    for path in sorted(glob.glob(os.path.join(corpus_dir, "*.txt"))):
        fields = parse_sample(path)
        phan_chu = " ".join(
            strip_html(fields.get(k, "")) for k in ("title", "summary", "body")
        )
        docs.append({
            "sample_id": os.path.splitext(os.path.basename(path))[0],
            "title": fields.get("title", ""),
            "text": phan_chu,
        })
    return docs


def _chon_da_so(dem_theo_bai: dict[str, int], n_docs: int):
    """Trả (ứng viên nhiều bài nhất, số bài, p_value)."""
    ung_vien = max(dem_theo_bai, key=lambda k: dem_theo_bai[k])
    so_bai = dem_theo_bai[ung_vien]
    return ung_vien, so_bai, binom_two_sided_p(so_bai, n_docs)


def _phieu_theo_bai(docs: list[dict], nhom: list[str]):
    """Mỗi bài CÓ NHẮC tới nhóm bỏ một phiếu cho biến thể nó dùng nhiều nhất.

    Trả (phiếu theo biến thể, số lần theo biến thể, số bài có nhắc tới nhóm).

    Bài không nhắc tới nhóm thì KHÔNG bỏ phiếu - im lặng không phải phản đối.
    Tính chúng vào mẫu số là sai về phương pháp và đã cho kết quả sai thật:
    "xe máy điện" thắng tuyệt đối trong 4/4 bài có bàn về xe máy (106 lần, 0
    lần cho biến thể khác) nhưng bị kết luận "chưa đủ căn cứ" chỉ vì 6 bài
    còn lại viết về chủ đề khác.

    Bỏ phiếu theo biến thể DÙNG NHIỀU NHẤT trong bài, không theo "có xuất
    hiện hay không": một bài dùng cả hai biến thể vẫn phải quy về một lựa
    chọn, nếu không tổng phiếu vượt quá số bài.
    """
    phieu = {v: 0 for v in nhom}
    theo_lan = {v: 0 for v in nhom}
    so_bai_nhac = 0
    for doc in docs:
        dem = count_variants(doc["text"], nhom)
        for v, so in dem.items():
            theo_lan[v] += so
        if sum(dem.values()) == 0:
            continue
        so_bai_nhac += 1
        phieu[max(dem, key=lambda k: dem[k])] += 1
    return phieu, theo_lan, so_bai_nhac


def analyze_corpus(docs: list[dict], candidates: dict) -> dict:
    """Thống kê corpus -> cấu trúc brand_rules.json.

    QUYẾT ĐỊNH dựa trên SỐ BÀI (đơn vị độc lập), không dựa trên số lần xuất
    hiện: các lần xuất hiện trong cùng một bài không độc lập với nhau, áp
    kiểm định lên chúng sẽ thổi phồng mức ý nghĩa (spec mục 4.5). Số lần vẫn
    được đếm và báo cáo, nhưng chỉ là số mô tả.
    """
    n_docs = len(docs)
    terms, excluded, undecided = [], [], []

    for nhom in candidates["term_pairs"]:
        phieu, theo_lan, so_bai_nhac = _phieu_theo_bai(docs, nhom)
        chuan, so_phieu, p = _chon_da_so(phieu, so_bai_nhac)
        tong_lan = sum(theo_lan.values())
        if p < SIGNIFICANCE and so_phieu * 2 > so_bai_nhac:
            terms.append({
                "standard": chuan,
                "non_standard": [v for v in nhom if v != chuan and theo_lan[v] > 0],
                # [số bài bầu cho chuẩn, số bài CÓ NHẮC tới nhóm]. Mẫu số là
                # số bài có nhắc, không phải toàn corpus - xem _phieu_theo_bai.
                "docs": [so_phieu, so_bai_nhac],
                "occurrences": [theo_lan[chuan], tong_lan],
                "p_value": round(p, 5),
            })
            # Biến thể 0 lần trong TOÀN corpus -> BV7 (nhị phân), khác hẳn
            # biến thể có xuất hiện nhưng thiểu số -> BV2 (chấm theo số chỗ).
            excluded.extend(v for v in nhom if v != chuan and theo_lan[v] == 0)
        else:
            undecided.append({
                "kind": "term",
                "candidates": nhom,
                "docs": [so_phieu, so_bai_nhac],
                "p_value": round(p, 5),
            })

    # --- Xưng hô (cùng cách tính mẫu số: bài không xưng hô thì không bỏ phiếu) ---
    xh_phieu, xh_theo_lan, xh_so_bai = _phieu_theo_bai(docs, candidates["address_forms"])
    xh_chuan, xh_bai, xh_p = _chon_da_so(xh_phieu, xh_so_bai)
    if xh_p < SIGNIFICANCE and xh_bai * 2 > xh_so_bai:
        address_form = {
            "standard": xh_chuan,
            "docs": [xh_bai, xh_so_bai],
            "occurrences": [xh_theo_lan[xh_chuan], sum(xh_theo_lan.values())],
            "p_value": round(xh_p, 5),
        }
    else:
        address_form = None
        undecided.append({
            "kind": "address_form",
            "candidates": candidates["address_forms"],
            "docs": [xh_bai, xh_so_bai],
            "p_value": round(xh_p, 5),
        })

    # --- Kiểu viết hoa tiêu đề -------------------------------------------
    kieu_theo_bai = {}
    for doc in docs:
        kieu = classify_title_case(doc["title"])
        kieu_theo_bai[kieu] = kieu_theo_bai.get(kieu, 0) + 1
    tc_chuan, tc_bai, tc_p = _chon_da_so(kieu_theo_bai, n_docs)
    if tc_p < SIGNIFICANCE and tc_bai * 2 > n_docs:
        title_case = {"standard": tc_chuan, "docs": [tc_bai, n_docs], "p_value": round(tc_p, 5)}
    else:
        title_case = None
        undecided.append({
            "kind": "title_case",
            "candidates": sorted(kieu_theo_bai),
            "docs": [tc_bai, n_docs],
            "p_value": round(tc_p, 5),
        })

    # --- Tên model: thống kê để báo cáo, danh sách chuẩn lấy từ ứng viên ---
    model_dung, model_sai = 0, []
    for doc in docs:
        dung, sai = count_model_name_usage(doc["text"], candidates["model_names"])
        model_dung += dung
        model_sai.extend(sai)

    return {
        "version": 1,
        "generated_at": date.today().isoformat(),
        "significance_level": SIGNIFICANCE,
        "corpus": {"n_docs": n_docs, "sample_ids": [d["sample_id"] for d in docs]},
        "model_names": candidates["model_names"],
        "model_name_stats": {"correct": model_dung, "wrong_examples": sorted(set(model_sai))},
        "terms": terms,
        "excluded_terms": excluded,
        "address_form": address_form,
        "title_case": title_case,
        "undecided": undecided,
    }


def render_guideline(rules: dict) -> str:
    """Bản cho người đọc. Mọi quy tắc đều kèm số liệu chứng minh."""
    n = rules["corpus"]["n_docs"]
    dong = [
        "# Brand guideline (tự trích xuất từ corpus)",
        "",
        f"**Sinh tự động** bởi `multiagent/scripts/build_brand_guideline.py` ngày {rules['generated_at']}.",
        "**Không sửa tay** — sửa `docs/brand/variant_candidates.json` rồi chạy lại script.",
        "",
        f"**Corpus:** {n} bài thuộc tập `BRAND` (`docs/goldset/sources.md` mục 1.6), "
        "rời hẳn gold set để tránh rò rỉ dữ liệu.",
        "",
        f"**Quy tắc chỉ được sinh khi** tỉ lệ lệch khỏi 50-50 ở mức có ý nghĩa thống kê "
        f"(kiểm định nhị thức hai phía, p < {rules['significance_level']}).",
        "",
        "**Cách đếm:** mỗi bài **có nhắc tới** nhóm khái niệm bỏ một phiếu cho biến thể "
        "nó dùng nhiều nhất. Bài không nhắc tới nhóm thì không bỏ phiếu — im lặng không "
        "phải phản đối. Vì vậy mẫu số là *số bài có nhắc*, không phải toàn corpus.",
        "",
        "Hệ quả cần biết khi đọc bảng: nhóm chỉ được bàn trong ít bài thì rất khó đạt "
        "mức ý nghĩa — 4/4 bài đồng thuận tuyệt đối vẫn cho p = 0,125. Đó là giới hạn "
        "thật của cỡ mẫu, không phải lỗi; cách xử lý là thu thêm corpus, không phải hạ "
        "mức ý nghĩa.",
        "",
        "## Thuật ngữ chuẩn",
        "",
        "| Chuẩn | Không dùng | Bài bầu / bài có nhắc | Số lần | p-value |",
        "|---|---|---|---|---|",
    ]
    for t in rules["terms"]:
        dong.append(
            f"| {t['standard']} | {', '.join(t['non_standard']) or '—'} | "
            f"{t['docs'][0]}/{t['docs'][1]} | {t['occurrences'][0]}/{t['occurrences'][1]} | "
            f"{t['p_value']} |"
        )
    if not rules["terms"]:
        dong.append("| _(chưa quy tắc nào đủ căn cứ)_ | | | | |")

    dong += ["", "## Cách viết tên model", ""]
    dong.append(f"Dạng chuẩn: {', '.join(f'`{m}`' for m in rules['model_names'])}")
    stats = rules["model_name_stats"]
    dong.append("")
    dong.append(f"Trong corpus: {stats['correct']} chỗ viết đúng dạng chuẩn.")
    if stats["wrong_examples"]:
        dong.append(f"Chỗ viết khác chuẩn quan sát được: {', '.join(stats['wrong_examples'])}.")

    dong += ["", "## Xưng hô", ""]
    if rules["address_form"]:
        a = rules["address_form"]
        dong.append(
            f"Chuẩn: **{a['standard']}** — {a['docs'][0]}/{a['docs'][1]} bài, "
            f"{a['occurrences'][0]}/{a['occurrences'][1]} lần, p = {a['p_value']}."
        )
    else:
        dong.append("_Chưa đủ căn cứ để chốt xưng hô chuẩn._")

    dong += ["", "## Quy ước viết hoa tiêu đề", ""]
    if rules["title_case"]:
        tc = rules["title_case"]
        dong.append(
            f"Chuẩn: **{tc['standard']}** — {tc['docs'][0]}/{tc['docs'][1]} bài, p = {tc['p_value']}."
        )
    else:
        dong.append("_Chưa đủ căn cứ để chốt quy ước viết hoa._")

    dong += ["", "## Từ bị loại (corpus chưa bao giờ dùng)", ""]
    if rules["excluded_terms"]:
        for v in rules["excluded_terms"]:
            dong.append(f"- `{v}` — 0 lần trong toàn corpus")
    else:
        dong.append("_(không có)_")

    dong += [
        "",
        "## Chưa đủ căn cứ — KHÔNG sinh quy tắc",
        "",
        "Tiêu chí tương ứng sẽ trả `NA` lúc chấm (bị loại khỏi cả tử số lẫn mẫu số), "
        "**không** phải cho 0 điểm. Đây cũng là tín hiệu nên thu thêm corpus `BRAND` "
        "(spec mục 4.4).",
        "",
        "| Loại | Ứng viên | Bài bầu / bài có nhắc | p-value |",
        "|---|---|---|---|",
    ]
    for u in rules["undecided"]:
        dong.append(
            f"| {u['kind']} | {', '.join(u['candidates'])} | "
            f"{u['docs'][0]}/{u['docs'][1]} | {u['p_value']} |"
        )
    if not rules["undecided"]:
        dong.append("| _(không có — mọi quy ước đều đủ căn cứ)_ | | | |")
    return "\n".join(dong) + "\n"


if __name__ == "__main__":
    with open(CANDIDATES_PATH, encoding="utf-8") as f:
        candidates = json.load(f)
    docs = load_corpus()
    if not docs:
        print(f"Khong tim thay file nao trong {CORPUS_DIR} - chay extract_brand_corpus.py truoc")
        sys.exit(1)

    rules = analyze_corpus(docs, candidates)

    with open(RULES_PATH, "w", encoding="utf-8") as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)
    with open(GUIDELINE_PATH, "w", encoding="utf-8") as f:
        f.write(render_guideline(rules))

    print(f"Corpus: {rules['corpus']['n_docs']} bai")
    print(f"Quy tac thuat ngu: {len(rules['terms'])}")
    print(f"Tu bi loai (BV7): {len(rules['excluded_terms'])}")
    print(f"Chua du can cu: {len(rules['undecided'])}")
    for u in rules["undecided"]:
        print(f"  - {u['kind']}: {u['docs'][0]}/{u['docs'][1]} bai, p={u['p_value']}")
    print(f"\nDa ghi:\n  {GUIDELINE_PATH}\n  {RULES_PATH}")
