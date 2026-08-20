/**
 * Bon trang thai bat buoc cua moi man hinh doc du lieu.
 *
 * Tach ra mot cho de khong man hinh nao "quen" trang thai rong hay trang thai
 * khong du quyen - do la hai trang thai hay bi bo sot nhat.
 */
import type { ReactNode } from "react";

import { ConsoleApiError } from "../api/client";

type Props<T> = {
  isLoading: boolean;
  error: unknown;
  data: T | undefined;
  /** Tra true khi du lieu hop le nhung rong. */
  isEmpty?: (data: T) => boolean;
  emptyText?: string;
  children: (data: T) => ReactNode;
};

export function AsyncBoundary<T>({
  isLoading,
  error,
  data,
  isEmpty,
  emptyText = "Chưa có dữ liệu",
  children,
}: Props<T>) {
  if (isLoading) return <p>Đang tải…</p>;

  if (error) {
    const message =
      error instanceof ConsoleApiError ? error.message : "Đã xảy ra lỗi không xác định";
    // 403 KHONG duoc dieu huong ve trang dang nhap: nguoi dung da dang nhap
    // hop le, chi la khong du quyen. Dieu huong se tao vong lap.
    const forbidden = error instanceof ConsoleApiError && error.status === 403;
    return <p role="alert">{forbidden ? "Bạn không có quyền xem nội dung này." : message}</p>;
  }

  if (data === undefined) return <p>Chưa có dữ liệu</p>;
  if (isEmpty?.(data)) return <p>{emptyText}</p>;
  return <>{children(data)}</>;
}
