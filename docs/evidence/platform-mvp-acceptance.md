# Ma trận nghiệm thu MVP — nền tảng Multi-Agent độc lập

**Ngày lập:** 2026-08-14 · **Nhánh:** `feat/platform-hardening-rollout`
**Tiêu chí gốc:** [design spec 2026-08-12 mục 14](../superpowers/specs/2026-08-12-standalone-multiagent-platform-admin-design.md)

Một dòng **chỉ được `pass`** khi có test tự động chạy được **và** evidence trỏ tới commit cụ thể. Test `[SKIP]` không tính là pass. Tiêu chí thiếu bằng chứng phải ghi `blocked`, không được hạ chuẩn cho đủ điểm.

**Cổng bảo vệ phép đo tại thời điểm lập bảng:** `prompt_version` = `020738e209017213` (không đổi), `git diff` score-path vs `04f10e1` **rỗng**. Không lần gọi Anthropic nào trong toàn bộ P1→P5.

---

| # | Tiêu chí | Test tự động | Evidence | Trạng thái | Rủi ro còn lại |
|---|---|---|---|---|---|
| 1 | Người viết chỉ dùng Drupal; một lần Needs Review tạo đúng một job | `test_platform_end_to_end.py`, `test_vf_ai_trigger.php` | `platform-api-cutover-verification.txt` §7 | **pass** | Chưa thử với người dùng thật ở quy mô nhiều bài/phút |
| 2 | Job gắn đúng site/profile/policy và dedup đúng | `test_api_v1.py`, `test_job_queue.py`, `test_platform_end_to_end.py` | `platform-api-connector-verification.txt` | **pass** | Dedup chỉ được thử ở một site; đa site mới có schema, chưa có tải thật |
| 3 | Một lần chấm chỉ write-back một lần; revision cũ không ghi đè; retry idempotent | `test_platform_failure_matrix.py` (14 case), `test_ai_result_callback.php` (29 assert trên revision **thật**) | `platform-api-cutover-verification.txt` §2–4 | **pass** | Callback là endpoint tự viết, phải giữ hợp đồng và security-test khi sửa |
| 4 | viewer/operator/admin đúng quyền ở **cả** UI lẫn server | `test_admin_connection.py`, `test_admin_routes.py`, `test_admin_user_routes.py` | `platform-admin-auth-verification.txt`, `platform-admin-operations-verification.txt` | **pass** | Chưa có SSO; kho tài khoản thứ hai là nợ đã chấp nhận |
| 5 | Dashboard/jobs/history đọc dữ liệu thật, không metric giả | `test_admin_dashboard.py` (gồm test **render template**), `test_platform_usage.py` | `platform-rollout-smoke.txt` §4 | **pass** | Chi phí legacy vẫn đọc từ snapshot `run_log`; chỉ run mới dùng `llm_usage_event` |
| 6 | Operator xử lý dead-letter mà không trả tiền LLM lần hai | `test_platform_failure_matrix.py` (case mất response, worker chết), `test_worker.py` | `platform-api-connector-verification.txt` | **pass** | — |
| 7 | Config, KB, evaluation chỉ đọc | `test_admin_read_only.py`, `test_admin_evaluation.py` | `platform-admin-operations-verification.txt` | **pass** | `kb_chunk.meta` chưa lưu embedding model/dimension (nợ đã ghi) |
| 8 | Không lưu toàn văn bài nháp; không secret trong Git/log/audit/UI | `test_no_sensitive_persistence.py` (7 canary × 7 bảng + log + HTML), `test_platform_logging.py` | `platform-api-connector-verification.txt` §privacy | **pass** | Redaction theo tên khoá + hình dạng giá trị; mẫu secret mới có thể lọt cho tới khi bổ sung pattern |
| 9 | Nâng database không mất dữ liệu | `test_migrations.py` (nâng từ schema legacy) | `platform-backup-restore-rehearsal.txt` — **11/11 bảng khớp** | **pass** | Diễn tập chạy trên DEV; chưa đo ở quy mô production |
| 10 | Offline regression xanh; hành vi engine và `prompt_version` không đổi | `run_test_group.py all-offline` → **72 file, 0 hỏng, 0 skip**; `test_worker_graph_integration.py` (tương đương output) | `platform-rollout-smoke.txt` | **pass** | — |
| 11 | Tài liệu kiến trúc/roadmap/vận hành/nợ/AI cùng mô tả đúng trạng thái | — (không tự động hoá được) | Commit tài liệu của T8 | **pass** | Tài liệu trôi lệch khỏi code đã xảy ra **4 lần** trong dự án này; phải kiểm lại mỗi lần bàn giao |

