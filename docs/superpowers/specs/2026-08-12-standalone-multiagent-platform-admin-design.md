# Thiết kế nền tảng Multi-Agent độc lập và trang quản trị

**Ngày chốt thiết kế:** 2026-08-12
**Trạng thái:** Đã được chủ dự án duyệt; **P1 Foundation và P2 Admin Auth đã triển khai/kiểm chứng, P3–P5 chưa triển khai**
**Phạm vi MVP:** một công ty, thị trường Việt Nam, tiếng Việt, loại nội dung `cam_nang`, một website Drupal
**Quan hệ với roadmap:** thực hiện song song với Sprint 3 nhưng không được làm thay đổi đường chấm điểm đang khóa
**Bổ sung kỹ thuật sau implementation review:** reconciliation dùng Drupal pending metadata feed; write-back chuyển sang callback Drupal có kiểm tra revision/hash và idempotency; legacy hash v1 được giữ trong cửa sổ rollback; không thay đổi phạm vi nghiệp vụ MVP

---

## 1. Bối cảnh và quyết định

Hệ thống hiện đã chạy theo mô hình Drupal gửi job sang FastAPI, worker lấy job từ PostgreSQL, gọi đồ thị Multi-Agent rồi ghi kết quả về Drupal. Tuy nhiên phần Python vẫn mang nhiều giả định của một website duy nhất: một token dùng chung, một bộ biến môi trường Drupal, job chỉ nhận diện bằng `node_id`, và chưa có giao diện quản trị hay tài khoản vận hành riêng.

Quyết định đã duyệt là phát triển phần Multi-Agent thành **một service độc lập** để:

- Drupal chỉ là client đầu tiên, không phải nơi chứa logic chấm điểm;
- có thể kết nối thêm website khác mà không sao chép toàn bộ hệ thống;
- có profile riêng cho từng thị trường, ngôn ngữ và loại nội dung khi thật sự mở rộng;
- người vận hành có trang quản trị riêng để xem job, lịch sử, chi phí, lỗi và tình trạng kết nối;
- giữ nguyên trải nghiệm của người viết: họ chỉ đăng nhập và làm việc trong Drupal.

MVP chọn kiến trúc **modular monolith**: một ứng dụng FastAPI có API `/api/v1` và giao diện quản trị server-rendered `/admin`; worker vẫn là tiến trình riêng; PostgreSQL là kho dữ liệu chung. Không tách microservice ở giai đoạn này.

---

## 2. Mục tiêu và ngoài phạm vi

### 2.1. Mục tiêu MVP

1. Đóng gói Multi-Agent thành nền tảng có ranh giới rõ với Drupal.
2. Xác thực riêng cho request máy–máy và người quản trị.
3. Mọi job và run đều gắn `site_id`, profile và phiên bản policy đã dùng.
4. Có trang quản trị đủ để theo dõi, điều tra lỗi và thao tác retry có kiểm soát.
5. Nâng cấp được database hiện hành mà không mất queue, log hay KB.
6. Không làm thay đổi kết quả của engine 4 agent hiện tại trong lúc Sprint 3 đang đo.

### 2.2. Ngoài phạm vi MVP

- Không triển khai WordPress hoặc connector thứ hai.
- Không mở thị trường/ngôn ngữ thứ hai.
- Không làm SaaS nhiều công ty, billing hoặc self-service onboarding.
- Không làm React SPA; không xây hệ design system lớn.
- Không cho sửa prompt, rubric, rule, KB hay ngưỡng đã calibrate trên web.
- Không cung cấp màn hình chạy E1–E6; admin chỉ đọc kết quả/evidence.
- Không lưu toàn văn bản nháp bài viết trong database Multi-Agent.
- Không làm SSO/OIDC trong MVP; có thể thay local auth ở giai đoạn sau.

Thiết kế schema có `site_id` và `review_profile`, nhưng điều đó chỉ là **khả năng mở rộng**, không phải tuyên bố hệ thống đã hỗ trợ nhiều website hoặc nhiều thị trường.

---

## 3. Nguyên tắc bảo vệ Sprint 3

Productization chạy song song chỉ được thay đổi lớp bao quanh engine. Trong suốt E1 → E5 hiện hành, không được sửa:

- 4 agent và mọi system prompt;
- `fact_check.py` và các prompt con;
- `scoring.py`, Aggregator và luật ra quyết định;
- `scoring.yaml`, `compliance_rules.json`, `brand_rules.json`;
- nội dung hoặc cách retrieval của KB hiện hành.

`prompt_version` phải giữ nguyên `020738e209017213`. Nếu một thay đổi productization buộc phải chạm đường chấm điểm hoặc làm hash này đổi, dừng nhánh productization, ghi rõ nguyên nhân và coi E1/E5 hiện hành mất hiệu lực theo `evaluation-plan.md`.

