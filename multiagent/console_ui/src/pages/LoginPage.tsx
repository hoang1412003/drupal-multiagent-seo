import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { ConsoleApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

export function LoginPage() {
  const { user, loading, login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (loading) return null; // or a loading spinner
  if (user !== null) return <Navigate to="/" replace />;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const me = await login(username, password);
      navigate(me.must_change_password ? "/doi-mat-khau" : "/", { replace: true });
    } catch (caught) {
      setError(
        caught instanceof ConsoleApiError
          ? caught.message
          : "Đã xảy ra lỗi không xác định",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#f9f9f9] dark:bg-[#111314] flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-md bg-white dark:bg-[#1a1c1c] rounded-lg border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="p-8">
          <div className="text-center mb-8">
            <h1 className="text-2xl font-semibold text-[#1a1c1c] dark:text-gray-100 tracking-tight">AI Review Platform</h1>
            <p className="text-sm text-gray-500 mt-2">Đăng nhập để quản trị hệ thống</p>
          </div>
          
          <form onSubmit={handleSubmit} className="space-y-5">
            {error && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:border-red-900/50 dark:text-red-300">
                {error}
              </div>
            )}
            
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                Tên đăng nhập
              </label>
              <input 
                className="h-10 w-full rounded-md border border-gray-300 bg-white px-3 text-sm text-[#1a1c1c] focus:border-[#00237a] focus:outline-none focus:ring-2 focus:ring-[#00237a]/20 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-200 dark:focus:border-[#3b5bdb] dark:focus:ring-[#3b5bdb]/20"
                value={username} 
                onChange={(e) => setUsername(e.target.value)} 
                disabled={submitting}
                required
              />
            </div>
            
            <div>
              <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">
                Mật khẩu
              </label>
              <input
                type="password"
                className="h-10 w-full rounded-md border border-gray-300 bg-white px-3 text-sm text-[#1a1c1c] focus:border-[#00237a] focus:outline-none focus:ring-2 focus:ring-[#00237a]/20 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-200 dark:focus:border-[#3b5bdb] dark:focus:ring-[#3b5bdb]/20"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                disabled={submitting}
                required
              />
            </div>
            
            <button 
              type="submit" 
              disabled={submitting || !username || !password}
              className="mt-2 h-10 w-full rounded-md bg-[#00237a] px-4 text-sm font-medium text-white hover:bg-[#00237a]/90 focus:outline-none focus:ring-2 focus:ring-[#00237a]/30 disabled:opacity-50 disabled:cursor-not-allowed dark:bg-[#3b5bdb] dark:hover:bg-[#3b5bdb]/90 transition-colors"
            >
              {submitting ? (
                <span className="flex items-center justify-center gap-2">
                  <svg className="h-4 w-4 animate-spin" viewBox="0 0 24 24" fill="none">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" className="opacity-25" />
                    <path fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" className="opacity-75" />
                  </svg>
                  Đang đăng nhập…
                </span>
              ) : "Đăng nhập"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
