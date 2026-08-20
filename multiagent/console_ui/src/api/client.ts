/**
 * Lop goi API duy nhat cua Console.
 *
 * MOI request phai di qua day. Khong duoc goi fetch/axios truc tiep o component:
 * CSRF, xu ly 401 va hinh dang loi chi dung o mot cho, sai mot cho la sai het.
 */
import type { components } from "./api-types";

export type MeResponse = components["schemas"]["MeResponse"];
export type DashboardResponse = components["schemas"]["DashboardResponse"];
export type JobPage = components["schemas"]["JobPage"];
export type JobDetail = components["schemas"]["JobDetailModel"];
export type ReviewPage = components["schemas"]["ReviewPage"];
export type ReviewDetail = components["schemas"]["ReviewDetailModel"];

const BASE = "/api/console/v1";

/** Ma loi do server tra ve. Xem docs/console-ui/integration.md muc 4. */
export class ConsoleApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
    readonly field: string | null = null,
  ) {
    super(message);
    this.name = "ConsoleApiError";
  }
}

// Phien nam trong cookie HttpOnly nen JS khong doc duoc. Chi rieng csrf_token
// duoc giu trong bo nho (KHONG phai localStorage - no khong phai bi mat lau
// dai, va luu vao do la buoc dau cua thoi quen luu ca token phien vao do).
let csrfToken: string | null = null;

export function setCsrfToken(token: string | null): void {
  csrfToken = token;
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  const method = init.method ?? "GET";
  if (method !== "GET") {
    headers.set("Content-Type", "application/json");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(BASE + path, {
    ...init,
    headers,
    // Mac dinh cua fetch cung la same-origin, nhung ghi ro de khong ai doi
    // nham thanh "omit": cookie la thu DUY NHAT xac thuc request nay.
    credentials: "same-origin",
  });

  if (response.status === 204) return undefined as T;

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = (body as { error?: Record<string, unknown> } | null)?.error;
    throw new ConsoleApiError(
      response.status,
      (detail?.code as string) ?? "unknown",
      (detail?.message as string) ?? "Đã xảy ra lỗi không xác định",
      (detail?.field as string | null) ?? null,
    );
  }
  return body as T;
}

export const client = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body === undefined ? undefined : JSON.stringify(body),
    }),
};

/** Ghep query string, bo qua gia tri rong de khong gui `?status=`. */
export function query(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
