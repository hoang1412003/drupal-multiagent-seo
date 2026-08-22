# Sổ tay vận hành

Tài liệu này trả lời đúng ba câu hỏi khi hệ thống **đang chạy**: khởi động thế
nào, biết nó khoẻ hay hỏng bằng cách nào, và khi hỏng thì sửa ở đâu.

**Đây không phải tài liệu thiết kế.** Muốn biết *vì sao* hệ thống được dựng như
vậy thì đọc:

| Cần gì | Đọc file nào |
|---|---|
| Vì sao ghi nhật ký truy vết, vòng phản hồi người duyệt | [`operations.md`](operations.md) |
| Kiến trúc Multi-Agent, 4 agent, Aggregator | [`architecture.md`](architecture.md) |
| Việc phải làm ngay trước buổi demo | [`pre-demo-checklist.md`](pre-demo-checklist.md) |
| Chạy trên máy chủ thật (EC2), bật HTTPS | [`deployment-aws-demo.md`](deployment-aws-demo.md) |
| Nợ kỹ thuật, giới hạn đã biết, trạng thái bàn giao | [`technical-debt.md`](technical-debt.md) |

---

## 1. Hệ thống gồm bốn tiến trình

Thiếu bất kỳ cái nào cũng làm hỏng một phần, nhưng **phần lớn hỏng theo kiểu im
lặng** — không có thông báo lỗi nào cho người soạn bài. Đó là lý do mục 4 quan
trọng hơn vẻ ngoài của nó.

| Tiến trình | Việc của nó | Thiếu thì sao |
|---|---|---|
| **Drupal** (DDEV) | nơi người viết soạn bài, hiển thị báo cáo AI | không có gì để chấm |
| **Postgres** (Docker) | hàng đợi job, nhật ký chấm, kho vector của KB | service và worker đều không khởi động được |
| **`api.py`** | nhận job từ Drupal, phục vụ Console `/console` | bài không vào hàng đợi ngay; phải chờ vòng đối soát 300 giây |
| **`worker.py`** | lấy job ra, gọi 4 agent, ghi kết quả ngược về Drupal | job nằm im trong hàng đợi mãi mãi |

Hai tiến trình cuối phải chạy **song song, mỗi cái một cửa sổ terminal riêng**.
Chúng không tự khởi động cùng nhau.

---

## 2. Khởi động từ đầu

Đúng thứ tự này. Mỗi bước giải thích ngay bên dưới lệnh.

**Bước 1 — bật cơ sở dữ liệu**

```
cd multiagent
docker compose up -d
```
*Khởi động Postgres trong Docker, chạy nền. `-d` nghĩa là chạy ngầm, không
chiếm cửa sổ terminal.*

**Bước 2 — bật Drupal**

```
cd drupal
ddev start
```
*Khởi động toàn bộ container của Drupal (web + database riêng của nó). Lần đầu
chạy có thể mất vài phút.*

**Bước 3 — bật service**

```
cd multiagent
.venv\Scripts\python.exe -m uvicorn api:app --port 8900 --app-dir src
```
*Chạy máy chủ HTTP nhận job từ Drupal, ở cổng 8900. **Cửa sổ này phải để mở** —
đóng là service tắt.*

**Bước 4 — bật worker, ở cửa sổ terminal KHÁC**

```
cd multiagent
.venv\Scripts\python.exe src\worker.py
```
*Chạy vòng lặp liên tục lấy job ra chấm. **Cửa sổ này cũng phải để mở.***

Muốn dừng: bấm `Ctrl + C` ở cửa sổ của service và worker, rồi `ddev stop` và
`docker compose stop`.

> Máy mới hoàn toàn (chưa từng chạy dự án) thì trước bước 3 còn phải chạy
> migration, dựng lại KB và nạp credential. Xem [`README.md`](../README.md) mục
> Setup và [`pre-demo-checklist.md`](pre-demo-checklist.md) mục 2.

---

## 3. Kiểm tra sức khoẻ