Việc thêm metadata `site/profile/policy`, authentication, migration, admin UI, connector adapter và observability chỉ hợp lệ khi regression chứng minh output engine không đổi với cùng input.

---

## 4. Kiến trúc mục tiêu

```text
┌─────────────────────────────┐
│ Drupal                      │
│ - content_editor làm bài    │
│ - workflow Needs Review     │
│ - hiển thị báo cáo AI       │
└──────────────┬──────────────┘
               │ Bearer credential theo site
               ▼
┌──────────────────────────────────────────────────┐
│ Nền tảng Multi-Agent — FastAPI modular monolith │
│                                                  │
│ /api/v1             /admin                      │
│ API cho connector   UI server-rendered          │
│        │                 │                       │
│ auth ──┼── reviews ──────┼── profiles           │
│        │                 │                       │
│ connectors/drupal ───── engine hiện tại         │
└──────────────┬───────────────────┬───────────────┘
               │                   │
               ▼                   ▼
        ┌────────────┐       ┌──────────────┐
        │ PostgreSQL │       │ Worker riêng │
        │ queue/log/ │◄──────│ xử lý job    │
        │ auth/KB    │       └──────────────┘
        └────────────┘
```

### 4.1. Ranh giới module dự kiến

| Module | Trách nhiệm |
|---|---|
| `platform/api` | Contract `/api/v1`, xác thực site credential, validate request, trả job/status |
| `platform/admin` | Route và template `/admin`, dashboard, job/history, user management |
| `platform/auth` | Password, session, CSRF, RBAC, rate limit và bootstrap admin |
| `platform/connectors` | Interface nguồn nội dung/đích write-back; MVP có `drupal.py` |
| `platform/reviews` | Enqueue, dedup, retry, pause intake, orchestration giữa job và worker |
| `platform/profiles` | Chọn profile theo site/content/language và snapshot policy |
| `review_platform/engine` | Bao quanh graph/agents/scoring hiện tại; không đổi hành vi chấm |

Khi triển khai, các module mới đặt dưới `multiagent/src/review_platform/` theo đúng các nhánh trong bảng. Không đặt package top-level tên `platform`: khi `multiagent/src` đứng đầu `sys.path`, tên đó che module chuẩn `platform` của Python và làm các dependency như `zstandard/httpx` lỗi import. Code engine hiện hành được bao bằng `review_platform/engine` theo từng bước nhỏ; không di chuyển đồng loạt agent/graph trong pha đầu nếu việc đó làm tăng rủi ro regression.

### 4.2. Vì sao chọn modular monolith

- Một codebase và một database phù hợp quy mô MVP, dễ demo và vận hành.
- API, admin và worker vẫn có ranh giới module, nên không trộn logic giao diện với engine.
- Có thể tách worker, connector hoặc auth thành service sau nếu tải và tổ chức thật sự yêu cầu.
- Tránh chi phí distributed tracing, service discovery và nhiều pipeline deploy khi mới có một site.

---

## 5. Danh tính, vai trò và quyền

Hai hệ thống có hai kho danh tính độc lập. Role Drupal không tự ánh xạ sang role trang quản trị.

### 5.1. Role trong Drupal

| Role | Người dùng | Quyền MVP |
|---|---|---|
| `content_editor` | Người viết đồng thời là người duyệt bài | Tạo/sửa bài; chuyển Draft → Needs Review; xem báo cáo AI; tiếp tục sửa; tự quyết định publish theo workflow. Sửa nội dung bình thường tự tạo job mới |
| `site_admin` | Quản trị Drupal | Quản lý user/workflow/module; cấu hình tích hợp; thao tác force rescore khi cần |
| `ai_service` | Tài khoản máy của connector | Chỉ đọc article/revision cần chấm và ghi các field kết quả AI; không publish, xóa hay quản trị site |

MVP không tách `content_writer` và `content_reviewer` vì quy trình đã duyệt cho phép cùng một người viết và duyệt. Có thể tách sau bằng Content Moderation nếu tổ chức cần nguyên tắc bốn mắt.

Drupal phải kiểm quyền người dùng trước khi route rescore được gọi. Credential site gửi sang Multi-Agent chỉ tồn tại phía server trong `settings.php`, không đưa xuống trình duyệt.

### 5.2. Role trong trang quản trị Multi-Agent

| Role | Quyền |
|---|---|
| `viewer` | Xem dashboard, jobs, review history, cấu hình/KB/evaluation dạng chỉ đọc. Phù hợp mentor, quản lý, compliance hoặc auditor |
| `operator` | Toàn bộ quyền viewer; test connection; retry/rescore có cảnh báo chi phí; pause/resume intake; xử lý dead-letter |
| `admin` | Toàn bộ quyền operator; tạo/khóa user; gán role; reset mật khẩu tạm; xem audit và quản lý thiết lập vận hành |

