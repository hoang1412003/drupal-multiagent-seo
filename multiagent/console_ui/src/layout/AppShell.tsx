/**
 * Khung trang: dieu huong + vung noi dung.
 *
 * CO Y de tran: phan trinh bay se do Antigravity dap theo thiet ke Stitch.
 * O day chi co cau truc va hanh vi (dieu huong, dang xuat) de khong phai lam
 * lai khi ap thiet ke.
 */
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

const NAV = [
  { to: "/", label: "Tổng quan", end: true },
  { to: "/jobs", label: "Jobs", end: false },
  { to: "/reviews", label: "Reviews", end: false },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen">
      <header className="flex items-center gap-6 border-b px-6 py-3">
        <Link to="/" className="font-semibold">
          VF Console
        </Link>
        <nav className="flex gap-4">
          {NAV.map((item) => (
            <NavLink key={item.to} to={item.to} end={item.end}>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-sm">
          <span>
            {user?.username} · {user?.role}
          </span>
          <Link to="/doi-mat-khau">Đổi mật khẩu</Link>
          <button type="button" onClick={handleLogout}>
            Đăng xuất
          </button>
        </div>
      </header>
      <main className="p-6">
        <Outlet />
      </main>
    </div>
  );
}
