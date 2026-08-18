# Integrity checkpoint — corrected publish và criterion coverage v1

## 1. Phạm vi checkpoint

- Ngày khóa: **17/08/2026**.
- Branch/worktree: `ai/v14-relabel` / `.worktrees/ai-v14-relabel`.
- Commit base Task 10: `8e5ca609ace115fe745055444490976c9cbe7865`.
- Guideline: `v1.4`.
- Không sửa `docs/goldset/labels.csv`, `docs/goldset/raw/`, `scoring.yaml` hoặc evidence thí nghiệm v1.
- Mọi kiểm tra trong tài liệu này chạy offline với `HF_HUB_OFFLINE=1` và `VF_ALLOW_PAID_EVAL=0`; không gọi model/API trả phí.

Checkpoint này khóa integrity của dữ liệu; nó chưa chạy phép evaluation release v2 và chưa tạo quyết định ngưỡng.

## 2. Bốn lớp dữ liệu tách vật lý

| Lớp | IDs | Số mẫu | Nhãn kỳ vọng | Vai trò |
|---|---|---:|---|---|
| Historical gold | 20 `G` + 13 `P` | 33 | 23 `needs_revision`, 10 `rejected` theo candidate AI v1.4 | Giữ nguyên E5 v1; không có publish |
| Functional clean | `C-001`…`C-010` | 10 | 10 `publish` | Bài đã sửa từ HTML nguồn; review AI v1.4 mới |
| Gold corrected | `GC-001`…`GC-020` | 20 | 20 `publish` | Bản sửa từ đúng parent `G-001`…`G-020` |
| Criterion coverage | 11 canonical `CV` | 11 | 7 `rejected`, 4 `needs_revision` | Perturbation một lỗi; báo cáo riêng |

Tập chính dự kiến có 63 samples theo phép cộng 33 historical + 10 C + 20 GC và phân bố 30 `publish` / 23 `needs_revision` / 10 `rejected`. Đây **không phải 63 quan sát độc lập**: 20 GC là bản sửa có parent G và 10 C cũng là dữ liệu corrected. 11 CV tách ngoài tập chính và luôn đi cùng parent sạch khi báo cáo.

Test vật lý xác nhận:

- exact manifest IDs khớp exact basename TXT ở cả bốn lớp;
- không `sample_id` nào giao nhau giữa G/P, C, GC và CV;
- 30 expected-publish là exact 10 C + 20 GC;
- C/GC/CV không được đưa vào `docs/goldset/labels.csv` hoặc `docs/goldset/raw/`.

## 3. Manifest và parent integrity

CLI read-only `functional_dataset_v2.py` cho kết quả:

```text
valid samples: 20
valid samples: 11
valid inventory: 20 corrected, 11 coverage
```

Validator khóa schema 15 cột, path containment, content SHA-256, canonical mapping, source URL, parent SHA-256, nhãn theo target và exact inventory. Corrected mapping là `GC-n <- G-n`; coverage mapping/target/label là literal trong code và test.

Mọi row mới dùng:

- annotator `AI-A1`;
- generator `not-exposed-by-runtime`;
- guideline `v1.4`;
- marker coverage `TEST FIXTURE — KHÔNG XUẤT BẢN` chỉ ở manifest/log, không nằm trong body.

## 4. Criterion coverage đã khóa

| Target | Fixtures | Expected label |
|---|---|---|
| A3 | CV-A3-01 | rejected |
| A5 | CV-A5-01, CV-A5-02 | rejected |
| A6 | CV-A6-01, CV-A6-02 | rejected |
| A7 | CV-A7-01, CV-A7-02 | rejected |
| B6 | CV-B6-01 | needs_revision |
| B7 | CV-B7-01 | needs_revision |
| B9 | CV-B9-01, CV-B9-02 | needs_revision |

Đây là coverage có chủ đích cho bảy target được thiết kế, không phải tuyên bố đã có perturbation độc lập cho toàn bộ A1–A7/B1–B11. Mỗi fixture đã được so diff với parent, chạy helper/scanner và đọc full taxonomy; chi tiết before/after, disposition và hash nằm trong `docs/functional-tests/coverage-changes-v1.4.md`.