Không role nào được sửa policy đã calibrate trên web. Một người có thể đồng thời là `site_admin` trong Drupal và `admin` trong Multi-Agent, nhưng đó vẫn là hai tài khoản/quyền độc lập trong MVP.

### 5.3. Xác thực máy–máy

- Mỗi site có Bearer credential riêng.
- Service xác định `site_id` từ credential đã xác thực, không tin `site_id` trong body.
- Database chỉ lưu hash của token và prefix nhận diện; plaintext chỉ hiển thị một lần khi tạo/rotate.
- Token plaintext được đặt ở Drupal `settings.php` hoặc secret store, không vào config export, log hay Git.
- Credential để Multi-Agent gọi ngược Drupal không lưu plaintext trong database; bảng site chỉ giữ secret reference trỏ tới environment/secret store.

### 5.4. Xác thực người quản trị

- Local account cho MVP, không public signup.
- Password băm bằng Argon2id.
- Bootstrap tài khoản admin đầu tiên qua CLI, mật khẩu tạm buộc đổi ở lần đăng nhập đầu.
- Session token ngẫu nhiên; database chỉ giữ hash session token.
- Cookie `HttpOnly`, `Secure` ở production, `SameSite=Lax`; mọi form thay đổi trạng thái có CSRF token.
- Rate-limit đăng nhập theo tài khoản và IP; có idle timeout và absolute expiry.
- Đổi/reset mật khẩu thu hồi mọi session đang hoạt động của tài khoản.
- Không cho khóa, vô hiệu hóa hoặc hạ role của admin hoạt động cuối cùng.
- Audit không bao giờ ghi password, raw session hoặc API token.

---

## 6. Mô hình dữ liệu và migration

### 6.1. Bảng mới hoặc mở rộng

| Bảng | Trường cốt lõi | Mục đích |
|---|---|---|
| `site` | `id`, `slug`, `name`, `connector_type`, `base_url`, `secret_ref`, `active`, `intake_paused`, timestamps | Website/connector đã đăng ký; MVP seed đúng một Drupal site |
| `site_api_credential` | `id`, `site_id`, `token_prefix`, `token_hash`, `active`, `created_at`, `last_used_at`, `revoked_at` | Xác thực request Drupal → service và hỗ trợ rotate |
| `review_profile` | `id`, `code`, `market_code`, `language_code`, `content_type`, `status`, `policy_version` | Cấu hình chấm cho một phạm vi |
| `site_profile_assignment` | `site_id`, `profile_id`, `active`, timestamps | Gắn site với profile được phép dùng; unique theo cặp site/profile và chỉ một profile active cho cùng phạm vi tại một site |
| `review_job` | các cột hiện có + `site_id`, `profile_id`, `policy_version`, `external_content_id`, `external_revision_id`, attempt/backoff fields | Queue bền vững, nhận diện nguồn không phụ thuộc Drupal `node_id` |
| `run_log` | các cột hiện có + site/profile/policy/external ID, token/cost/latency và trạng thái write-back | Lịch sử bất biến, dùng cho dashboard và điều tra |
| `llm_usage_event` | `job_id`, attempt/sequence, correlation ID, agent/phase/model, input/output token, timestamp | Nhật ký từng lần gọi LLM, kể cả attempt lỗi trước khi tạo được `run_log` |
| `worker_heartbeat` | `instance_id`, `started_at`, `last_seen_at`, `version`, `current_job_id` | Cho dashboard phân biệt worker đang sống với queue chỉ đang trống |
| `admin_user` | `id`, `username_normalized`, `password_hash`, `role`, `active`, `must_change_password`, timestamps | Tài khoản quản trị local |
| `admin_session` | `id`, `user_id`, `token_hash`, `csrf_secret`, idle/absolute expiry, revoked fields | Session server-side |
| `admin_audit_log` | `id`, `actor_user_id`, `action`, `target_type/id`, metadata đã lọc, `created_at` | Truy vết thao tác có quyền/chi phí |

Khóa chính public dùng UUID để không lộ số lượng bản ghi và tránh va chạm khi di chuyển dữ liệu. Các khóa ngoại bắt buộc có index phù hợp với lọc job/history.

### 6.2. Default seed cho MVP

- Site: `drupal-vn-primary`.
- Profile: `cam-nang-vn`.
- Assignment active duy nhất: `drupal-vn-primary → cam-nang-vn`.
- `market_code = VN`, `language_code = vi`, `content_type = cam_nang`.
- `policy_version` là mã phát hành bất biến của bộ prompt/rubric/scoring/rules/KB hiện hành; bản ghi run lưu cả metadata thành phần để kiểm chứng.

