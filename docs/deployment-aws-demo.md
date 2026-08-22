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

**Địa chỉ hiện tại (từ 2026-08-21, sau khi bật HTTPS — xem mục 7):**

- Drupal: `https://vf-multiagent.duckdns.org`
- Console: `https://vf-multiagent.duckdns.org/console/`

**Địa chỉ cũ, giữ lại làm bản ghi:**

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
- ~~Không có HTTPS/domain~~ — **đã có từ 2026-08-21** (mục 7):
  `vf-multiagent.duckdns.org`, chứng chỉ Let's Encrypt, `ADMIN_COOKIE_SECURE=true`.
  Nhưng tên miền là **DuckDNS miễn phí**, không phải miền của tổ chức; và IP sẽ
  đổi nếu instance bị Stop rồi Start (reboot thì không), lúc đó phải cập nhật
  lại bản ghi DuckDNS.
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

### 6.7. Đưa ba bài demo lên server

Ba bài dùng để demo (`C-008` publish, `G-014` needs_revision, `G-010` rejected)
được dựng lại bằng script, **không tạo tay** — tạo tay thì nội dung hai bên lệch
nhau và kết quả chấm không so sánh được.

**Nguồn dữ liệu:** [`drupal/scripts/demo-articles.json`](../drupal/scripts/demo-articles.json)
— bản chụp nguyên văn ba bài, gồm cả `src` ảnh mà CKEditor đã chèn.

> **Vì sao không đọc thẳng `docs/goldset/raw/*.txt`:** sau khi chèn ảnh,
> CKEditor viết lại body (thêm `data-entity-uuid`, đổi độ dài từ 14.086 lên
> 18.954 ký tự ở `G-014`). File `.txt` vẫn là nguồn chuẩn cho việc **chấm
> điểm**; JSON là bản chụp của **ba bài đã chuẩn bị để demo**.

**Ảnh phải chép sang TRƯỚC.** 21 file, khoảng 5 MB, nằm trong
`web/sites/default/files/` — thư mục bị `.gitignore` loại khỏi repo (dòng 34
`drupal/web/*`), nên `git pull` **không** mang chúng lên. Chép thiếu thì bài vẫn
tạo được nhưng thẻ `<img>` trỏ vào file không tồn tại.

Gom ảnh ở máy dev (script đọc `demo-articles.json`, chỉ lấy đúng file được
tham chiếu):

```bash
# tao thu muc demo-images/ o goc repo
python scripts_gom_anh.py   # hoac gom tay theo src trong demo-articles.json
scp -i <khoa.pem> -r demo-images/* \
    ec2-user@<IP>:~/drupal-multiagent-seo/drupal/web/sites/default/files/
```

Rồi trên server:

```bash
cd ~/drupal-multiagent-seo
git pull --ff-only
cd drupal
drush php:script scripts/seed_demo_articles.php
```

Script **chạy lại được nhiều lần**: bài đã tồn tại (khớp `title`) thì bỏ qua,
không tạo bản trùng. Nếu thiếu file ảnh đại diện nó in cảnh báo
`[!] thieu file anh dai dien` chứ không im lặng.

**Bài được tạo ở trạng thái `draft` và không có báo cáo AI** — cố ý, để lúc demo
tự chuyển sang "Needs Review" và chấm ngay trước mặt người xem. Muốn vậy thì
service và worker trên server phải đang chạy (mục 6.3).

## 7. Bật HTTPS (2026-08-21)

Trước ngày này server chạy HTTP trần, `ADMIN_COOKIE_SECURE=false` cố ý để khớp.
Mục này ghi lại cách bật HTTPS và **bốn thứ phải đổi kèm** — bỏ sót một cái là
hệ thống hỏng, mà ba trong bốn cái hỏng **im lặng**.

### 7.1. Bắt buộc phải có tên miền

Let's Encrypt **không cấp chứng chỉ cho địa chỉ IP trần**. Phải có một tên.