**Service còn sống không:**

```
curl http://127.0.0.1:8900/health
```
*Gọi thử vào service để xem nó có trả lời không. Endpoint này **không cần mật
khẩu**.*

Trả về dạng:

```json
{"ok":true,"queued":0,"running":0,"failed":2}
```

Đọc ba con số:

| Trường | Nghĩa | Đáng lo khi |
|---|---|---|
| `queued` | job đang chờ được chấm | tăng dần mà không giảm → worker chết |
| `running` | job đang chấm dở | nằm im ở một số > 0 rất lâu → worker treo giữa chừng |
| `failed` | job đã bỏ cuộc sau nhiều lần thử | tăng lên sau khi demo → có lỗi thật, đi xem nhật ký |

Không kết nối được nghĩa là service chưa chạy hoặc đã tắt.

**Drupal còn sống không:**

```
cd drupal
ddev describe
```
*In trạng thái các container. Cột `STAT` phải là `running`; `exited` là đã tắt.*

**Cơ sở dữ liệu còn sống không:**

```
cd multiagent
docker compose ps
```
*Cột `STATUS` phải có chữ `healthy`.*

---

## 4. Sổ tay sự cố

Xếp theo mức hay gặp. Mỗi mục: **triệu chứng → nguyên nhân → cách kiểm → cách sửa.**

### 4.1. Bài chuyển sang Needs Review nhưng không thấy báo cáo AI

Đi lần lượt, đừng nhảy cóc:

1. **Worker có chạy không?** Nhìn cửa sổ terminal của `worker.py`. Không chạy
   thì job nằm im trong hàng đợi.
2. **Job có vào hàng đợi không?** Gọi `/health` xem `queued` có tăng.
3. **`queued` vẫn bằng 0** → job chưa hề được tạo. Sang mục 4.2.
4. **`queued` tăng nhưng không giảm** → worker chết hoặc không kết nối được
   database. Xem thông báo lỗi ở cửa sổ worker.

### 4.2. Báo cáo hiện CHẬM vài phút thay vì vài giây — bẫy nguy hiểm nhất

**Triệu chứng:** bài vẫn được chấm, chỉ chậm. Nhìn bên ngoài giống "hệ thống
chạy đúng, hơi chậm thôi".

**Thực tế:** đường chính (Drupal gọi thẳng service, ~2 giây) đang **hỏng hoàn
toàn**, và bài chỉ được chấm nhờ vòng đối soát định kỳ 300 giây — vốn là lưới an
toàn, không phải đường chính. Drupal **không hiện lỗi gì** cho người soạn bài.

**Nguyên nhân thường gặp nhất:** chuỗi bí mật `VF_SERVICE_TOKEN` ở hai nơi
không giống nhau, nên mọi request bị trả 401.

**Cách kiểm:**

```
cd drupal
ddev drush watchdog:show
```
*In nhật ký lỗi của Drupal. Tìm dòng 401 đến từ `vf_ai_trigger`.*

**Cách sửa:** chuỗi bí mật phải **giống hệt nhau** ở hai chỗ:

1. `.env` — dòng `VF_SERVICE_TOKEN=`
2. `drupal/web/sites/default/settings.php` — `$settings['vf_ai_service_token']`

Sinh chuỗi mới bằng:

```
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```
*In ra một chuỗi ngẫu nhiên đủ dài để làm mật khẩu. Dán **cùng một chuỗi** vào
cả hai file.*

Từ P4 còn cần credential riêng theo site — thiếu thì `/api/v1/jobs` trả 401 y
hệt. Xem [`pre-demo-checklist.md`](pre-demo-checklist.md) mục 2c.

### 4.3. "Test connection" báo đạt nhưng ghi kết quả ngược về vẫn hỏng

**Nguyên nhân:** tài khoản tích hợp đang là **UID 1** (tài khoản `admin` đầu
tiên của Drupal). Drupal cho UID 1 **bỏ qua mọi kiểm tra quyền**, nên phép thử
nào cũng xanh dù role cấu hình sai hoàn toàn.