Migration có thể seed `base_url=http://drupal.ddev.site` để giữ môi trường local hiện tại, nhưng đây chỉ là giá trị bootstrap. Trước khi deploy API/worker mới ở staging hoặc production, operator bắt buộc dùng `site_config.py` để ghi `base_url` và `secret_ref` của đúng môi trường, rồi chạy capability test. Không có đường triển khai nào được coi là sẵn sàng chỉ vì giá trị DDEV mặc định tồn tại trong database.

### 6.3. Migration có phiên bản

Không tiếp tục chỉ dựa vào `CREATE TABLE IF NOT EXISTS`. Dùng các file SQL đánh số tăng dần trong thư mục migration và bảng `schema_migration` để ghi version đã áp dụng. Migration runner chạy transaction cho từng file, từ chối version trùng/đảo thứ tự và có lệnh kiểm tra trạng thái.

Migration đầu tiên phải:

1. tạo site/profile mặc định;
2. thêm cột nullable vào bảng hiện hành;
3. backfill mọi job/run cũ về site/profile mặc định;
4. kiểm tra không còn dòng thiếu khóa;
5. mới chuyển cột cần thiết sang `NOT NULL` và thêm constraint/index.

Test migration phải bắt đầu từ schema/database giống bản hiện hành và chứng minh số dòng, payload JSON, trạng thái queue và run history không mất.

`run_log` lịch sử được ghi trước thao tác PATCH nên không đủ bằng chứng để suy write-back thành công hay thất bại. Migration phải backfill các row này thành `writeback_status=unknown`; dashboard không được tính chúng vào tỷ lệ thành công/thất bại và UI phải hiển thị “Không có dữ liệu”. Không được đổi sự kiện chưa biết thành `succeeded` để làm đẹp metric.

### 6.4. Dữ liệu nội dung

Drupal là nguồn sự thật của bài viết. Nền tảng chỉ lưu:

- external content ID và revision ID nếu Drupal cung cấp;
- `content_hash`;
- kết quả agent, evidence, quyết định, phiên bản cấu hình;
- link quay lại Drupal;
- metadata token, chi phí, thời gian và audit.

Không lưu title/summary/body/SEO text toàn phần trong queue, run log hoặc audit. Nếu production sau này bắt buộc snapshot để điều tra, phải có quyết định riêng về trường được phép lưu, mã hóa và thời hạn xóa; không âm thầm mở rộng từ MVP.

---

## 7. Contract API và connector Drupal

### 7.1. API v1

API máy–máy đặt dưới `/api/v1`. Contract khởi đầu:

- `POST /api/v1/jobs`: nhận `external_content_id`, `external_revision_id` nếu có, `content_type`, `langcode`, `content_hash`, `source` và cờ `force` khi route Drupal đã xác thực quyền rescore. MVP dùng `content_type=cam_nang`, `langcode=vi`; hai giá trị vẫn phải gửi tường minh để profile selection không rơi về mặc định im lặng.
- `GET /api/v1/jobs/{job_id}`: trạng thái một job thuộc đúng site của credential.
- `GET /api/v1/jobs/by-content/{external_content_id}`: trạng thái mới nhất thuộc đúng site.
- `/health`: chỉ trả tình trạng sống tối thiểu, không lộ database URL, secret hoặc stack trace.

Body không nhận `site_id`. Với mọi lookup, service luôn thêm phạm vi site từ credential để tránh đọc chéo tenant trong tương lai.

Endpoint cũ được giữ trong giai đoạn chuyển tiếp đủ để Drupal hiện hành không gãy; sau khi module Drupal chuyển sang `/api/v1` và regression xanh mới đánh dấu deprecated. Không duy trì hai contract vô thời hạn.

### 7.2. Chọn profile

Khi enqueue:

1. xác thực credential và suy ra site;
2. kiểm tra site active/intake không pause;
3. qua `site_profile_assignment`, chọn đúng một profile active khớp site, `content_type`, `langcode`;
4. snapshot `profile_id` và `policy_version` vào job;
5. áp dụng dedup.

Nếu không có đúng một profile khớp, request thất bại rõ ràng và không rơi về default im lặng.

### 7.3. Dedup

Khóa logic của một lượt chấm bình thường là:

```text
(site_id, external_content_id, content_hash, policy_version)
```

Cùng bài, cùng nội dung và cùng policy chỉ có một job hiệu lực. `force` là thao tác có quyền và có audit; nó tạo lượt chạy mới có liên kết tới job cũ thay vì sửa/xóa lịch sử.

### 7.4. Connector interface

