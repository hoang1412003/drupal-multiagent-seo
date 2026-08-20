# Console UI — hệ thống thiết kế

**Ngày:** 2026-08-20 · **Ảnh tham chiếu:** [`reference/jobs-list.png`](reference/jobs-list.png)

Tài liệu này thay cho việc thiết kế từng màn hình. Ảnh tham chiếu là **chuẩn
về hình thức**; tài liệu này chốt những gì ảnh không nói được: chế độ tối,
trạng thái hover, hành vi khi màn hình hẹp, và công thức class cụ thể để bảy
màn hình không lệch nhau.

**Thứ tự ưu tiên khi hai nguồn mâu thuẫn:**

1. `openapi.json` — tên trường, kiểu dữ liệu. Luôn đúng.
2. `stitch-briefs.md` — màn hình nào có cột nào, cấm cái gì.
3. Tài liệu này — hình thức.
4. Ảnh tham chiếu — hình thức, khi tài liệu này không nói rõ.

## 1. Khung trang

```
┌──────────────┬────────────────────────────────────────────────────┐
│ AI Review    │              admin · admin  Đổi mật khẩu  Đăng xuất│
│ Platform     ├────────────────────────────────────────────────────┤
│              │                                                    │
│ ▸ Tổng quan  │   Job Queue                                        │
│ ▪ Jobs       │   Giám sát và quản lý các tác vụ xử lý hàng loạt.   │
│ ▸ Reviews    │                                                    │
│              │   ┌──────────── thẻ bộ lọc ─────────────────────┐   │
│              │   └─────────────────────────────────────────────┘   │
│              │   ┌──────────── thẻ bảng ───────────────────────┐   │
│              │   └─────────────────────────────────────────────┘   │
└──────────────┴────────────────────────────────────────────────────┘
```

- **Sidebar** rộng cố định `w-56` (224px), nền trắng, viền phải hairline.
  Không thu gọn được, không có nút toggle.
- **Đúng ba mục điều hướng**: Tổng quan · Jobs · Reviews. Mỗi mục có một icon
  đơn sắc bên trái. Xem `stitch-briefs.md` khối `NAVIGATION` — danh sách những
  mục **cấm** thêm nằm ở đó.
- **Thanh trên** chỉ chứa, canh phải: `username · role`, link "Đổi mật khẩu",
  nút "Đăng xuất". Không chuông thông báo, không icon trợ giúp, không avatar
  menu.
- **Vùng nội dung** nền `bg-surface`, padding `p-6`, các thẻ trắng xếp dọc
  cách nhau `gap-4`.

## 2. Bảng màu

Token đã khai báo sẵn trong `console_ui/src/index.css` khối `@theme`. Dùng qua
class Tailwind (`bg-vf`, `text-ink`, …), **không viết hex trực tiếp trong
component**.

| Vai trò | Sáng | Tối | Ghi chú |
|---|---|---|---|
| Nền trang | `#f9f9f9` | `#111314` | |
| Nền thẻ | `#ffffff` | `#1a1c1c` | |
| Chữ chính | `#1a1c1c` | `#e8e9e9` | |
| Chữ phụ | `#6b7280` | `#9ca3af` | nhãn bảng, chú thích |
| Viền | `#e5e7eb` | `#2f3131` | hairline, 1px |
| Hành động chính | `#00237a` | `#3b5bdb` | navy đậm quá tối cho nền tối |

**Kỷ luật màu:** navy chỉ dùng cho **một** hành động chính mỗi màn hình. Mọi
thứ khác là xám trung tính. Màu duy nhất còn lại là màu ngữ nghĩa của trạng
thái, và chỉ hiện dưới dạng pill.

## 3. Màu ngữ nghĩa của trạng thái

| Giá trị | Nhãn tiếng Việt | Chấm | Nền pill | Chữ pill |
|---|---|---|---|---|
| `queued` | Trong hàng đợi | `bg-amber-500` | `bg-amber-50` | `text-amber-700` |
| `running` | Đang chạy | `bg-blue-500` | `bg-blue-50` | `text-blue-700` |
| `done` | Hoàn thành | `bg-emerald-500` | `bg-emerald-50` | `text-emerald-700` |
| `failed` | Thất bại | `bg-red-500` | `bg-red-50` | `text-red-700` |
| `superseded` | Bị thay thế | `bg-gray-400` | `bg-gray-100` | `text-gray-600` |

Quyết định review dùng cùng khuôn pill:

