import type { ReactNode } from "react";

import { useAuth } from "./AuthProvider";

/** Thu tu quyen, chep dung tu src/review_platform/auth/rbac.py. */
const ROLE_RANK: Record<string, number> = {
  viewer: 10,
  operator: 20,
  admin: 30,
};

export function hasRole(actual: string | undefined, required: string): boolean {
  if (actual === undefined) return false;
  return (ROLE_RANK[actual] ?? 0) >= (ROLE_RANK[required] ?? Number.MAX_SAFE_INTEGER);
}

/**
 * An phan UI ma role hien tai khong duoc dung.
 *
 * Day CHI la lop tien nghi cho nguoi dung. Server van kiem tra role o moi
 * endpoint, nen an nut khong phai la bien phap bao mat va khong duoc coi la.
 */
export function RequireRole({
  role,
  children,
  fallback = null,
}: {
  role: "viewer" | "operator" | "admin";
  children: ReactNode;
  fallback?: ReactNode;
}) {
  const { user } = useAuth();
  return hasRole(user?.role, role) ? <>{children}</> : <>{fallback}</>;
}