Connector Drupal chuyển payload JSON:API thành input chuẩn gồm sáu trường nội dung hiện tại cùng `content_type`, `langcode`, external ID/revision và link nguồn. Worker chỉ gọi interface connector, không đọc trực tiếp biến môi trường Drupal toàn cục.

Khi job có `external_revision_id`, connector đọc đúng revision bằng `?resourceVersion=id:{revision_id}`. Không được fetch revision mặc định rồi ghi audit dưới hash của bản nháp. Cơ chế resource version này là contract chính thức của JSON:API cho node/media revisions: <https://www.drupal.org/docs/core-modules-and-themes/core-modules/jsonapi-module/revisions>.

JSON:API không cung cấp collection các revision/working copy để reconciliation quét hàng loạt. Vì vậy module Drupal cung cấp read-only feed `GET /vf-ai/integration/v1/pending`, chỉ cho machine permission riêng. Feed dùng entity query `latestRevision()` để liệt kê revision mới nhất đang `needs_review`, trả UUID, revision ID, content type, langcode, fingerprint v2 và link nguồn; **không trả title/body/summary**. Connector lấy danh sách metadata từ feed rồi fetch từng revision cụ thể qua JSON:API. `rel:working-copy` chỉ là fallback cho một external ID legacy không có revision ID, không phải collection discovery. Drupal Entity API định nghĩa `latestRevision()` là default revision hoặc pending revision mới hơn: <https://api.drupal.org/api/drupal/core%21lib%21Drupal%21Core%21Entity%21Query%21QueryInterface.php/function/QueryInterface%3A%3AlatestRevision/10>.

Write-back dùng callback `POST /vf-ai/integration/v1/results`, không PATCH JSON:API article trực tiếp. Request chỉ được chứa run UUID, external content ID, expected revision ID, expected content hash/version và bốn field kết quả AI hiện hành; callback không nhận moderation state, title/body hay field tùy ý. Machine role có permission riêng cho callback và không cần quyền `edit any article content`.

Callback phải thực hiện compare-and-set trong transaction: khóa node, đọc lại latest revision, rồi chỉ ghi khi revision và fingerprint đầu vào vẫn khớp expected values. Nếu nội dung đã đổi, trả conflict `content_superseded`, không ghi field AI; worker đánh dấu run/job là `superseded` và để event/reconciliation xử lý revision mới. Mỗi request mang `run_id`; nếu latest report đã có đúng `run_id`, callback trả `already_applied` như thành công để retry sau timeout không tạo revision hoặc PATCH thứ hai. Kiểm tra này phải nằm phía Drupal tại cùng ranh giới ghi để không có khe TOCTOU giữa GET lại và write-back.

Trong cửa sổ rollback, endpoint `/jobs` cũ vẫn tạo job `content_hash_version=1`. Worker phải chọn đúng thuật toán theo version: v2 dùng fingerprint sáu field và exact revision; v1 dùng `text_utils.content_hash()` bốn field, fetch working copy khi job legacy thiếu revision ID, đồng thời lấy revision ID thực từ response trước callback. Không được so hash v1 bằng công thức v2.

---

## 8. Luồng nghiệp vụ chính

### 8.1. Người viết gửi bài để chấm

```text
content_editor lưu/chuyển Needs Review trong Drupal
→ Drupal kiểm quyền và gửi event server-side
→ API xác thực credential, suy site/profile/policy
→ tạo hoặc trả job dedup
→ worker claim job
→ connector đọc revision hiện hành từ Drupal
→ engine 4 agent + Aggregator chạy như hiện tại
→ ghi run_log trước write-back
→ callback Drupal so revision/hash và ghi kết quả idempotent đúng một lần
→ Drupal hiển thị báo cáo; content_editor sửa hoặc publish
```

Người viết không cần tài khoản Multi-Agent và không thấy site API token.

### 8.2. Nội dung thay đổi

Khi trường đầu vào thay đổi, `content_hash` đổi và Drupal tự enqueue job mới. Chỉ thay đổi field kết quả AI không được tạo vòng enqueue. Kết quả cũ vẫn giữ trong run history; UI Drupal phải cảnh báo báo cáo cũ nếu hash không còn khớp. Job của revision cũ hoàn thành muộn không được ghi đè báo cáo của revision mới: callback trả `content_superseded`, worker không retry LLM/write-back cho payload cũ và reconciliation bảo đảm revision hiện hành có job riêng.

### 8.3. Pause/resume

Pause đóng băng phần việc chưa bắt đầu của site:

- API và reconciliation không enqueue job mới;
- worker không claim job `queued` của site đang pause;
- job đang chạy được hoàn tất;
- job đã queue được giữ nguyên;
- resume cho phép xử lý tiếp queue, không xóa hay tạo lại hàng loạt.

Mọi pause/resume có actor, thời điểm, lý do tùy chọn trong audit.

