# Hướng dẫn thao tác gán nhãn gold set (33 mẫu)

File làm việc cá nhân — không phải tài liệu chính thức của dự án (quy tắc gán nhãn đầy đủ nằm ở `annotation-guideline.md`, file này chỉ là hướng dẫn *thao tác* cụ thể + lịch phiên).

---

## Chuẩn bị một lần trước phiên đầu

```
cd multiagent
.venv\Scripts\python.exe scripts\quet_ung_vien.py "..\docs\goldset\raw\*.txt" > ..\docs\goldset\ung_vien_report.txt
```

Sinh ra `ung_vien_report.txt` — file bạn làm việc trực tiếp trong cả 3 phiên.

---

## Không phải bài nào cũng tốn công như nhau

Quy tắc quy nhãn ở mục 5 của guideline **dừng sớm (short-circuit)**: tìm thấy **một** mã A là chốt `rejected` ngay, không cần tìm tiếp; đã có **một** mã B là chắc chắn ít nhất `needs_revision`, chỉ còn phải kiểm xem có mã A nào không.

Nghĩa là **không phải liệt kê đủ mọi mã lỗi để gán được nhãn**. Chạy `scripts/quet_ung_vien.py`, nó tự xếp mỗi bài vào một trong ba nhóm:

| Nhóm | Số bài | Phải làm gì |
|---|---|---|
| **XONG** | 13 | Nhãn suy từ `injected_codes`. **Không cần đọc.** 7 bài chèn mã A → `rejected`, 6 bài chèn mã B → `needs_revision` |
| **CHỈ QUÉT A** | 7 | Máy đã tìm ra mã B → chắc chắn ≥ `needs_revision`. Chỉ cần trả lời *"có mã A nào không?"* |
| **QUÉT ĐẦY ĐỦ** | 13 | Chưa có mã nào → phải phân biệt `publish` với `needs_revision`. Quét 6 mã A + 4 mã B thủ công + đọc tìm B8 |

**Chỉ 20/33 bài cần mở ra xem, và chỉ 13 bài cần quét đầy đủ.**

---

## Quy trình rút gọn cho mỗi bài

**Bước 1 — Mở `docs/goldset/ung_vien_report.txt`,** tìm đoạn của `sample_id`. Report này do `scripts/quet_ung_vien.py` sinh, gồm 4 khối:

- `[MÁY ĐÃ CHỐT - ĐỔI NHÃN]` → tin được, chép thẳng vào `defect_codes`
- `[NHÓM C]` → chép vào `notes`, **không** đổi nhãn
- `[CHỖ CẦN NGƯỜI XÁC NHẬN]` → các đoạn cần liếc, **script không kết luận gì**
- `[KHÔNG QUÉT ĐƯỢC]` → A5, A6, B8: tự đọc

**Bước 2 — Duyệt các đoạn ở khối 3, xác nhận hoặc bác bỏ.** Đây là chỗ tốn thời gian nhất, nhưng là *liếc từng đoạn đã đánh dấu* chứ không phải đọc cả bài đi tìm. Trung bình ~10 đoạn/bài.

⚠️ **Script cố ý quét RỘNG, nên phần lớn đoạn nó đánh dấu KHÔNG phải lỗi.** Ví dụ thật: `"số 1"` trong *"Nghị định số 10/2022/NĐ-CP"*, `"tốt nhất"` trong *"cách tốt nhất để khắc phục sự cố"*, `"duy nhất"` trong *"áp dụng duy nhất 01 gói"* — cả ba đều **không** phải A1. Quét rộng là có chủ đích: thà bác bỏ vài chỗ thừa còn hơn không nhìn thấy chỗ thiếu.

**Bước 3 — Đọc bài để tìm A5, A6, B8.** Chỉ với nhóm QUÉT ĐẦY ĐỦ. A5 và A6 thường quyết được bằng cách đọc title rồi lướt các H2.

**Bước 4 — Áp quy tắc, dừng sớm:**
```
Thấy 1 mã A   → rejected        (DỪNG, không tìm tiếp)
Không A, có B → needs_revision
Không A, không B → publish
```

**Bước 5 — Ghi vào `docs/goldset/labels.csv`, đúng dòng của sample:**

| Cột | Ghi gì |
|---|---|
| `defect_codes` | Mã **nhóm A/B** tìm thấy, cách nhau bằng `;`. VD: `B3;B8`. **Không** ghi mã C vào đây |
| `label` | `publish` / `needs_revision` / `rejected` |
| `annotator` | Ký hiệu của bạn, VD `A1` |
| `date` | Ngày gán, VD `2026-08-11` |
| `notes` | Ca khó + **mã nhóm C** (C4/C5 chép từ report) + **số lỗi chính tả** nếu có B8 |

