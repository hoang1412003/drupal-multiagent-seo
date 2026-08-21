/**
 * Nhan tieng Viet va mau cho moi gia tri trang thai, dung chung MOI man hinh.
 *
 * Truoc khi gom vao day, bang nay bi chep lai o bon file va da lech nhau: man
 * Dashboard tung de `unavailable` mau do trong khi dac ta noi mau xam. Mot bang
 * chep bon lan la bon co hoi lech.
 *
 * Nguon cua bang: docs/console-ui/design-system.md muc 3.
 * DANH SACH gia tri thi lay tu GET /filters, khong viet cung o day - bang nay
 * chi anh xa gia tri -> nhan va mau.
 */

export type PillStyle = {
  label: string;
  dot: string;
  bg: string;
  text: string;
};

const EMERALD = {
  dot: "bg-emerald-500",
  bg: "bg-emerald-50 dark:bg-emerald-500/15",
  text: "text-emerald-700 dark:text-emerald-300",
};
const AMBER = {
  dot: "bg-amber-500",
  bg: "bg-amber-50 dark:bg-amber-500/15",
  text: "text-amber-700 dark:text-amber-300",
};
const BLUE = {
  dot: "bg-blue-500",
  bg: "bg-blue-50 dark:bg-blue-500/15",
  text: "text-blue-700 dark:text-blue-300",
};
const RED = {
  dot: "bg-red-500",
  bg: "bg-red-50 dark:bg-red-500/15",
  text: "text-red-700 dark:text-red-300",
};
const GRAY = {
  dot: "bg-gray-400",
  bg: "bg-gray-100 dark:bg-gray-500/15",
  text: "text-gray-600 dark:text-gray-300",
};

export const JOB_STATUS: Record<string, PillStyle> = {
  queued: { label: "Trong hàng đợi", ...AMBER },
  running: { label: "Đang chạy", ...BLUE },
  done: { label: "Hoàn thành", ...EMERALD },
  failed: { label: "Thất bại", ...RED },
  superseded: { label: "Bị thay thế", ...GRAY },
};

export const REVIEW_DECISION: Record<string, PillStyle> = {
  publish: { label: "Xuất bản", ...EMERALD },
  needs_revision: { label: "Cần sửa", ...AMBER },
  rejected: { label: "Từ chối", ...RED },
  unknown: { label: "Chưa rõ", ...GRAY },
};

export const WRITEBACK_STATUS: Record<string, PillStyle> = {
  succeeded: { label: "Thành công", ...EMERALD },
  failed: { label: "Thất bại", ...RED },
  superseded: { label: "Bị thay thế", ...GRAY },
  pending: { label: "Đang chờ", ...AMBER },
  unknown: { label: "Chưa rõ", ...GRAY },
};

export const WORKER_STATUS: Record<string, PillStyle> = {
  running: { label: "Đang chạy", ...EMERALD },
  // stale = tung chay roi im lang. DAY moi la su co, nen mau do.
  stale: { label: "Mất tín hiệu", ...RED },
  // unavailable = chua bao gio bat. Chua chac la su co, nen mau xam:
  // de mau do se bao dong gia moi khi worker chi don gian la chua chay.
  unavailable: { label: "Chưa từng chạy", ...GRAY },
};

export const AUDIT_OUTCOME: Record<string, PillStyle> = {
  success: { label: "Thành công", ...EMERALD },
  denied: { label: "Bị từ chối", ...RED },
  failed: { label: "Lỗi", ...AMBER },
};

export const EVALUATION_STATUS: Record<string, PillStyle> = {
  valid: { label: "Hợp lệ", ...EMERALD },
  pending: { label: "Chưa chạy", ...GRAY },
  // Ket qua tung dung nhung code da doi tu do -> KHONG duoc dung lam bang
  // chung cho ban hien tai. Day la canh bao, khong phai trang thai trung tinh:
  // de mau xam se khien nguoi doc tuong no van dung duoc.
  historical_invalid: { label: "Không còn hiệu lực", ...AMBER },
};

export const BOOLEAN_PILLS = {
  SITE_ACTIVE: {
    true: { label: "Đang bật", ...EMERALD },
    false: { label: "Đã tắt", ...GRAY },
  } as Record<string, PillStyle>,
  INTAKE_PAUSED: {
    true: { label: "Đang tạm dừng", ...RED },
    false: { label: "Đang nhận", ...EMERALD },
  } as Record<string, PillStyle>,
};

/** Gia tri la (hoac null) van phai hien duoc, khong duoc lam vo giao dien. */
export function pillOf(
  bang: Record<string, PillStyle>,
  value: string | null | undefined,
): PillStyle {
  if (!value) return { label: "—", ...GRAY };
  return bang[value] ?? { label: value, ...GRAY };
}

export const HEALTH_STATUS: Record<string, PillStyle> = {
  ok: { label: "Đạt", ...EMERALD },
};

export const USER_ROLE: Record<string, PillStyle> = {
  viewer: { label: "Chỉ xem", ...GRAY },
  operator: { label: "Vận hành", ...BLUE },
  admin: { label: "Quản trị", ...AMBER },
};

export const USER_ACTIVE: Record<string, PillStyle> = {
  true: { label: "Đang hoạt động", ...EMERALD },
  false: { label: "Đã khoá", ...RED },
};

export const RED_PILL = RED;
