import { useState } from "react";
import { useNavigate } from "react-router-dom";

import { ConsoleApiError } from "../api/client";
import { useAuth } from "../auth/AuthProvider";

export function ChangePasswordPage() {
  const { changePassword } = useAuth();
  const navigate = useNavigate();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await changePassword(currentPassword, newPassword);
      // Doi mat khau huy moi phien nen phai dang nhap lai.
      navigate("/login", { replace: true });
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

  // TODO(Antigravity): dựng giao diện theo thiết kế Stitch "Login" (biến thể
  // đổi mật khẩu).
  return (
    <form onSubmit={handleSubmit}>
      <h1>Đổi mật khẩu</h1>
      {error && <p role="alert">{error}</p>}
      <label>
        Mật khẩu hiện tại
        <input
          type="password"
          value={currentPassword}
          onChange={(e) => setCurrentPassword(e.target.value)}
        />
      </label>
      <label>
        Mật khẩu mới
        <input
          type="password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
        />
      </label>
      <button type="submit" disabled={submitting}>
        {submitting ? "Đang đổi…" : "Đổi mật khẩu"}
      </button>
    </form>
  );
}
