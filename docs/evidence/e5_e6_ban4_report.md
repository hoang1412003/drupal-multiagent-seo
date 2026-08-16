# E5 calibration + E6 k-fold — bản khoá 4 (chạy 2026-08-16)

Số liệu thô: [`e5_ban4_kfold.json`](e5_ban4_kfold.json) (điểm 33 bài),
[`e6_kfold.json`](e6_kfold.json) (CV chính),
[`e6_kfold_phu_quet_ca_publish.json`](e6_kfold_phu_quet_ca_publish.json) (phân tích phụ),
[`e5_quet_nguong.json`](e5_quet_nguong.json) (50 bộ ngưỡng tốt nhất).

> ## ⛔ Kết luận điều hành
>
> **Không được chốt bộ ngưỡng nào vào `scoring.yaml` từ lượt đo này, và không được bật `meta.calibrated`.**
>
> Lý do: `publish_min` hiện hành (**80**) làm hệ thống đề xuất `publish` cho **9/33 bài (27%)**
> mà người gán nhãn nói là cần sửa hoặc từ chối — **sai cả 9**. Cách duy nhất gold set "sửa"
> được điều đó là đẩy `publish_min` lên **96**, tức **trên** điểm cao nhất quan sát được
> (93,3) — nghĩa là **vô hiệu hoá đường ra `publish`**, không phải calibrate nó.

## Truy vết

| | |
|---|---|
| HEAD | `bf3d955` (nhánh `docs/test-retest-2026-08-15`) |
| Score-path snapshot | `04f10e1`, diff **rỗng** |
| Đăng ký trước thiết kế E6 | `4e0fb3d` — **là tổ tiên** của lượt đo này |
| `prompt_version` | `020738e209017213` |
| Model | `claude-haiku-4-5-20251001` |
| Mẫu | 33 (10 `rejected` / 23 `needs_revision` / **0** `publish`) |
| Chi phí E5 | **$1,87** (1.325.064 token vào, 108.068 ra, 1150 giây) |
| Chi phí E6 | **$0** — phân tích lại output E5 |

Guard đã **từ chối** resume file bản 3 (`e5_sau_sua_cp3_cp4.json`, `prompt_version`
`0bdc5ab12ec65f89`) **trước** đường trả phí, đúng như `technical-debt.md` mục 8.0 mô tả.

## Kết quả

### Ngưỡng đang chạy (chưa calibrate)

`veto=50, nr=50, publish=80` → **Kappa 0,369**, accuracy 0,606.
Dự đoán: 13 `needs_revision`, 11 `rejected`, **9 `publish`**.

### E6 — bản chính, đã đăng ký trước (`publish` cố định 80)

| | |
|---|---|
| Kappa in-sample | **0,406** |
| Kappa CV (33 dự đoán out-of-fold) | **0,406** |
| Khoảng cách (selection bias) | **+0,000** |
| Accuracy CV | 0,636 |
| F1 CV | `rejected` 0,80 · `needs_revision` 0,70 · `publish` 0,00 |

### E6 — phân tích phụ (quét cả `publish`), **không thay thế bản chính**

| | |
|---|---|
| Kappa in-sample | **0,713** |
| Kappa CV | **0,713** |
| Khoảng cách | **+0,000** |
| Accuracy CV | 0,879 |
| Ngưỡng chọn | `veto=34, nr=50, publish=96` |

Chạy lại được: `scripts/eval_kfold.py --ket-qua e5_ban4_kfold.json --quet-ca-publish`.

### Ngưỡng từng fold

| fold | mẫu | rej | nr | chính (`pub`=80) | phụ (quét `pub`) |
|---|---|---|---|---|---|
| 0 | 7 | 2 | 5 | veto=34 nr=50 | veto=34 nr=50 pub=96 |
| 1 | 7 | 2 | 5 | veto=34 nr=50 | veto=34 nr=50 pub=96 |
| 2 | 7 | 2 | 5 | veto=34 nr=50 | veto=34 nr=50 pub=96 |
| 3 | 6 | 2 | 4 | veto=34 nr=50 | veto=34 nr=50 pub=96 |
| 4 | 6 | 2 | 4 | veto=**40** nr=50 | veto=**40** nr=50 pub=96 |

## Bốn phát hiện