**Cách kiểm — hai bước.** Bước 1, xem phía Python đang dùng tài khoản nào:

```
grep "^DRUPAL_USER=" .env
```
*In tên tài khoản mà hệ Multi-Agent dùng để gọi sang Drupal.*

Bước 2, xem tài khoản đó là số mấy và mang role gì bên Drupal:

```
cd drupal
ddev drush php:eval "\$u=user_load_by_name('ai_service'); print \$u ? 'uid='.\$u->id().' roles='.implode(',',\$u->getRoles()) : 'khong tim thay';"
```
*Thay `ai_service` bằng tên lấy được ở bước 1. Kết quả đúng phải dạng
`uid=13 roles=authenticated,ai_service` — **`uid=1` là sai**, và `uid=0` nghĩa
là không tìm thấy tài khoản đó.*

> Đừng gộp hai bước bằng `getenv('DRUPAL_USER')` trong `php:eval`: lệnh đó chạy
> **bên trong container Drupal**, nơi không có `.env` của phía Python, nên nó
> luôn trả về `0` — trông y hệt như tài khoản không tồn tại.

**Cách sửa:** dùng một tài khoản riêng chỉ mang role `ai_service`:

```
ddev drush php:script scripts/configure_ai_service_role.php -- --apply
ddev drush php:script scripts/test_ai_service_role.php
```
*Lệnh đầu tạo/cập nhật role `ai_service` với đúng bảy quyền. Lệnh sau kiểm lại
role đó. Lưu ý: nó chỉ kiểm **role**, không kiểm role đã gán cho ai — phải tự
kiểm bằng lệnh ở trên.*

### 4.4. Tạo bài qua API bị trả 403

**Đây không phải lỗi.** Role `ai_service` có đúng bảy quyền và **không có quyền
tạo bài** — cố ý, theo nguyên tắc quyền tối thiểu. Nó chỉ được đọc nội dung và
ghi kết quả AI.

**Đừng nới quyền cho role này chỉ để nạp dữ liệu mẫu.** Tạo bài bằng drush, vốn
chạy với quyền quản trị bên trong container:

```
cd drupal
ddev drush php:script /var/www/html/<duong-dan>/script.php
```

> Trên Git Bash (Windows), đường dẫn kiểu Linux bị tự đổi thành đường dẫn
> Windows và lệnh sẽ báo không tìm thấy file. Thêm `MSYS_NO_PATHCONV=1` vào
> trước lệnh để tắt việc đó.

### 4.5. Ẩn bài không có tác dụng — bài vẫn hiện

**Triệu chứng:** đã gọi `setUnpublished()` và `save()`, lệnh chạy không báo lỗi,
nhưng bài vẫn ở trạng thái xuất bản.

**Nguyên nhân:** content type Article đang bật **Content Moderation**. Khi đó
`status` là giá trị **dẫn xuất** từ `moderation_state` — đặt `status` trực tiếp
sẽ bị ghi đè lúc lưu, im lặng.

**Cách kiểm:**

```
ddev drush php:eval '$n=\Drupal\node\Entity\Node::load(21); printf("status=%s moderation=%s\n", $n->isPublished()?"hien":"an", $n->get("moderation_state")->value);'
```
*In cả hai giá trị cạnh nhau. `status=hien` trong khi bạn vừa ẩn nó nghĩa là
đang dính đúng bẫy này.*

**Cách sửa:** đổi `moderation_state` (`draft` / `archived`), đừng đụng `status`.

### 4.6. Lọc bài theo trạng thái duyệt không ra kết quả

`moderation_state` là field **tính toán**, không query được bằng entity query
lẫn `filter[]` của JSON:API. Dự án đã vấp **hai lần**, và cả hai lần chỉ lộ ra
khi gọi HTTP thật — test offline không bắt được.