Đang dùng **DuckDNS** (miễn phí): `vf-multiagent.duckdns.org` → `18.142.116.87`.
Tài khoản đăng nhập bằng Google, quản lý tại [duckdns.org](https://www.duckdns.org).

Cạm bẫy khi tạo: DuckDNS **tự điền IP của máy bạn đang ngồi**, không phải IP
server. Phải sửa tay thành IP EC2 rồi bấm *update ip*. Để nguyên thì Let's
Encrypt gửi yêu cầu xác minh về máy cá nhân, không ai trả lời, và từ chối cấp.

Kiểm trước khi xin chứng chỉ:

```bash
nslookup vf-multiagent.duckdns.org 8.8.8.8   # phải ra IP của EC2
```

### 7.2. Bốn thứ phải đổi kèm

**(1) Drupal `trusted_host_patterns` — hỏng ngay, dễ thấy**

`web/sites/default/settings.php` chỉ liệt kê IP, `127.0.0.1`, `localhost`. Gọi
qua tên miền mới sẽ nhận **400 Bad Request**. Đây là cơ chế chống giả mạo Host
header, không phải lỗi. Thêm tên miền vào mảng:

```php
$settings['trusted_host_patterns'] = [
  '^vf-multiagent\.duckdns\.org$',
  '^18\.142\.116\.87$',
  ...
];
```

**(2) Cổng 8900 phải vào sau nginx — hỏng im lặng**

uvicorn phục vụ Console/API thẳng ở cổng 8900, không qua nginx. Chứng chỉ gắn
vào nginx nên nó **không** bảo vệ cổng đó.

Nếu bật `ADMIN_COOKIE_SECURE=true` mà Console vẫn chạy HTTP, trình duyệt từ
chối gửi cookie "chỉ dành cho HTTPS" — **đăng nhập xong lại quay về trang đăng
nhập**, không lỗi nào hiện ra.

Cách làm: cho nginx đứng trước cả hai.

```nginx
location ^~ /console      { proxy_pass http://127.0.0.1:8900; include .../proxy-headers.inc; }
location ^~ /api/console  { proxy_pass http://127.0.0.1:8900; include .../proxy-headers.inc; }
location ^~ /api/v1       { proxy_pass http://127.0.0.1:8900; include .../proxy-headers.inc; }
location = /health        { proxy_pass http://127.0.0.1:8900; include .../proxy-headers.inc; }
```

**`^~` là bắt buộc.** Không có nó, quy tắc regex `\.(js|css|gif|jpe?g|png)$`
của Drupal sẽ nuốt file tĩnh của Console và đi tìm trong docroot Drupal → 404,
Console trắng trang.

Xong thì **đóng cổng 8900** trong security group: nginx gọi qua loopback nên
không cần mở ra ngoài nữa, và đóng lại thì không còn đường vòng qua HTTP.

**(3) `--forwarded-allow-ips` cho uvicorn — hỏng im lặng, nguy hiểm nhất**

Đặt nginx ở giữa khiến `request.client.host` thành `127.0.0.1` cho **mọi**
request. `admin_api/auth_routes.py::_client_ip()` đọc thẳng giá trị đó, nên:

- cơ chế chặn dò mật khẩu gộp tất cả mọi người vào **một rổ** — một người gõ
  sai vài lần là khoá cả hệ thống
- mất hoàn toàn giá trị truy vết theo IP

Sửa trong `/etc/systemd/system/multiagent-api.service`:

```
ExecStart=... uvicorn api:app --host 0.0.0.0 --port 8900 --app-dir src \
  --proxy-headers --forwarded-allow-ips=127.0.0.1
```

Giới hạn `127.0.0.1` là quan trọng: uvicorn chỉ tin `X-Forwarded-For` khi
request đến **từ chính nginx**. Request từ ngoài vào thẳng cổng 8900 không được
tin, nên không ai giả mạo IP được.

Và nginx phải thực sự gửi header đó (`proxy-headers.inc`):

```nginx
proxy_set_header Host $host;
proxy_set_header X-Real-IP $remote_addr;
proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
proxy_set_header X-Forwarded-Proto $scheme;
```

Kiểm chứng — nhật ký uvicorn phải ghi IP THẬT, không phải 127.0.0.1:

```bash
sudo journalctl -u multiagent-api --since "5 min ago" | grep auth/login | tail -3
```

**(4) `ADMIN_COOKIE_SECURE=true` trong `.env`**

Đổi rồi `systemctl restart multiagent-api`. Sao lưu `.env` trước: nếu đăng nhập
Console hỏng thì lùi về `false` là cách khôi phục nhanh nhất.

### 7.3. Cái KHÔNG được đổi

`DRUPAL_BASE_URL` và `base_url` của site trong Postgres đang là
`http://127.0.0.1` — **giữ nguyên**. Đó là lưu lượng loopback trong máy, không
ra ngoài, và chứng chỉ chỉ hợp lệ cho tên miền chứ không cho `127.0.0.1`. Đổi
sang `https://` sẽ làm worker không gọi được Drupal.

### 7.4. Lệnh xin chứng chỉ

```bash
sudo dnf install -y certbot python3-certbot-nginx
sudo sed -i 's/server_name _;/server_name vf-multiagent.duckdns.org;/' /etc/nginx/conf.d/drupal.conf
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d vf-multiagent.duckdns.org \
  --non-interactive --agree-tos --email <email> --redirect
```

certbot tự sửa nginx cho cổng 443, tự thêm chuyển hướng HTTP→HTTPS, và tự đặt
lịch gia hạn. Chứng chỉ hiện tại hết hạn **2026-11-19**.

Nhớ mở cổng **443** trong security group trước.

### 7.5. Kiểm chứng sau khi bật

```bash
D=https://vf-multiagent.duckdns.org
curl -s -o /dev/null -w "%{http_code}\n" $D              # 200 Drupal
curl -s -o /dev/null -w "%{http_code}\n" $D/console/     # 200 Console
curl -s -o /dev/null -w "%{http_code}\n" $D/health       # 200
curl -s -o /dev/null -w "%{http_code} %{redirect_url}\n" http://vf-multiagent.duckdns.org  # 301
```

Và ba thứ chỉ kiểm được bằng tay:

1. Tải một file JS của Console (`/console/assets/*.js`) → phải trả `200` với
   `content-type: application/javascript`, không phải HTML của Drupal.
2. **Đăng nhập Console** → phải vào được. Quay về trang đăng nhập nghĩa là
   cookie `Secure` không qua được (mục 7.2 phần 2 hoặc 4).
3. Nhật ký uvicorn ghi IP thật (mục 7.2 phần 3).
