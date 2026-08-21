# Deploy demo lên AWS EC2 + HuggingFace Space (2026-08-16/17)

Tài liệu này ghi lại lần đầu tiên dự án được deploy ra ngoài máy dev/ddev, để
lần sau (người hoặc AI khác) không phải dò lại từ đầu. Đây là **deploy demo**,
không phải hạ tầng production chính thức — xem giới hạn ở mục cuối.

## 1. Kiến trúc đã dựng

Một EC2 instance duy nhất (region `ap-southeast-1`, Amazon Linux 2023,
`t3.micro`) chạy tất cả:

- **Drupal**: Nginx + PHP-FPM 8.4 + MariaDB 11.8, docroot `drupal/web`.
  Database là **bản copy một lần** từ `ddev export-db` của máy dev — không tự
  đồng bộ tiếp, sửa trên demo không chảy ngược về local và ngược lại.
- **Multi-Agent**: Postgres/pgvector qua `docker-compose.yml` (không đổi so
  với local). Service `api.py` (uvicorn, port 8900) và `worker.py` chạy dưới
  dạng **systemd service** (`multiagent-api`, `multiagent-worker`,
  `Restart=always`) — không phải chạy tay trong phiên SSH.
- **Embedding BGE-M3**: chạy trên **HuggingFace Space** riêng
  (`hoang2003/bge-m3-embedding-api`, SDK Gradio, hardware ZeroGPU free) thay vì
  nạp model ~2GB local. Xem `RemoteEmbedder` trong `multiagent/src/embeddings.py`
  — kích hoạt bằng biến `EMBEDDING_SPACE_URL` trong `.env`; để trống thì quay
  lại nạp model local như cũ (không phá hành vi máy dev).

`.env` production nằm ở gốc repo trên server (`~/drupal-multiagent-seo/.env`),
**không phải bản copy của `.env` local** — mọi secret (DB password, `hash_salt`,
`VF_SERVICE_TOKEN`, `EMBED_API_TOKEN`, mật khẩu admin) đều sinh mới riêng cho
môi trường này. Không có secret nào trong tài liệu này hay trong git.

## 2. Việc bắt buộc phải làm cho MỌI site/môi trường mới

Đây là phần dễ quên nhất, vì local dev dùng seed sẵn nên các bước này vô hình
cho tới khi deploy nơi khác:

1. **`site_config.py set-from-env`** — seed migration 0001 gán site
   `drupal-vn-primary` với `base_url=http://drupal.ddev.site`. Trên môi trường
   mới, worker poll job qua base URL đó sẽ lỗi kết nối. Đã ghi ở mục 8.9 quyết
   định (3) của `technical-debt.md`, đúng như dự đoán trong đó.
2. **`site_credential.py import-env --site <slug> --env VF_SERVICE_TOKEN`** —
   đây là bước **KHÔNG được nhắc ở đâu trước đây**. Có **hai hệ thống xác thực
   độc lập** giữa Drupal và multiagent:
   - Worker polling (`worker.py` gọi Drupal qua JSON:API bằng
     `DRUPAL_USER`/`DRUPAL_PASSWORD`) — chỉ cần bước 1 ở trên.
   - `vf_ai_trigger` module (Drupal gọi *sang* multiagent qua
     `/api/v1/jobs*`, dùng Bearer token = `Settings::get('vf_ai_service_token')`)
     — token này được so khớp với bảng `site_api_credential` trong Postgres
     (hash SHA-256), **không phải** so trực tiếp với `VF_SERVICE_TOKEN` như
     endpoint `/jobs` cũ. Database Postgres mới tinh không có row nào ở bảng
     đó → mọi request từ khung "Đánh giá AI"/nút "Chấm lại" trên Drupal nhận
     `401 unauthorized` cho tới khi chạy lệnh này.
3. **`drush config:set vf_ai_trigger.settings service_url 'http://127.0.0.1:8900'`**
   — config entity `vf_ai_trigger.settings.service_url` được copy nguyên từ
   database local, ở đó mang giá trị `http://host.docker.internal:8900` (địa
   chỉ chỉ có nghĩa trong container ddev, gọi để Drupal-trong-Docker với ra
   máy host). Trên server thường (không Docker), hostname này không resolve
   được → lỗi `cURL error 6: Could not resolve host`. Không thấy ngay vì lỗi
   này chỉ ghi vào watchdog log (`drush watchdog:show`), không hiện ra UI rõ
   ràng — JS chỉ hiện chung chung "Không liên lạc được với dịch vụ chấm điểm".