**Tổng: 11/11 pass, 0 blocked.**

---

## Những gì bảng này KHÔNG khẳng định

Phần này quan trọng ngang phần trên. Đọc bảng mà bỏ mục này là hiểu sai kết quả.

1. **Không có kết quả chấm điểm thật nào từ P1→P5.** Mọi run trong `run_log` sinh ra bởi các lượt kiểm đều là `is_fixture=true`, điểm do engine giả đặt. Tuyệt đối không trình bày như kết quả chất lượng.

2. **E1, E3, E5, E6 vẫn chưa chạy.** Thứ tự bắt buộc không đổi: **test–retest nhãn → E1 → E5**. Không phần nào của Plan 5 thay thế được các phép đo đó. Xem `docs/technical-debt.md` mục 8.

3. **"Pass" nghĩa là quy trình chạy đúng trên máy dev, không phải production-ready.** Chưa chạy trên host khác máy dev, chưa đo độ trễ/thông lượng dưới tải, chưa diễn tập khôi phục khi dump hỏng.

4. **Một số tiêu chí pass nhờ test, không nhờ vận hành thật.** Ví dụ tiêu chí 4: quyền được kiểm bằng test HTTP, nhưng chưa có người dùng thật ở ba role dùng hệ thống trong một chu kỳ làm việc.

## Nợ còn mở sau MVP

| Nợ | Mã | Vì sao chấp nhận được ở MVP |
|---|---|---|
| Một site, một thị trường | — | Schema đã có `site_id`/`review_profile`; UI mở rộng sau |
| Local auth, chưa SSO | — | Không phụ thuộc hạ tầng danh tính công ty; đánh đổi đã ghi ở spec mục 15 |
| Chưa khoá phiên bản dependency | **H4** | Plan 5 không tạo lockfile. Hai lần dựng môi trường có thể lấy dependency khác nhau |
| Endpoint legacy `/jobs` chưa gỡ | — | Cần thiết cho cửa sổ rollback. Gỡ cần quyết định riêng sau khi production qua cửa sổ đó |
| `kb_chunk.meta` chưa có provenance | **H6** | Trang Config & KB ghi đúng "Chưa version hoá" |
| `StarletteDeprecationWarning` (TestClient/httpx2) | **H1/H4** | Cần nâng dependency có kiểm thử, không đổi vội trong checkpoint feature |
| Chưa có connection pool | **H3** | Chỉ thêm khi tải thực tế yêu cầu |

## Ba lỗi đáng nhớ đã bắt được trong P4–P5

Ghi lại vì cả ba đều thuộc loại **test offline không bắt được**:

1. **`moderation_state` là computed field** — lọc nó trong entity query làm HTTP 500. Đây là **lần thứ hai** dự án gặp (lần đầu 2026-08-07 ở `drupal_client.py`). Chỉ lộ khi gọi HTTP thật.

2. **`DRUPAL_USER=admin` là UID 1** — Drupal cho UID 1 bỏ qua mọi kiểm tra quyền, nên `capabilities` trả `true` bất kể role đúng hay sai. "Test connection" xanh giả. Đã chuyển sang user riêng chỉ có role `ai_service`.

3. **`content_editor` thiếu quyền `use kiem_duyet_noi_dung transition gui_duyet`** — người viết thật không đưa được bài sang Needs Review. Không ai phát hiện vì mọi thử nghiệm đều chạy bằng UID 1.

Cả ba đều có cùng bài học: **thử bằng đúng tài khoản và đúng giao thức mà người dùng thật sẽ dùng**, đừng thử bằng admin.