**Cách làm đúng:** lọc thô bằng `vid`/`status` ở SQL trước, rồi lọc tinh bằng
code.

### 4.7. KB rỗng hoặc truy vấn RAG không ra gì

KB là **dữ liệu dẫn xuất, không nằm trong git**. Máy mới phải dựng lại:

```
cd multiagent
.venv\Scripts\python.exe scripts\migrate.py apply
.venv\Scripts\python.exe src\kb\build_kb.py
.venv\Scripts\python.exe src\kb\build_brand_kb.py
```
*Lệnh 1 tạo bảng trong database. Lệnh 2 dựng KB thông số kỹ thuật (4 chunk,
nhanh). Lệnh 3 dựng KB brand (1128 chunk, mất vài phút).*

### 4.8. Giao diện báo cáo trong trang soạn bài hiển thị sai

Module `vf_ai_review` **không có bộ kiểm tự động nào**. Sửa `js/vf_ai_review.js`
là phải mở trình duyệt kiểm lại bằng mắt.

Bốn cái bẫy đã gặp — **cả bốn đều im lặng, không test nào bắt được** — ghi ở
[`editor-ui-design.md` mục 10.6](editor-ui-design.md). Đáng nhớ nhất: dùng
`#markup` thì Drupal nuốt mất thẻ `<input>` và `<label>` không báo gì.

Test phần PHP thì có:

```
cd drupal
ddev exec php scripts/test_ai_report_renderer.php
```

---

## 5. Việc định kỳ

**Chạy toàn bộ bộ kiểm** (91 file, phải ra 0 hỏng 0 bỏ qua):

```
cd multiagent
.venv\Scripts\python.exe scripts\run_test_group.py all-offline
```
*Chạy hết test không tốn tiền API. `[SKIP]` **không** được tính là đạt — test bị
bỏ qua vì thiếu dịch vụ là dấu hiệu môi trường chưa dựng đủ.*

**Sao lưu và khôi phục:** quy trình đã diễn tập, ghi ở
[`operations.md` mục 6.5](operations.md).

---

## 6. Ai được làm gì

Hai hệ thống tài khoản **tách biệt**, không tự ánh xạ sang nhau:

| Hệ | Vai trò | Được làm gì |
|---|---|---|
| Drupal | `content_editor` | người viết bài — cũng là người tự duyệt |
| Drupal | `ai_service` | tài khoản máy: đọc nội dung, ghi kết quả AI. **Bảy quyền, không hơn** |
| Multi-Agent | `viewer` | chỉ xem Console |
| Multi-Agent | `operator` | xem + chạy lại job |
| Multi-Agent | `admin` | thêm quản lý người dùng, xem nhật ký kiểm toán |

Người viết bài **không cần và không nên** được cấp tài khoản Multi-Agent chỉ để
gửi bài đi chấm.

---

## 7. Những việc không được làm

**Không sửa đường chấm điểm nếu không chủ đích.** `prompt_version` được tính
bằng cách băm nguyên file, nên sửa một dòng prompt cũng làm **mất hiệu lực toàn
bộ kết quả đo đã có**. Đường chấm điểm gồm: 4 agent, prompt, `fact_check.py`,
`scoring.py`, Aggregator, rule, KB và `scoring.yaml`.

**Không tự chạy script đo tốn tiền.** Các script `eval_*` gọi API trả phí và
phải có người xác nhận từng lượt. Đường trả phí có **ba lớp khoá** — token xác
nhận, biến môi trường `VF_ALLOW_PAID_EVAL`, và chốt chặn không cho ghi tiếp vào
file kết quả của bản code cũ. Cả ba đều cố ý.

**Không nói ngưỡng đã được calibrate.** `scoring.yaml` ghi
`meta.calibrated: false`, và đó là sự thật: ngưỡng `publish_min = 80` là giá trị
minh hoạ, chưa chốt được từ gold set. Cách trình bày đúng ghi ở
[`pre-demo-checklist.md` mục 3](pre-demo-checklist.md).