### 1. `publish_min` là toàn bộ khoảng cách giữa 0,406 và 0,713

Chín bài có `final_score ≥ 80`, **không bài nào** được người gán nhãn `publish`:

| Bài | `final_score` | Nhãn người |
|---|---|---|
| G-014 | 81,6 | needs_revision |
| G-005 | 81,7 | needs_revision |
| G-020 | 82,0 | **rejected** |
| G-008 | 82,5 | needs_revision |
| G-012 | 86,3 | needs_revision |
| P-001b | 89,2 | needs_revision |
| G-019 | 89,5 | needs_revision |
| G-018 | 93,0 | needs_revision |
| G-002 | 93,3 | needs_revision |

`final_score` cao nhất là **93,3**. Quét tự do chọn `publish=96` — trên trần đó, nên nhánh
`publish` **không bao giờ chạy**. Đúng thứ `technical-debt.md` mục 8.2 đã cảnh báo:

> *"`publish ≥ 92` không phải calibration thật — nó chỉ phản ánh lớp `publish` rỗng. Ghi 92
> vào config là mã hoá một hiện vật của gold set thành tham số hệ thống."*

**Hệ quả thực tế:** với cấu hình đang chạy, hệ thống nói *"có thể xuất bản"* cho 27% số bài
mà người duyệt cho là chưa đăng được. Đây là lỗi phải xử lý trước pilot, không phải một con
số thống kê để tối ưu.

### 2. `needs_revision_min = 50` được dữ liệu xác nhận

**Cả 5 fold, ở cả hai phân tích, đều chọn `nr = 50`** — đúng bằng giá trị đang chạy. Đây là
ngưỡng duy nhất trong ba ngưỡng có bằng chứng ủng hộ.

### 3. `compliance_veto_below` gần như không xác định được

Fold chọn 34 (×4) và 40 (×1). Nhìn có vẻ phân tán, nhưng chỉ **một** mẫu duy nhất có điểm
Compliance trong khoảng `[34, 40)` — `P-005a` = 37,5 — và nó nằm ở **fold 1**, fold đã chọn
34. Nên chênh lệch 34↔40 **không đổi một dự đoán nào**: đây là plateau, không phải bất đồng.

Giá trị đang chạy là **50**; cả 5 fold đều chọn thấp hơn hẳn. Đổi `veto` 50 → 34 chỉ nâng
Kappa từ 0,369 lên 0,406 (+0,037), trong khi `publish` 80 → 96 nâng +0,307. **Ngưỡng veto
không phải chỗ đáng sửa trước.**

### 4. Selection bias = 0,000 — không overfit, nhưng cũng không học được gì mấy

Dự đoán out-of-fold **trùng khít** dự đoán in-sample trên cả 33 mẫu, ở cả hai phân tích.

Đọc đúng: quy trình calibration **không overfit** — giữ 20% dữ liệu ra ngoài không làm đổi
kết quả. Nhưng đọc đủ thì phải nói thêm: điều đó cũng có nghĩa việc quét 441 (hoặc 7.056) tổ
hợp **hầu như không chọn ra thông tin gì** từ dữ liệu — các ngưỡng nằm trên plateau rộng, và
mô hình chỉ có 1-2 tham số hiệu dụng trên 33 mẫu.

Đây là câu trả lời trực tiếp cho câu hỏi mà k-fold được chọn để trả lời (mục 4.6.1): **ngưỡng
ổn định, nhưng ổn định vì dữ liệu không đủ sức phân biệt các lựa chọn, không phải vì đã hội tụ.**

## So với bản 3: cùng con số, khác thành phần

Kappa **0,713** và accuracy **0,879** trùng khít số lịch sử bản 3. **Không phải vì không có gì
thay đổi:**

- **13/33 mẫu đổi điểm Compliance** (VD G-008: 50,0 → 64,3; G-013: 50,0 → 66,7; G-010: 50,0 → 40,0)
- **2 dự đoán lật** ở cùng bộ ngưỡng:
  - **G-008**: `rejected` → `needs_revision` — **sửa đúng**, đây chính là ca false-critical mà chốt CP4 nhắm tới (`technical-debt.md` mục 8.5)
  - **G-015**: `needs_revision` → `rejected` — **hỏng đi**, mẫu này trước đúng nay sai

