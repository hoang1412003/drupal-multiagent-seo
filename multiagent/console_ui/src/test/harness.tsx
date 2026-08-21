/**
 * Khung dung chung cho moi test man hinh.
 *
 * Hai quyet dinh dang chu y:
 *
 * 1. Gia lap o muc `fetch`, KHONG gia lap module `client`. Nho vay test van
 *    chay qua code that cua client.ts: gan header X-CSRF-Token, boc hinh dang
 *    loi {error:{code,message,field}}, xu ly 204. Gia lap `client` se bo qua
 *    het nhung thu do - va chinh chung la cho de sai.
 *
 * 2. `retry: false` va tat log cua React Query. Mac dinh no thu lai 3 lan roi
 *    moi bao loi, khien mot test nhanh phai cho vai giay.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { vi } from "vitest";

import { setCsrfToken } from "../api/client";
import { AuthProvider } from "../auth/AuthProvider";

const BASE = "/api/console/v1";

export type Route =
  | { status?: number; body: unknown }
  | ((body: unknown) => { status?: number; body: unknown });

/** Nguoi dang dang nhap trong test. Doi `role` de kiem phan quyen. */
export function nguoiDung(role = "admin", ghiDe: Record<string, unknown> = {}) {
  return {
    id: "00000000-0000-4000-8000-0000000000aa",
    username: "admin",
    role,
    must_change_password: false,
    csrf_token: "csrf-test",
    ...ghiDe,
  };
}

export type ApiGia = {
  /** Moi loi goi da di qua, theo thu tu: dung de kiem "co goi API khong". */
  calls: { method: string; path: string; body: unknown }[];
  /** So lan mot duong dan duoc goi. */
  soLan: (path: string) => number;
};

/**
 * Khai bao bang route cho mot test.
 *
 * Khoa co dang "GET /users" hoac "POST /users/{id}/lock" - phan `{...}` khop
 * voi bat ky doan nao khong chua dau /.
 */
export function mockApi(routes: Record<string, Route>): ApiGia {
  const calls: ApiGia["calls"] = [];

  const khop = (method: string, path: string): Route | null => {
    for (const [khoa, route] of Object.entries(routes)) {
      const [m, mau] = khoa.split(" ");
      if (m !== method) continue;
      const bieu_thuc = new RegExp(
        "^" + mau.replace(/\{[^}]+\}/g, "[^/]+").replace(/\?/g, "\\?") + "$",
      );
      // So khong tinh query string cho route khong khai bao query.
      if (bieu_thuc.test(path) || bieu_thuc.test(path.split("?")[0])) {
        return route;
      }
    }
    return null;
  };

  globalThis.fetch = vi.fn(async (url: string, init: RequestInit = {}) => {
    const method = init.method ?? "GET";
    const path = String(url).slice(BASE.length);
    const body = init.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });

    const route = khop(method, path);
    if (route === null) {
      throw new Error(
        `Test goi ${method} ${path} nhung khong khai bao route nao khop. ` +
          `Da khai bao: ${Object.keys(routes).join(", ")}`,
      );
    }
    const ket_qua = typeof route === "function" ? route(body) : route;
    const status = ket_qua.status ?? 200;
    return {
      ok: status >= 200 && status < 300,
      status,
      json: async () => ket_qua.body,
    } as Response;
  }) as unknown as typeof fetch;

  return {
    calls,
    soLan: (path) => calls.filter((c) => c.path.split("?")[0] === path).length,
  };
}

/** Dung de khai bao nhanh mot loi theo dung hinh dang cua Console API. */
export function loi(status: number, code: string, message: string, field: string | null = null) {
  return { status, body: { error: { code, message, field } } };
}

/**
 * @param duongDan  duong dan gia lap, vi du "/reviews/abc-123"
 * @param mau       mau route khi trang doc tham so, vi du "/reviews/:publicId".
 *                  Thieu no thi `useParams()` tra ve rong va trang goi sai URL.
 */
export function renderPage(
  ui: ReactElement,
  { duongDan = "/", mau }: { duongDan?: string; mau?: string } = {},
) {
  setCsrfToken("csrf-test");
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
  return render(
    <MemoryRouter initialEntries={[duongDan]}>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          {mau ? <Routes><Route path={mau} element={ui} /></Routes> : ui}
        </AuthProvider>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}
