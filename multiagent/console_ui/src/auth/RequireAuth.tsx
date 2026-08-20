import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";

export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();

  // Chua hoi xong /auth/me thi CHUA duoc dieu huong: dieu huong som se day
  // nguoi dang co phien hop le ve trang dang nhap moi lan tai trang.
  if (loading) return <div className="p-8 text-sm">Đang tải…</div>;
  if (user === null) return <Navigate to="/login" replace state={{ from: location }} />;
  // Bi buoc doi mat khau thi moi endpoint khac deu tra 403, nen chan tai day.
  if (user.must_change_password && location.pathname !== "/doi-mat-khau") {
    return <Navigate to="/doi-mat-khau" replace />;
  }
  return <Outlet />;
}