### 8.4. Retry và dead-letter

- Luồng chuẩn: `queued → running → done`.
- Timeout, 429 và lỗi 5xx tạm thời được đưa lại `queued` với exponential backoff có jitter.
- Lỗi schema, xác thực, programming hoặc input không hợp lệ không retry mù.
- Tối đa 3 attempt tự động; hết giới hạn chuyển `failed`/dead-letter.
- Operator/admin có thể retry thủ công sau màn xác nhận nêu rõ có thể phát sinh chi phí LLM.
- Nếu chỉ write-back thất bại sau khi đã có run result, retry phải dùng lại kết quả đã lưu, không gọi lại LLM.
- Retry callback dùng cùng `run_id`: `already_applied` là thành công idempotent; `content_superseded` là kết thúc không retry và không ghi payload cũ.

---

## 9. Trang quản trị

UI dùng template server-rendered với Jinja2, HTMX cho tương tác nhỏ và JavaScript tối thiểu. Mục tiêu là vận hành rõ ràng, không phải một ứng dụng frontend độc lập phức tạp.

### 9.1. Các màn hình MVP

1. **Đăng nhập:** username/password, thông báo lỗi không tiết lộ tài khoản có tồn tại, trạng thái bắt buộc đổi mật khẩu.
2. **Dashboard:** health API/worker/database/connector; queue depth; tổng lượt chấm; phân bố decision; token/chi phí/độ trễ theo khoảng thời gian.
3. **Jobs:** lọc theo trạng thái/site/thời gian/external ID; xem attempt/error; retry với xác nhận chi phí; liên kết review/run.
4. **Review history/detail:** điểm từng agent/tiêu chí, evidence, veto, missing agent, model, prompt/profile/policy, token, chi phí, thời gian, trạng thái write-back và link Drupal.
5. **Drupal connection:** hiển thị đúng site MVP, trạng thái/last success; test capability không mutation; pause/resume intake. Test phải xác minh quyền pending feed, callback result và khả năng đọc exact revision khi có item, không được báo `ok` chỉ từ một GET collection JSON:API. Không có UI thêm nhiều site ở MVP.
6. **Config & KB:** chỉ đọc metadata scoring, rules, profile, KB version/chunk metadata; không có nút Save và không hiển thị secret.
7. **Users:** admin tạo tài khoản, gán role, khóa/mở khóa, reset mật khẩu tạm; mỗi user tự đổi mật khẩu.
8. **Evaluation:** chỉ đọc trạng thái/evidence E1–E6 và cảnh báo kết quả lịch sử/hết hiệu lực; không chạy phép đo trả phí từ UI. Nguồn là `docs/evidence/evaluation-manifest.json` được version-control, mỗi entry có `experiment`, `status`, `score_path_snapshot`, `prompt_version`, `model`, `run_at`, `evidence_path`, `metadata_complete`; provenance không tồn tại trong evidence cũ phải để `null` và cảnh báo, không suy diễn. Loader chỉ nhận đường dẫn dưới `docs/evidence/`, không quét/mở file tùy ý từ request web.
9. **Audit:** admin xem thao tác đăng nhập, user/role, pause/resume, test connection, retry/rescore và rotate credential theo metadata đã lọc.

### 9.2. Nguyên tắc hiển thị

- Dashboard phải đọc dữ liệu thật, không mock metric.
- Staging smoke dùng fake engine phải lưu cờ `is_fixture`; dashboard/cost/decision mặc định loại fixture, review detail hiển thị cảnh báo rõ và không được trình bày fixture score như kết quả AI.
- Viewer không thấy nút thao tác gây hiệu ứng phụ.
- Mọi action operator/admin dùng POST + CSRF và xác nhận khi có chi phí/rủi ro.
- Lỗi kỹ thuật và `last_error` nhạy cảm được làm sạch trước khi hiển thị.
- Không render raw HTML do LLM sinh; evidence/suggestion phải escape như UI Drupal hiện tại.
- Không hiển thị password hash, token hash đầy đủ, secret reference value hoặc database URL.

---

## 10. Profile, policy và mở rộng thị trường

Profile MVP `cam-nang-vn` gắn với thị trường Việt Nam, tiếng Việt và loại bài cẩm nang. Profile trỏ tới một `policy_version` bất biến gồm tối thiểu:

- rubric version;
- prompt version;
- model;
- hash cấu hình scoring;
- hash rule compliance/brand;
- phiên bản/hash KB và embedding model.

Admin chỉ đọc những giá trị này. Thay policy phải qua quy trình tạo release mới, chạy regression/evaluation rồi mới kích hoạt; không sửa bản đang dùng tại chỗ.