## 5. Functional clean review v1.4

`docs/evidence/functional-clean-ai-review-v1.4.csv` khóa exact 10 ID, expected `publish`, ngày rà, provenance và SHA-256 hiện tại. `test_evaluation_datasets.py` đối chiếu từng hash CSV với file trên disk.

Kết quả review:

- helper không kết luận A/B ở 10/10;
- scanner không tạo candidate ở 10/10;
- manual A1–A7/B1–B11 không tìm thấy mã còn lại;
- không có shape văn xuôi ẩn A7;
- C-006 có CP7=`NA` vì chỉ dẫn chính sách chung, không có claim chính sách cụ thể;
- cả 10 URL VinFast trong `clean_labels.csv` còn truy cập được khi kiểm ngày 17/08/2026.

Review này không thay đổi `clean_labels.csv` v1.3, `corrections.md` hoặc content C.

## 6. Gold v1 bất biến

`test_evaluation_datasets.py` khóa SHA-256 literal cho toàn bộ 33 file `docs/goldset/raw/*.txt`. Lệnh `git diff --name-only 2f0463a..8e5ca60 -- docs/goldset/raw docs/goldset/labels.csv` không trả file nào.

SHA-256 của `docs/goldset/labels.csv` vẫn là:

```text
ac74ee3e3f11103f8afb0223685aa3e4004dae7e8eaf3b9cd6f716bb58dfcb17
```

Test focused xác nhận cả hash labels và dictionary hash 33 raw files. Vì vậy checkpoint mới không viết lại dữ liệu/evidence E5 v1 và không biến các run fixture P1→P5 thành kết quả chấm điểm.

## 7. Test evidence thực tế

### Focused dataset integrity

- `test_functional_dataset_v2.py`: 15 test functions pass; gồm exact 20 GC + 11 CV và phân bố coverage 7/4.
- `test_evaluation_datasets.py`: 36 checks pass; gồm physical separation, exact IDs, 30 expected-publish, review C hashes và gold v1/raw hashes.
- `test_eval_calibration_dataset.py`: pass; calibration loader lịch sử vẫn chỉ lấy hai split gold.
- `test_moi_test_deu_chay.py`: manifest phủ đúng 77 test files.
- `test_test_group_runner.py`: pass ngoài sandbox; lượt trong sandbox chỉ gặp ACL `%TEMP%`, không phải assertion.

### Full offline

Lệnh:

```powershell
$env:HF_HUB_OFFLINE = '1'
$env:VF_ALLOW_PAID_EVAL = '0'
& 'D:\drupal-multiagent-seo\multiagent\.venv\Scripts\python.exe' scripts\run_test_group.py all-offline
```

Runner in summary:

```text
=== NHOM pure (48 file) ===
=== NHOM postgres (29 file) ===
=== TOM TAT ===
  tong: 77   hong: 0   co [SKIP]: 0
```

Exit code 0; wall time runner khoảng 126,7 giây. Đây là full offline summary mới, không phải preflight và không có DDEV/PHP tests.

## 8. Provenance và giới hạn diễn giải

- 33 candidate labels v1.4, 10 C review, 20 GC và 11 CV đều có AI tham gia; provenance là `AI-annotated-partially-exposed` ở nơi áp dụng.
- Không có inter-annotator agreement độc lập trên lớp publish. Dữ liệu corrected/synthetic không thay bằng chứng đồng thuận AI-người hoặc người-người trên bài thật.
- Không gọi 30 bài là lớp publish tự nhiên; 20 GC và 10 C đều là corrected.
- Không dùng 11 CV để chọn ngưỡng sau khi xem output; CV chỉ đo pass/fail theo target đã khóa trước.
- Checkpoint không chứng minh `publish_min=80` đúng, không bật `meta.calibrated=true`, không đổi `scoring.yaml` và không hồi tố E5 v1.
- Bộ 63+11 chỉ sẵn sàng về integrity để bước sang protocol evaluation release v2. Stability, confusion matrix, metric và quyết định ngưỡng vẫn phải được chạy/báo cáo riêng theo plan evaluation.