4. **`admin_user.py bootstrap --username admin`** — Platform Admin (`/admin`
   trên port 8900) là hệ xác thực **thứ ba**, hoàn toàn tách biệt (Postgres +
   Argon2id), không liên quan gì tới tài khoản Drupal hay `VF_SERVICE_TOKEN`.
   Database mới không có user nào ở đây cho tới khi bootstrap.

## 3. Bẫy hạ tầng khác (không phải bug code, nhưng tốn thời gian)

- **`/tmp` là tmpfs cỡ ~50% RAM.** Trên `t3.micro` (1GB RAM), `/tmp` chỉ có
  ~457MB. `pip install torch` (gói ~526MB) báo `OSError: [Errno 28] No space
  left on device` dù `df -h /` báo còn 28GB trống — vì pip tải/build trong
  `/tmp`, không phải ổ chính. Đây chính là lý do kỹ thuật để chuyển
  embedding sang HuggingFace Space thay vì cố nhét `sentence-transformers`
  vào server nhỏ.
- **PHP-FPM tên service không có số phiên bản.** Gói `php8.4-fpm` cài ra
  service tên `php-fpm.service` (không phải `php8.4-fpm.service`) trên
  Amazon Linux 2023.
- **Amazon Linux 2023's nginx.conf có sẵn 1 default server** (`server_name
  _;`, root `/usr/share/nginx/html`, dòng ~37-53 của `/etc/nginx/nginx.conf`).
  Thêm vhost Drupal riêng ở `conf.d/` cũng khai `server_name _` sẽ bị cảnh báo
  `conflicting server name "_" on 0.0.0.0:80, ignored` và có thể phục vụ nhầm
  trang chào mừng mặc định thay vì Drupal. Phải comment/xoá block mặc định đó.
- **HuggingFace free tier, hai giới hạn cùng lúc:** (a) SDK **Docker** cho
  Space yêu cầu xác minh thanh toán (thẻ hoặc credit), dù hardware CPU Basic
  free — tài khoản mới không thẻ sẽ thấy icon khoá; (b) SDK **Gradio** ở free
  tier chỉ cho chọn hardware **ZeroGPU**, không chọn được **CPU Basic** (CPU
  Basic yêu cầu PRO). Giải pháp dùng được: Gradio + ZeroGPU, nhưng bắt buộc có
  ít nhất một hàm đánh dấu `@spaces.GPU`, nếu không Space báo lỗi runtime
  `No @spaces.GPU function detected during startup` dù code không có lỗi gì.
- **`vendor/bin/drush` là launcher script, không phải file PHP.** Chạy
  `php vendor/bin/drush ...` sẽ khiến PHP in ra nguyên văn nội dung script
  (vì không có `<?php` ở đầu) thay vì thực thi. Phải gọi trực tiếp
  `./vendor/bin/drush ...`.

## 4. Địa chỉ (chỉ để tham khảo — instance có thể đã bị tắt/xoá)

- Drupal: `http://<EC2-public-IP>`
- Platform Admin: `http://<EC2-public-IP>:8900/admin` — **địa chỉ của lần deploy
  16–17/08/2026, nay không còn**: admin Jinja2 đã bị xoá ngày 2026-08-21 và
  thay bằng Console React ở `/console/`. Bản deploy này có từ TRƯỚC khi Console
  tồn tại, nên nó chưa bao giờ phục vụ `/console/`. Xem mục 6 để deploy lại.
- HuggingFace Space: `https://hoang2003-bge-m3-embedding-api.hf.space`

Không ghi IP/port cụ thể ở đây vì đây là máy demo dùng gói AWS Free Trial
($100 credit, ~184 ngày kể từ khi tạo tài khoản) — có thể bị dừng/xoá bất cứ
lúc nào, IP sẽ đổi nếu instance khởi động lại (chưa gắn Elastic IP).

## 5. Giới hạn đã biết — KHÔNG được coi là production-ready

