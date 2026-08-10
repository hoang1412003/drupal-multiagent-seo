# Hướng dẫn thao tác gán nhãn gold set (33 mẫu)

File làm việc cá nhân — không phải tài liệu chính thức của dự án (quy tắc gán nhãn đầy đủ nằm ở `annotation-guideline.md`, file này chỉ là hướng dẫn *thao tác* cụ thể + lịch phiên).

---

## Quy trình 5 bước cho MỖI bài — làm mẫu với G-001

**Bước 1 — Mở 2 file cạnh nhau:**
- `docs/goldset/label_helper_report.txt` → tìm đoạn `G-001.txt`
- `docs/goldset/raw/G-001.txt` → đọc toàn văn

**Bước 2 — Đọc phần máy đã tính sẵn trong report (khỏi phải đo tay):**
```
[MÃ LỖI MÁY KẾT LUẬN ĐƯỢC - ĐỔI NHÃN]
  B3 (220 ký tự, ngoài 140-170)   ← meta_description quá dài

[MÃ NHÓM C - GHI VÀO `notes`, KHÔNG ĐỔI NHÃN]
  C4 (29 câu > 30 tiếng)          ← nhiều câu dài
```
→ Biết ngay bài này **ít nhất** dính B3 (trừ khi có mã A thì nhãn đổi thành `rejected`).

⚠️ **Hai khối này KHÔNG được trộn lẫn.** Chỉ khối đầu quy ra nhãn theo quy tắc ở Bước 4. Khối C4/C5 chép nguyên vào cột `notes` và **dừng ở đó** — nếu để nó đổi nhãn thì mọi bài đều thành `needs_revision` và gold set mất sạch lớp `publish` (đó chính là lỗi guideline v1.3 vừa sửa).

**Bước 3 — Đọc toàn văn `raw/G-001.txt`, tự tìm nốt phần máy không đoán được**, theo đúng thứ tự bảng mã ở `annotation-guideline.md` mục 4:
- **Nhóm A trước** (A1-A6): claim "số 1/tốt nhất/duy nhất"? So sánh Tesla/BYD...? Số liệu sai so với `sources.md` mục 2? Khuyến mại thiếu thời hạn? Lạc đề >50%? Hướng dẫn kỹ thuật gây mất an toàn?
- **Rồi nhóm B còn lại**: B1 (tầm hoạt động thiếu chuẩn đo), B2 (sạc thiếu trụ/%), B5 (sai thuật ngữ brand), B8 (chính tả/ngữ pháp), B10 (số liệu không nguồn). Cộng thêm phần report nhắc riêng: B6 (alt có mô tả đúng ảnh không, dù đủ alt) và B7 (url_alias có thiếu từ khóa chính không).
- **Ghi lại mọi mã tìm thấy**, không chỉ mã đầu tiên gặp.

**Bước 4 — Áp quy tắc mục 5 của guideline để ra nhãn:**
```
Có ≥1 mã A  → rejected
Không A, có ≥1 mã B → needs_revision
Không A, không B → publish
```
(Số lượng lỗi B không đổi nhãn — 1 lỗi B hay 8 lỗi B đều là `needs_revision`.)

**Bước 5 — Ghi vào `docs/goldset/labels.csv`, đúng dòng của sample:**

| Cột | Ghi gì |
|---|---|
| `defect_codes` | Mọi mã **nhóm A/B** tìm thấy, cách nhau bằng `;`. VD: `B3;B8`. **Không** ghi mã C vào đây |
| `label` | `publish` / `needs_revision` / `rejected` |
| `annotator` | Ký hiệu của bạn, VD `A1` |
| `date` | Ngày gán, VD `2026-07-31` |
| `notes` | Ca khó + **mã nhóm C** (C4/C5 lấy từ report, kèm số đếm). VD: `C4 (29 câu > 30 tiếng)` |

Sửa trực tiếp trong CSV (Excel/Notepad đều được, giữ đúng số cột phân tách bằng dấu phẩy).

---

## Lịch 3 phiên (đã xáo trộn G/P, tối đa 15 bài/phiên)

**Phiên 1 (15 bài):** P-006a, G-006, G-012, G-017, P-005a, G-013, P-001a, G-016, G-011, G-015, G-020, P-002a, G-010, P-007b, P-004a

**Phiên 2 (15 bài):** G-007, P-004b, G-001, P-009a, G-014, G-019, G-003, G-018, P-001b, G-004, P-008a, G-005, P-007a, P-010a, G-009

**Phiên 3 (3 bài):** P-003a, G-002, G-008

Mỗi phiên: mở lần lượt từng file theo đúng thứ tự trên, làm 5 bước như G-001, ghi vào `labels.csv`, nghỉ giữa các phiên.

---

## 2 điều bắt buộc không được bỏ qua

1. **Gán mù** — bài nào cũng ở trạng thái Draft/chưa publish, hệ thống AI chưa chạy nên chưa có gì để "lỡ nhìn thấy". Cứ đọc và gán theo cảm nhận từ nội dung.
2. **Sau khi xong cả 33 bài, đợi ≥3 ngày**, chọn ngẫu nhiên 3-4 bài gán lại (mù với nhãn cũ) để tính Kappa test-retest (`annotation-guideline.md` mục 8.1). Đây là cổng bắt buộc trước khi tin bất kỳ con số Sprint 3 nào — đừng bỏ qua dù đã mệt.

---

## Tiến độ (tự cập nhật khi làm xong từng phiên)

- [ ] Phiên 1 (15 bài) — ngày: ____
- [ ] Phiên 2 (15 bài) — ngày: ____
- [ ] Phiên 3 (3 bài) — ngày: ____
- [ ] Test-retest (≥3 ngày sau Phiên 3, 3-4 bài) — ngày: ____
