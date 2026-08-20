/**
 * Nguon su that duy nhat ve nguoi dang dang nhap.
 *
 * Cookie phien la HttpOnly nen JS khong doc duoc. Khi app khoi dong, cach duy
 * nhat de biet da dang nhap hay chua la HOI server qua GET /auth/me.
 */
import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { client, ConsoleApiError, setCsrfToken } from "../api/client";
import type { MeResponse } from "../api/client";

type AuthState = {
  user: MeResponse | null;
  /** true trong lan hoi /auth/me dau tien; chua biet gi nen chua duoc dieu huong. */
  loading: boolean;
  login: (username: string, password: string) => Promise<MeResponse>;
  logout: () => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<MeResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const apply = useCallback((me: MeResponse | null) => {
    setUser(me);
    setCsrfToken(me?.csrf_token ?? null);
  }, []);

  useEffect(() => {
    let huy = false;
    client
      .get<MeResponse>("/auth/me")
      .then((me) => {
        if (!huy) apply(me);
      })
      .catch((error: unknown) => {
        // 401 la truong hop binh thuong: chua dang nhap. Loi khac cung coi nhu
        // chua dang nhap - khong co trang thai nao khac de hien.
        if (!(error instanceof ConsoleApiError)) console.error(error);
        if (!huy) apply(null);
      })
      .finally(() => {
        if (!huy) setLoading(false);
      });
    return () => {
      huy = true;
    };
  }, [apply]);

  const login = useCallback(
    async (username: string, password: string) => {
      const me = await client.post<MeResponse>("/auth/login", { username, password });
      apply(me);
      return me;
    },
    [apply],
  );

  const logout = useCallback(async () => {
    await client.post<void>("/auth/logout");
    apply(null);
  }, [apply]);

  const changePassword = useCallback(
    async (currentPassword: string, newPassword: string) => {
      await client.post<void>("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });
      // Doi mat khau huy MOI phien, ke ca phien hien tai.
      apply(null);
    },
    [apply],
  );

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, changePassword }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (value === null) throw new Error("useAuth phai nam trong <AuthProvider>");
  return value;
}