- Không có HTTPS/domain. `ADMIN_COOKIE_SECURE=false` cố ý để khớp HTTP.
- Security group mở `0.0.0.0/0` cho cổng 80/443/8900; SSH (22) giới hạn theo
  IP đã SSH lúc tạo máy — sẽ chặn nếu đổi mạng, phải sửa lại rule SSH.
- Database Drupal là ảnh chụp một lần, không có cơ chế sync/backup định kỳ.
- Không đụng gì tới các quyết định đo lường ở `technical-debt.md` mục 8 — đây
  thuần tuý là hạ tầng demo, không phải một lượt production pilot có ý nghĩa
  đo lường.

## 6. Cập nhật server đã deploy (2026-08-21)

Mục 1–5 ghi lần **dựng đầu tiên**. Mục này ghi cách **cập nhật** một server đã
chạy — trước đây không có, nên mỗi lần cập nhật lại phải dò từ đầu.

### 6.1. Việc dễ quên nhất: Console không có trong git

`multiagent/console_ui/dist/` nằm trong `.gitignore`. Server `git pull` sẽ
**không** có bản build, và `api.py` có `if _CONSOLE_DIST.is_dir()` nên nó
**lặng lẽ không mount `/console`** — app vẫn chạy, `/health` vẫn 200, chỉ có
điều không còn giao diện quản trị nào (`/admin` đã xoá 2026-08-21).

Cách làm: **dựng ở máy dev rồi copy lên**. Không cài Node trên server vì
`t3.micro` chỉ có 1 GB RAM, `vite build` dễ hết bộ nhớ.

### 6.2. Quy trình đầy đủ

**Bước 1 — ở máy dev**, dựng Console:

```bash
cd D:\drupal-multiagent-seo\multiagent\console_ui
npm run build
```

**Bước 2 — ở máy dev**, đẩy bản build lên server:

```bash
scp -i <khoa.pem> -r dist ec2-user@<IP>:~/drupal-multiagent-seo/multiagent/console_ui/
```

**Bước 3 — SSH vào server**, kéo code:

```bash
ssh -i <khoa.pem> ec2-user@<IP>
cd ~/drupal-multiagent-seo
git pull
```

**Bước 4 — cập nhật Drupal.** Bắt buộc khi có `hook_update_N` mới:

```bash
cd ~/drupal-multiagent-seo/drupal
./vendor/bin/drush updatedb --yes
./vendor/bin/drush cache:rebuild
```

Nhớ gọi `./vendor/bin/drush`, **không** phải `php vendor/bin/drush` — xem mục 3.

**Bước 5 — khởi động lại service.** Không làm thì systemd vẫn chạy code cũ
trong bộ nhớ, và mọi thứ trông như deploy thất bại:

```bash
sudo systemctl restart multiagent-api multiagent-worker
sudo systemctl status multiagent-api --no-pager | head -5
```

**Bước 6 — kiểm chứng.** Chạy ở máy dev, thay `<IP>`:

```bash
curl -s -o /dev/null -w "health   %{http_code}\n" http://<IP>:8900/health
curl -s -o /dev/null -w "console  %{http_code}\n" http://<IP>:8900/console/
curl -s -o /dev/null -w "admin    %{http_code}\n" http://<IP>:8900/admin
```

Kết quả đúng: `health 200`, `console 200`, **`admin 404`**.

`admin` trả 303 nghĩa là service **chưa khởi động lại** (bước 5 chưa xong).
`console` trả 404 nghĩa là bản build **chưa lên tới nơi** (bước 1–2 chưa xong).

### 6.3. Sau khi deploy phải kiểm bằng tay

Ba thứ dưới đây không có phép kiểm tự động nào phủ trên server:

1. Đăng nhập `/console/`, xem đủ **tám** mục menu. Thiếu mục nào nghĩa là bản
   build cũ — quay lại bước 1.
2. Vào màn **Kết nối**, bấm **Chẩn đoán kết nối** → phải đạt. Không đạt thì
   xem lại mục 2 (site_config, site_credential, service_url).
3. Trên Drupal, sửa một bài rồi lưu ở trạng thái **Needs Review** → phải **ở
   lại trang Edit**. Nhảy sang trang xem nghĩa là bước 4 chưa chạy.