| Giá trị | Nhãn | Màu |
|---|---|---|
| `publish` | Xuất bản | emerald |
| `needs_revision` | Cần sửa | amber |
| `rejected` | Từ chối | red |
| `unknown` | Chưa rõ | gray |

Trạng thái ghi ngược (`writeback_statuses`) cũng phải có nhãn tiếng Việt —
đừng để nguyên chuỗi tiếng Anh giữa một giao diện tiếng Việt:

| Giá trị | Nhãn |
|---|---|
| `succeeded` | Thành công |
| `failed` | Thất bại |
| `superseded` | Bị thay thế |
| `pending` | Đang chờ |
| `unknown` | Chưa rõ |

Trạng thái worker — **ba giá trị, và màu phải phản ánh mức độ nghiêm trọng**:

| Giá trị | Nhãn | Màu | Vì sao |
|---|---|---|---|
| `running` | Đang chạy | emerald | bình thường |
| `stale` | Mất tín hiệu | **red** | từng chạy rồi im lặng — đây mới là sự cố |
| `unavailable` | Chưa từng chạy | **gray** | chưa bao giờ khởi động, chưa chắc là sự cố |

Để `unavailable` màu đỏ sẽ báo động giả mỗi khi worker chỉ đơn giản là chưa bật.

**Lấy giá trị từ `GET /filters`, đừng viết cứng danh sách.** Bảng trên chỉ ánh
xạ giá trị sang màu và nhãn; bản thân danh sách giá trị đến từ API. Xem
`integration.md` mục 5.

## 4. Công thức class

Chép nguyên, đừng tự chế biến thể. Bảy màn hình dùng chung mới đồng nhất.

**Thẻ (card)**
```
rounded-lg border border-gray-200 bg-white
dark:border-gray-800 dark:bg-[#1a1c1c]
```

**Tiêu đề trang**
```
text-xl font-semibold text-ink dark:text-gray-100
```
kèm một dòng mô tả `text-sm text-gray-500` ngay dưới.

**Nhãn ô lọc** — chữ nhỏ, in hoa, xám, nằm **trên** ô nhập
```
mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500
```

**Ô nhập / select**
```
h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm
focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20
dark:border-gray-700 dark:bg-[#111314]
```

**Nút chính** (một cái mỗi màn hình)
```
h-9 rounded-md bg-vf px-4 text-sm font-medium text-white
hover:bg-vf-hover focus:outline-none focus:ring-2 focus:ring-vf/30
disabled:opacity-50 disabled:cursor-not-allowed
```

**Nút phụ** (Đặt lại, Hủy)
```
h-9 rounded-md border border-gray-300 bg-white px-4 text-sm
hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent
```

**Đầu bảng**
```
border-b border-gray-200 bg-gray-50/60
px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500
dark:border-gray-800 dark:bg-white/5
```

**Ô trong bảng**
```
border-b border-gray-100 px-3 py-2.5 text-sm
dark:border-gray-800
```
Không kẻ dọc. Không sọc xen kẽ. Phân cách bằng hairline ngang.

**Pill trạng thái**
```
inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium
```
kèm một chấm `h-1.5 w-1.5 rounded-full` phía trước.

**Cột mã và số** — monospace, số canh phải
```
font-mono text-xs           (mã job, ID nội dung)
text-right tabular-nums     (số lần thử, điểm)
```

## 4b. Định dạng dữ liệu — dùng hàm chung, không tự viết

Mọi hàm định dạng nằm trong `console_ui/src/lib/format.ts`. **Không viết lại ở
từng trang** — bảy màn hình mỗi trang một kiểu là cách nhanh nhất để cùng một
job hiện hai giờ khác nhau ở hai chỗ.

| Hàm | Dùng cho | Ví dụ |
|---|---|---|
| `formatDateTime(iso)` | mọi cột thời gian | `19/08/2026 14:32` |
| `formatDate(iso)` | ngày không giờ (`date_from`, `effective_at`) | `19/08/2026` |
| `formatNumber(n, digits)` | `final_score`, tỷ lệ, percentile | `40.9` |
| `shortId(uuid)` | `public_id`, `correlation_id` | `a3f2…9c41` |

Cả bốn hàm trả `"—"` khi giá trị là `null`. **Không bao giờ hiện `0` thay cho
`null`** — `final_score` null nghĩa là chưa chấm được, khác hẳn chấm được 0
điểm.

