/**
 * Ham dinh dang dung chung cho MOI man hinh.
 *
 * Khong tu viet lai o tung trang: bay man hinh moi trang mot kieu la cach
 * nhanh nhat de cung mot job hien hai gio khac nhau o hai cho.
 */

/** Nhan mui gio, dat canh moi cot thoi gian. */
export const TIMEZONE_LABEL = "giờ VN";

/**
 * ISO-8601 UTC tu API -> "19/08/2026 14:32" theo GIO VIET NAM.
 *
 * API luon tra UTC. Console hien gio dia phuong vi nguoi van hanh doc gio VN,
 * nhung PHAI ghi nhan TIMEZONE_LABEL canh cot - admin Jinja2 cu hien UTC, nen
 * khong ghi thi cung mot job se hien 11:20 o day va 04:20 o /admin ma khong ai
 * hieu tai sao.
 */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "—";
  const pad = (n: number) => n.toString().padStart(2, "0");
  return (
    `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ` +
    `${pad(d.getHours())}:${pad(d.getMinutes())}`
  );
}

/** Chi ngay, khong gio. Dung cho date_from/date_to va effective_at. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  const [year, month, day] = iso.slice(0, 10).split("-");
  if (!year || !month || !day) return "—";
  return `${day}/${month}/${year}`;
}

/**
 * So co the null -> chuoi hien thi.
 *
 * `null` hien "—", KHONG hien 0: final_score null nghia la chua cham duoc,
 * khac han voi cham duoc 0 diem.
 */
export function formatNumber(
  value: number | null | undefined,
  digits = 1,
): string {
  if (value === null || value === undefined) return "—";
  return value.toFixed(digits);
}

/** UUID -> "a3f2…9c41". Du de nhan ra, du ngan de khong pha bo cuc bang. */
export function shortId(id: string | null | undefined): string {
  if (!id) return "—";
  const bo = id.replace(/-/g, "");
  if (bo.length <= 8) return id;
  return `${bo.slice(0, 4)}…${bo.slice(-4)}`;
}
