/**
 * Khung trang: dieu huong + vung noi dung.
 *
 * CO Y de tran: phan trinh bay se do Antigravity dap theo thiet ke Stitch.
 * O day chi co cau truc va hanh vi (dieu huong, dang xuat) de khong phai lam
 * lai khi ap thiet ke.
 */
import { Link, NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthProvider";
import { RequireRole } from "../auth/RequireRole";

type Role = "viewer" | "operator" | "admin";

type NavItem = {
  to: string;
  label: string;
  end: boolean;
  /** Bo trong = ai dang nhap cung thay. */
  requireRole?: Role;
  icon: React.ReactNode;
};

const NAV: NavItem[] = [
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
  {
    to: "/audit",
    label: "Nhật ký",
    end: false,
    requireRole: "admin",
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
      </svg>
    ),
  },
  {
    to: "/cau-hinh",
    label: "Cấu hình",
    end: false,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M10.34 15.84c-.688-.06-1.386-.09-2.09-.09H7.5a4.5 4.5 0 1 1 0-9h.75c.704 0 1.402-.03 2.09-.09m0 9.18c.253.962.584 1.892.985 2.783.247.55.06 1.21-.463 1.511l-.657.38c-.551.318-1.26.117-1.527-.461a20.845 20.845 0 0 1-1.44-4.282m3.102.069a18.03 18.03 0 0 1-.59-4.59c0-1.586.205-3.124.59-4.59m0 9.18a23.848 23.848 0 0 1 8.835 2.535M10.34 6.66a23.847 23.847 0 0 0 8.835-2.535m0 0A23.74 23.74 0 0 0 18.795 3m.38 1.125a23.91 23.91 0 0 1 1.014 5.395m-1.014 8.855c-.118.38-.245.754-.38 1.125m.38-1.125a23.91 23.91 0 0 0 1.014-5.395m0-3.46c.495.413.811 1.035.811 1.73 0 .695-.316 1.317-.811 1.73m0-3.46a24.347 24.347 0 0 1 0 3.46" />
      </svg>
    ),
  },
  {
    to: "/danh-gia",
    label: "Kết quả đo",
    end: false,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 0 1 3 19.875v-6.75ZM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V8.625ZM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 0 1-1.125-1.125V4.125Z" />
      </svg>
    ),
  },
  {
    to: "/ket-noi",
    label: "Kết nối",
    end: false,
    icon: (
      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
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
          {NAV.map((item) => {
            const link = (
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
            );

            if (item.requireRole) {
              return (
                <RequireRole key={item.to} role={item.requireRole}>
                  {link}
                </RequireRole>
              );
            }
            return link;
          })}
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