**Múi giờ.** API luôn trả UTC. Console hiện **giờ Việt Nam** vì người vận hành
đọc giờ VN. Nhưng mọi cột thời gian **bắt buộc** ghi nhãn `TIMEZONE_LABEL`
("giờ VN") ngay trong tiêu đề cột:

```tsx
<th>Thời gian tạo <span className="font-normal normal-case text-gray-400">
  ({TIMEZONE_LABEL})</span></th>
```

Lý do: admin Jinja2 cũ hiện UTC. Không ghi nhãn thì cùng một job hiện `11:20` ở
Console và `04:20` ở `/admin`, và không ai hiểu tại sao.

**Làm tròn `final_score` về 1 chữ số.** API trả nguyên độ chính xác, tới 13 chữ
số thập phân (`40.9090909090909`). Hiện thô làm cột điểm lởm chởm.

## 5. Bốn trạng thái bắt buộc

Đây là chỗ bản thiết kế sinh tự động hay hỏng nhất. **Cả bốn trạng thái dùng
chung một khung**: sidebar, thanh trên, thẻ bộ lọc, và **đầu bảng** luôn hiện.
Chỉ phần thân bảng đổi.

| Trạng thái | Thân bảng hiện gì |
|---|---|
| Đang tải | 8–12 dòng skeleton: mỗi ô là một thanh xám bo tròn, `animate-pulse`. Giữ đúng số cột |
| Rỗng | Một dòng gộp toàn bảng, canh giữa, icon mờ + chữ "Chưa có job nào khớp bộ lọc" + nút phụ "Xóa bộ lọc" |
| Lỗi | Banner đỏ **phía trên** bảng: `rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700`, kèm nút "Thử lại". Đầu bảng vẫn hiện, thân rỗng |
| Không đủ quyền | Chỉ ẩn hành động, **không** ẩn dữ liệu. Nếu chính endpoint trả 403 thì hiện "Bạn không có quyền xem nội dung này" tại chỗ, **không** chuyển trang |

Lọc sai (422) là một dạng của trạng thái lỗi, nhưng banner nằm **trong thẻ bộ
lọc**, sát ô gây lỗi, và **giữ nguyên giá trị người dùng đã nhập**.

## 6. Chế độ tối — ĐÃ KIỂM CHỨNG (2026-08-20)

Đã xác nhận bằng ảnh chụp trên màn Tổng quan: nền, thẻ, chữ, viền, pill trạng
thái và nút hành động chính đều đổi đúng. Rà tĩnh cũng không còn nền màu nào
thiếu cặp `dark:`.

Dùng biến thể `dark:` của Tailwind, theo `prefers-color-scheme`, không cần nút
chuyển.

**Cách kiểm nhanh nhất** không phải DevTools mà là đổi chế độ màu của Windows
(Cài đặt → Cá nhân hoá → Màu → Tối) — Chrome tự theo. Đường DevTools là
`F12` → `Ctrl+Shift+P` → **Show Rendering** → cuộn tới **Emulate CSS media
feature prefers-color-scheme**; bảng đó mở ở **nửa dưới** khung DevTools nên
rất dễ tưởng là không có gì hiện ra.

Hai chỗ dễ sai: pill trạng thái cần nền đậm hơn ở chế độ tối
(`dark:bg-emerald-500/15 dark:text-emerald-300`), và navy `#00237a` quá tối
trên nền đen — dùng `#3b5bdb` cho hành động chính ở chế độ tối.

## 7. Màn hình hẹp — ĐÃ KIỂM CHỨNG (2026-08-20)

Đã xác nhận bằng ảnh chụp ở khoảng 1250px: sidebar thu về icon-only (icon có
`title` nên di chuột vẫn biết tên), thẻ lọc xếp thành một cột, thanh trên giữ
nguyên. Bảng có `overflow-x-auto` ở cả Jobs lẫn Reviews.

Desktop-first. Dưới `1280px`: sidebar thu về icon-only (`w-14`, ẩn chữ). Dưới
`1024px`: thẻ bộ lọc xếp dọc thành một cột. Bảng **luôn** cuộn ngang trong
`overflow-x-auto` thay vì bóp cột — bóp cột làm UUID và slug bị cắt mất nghĩa.

Không làm bố cục điện thoại. Đây là công cụ dùng trên máy tính.

## 8. Mật độ

Trên màn hình rộng 1440px phải thấy khoảng **15 dòng bảng** mà không cuộn.
Nếu ít hơn, giảm `py` của ô bảng trước, đừng giảm cỡ chữ xuống dưới `text-sm`.
