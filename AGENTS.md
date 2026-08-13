# Hướng dẫn cho AI/agent

- Giao tiếp với chủ dự án bằng tiếng Việt Nam, trừ khi người dùng yêu cầu ngôn ngữ khác.
- Trước khi đề xuất hoặc thay đổi bất kỳ thứ gì, đọc `README.md` mục **Dành cho AI/model tiếp nhận dự án**.
- Nguồn sự thật cho trạng thái công việc hiện hành là `docs/technical-debt.md` mục **8. BÀN GIAO**. Đọc mục này trước các báo cáo/số liệu lịch sử.
- Với công việc đo lường, đọc thêm `docs/evaluation-plan.md`; với gán nhãn/test–retest, bắt buộc đọc `docs/goldset/annotation-guideline.md` mục 8.
- Với công việc service độc lập, admin, auth, connector/site hoặc profile thị trường, bắt buộc đọc design spec `docs/superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md`, plan tổng `docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md` và sáu quyết định sau review ở `docs/technical-debt.md` mục 8.9; design/plan đã sửa sau review và chờ thực thi, chưa phải code hiện hành. Không tự đổi callback CAS thành JSON:API PATCH hoặc bỏ compatibility hash v1 trong cửa sổ rollback.
- Không coi preflight là kết quả thí nghiệm. Không chạy script gọi API trả phí nếu chưa có xác nhận chi phí riêng của người dùng cho đúng lượt chạy đó.
- Nếu tài liệu và code mâu thuẫn, dừng và đối chiếu bằng commit, `prompt_version` do code tính và file evidence; không tự chọn kết quả thuận lợi hơn.
