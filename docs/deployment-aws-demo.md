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

- **`t3.micro` chỉ có 913 MB RAM.** Đủ để *chạy*, không đủ để *bảo trì*: một
  lệnh `drush` nặng là máy nghẹt cả HTTP lẫn SSH (đã xảy ra 2026-08-21). Đã bật
  swap 2 GB làm giảm nhẹ, nhưng swap chậm hơn RAM nhiều lần — đây vẫn là máy
  demo, không phải máy chịu tải.
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

### 6.2. Máy chỉ có 913 MB RAM và mặc định KHÔNG có swap

Đây là thứ làm hỏng lần deploy 2026-08-21: chạy `drush updatedb` rồi
`drush cache:rebuild` liền nhau khiến máy hết bộ nhớ và **nghẹt hoàn toàn** —
mất cả HTTP lẫn SSH trong ~25 phút, phải reboot từ bảng điều khiển AWS mới cứu
được.

Dấu hiệu nhận biết: `ssh` báo **`Connection timed out during banner exchange`**.
Câu đó nghĩa là TCP vẫn tới nơi (tường lửa không chặn) nhưng máy không đủ bộ
nhớ để hoàn tất bắt tay. Đừng đi sửa security group — hãy reboot.

**Bật swap một lần, trước khi chạy bất cứ lệnh `drush` nào:**