Thị trường mới phải có profile, nguồn luật/brand/KB, gold set, calibration và test riêng. Không sao chép ngưỡng Việt Nam rồi đổi `market_code`. Connector website và profile thị trường là hai trục độc lập: thêm site Drupal thứ hai không đồng nghĩa thêm thị trường, và thêm thị trường không đồng nghĩa connector tự hỗ trợ CMS mới.

---

## 11. Xử lý lỗi, chi phí và quan sát

- API tắt không được làm Drupal lưu bài thất bại; module ghi watchdog và reconciliation bắt lại sau.
- Worker tắt không làm mất job; lease quá hạn được reclaim an toàn.
- Database lỗi phải trả thất bại đúng sự thật, không báo enqueue thành công giả.
- Connector nhận 401/403 dừng sớm, đánh dấu lỗi cấu hình và cảnh báo operator; không retry đến hết ngân sách.
- Một agent lỗi dùng đúng cơ chế degrade hiện tại; thiếu Compliance không bao giờ dẫn tới auto-publish.
- Ghi correlation ID xuyên Drupal → API → job → worker → agent → run → write-back.
- Ghi từng usage event ngay sau mỗi response LLM vào bảng riêng, gắn job/attempt/agent/phase/correlation; vì vậy attempt engine lỗi trước `run_log` vẫn được tính token/cost. `run_log.usage` có thể giữ snapshot tương thích nhưng dashboard không được cộng trùng hai nguồn. Thao tác trả phí của operator có audit.
- Không log nội dung đầy đủ, Authorization header, cookie, password hay response chứa secret.

---

## 12. Chiến lược kiểm thử

### 12.1. Unit

- Argon2id password verify, session expiry/revoke, RBAC, CSRF, rate limit và last-active-admin guard.
- Site token hashing/rotation và scope site.
- Profile selection, pause semantics, dedup key và retry classification.
- Sanitization audit/log/UI.

### 12.2. Migration

- Nâng từ schema hiện hành có dữ liệu thật mô phỏng.
- Bảo toàn số job/run/KB row và JSON payload.
- Backfill đúng site/profile mặc định; chạy migration lần hai không phá dữ liệu.
- Backfill write-back lịch sử thành `unknown`, không tính như thành công.
- Constraint/index được tạo sau backfill.

### 12.3. API và connector

- Token sai/revoked trả 401; không thể giả `site_id` trong body.
- Site pause chặn job mới nhưng không xóa queue.
- Cùng dedup key không tạo hai job.
- Connector đọc đúng sáu field; callback chỉ ghi bốn field AI, đúng một lần, không publish.
- Job A của revision cũ hoàn thành sau job B không thể ghi đè report B; callback idempotent trả `already_applied` sau timeout mơ hồ.
- Legacy endpoint/hash v1 vẫn hoàn tất được một job trong cửa sổ rollback; không bị so bằng fingerprint v2.
- Capability test thất bại nếu thiếu feed/result/revision-read dù GET article thông thường còn hoạt động.
- Write-back retry dùng lại saved result và không phát sinh lần gọi LLM thứ hai.

### 12.4. Worker và tích hợp

- Toàn luồng API → queue → worker → engine fake → audit → connector.
- Crash/reclaim, backoff, max attempt, dead-letter và retry thủ công.
- Reconciliation cùng dedup không tạo job trùng với event-driven.
- Mọi run gắn site/profile/policy/version và correlation ID.
- Usage của engine attempt thất bại vẫn tồn tại và dashboard không cộng trùng snapshot successful run.

### 12.5. Admin UI

- Login/logout/change temporary password.
- Mỗi role thấy đúng trang và action.
- Form action có CSRF; retry/pause có confirmation; viewer không thể gọi endpoint trực tiếp.
- Filter/pagination đọc dữ liệu thật; config/KB/evaluation thực sự read-only.
- Không rò secret hoặc raw LLM HTML.

### 12.6. Regression engine

Toàn bộ offline suite hiện tại phải xanh. Với cùng input và fake agent output, report/decision/write-back payload phải giống trước productization. CI không gọi API LLM trả phí. E1/E5 chỉ chạy theo cổng xác nhận trong tài liệu đo lường và `prompt_version` phải không đổi.

---

## 13. Thứ tự triển khai

Chương trình productization dùng **5 plan kỹ thuật** theo plan tổng tại
`docs/superpowers/plans/2026-08-12-standalone-multiagent-platform.md`. Phạm vi
P3 được gom thành một lát admin vận hành hoàn chỉnh để mọi màn hình dùng chung
read model, RBAC, CSRF, pagination, sanitization và checkpoint UI trước khi
chuyển sang ranh giới API/connector.

### P1 — Nền dữ liệu

- Migration runner có version.
- Site/profile mặc định và backfill schema hiện hành.
- Regression migration và repository/data access.

