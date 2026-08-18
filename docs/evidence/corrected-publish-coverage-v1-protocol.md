# Protocol đăng ký trước: Publish Policy v2

Ngày đăng ký: 2026-08-18
Policy candidate: `cam-nang-vn-v2`

## Trạng thái và phạm vi

Đây là **protocol planned**, không phải evidence kết quả. Tại thời điểm tạo
file này chưa có paid run v2, chưa có metric v2 và policy v2 chưa active/cutover.
Preflight chỉ chứng minh input/release/chi phí dự kiến đã được khóa; preflight
không được trình bày như kết quả thí nghiệm.

Phạm vi chỉ gồm bài `cam_nang`, tiếng Việt, thị trường Việt Nam và đúng release
tuple được manifest đóng băng. Đổi model, prompt, rubric, guideline, scoring,
policy, safety rule, KB/embedding, dataset, ngày assessment hoặc output path
đều tạo release/token khác và không được resume vào raw cũ.

## Thứ tự và năm paid gate độc lập

Mỗi gate cần một xác nhận chi phí riêng của chủ dự án; token của gate này
không dùng lại cho gate khác:

1. E1 stability v2.
2. Gold v2.
3. Corrected-publish 30 bài.
4. Criterion coverage 11 bài.
5. Smoke limited-pilot/cutover, chỉ sau khi toàn bộ Mức B đạt và người có
   thẩm quyền quyết định riêng.

Không chạy tiếp tự động chỉ để tìm kết quả đẹp. Nếu một upstream gate trượt,
downstream dừng; muốn chạy diagnostic phải sửa protocol bằng commit mới và
xin xác nhận chi phí mới.

## Gate đăng ký trước

Các ngưỡng được khóa trước output:

| Gate | Điều kiện đạt |
| --- | --- |
| E1 decision consistency | `>= 0.90` |
| Gold Cohen's Kappa | `>= 0.60` |
| Gold rejected recall | `>= 0.80` |
| Gold needs_revision recall | `>= 0.80` |
| Gold false publish | `0/33` |
| Corrected publish | `30/30` |
| Paired recovery G→GC | `20/20` |
| Coverage target + decision + parent | `11/11` |
| Coverage failure | `0` |
| Drift | `0` |
| Independent label reliability | `not_demonstrated` |

Không quét/chọn ngưỡng publish sau khi xem output v2. Điểm tổng chỉ là số
chẩn đoán; quyết định v2 theo thứ tự A → B → assessment incomplete → publish.

## Ba mức kết luận

- **Mức A — core offline-ready:** contract, mapping, route, evaluator, guard,
  dataset integrity và full offline test đạt. Không suy ra chất lượng thật.
- **Mức B — measured technical gates:** bốn paid dataset E1/gold/corrected/
  coverage hoàn tất trên cùng frozen release và đạt toàn bộ gate định lượng.
  Mức này vẫn không chứng minh nhãn độc lập.
- **Mức C — limited pilot:** chỉ sau Mức B, smoke riêng và phê duyệt có thẩm
  quyền. Không tự động chuyển production từ kết quả test.

## Giới hạn bằng chứng

Gold AI-v1.4 có provenance `AI-annotated-partially-exposed`; do đó
`independent_label_reliability` luôn là `not_demonstrated`, kể cả khi mọi
metric kỹ thuật đạt. Corrected/coverage là dữ liệu tổng hợp có chủ đích để
đo recovery và khả năng phát hiện từng criterion; chúng không thay thế đồng
thuận AI–người trên bài thật và không được trộn vào gold confusion/Kappa.

Không optional stopping, không sửa sample/prompt/policy giữa run, không dùng
`--force`, không ghi đè raw khác release và không gọi API trả phí nếu thiếu
đồng thời frozen manifest, đúng confirmation token, `VF_ALLOW_PAID_EVAL=1`
và xác nhận chi phí riêng cho đúng lượt chạy.