Bốn lỗi bản 3 là `{G-008, G-011, G-020, P-006a}`; bốn lỗi bản 4 là `{G-011, G-015, G-020, P-006a}`.
Cùng số lượng nên chỉ số tổng hợp không đổi, nhưng **thành phần đã khác**.

⚠️ **Không được kết luận "CP4 không có tác dụng" từ việc hai con số bằng nhau.** CP4 đạt đúng
mục tiêu đã nêu (G-008), đồng thời làm một mẫu khác lệch đi. Chỉ số tổng hợp che mất cả hai.

## Cấu trúc bốn lỗi còn lại

| Bài | Nhãn người | Dự đoán | `final` | `compliance` | `critical` | Loại lỗi |
|---|---|---|---|---|---|---|
| G-011 | rejected (A1;B3) | needs_revision | 74,2 | 60,0 | false | **bỏ sót A1** |
| G-020 | rejected (A1) | needs_revision | 82,0 | 60,0 | false | **bỏ sót A1** |
| G-015 | needs_revision (B8) | rejected | 79,6 | 66,7 | **true** | **critical sai** |
| P-006a | needs_revision (B10) | rejected | 73,5 | 42,9 | **true** | **critical sai** |

Lỗi chia đúng hai nhóm đối xứng: **2 lần bỏ sót claim tuyệt đối (A1/CP1)** và **2 lần gắn cờ
`critical` cho bài người chỉ đánh cần sửa**. Không phải nhiễu ngẫu nhiên — đây là hai lỗi hệ
thống cụ thể, đúng dạng "tìm lỗi cụ thể, đừng nhắm vào chỉ số" mà mẫu B14 khuyến nghị.

### Câu hỏi mở: vì sao P-006a vẫn `critical`?

`technical-debt.md` mục 8.4 ghi chốt CP4 xử lý cả **P-006a lẫn G-008**. G-008 đã sửa được;
**P-006a thì chưa**. Nhưng file kết quả E5 chỉ lưu `co_critical` dạng boolean, **không lưu
flag nào sinh ra nó**, nên không truy được nguyên nhân từ dữ liệu đã có.

**Không kết luận CP4 hỏng.** Cờ `critical` có thể đến từ tiêu chí khác (CP1/CP2/CP3/CP9).
Chẩn đoán cần chấm lại riêng P-006a với output flag đầy đủ — ước **~$0,06**. Việc này nên làm
trước khi báo cáo mục 8.4 là đã đóng hoàn toàn.

## Việc KHÔNG được làm từ lượt đo này

1. **Không ghi bộ ngưỡng nào vào `scoring.yaml`.** `publish=96` là hiện vật của lớp `publish`
   rỗng; `veto=34` nằm trên plateau; chỉ `nr=50` có bằng chứng, mà nó vốn đã là giá trị đang chạy.
2. **Không bật `meta.calibrated`.** Không ngưỡng nào được calibrate theo đúng nghĩa.
3. **Không báo cáo 0,713 mà bỏ đi ngữ cảnh.** Con số đó chỉ đạt được khi vô hiệu hoá đường
   ra `publish`. Báo cáo phải nêu cả **0,406** (cấu hình đang chạy) lẫn **0,713** (khi tắt
   nhánh publish), kèm giải thích khoảng cách.

## Việc nên làm tiếp

| Việc | Chi phí | Vì sao |
|---|---|---|
| Chạy bộ **functional-clean 10 mẫu** | ~$0,6 | Đây là bộ **duy nhất** có mẫu kỳ vọng `publish`. Nó trả lời được câu mà gold set không trả lời nổi: ngưỡng `publish` có khả thi không, hay hệ thống luôn tìm ra lỗi ở mọi bài |
| Chẩn đoán `critical` của **P-006a** | ~$0,06 | Xác minh tuyên bố ở mục 8.4 trước khi coi là đã đóng |
| Xem lại **CP1 recall** (G-011, G-020) | $0 trước, cần chấm lại sau | Hai lần bỏ sót A1 là lỗi hệ thống, không phải nhiễu |

**Quyết định ngưỡng `publish` vẫn cần mentor**, đúng như `technical-debt.md` mục 8.2 đã ghi —
nay có thêm số liệu: giữ 80 thì 27% bài bị đề xuất đăng sai, đẩy lên 96 thì đường ra `publish`
không bao giờ chạy.