```bash
sudo dd if=/dev/zero of=/swapfile bs=1M count=2048 status=none
sudo chmod 600 /swapfile
sudo mkswap /swapfile && sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

Dòng cuối để swap còn sau khi reboot. Đã bật ngày 2026-08-21; sau đó
`drush updatedb` chạy trôi chảy, swap chỉ dùng 1 MB — nhưng có 1 MB đó là đủ
để không nghẹt.

**Và đừng nối `drush` với nhau bằng `&&`.** Chạy từng lệnh, đợi xong hẳn. Nếu
cần `cache:rebuild` thì chạy riêng, sau `updatedb`.

### 6.3. Quy trình đầy đủ

**Thứ tự quan trọng.** Lần 2026-08-21 làm sai: `scp` bản build lên *trước* khi
`git pull`, và lệnh thất bại vì thư mục `multiagent/console_ui/` chưa hề tồn
tại trên server — server khi đó đang ở code có từ **trước** khi Console ra đời.
Phải kéo code trước để thư mục xuất hiện, rồi mới copy `dist` vào.

**Bước 1 — ở máy dev**, dựng Console:

```bash
cd D:\drupal-multiagent-seo\multiagent\console_ui
npm run build
```

**Bước 2 — SSH vào server, kéo code TRƯỚC:**

```bash
ssh -i <khoa.pem> ec2-user@<IP>
cd ~/drupal-multiagent-seo
git pull --ff-only
ls -d multiagent/console_ui        # phải thấy thư mục thì mới sang bước 3
```

**Bước 3 — ở máy dev**, giờ mới đẩy bản build lên:

```bash
cd D:\drupal-multiagent-seo\multiagent\console_ui
scp -i <khoa.pem> -r dist ec2-user@<IP>:~/drupal-multiagent-seo/multiagent/console_ui/
```

**Bước 4 — cập nhật Drupal.** Xem còn update nào chờ không (lệnh này chỉ đọc,
rất nhẹ):

```bash
cd ~/drupal-multiagent-seo/drupal
./vendor/bin/drush updatedb:status
```

Có update thì chạy — **một mình, không nối lệnh khác**:

```bash
./vendor/bin/drush updatedb --yes
```

Nhớ gọi `./vendor/bin/drush`, **không** phải `php vendor/bin/drush` — xem mục 3.
Và phải bật swap trước (mục 6.2).

**Bước 5 — khởi động lại service:**

```bash
sudo systemctl restart multiagent-api multiagent-worker
systemctl is-active multiagent-api multiagent-worker
```

Reboot máy cũng đạt cùng kết quả: hai service có `Restart=always` nên tự lên.

**Bước 6 — kiểm chứng.** Chạy ở máy dev, thay `<IP>`:

```bash
curl -s -o /dev/null -w "health   %{http_code}\n" http://<IP>:8900/health
curl -s -o /dev/null -w "console  %{http_code}\n" http://<IP>:8900/console/
curl -s -o /dev/null -w "admin    %{http_code}\n" http://<IP>:8900/admin
```

Kết quả đúng: `health 200`, `console 200`, **`admin 404`**.

| Thấy gì | Nghĩa là |
|---|---|
| `admin` trả 303 | service **chưa khởi động lại** — bước 5 chưa xong |
| `console` trả 404 | bản build **chưa lên tới nơi** — bước 1–3 chưa xong |
| Không phản hồi gì | máy đang nghẹt — xem mục 6.2, reboot |

### 6.4. `git pull` KHÔNG mang cấu hình Drupal lên

Bẫy nguy hiểm vì nó **trông giống deploy hỏng** trong khi mọi bước đều đúng.

Đã xảy ra 2026-08-21: sau khi deploy xong, trang chủ server vẫn hiện theme mặc
định Olivero với tên site "Drush Site-Install", trong khi máy dev hiện giao
diện VinFast. Không có lỗi nào, không có gì trong log.

Nguyên nhân: `git pull` mang **file** lên, nhưng ở Drupal những thứ dưới đây
nằm trong **database**, không nằm trong git:

- theme nào đang bật, theme nào mặc định
- module nào bật/tắt
- tên site, trang chủ, ngôn ngữ mặc định
- toàn bộ nội dung bài viết

Mà database server là **bản chụp một lần** từ `ddev export-db` ngày 16/08 (mục
1) — nó không biết `vinfast_theme` tồn tại, vì theme đó ra đời sau.

**Sau mỗi lần deploy có thêm theme hoặc module mới**, phải bật bằng tay:

```bash
cd ~/drupal-multiagent-seo/drupal
./vendor/bin/drush theme:enable vinfast_theme
./vendor/bin/drush config:set system.theme default vinfast_theme --yes
./vendor/bin/drush cache:rebuild
```

Kiểm lại:

```bash
./vendor/bin/drush php:eval "print \Drupal::config('system.theme')->get('default') . PHP_EOL;"
```

Rồi mở trang chủ bằng **Ctrl+Shift+R** — F5 thường có thể vẫn dùng CSS cũ trong
bộ nhớ đệm trình duyệt.

**Nội dung bài viết thì không đồng bộ được** bằng cách nào ngoài export/import
cả database. Server và máy dev là hai bản riêng biệt và sẽ ngày càng lệch —
đây là giới hạn đã biết của máy demo, không phải lỗi.

### 6.5. Sau khi deploy phải kiểm bằng tay

Ba thứ dưới đây không có phép kiểm tự động nào phủ trên server:

1. Đăng nhập `/console/`, xem đủ **tám** mục menu. Thiếu mục nào nghĩa là bản
   build cũ — quay lại bước 1.
2. Vào màn **Kết nối**, bấm **Chẩn đoán kết nối** → phải đạt. Không đạt thì
   xem lại mục 2 (site_config, site_credential, service_url).
3. Trên Drupal, sửa một bài rồi lưu ở trạng thái **Needs Review** → phải **ở
   lại trang Edit**. Nhảy sang trang xem nghĩa là bước 4 chưa chạy.
4. Mở trang chủ Drupal (`http://<IP>`) → phải thấy **giao diện VinFast**, không
   phải Olivero mặc định. Thấy Olivero nghĩa là theme chưa bật — xem mục 6.4.

### 6.6. Nhật ký lần deploy 2026-08-21

Lần đầu dùng quy trình này, để lần sau biết thực tế mất bao lâu và vấp ở đâu.

Server chậm **137 commit** (code từ 16–17/08, trước cả khi Console tồn tại).
Không có migration Postgres mới, không đổi `requirements.txt`, không đổi config
Drupal — nên phần Python chỉ cần `git pull` rồi restart.

Vấp hai lần, cả hai đã ghi thành mục 6.2 và 6.3:

1. `scp` trước `git pull` → thất bại vì thư mục chưa tồn tại.
2. `drush updatedb` + `cache:rebuild` liền nhau → máy nghẹt ~25 phút, phải
   reboot. Sau khi bật swap thì chạy trôi chảy.
3. Deploy xong nhưng trang chủ vẫn hiện theme Olivero mặc định — tưởng deploy
   hỏng, thực ra `vinfast_theme` chưa được bật trong database (mục 6.4).

Tổng thời gian ~40 phút, trong đó 25 phút là do sự cố ở mục 2. Nếu bật swap
trước, làm đúng thứ tự, và nhớ bật theme thì khoảng 10 phút.