### P2 — Auth và khung admin

- Local user, session, CSRF, RBAC, bootstrap CLI.
- Layout/login/logout và audit nền.

### P3 — Admin Operations

- Dashboard, jobs, review history/detail và retry/dead-letter có xác nhận chi
  phí + audit.
- Quản lý user theo last-admin invariant.
- Config/KB/evaluation chỉ đọc và audit log chỉ dành cho admin.

### P4 — API v1 và connector Drupal

- Extract connector interface/Drupal adapter nhưng giữ hành vi cũ; thêm
  per-site credential, profile selection, dedup và pause/resume.
- Chuyển module Drupal sang contract `/api/v1` và callback CAS/idempotent sau
  regression; giữ hash v1 trong cửa sổ rollback.

### P5 — Hardening và rollout

- Worker heartbeat, durable usage event, token/cost/latency/correlation metadata
  đầy đủ và connection health/capability thật.
- Security/integration test, staging smoke test, migration/rollback rehearsal,
  secret rotation và tài liệu bàn giao/demo flow.

Thứ tự kỹ thuật hiện hành là: foundation site/profile → auth/admin shell → admin
operations đọc dữ liệu hiện hành → tách connector nhưng giữ behavior →
regression → mới cut API/worker sang contract mới → hardening/rollout. Không
“big-bang rewrite”.

---

## 14. Tiêu chí hoàn thành MVP

MVP chỉ được coi là xong khi:

1. Người viết vẫn chỉ cần dùng Drupal và một lần chuyển Needs Review tạo đúng một job.
2. Job được gắn đúng site/profile/policy và dedup đúng.
3. Một lần chấm thành công chỉ write-back đúng một lần; kết quả revision cũ không thể ghi đè revision mới và retry timeout là idempotent.
4. Viewer/operator/admin bị giới hạn đúng quyền cả ở UI lẫn server endpoint.
5. Dashboard/jobs/history đọc dữ liệu thật; không có metric giả, không coi write-back legacy là thành công và không bỏ chi phí của engine attempt thất bại.
6. Operator xử lý được failed/dead-letter mà không vô tình trả tiền LLM lần hai cho lỗi write-back.
7. Config, KB và evaluation chỉ đọc.
8. Database không lưu toàn văn bài nháp và không có secret trong Git/log/audit/UI.
9. Database hiện hành nâng cấp không mất dữ liệu.
10. Offline regression xanh, hành vi engine và `prompt_version` không đổi.
11. Tài liệu kiến trúc, roadmap, vận hành, nợ kỹ thuật và hướng dẫn AI cùng mô tả đúng trạng thái.

---

## 15. Trade-off và rủi ro đã chấp nhận

- **Local auth tạo thêm kho tài khoản**, nhưng phù hợp MVP độc lập và tránh phụ thuộc Drupal; SSO là bước sau khi có hạ tầng danh tính công ty.
- **Một modular monolith chưa phải microservice**, nhưng đã đủ ranh giới để tái sử dụng; tách sớm sẽ tăng chi phí vận hành mà chưa có tải thật.
- **Một site trong UI nhưng schema nhiều site** tạo thêm metadata ngay từ đầu; đổi lại tránh gắn `node_id` toàn cục và credential toàn cục thêm lần nữa.
- **Callback Drupal làm MVP lớn hơn một chút**, nhưng đây là ranh giới nhỏ, chỉ nhận bốn field AI và đổi lại có compare-and-set, idempotency và quyền theo endpoint. JSON:API vẫn dùng để đọc exact revision; không dùng generic article PATCH cho write-back.
- **Không lưu snapshot nội dung** giảm khả năng tái dựng nguyên văn khi Drupal xóa revision, nhưng giảm đáng kể rủi ro sao chép dữ liệu nhạy cảm. MVP ưu tiên Drupal revision + hash + evidence.
- **Productization song song Sprint 3** tăng nguy cơ trôi measurement. Hàng rào score-path freeze và regression/prompt-version gate là điều kiện bắt buộc, không phải khuyến nghị.

---

## 16. Nguồn sự thật khi triển khai

- Tài liệu này là nguồn sự thật cho phạm vi và quyết định productization/admin.
- `docs/technical-debt.md` mục 8 là nguồn sự thật cho thứ tự đo lường đang mở và cổng chi phí.
- `docs/evaluation-plan.md` là nguồn sự thật cho tính hợp lệ E1–E6 và score-path freeze.
- `docs/architecture.md` mô tả tổng thể hệ thống và phải link về tài liệu này thay vì chép lại toàn bộ chi tiết.

Nếu implementation plan hoặc code cần khác quyết định trong tài liệu này, phải cập nhật thiết kế và xin duyệt lại phần thay đổi trước khi triển khai.
