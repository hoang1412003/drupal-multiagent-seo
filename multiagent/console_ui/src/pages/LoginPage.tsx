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

  if (loading) return <p>Đang tải…</p>;
  if (user !== null) return <Navigate to="/" replace />;

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const me = await login(username, password);
      navigate(me.must_change_password ? "/doi-mat-khau" : "/", { replace: true });
    } catch (caught) {
      // Server co tinh dung MOT thong bao cho ca "sai mat khau" lan "khong co
      // tai khoan". Khong duoc tach ra thanh loi tung truong.
      setError(
        caught instanceof ConsoleApiError
          ? caught.message
          : "Đã xảy ra lỗi không xác định",
      );
    } finally {
      setSubmitting(false);
    }
  }

  // TODO(Antigravity): dựng giao diện theo thiết kế Stitch "Login".
  return (
    <form onSubmit={handleSubmit}>
      <h1>Đăng nhập</h1>
      {error && <p role="alert">{error}</p>}
      <label>
        Tên đăng nhập
        <input value={username} onChange={(e) => setUsername(e.target.value)} />
      </label>
      <label>
        Mật khẩu
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </label>
      <button type="submit" disabled={submitting}>
        {submitting ? "Đang đăng nhập…" : "Đăng nhập"}
      </button>
    </form>
  );
}
