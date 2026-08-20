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
  {
    to: "/",
    label: "Tổng quan",
    end: true,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 6a7.5 7.5 0 1 0 7.5 7.5h-7.5V6Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 10.5H21A7.5 7.5 0 0 0 13.5 3v7.5Z" />
      </svg>
    ),
  },
  {
    to: "/jobs",
    label: "Jobs",
    end: false,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 6.75h12M8.25 12h12m-12 5.25h12M3.75 6.75h.007v.008H3.75V6.75Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0ZM3.75 12h.007v.008H3.75V12Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm-.375 5.25h.007v.008H3.75v-.008Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
      </svg>
    ),
  },
  {
    to: "/reviews",
    label: "Reviews",
    end: false,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0 1 18 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3 1.5 1.5 3-3.75" />
      </svg>
    ),
  },
];

export function AppShell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen bg-[#f9f9f9] text-[#1a1c1c] dark:bg-[#111314] dark:text-[#e8e9e9]">
      <aside className="flex w-14 shrink-0 flex-col border-r border-gray-200 bg-white dark:border-[#2f3131] dark:bg-[#1a1c1c] xl:w-56">
        <div className="flex h-14 items-center border-b border-gray-200 px-4 dark:border-[#2f3131]">
          <Link to="/" className="hidden truncate whitespace-nowrap text-lg font-semibold xl:block">
            AI Review Platform
          </Link>
          <Link to="/" className="w-full text-center text-lg font-bold xl:hidden">
            AI
          </Link>
        </div>
        <nav className="flex flex-1 flex-col gap-1 px-2 py-4">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-md px-2 py-2 transition-colors xl:px-3 ${
                  isActive
                    ? "bg-vf/10 font-medium text-vf dark:bg-[#3b5bdb]/20 dark:text-[#3b5bdb]"
                    : "text-gray-600 hover:bg-gray-100 hover:text-[#1a1c1c] dark:text-[#9ca3af] dark:hover:bg-white/5 dark:hover:text-[#e8e9e9]"
                }`
              }
              title={item.label}
            >
              {item.icon}
              <span className="hidden xl:inline">{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="sticky top-0 z-10 flex h-14 items-center border-b border-gray-200 bg-white/75 px-6 backdrop-blur-[20px] dark:border-[#2f3131] dark:bg-[#1a1c1c]/75">
          <div className="ml-auto flex items-center gap-4 text-sm text-gray-600 dark:text-[#9ca3af]">
            <span>
              {user?.username} · {user?.role}
            </span>
            <Link to="/doi-mat-khau" className="hover:text-[#1a1c1c] dark:hover:text-[#e8e9e9]">
              Đổi mật khẩu
            </Link>
            <button type="button" onClick={handleLogout} className="hover:text-[#1a1c1c] dark:hover:text-[#e8e9e9]">
              Đăng xuất
            </button>
          </div>
        </header>

        <main className="flex flex-1 flex-col gap-4 overflow-x-hidden p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