Sửa trực tiếp trong CSV (Excel/Notepad đều được, giữ đúng số cột phân tách bằng dấu phẩy).

⚠️ **Khối `[MÁY ĐÃ CHỐT]` và khối `[NHÓM C]` KHÔNG được trộn lẫn.** Chỉ khối đầu quy ra nhãn. Mã C4/C5 chép vào `notes` rồi **dừng ở đó** — để nó đổi nhãn thì mọi bài thành `needs_revision` và gold set mất sạch lớp `publish`, đúng lỗi guideline v1.3 vừa sửa.

---

## `defect_codes` KHÔNG cần đầy đủ trên bài thật

Ghi những mã bạn thực sự tìm thấy, **không** phải cố liệt kê cho đủ. Lý do không phải để làm ít đi mà vì nó **chính xác hơn**:

- Trong 4 phép đo của Sprint 3, chỉ **Recall/F1 theo từng mã** cần `defect_codes`; ba phép còn lại (E5 calibration, E3 baseline, E6 held-out) chỉ cần `label`.
- Recall/F1 theo mã sẽ báo cáo **trên tập perturbation**, nơi ground truth chính xác tuyệt đối vì chính bạn chèn vào — `annotation-guideline.md` mục 10.6 đã yêu cầu tách riêng hai tập.
- Nếu cố liệt kê đủ trên bài thật mà bỏ sót một mã, thì lúc AI bắt đúng mã đó nó bị tính thành **báo động giả**. Danh sách thiếu sót làm AI trông tệ hơn thực tế.

Ghi rõ giới hạn này trong báo cáo Sprint 3: *"`defect_codes` trên bài thật không liệt kê đầy đủ; chỉ số theo từng mã báo cáo trên tập perturbation."*

---

## Lịch 3 phiên (đã xáo trộn G/P)

**Phiên 1 (15 bài):** P-006a, G-006, G-012, G-017, P-005a, G-013, P-001a, G-016, G-011, G-015, G-020, P-002a, G-010, P-007b, P-004a

**Phiên 2 (15 bài):** G-007, P-004b, G-001, P-009a, G-014, G-019, G-003, G-018, P-001b, G-004, P-008a, G-005, P-007a, P-010a, G-009

**Phiên 3 (3 bài):** P-003a, G-002, G-008

Giữ nguyên thứ tự này (xáo trộn có chủ đích, `annotation-guideline.md` mục 2). Các bài nhóm XONG đi qua rất nhanh nên số bài mỗi phiên trông nhiều hơn thực tế.

---

## 3 điều bắt buộc không được bỏ qua

1. **Gán theo bảng mã lỗi, KHÔNG theo cảm nhận.** `annotation-guideline.md` mục 2 quy định nhãn phải suy ra từ dấu hiệu quan sát được, để hai người đọc cùng bài ra cùng nhãn. Cảm nhận tổng thể không tái lập được, và Kappa sẽ đo cả phần trôi đó.
2. **Gán mù** — bài nào cũng ở trạng thái Draft, hệ thống AI chưa chạy trên chúng nên chưa có gì để "lỡ nhìn thấy". Nếu vì lý do gì đó đã chạy, tuyệt đối không mở `field_ai_status`/`field_ai_score` trước khi chốt nhãn.
3. **Sau khi xong cả 33 bài, đợi ≥3 ngày**, chọn ngẫu nhiên 3-4 bài gán lại (mù với nhãn cũ) để tính Kappa test-retest (`annotation-guideline.md` mục 8.1). Đây là cổng bắt buộc trước khi tin bất kỳ con số Sprint 3 nào — đừng bỏ qua dù đã mệt.

---

## Canh chừng: B8 có thể thành B9 thứ hai

B8 (chính tả/ngữ pháp) đặt ngưỡng **"từ 1 lỗi trở lên"** — bar rất thấp. Nếu hết phiên 1 mà B8 dính gần như mọi bài thì đó đúng hình dạng của B9 (mã vừa phải tách ở v1.3 vì bắt 33/33 bài và xoá sạch lớp `publish`).

Cách canh: ghi **số lỗi chính tả tìm được** vào `notes`, không chỉ ghi "có B8". Cuối phiên 1 nhìn lại phân bố; nếu 15/15 bài dính thì dừng và xử lý trước khi gán tiếp, đừng gán hết 33 bài rồi mới phát hiện.

---

## Tiến độ (tự cập nhật khi làm xong từng phiên)

- [ ] Phiên 1 (15 bài) — ngày: ____
- [ ] Phiên 2 (15 bài) — ngày: ____
- [ ] Phiên 3 (3 bài) — ngày: ____
- [ ] Rà phân bố B8 sau phiên 1 — ngày: ____
- [ ] Test-retest (≥3 ngày sau Phiên 3, 3-4 bài) — ngày: ____
