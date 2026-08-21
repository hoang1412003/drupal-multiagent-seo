import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import type { components } from "../api/api-types";
import { client, ConsoleApiError } from "../api/client";
import { RequireRole } from "../auth/RequireRole";
import { formatDateTime, TIMEZONE_LABEL } from "../lib/format";
import { ErrorBanner } from "../lib/ErrorBanner";
import { BOOLEAN_PILLS, HEALTH_STATUS, RED_PILL, pillOf } from "../lib/status";
import { StatusPill } from "../lib/StatusPill";

type ConnectionModel = components["schemas"]["ConnectionModel"];
type TestConnectionResponse = components["schemas"]["TestConnectionResponse"];

function Field({ label, children, colSpan = false, mono = false, breakAll = false }: { label: string, children: React.ReactNode, colSpan?: boolean, mono?: boolean, breakAll?: boolean }) {
  return (
    <div className={colSpan ? "sm:col-span-full" : "sm:col-span-1"}>
      <dt className="text-sm font-medium text-gray-500 mb-1">{label}</dt>
      <dd className={`text-sm ${mono ? "font-mono text-xs" : ""} text-ink dark:text-gray-200 ${breakAll ? "break-all" : "break-words"}`}>
        {children ?? "—"}
      </dd>
    </div>
  );
}

function Section({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">{title}</h2>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        {children}
      </dl>
    </section>
  );
}

export function ConnectionPage() {
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [testResult, setTestResult] = useState<{ ok: boolean, error_code: string | null } | null>(null);
  // Tam dung nhan bai chan TOAN BO bai moi tu Drupal, nen phai hoi lai. Mo
  // lai thi khong: no dua he thong ve trang thai binh thuong.
  const [confirmingPause, setConfirmingPause] = useState(false);
  
  const { data: conn, isLoading, error, refetch } = useQuery({
    queryKey: ["connection"],
    queryFn: () => client.get<ConnectionModel>("/connection"),
    retry: false,
  });

  const testMutation = useMutation({
    mutationFn: () => client.post<TestConnectionResponse>("/connection/test", {}),
    onSuccess: (res) => {
      setTestResult({ ok: res.ok, error_code: res.error_code });
      queryClient.setQueryData(["connection"], res.connection);
    },
  });

  const pauseMutation = useMutation({
    mutationFn: () => client.post<ConnectionModel>("/connection/pause", reason ? { reason } : {}),
    onSuccess: (newConn) => {
      queryClient.setQueryData(["connection"], newConn);
      setReason("");
    },
  });

  const resumeMutation = useMutation({
    mutationFn: () => client.post<ConnectionModel>("/connection/resume", reason ? { reason } : {}),
    onSuccess: (newConn) => {
      queryClient.setQueryData(["connection"], newConn);
      setReason("");
    },
  });

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Kết nối</h1>
        <p className="text-sm text-gray-500">Quản lý kết nối tới hệ thống nguồn.</p>
      </div>
      <div className="h-48 w-full animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"></div>
    </div>
  );

  if (isLoading) return renderSkeleton();
  // 404 = chua cau hinh site nao. Do KHONG phai su co he thong, nen khong
  // duoc hien banner do - man hinh rong moi dung.
  if (error instanceof ConsoleApiError && error.status === 404) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Kết nối</h1>
          <p className="text-sm text-gray-500">Quản lý kết nối tới hệ thống nguồn.</p>
        </div>
        <section className="rounded-lg border border-gray-200 bg-white p-8 text-center dark:border-gray-800 dark:bg-[#1a1c1c]">
          <p className="text-sm text-gray-500">Chưa cấu hình site nào.</p>
        </section>
      </div>
    );
  }
  if (error) {
    return (
      <ErrorBanner
        message={error instanceof Error ? error.message : null}
        onRetry={() => refetch()}
      />
    );
  }
  if (!conn) return null;

  const health = conn.last_health_status;
  const healthPill = health === null
    ? null
    : health === "ok"
      ? HEALTH_STATUS.ok
      : { label: health, ...RED_PILL };

  const isNeverChecked = conn.last_health_status === null && conn.last_health_checked_at === null && conn.last_health_error === null;

  const actionError =
    (testMutation.error ?? pauseMutation.error ?? resumeMutation.error) as Error | null;
  // Server tra 422 kem field="reason" khi ly do qua dai. To do ngay o o nhap
  // lieu, dung de nguoi dung phai doan xem banner chung noi ve cho nao.
  const reasonError =
    actionError instanceof ConsoleApiError && actionError.field === "reason"
      ? actionError.message
      : null;

  const isTesting = testMutation.isPending;
  const isChangingIntake = pauseMutation.isPending || resumeMutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Kết nối</h1>
        <p className="text-sm text-gray-500">Quản lý kết nối tới hệ thống nguồn.</p>
      </div>

      {testResult && (
        <div className={`rounded-md border p-3 text-sm flex items-start gap-2 mb-4 ${
          testResult.ok 
            ? "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-900/20 dark:text-emerald-300"
            : "border-red-200 bg-red-50 text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
        }`}>
          {testResult.ok ? (
            <>
              <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span>Kết nối đạt</span>
            </>
          ) : (
            <>
              <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
              <span>Kết nối chưa đạt (mã: {testResult.error_code})</span>
            </>
          )}
        </div>
      )}

      {actionError && (
        <ErrorBanner
          message={
            actionError instanceof ConsoleApiError && actionError.field === "reason"
              ? null  // loi cua o Ly do da duoc bao ngay tai o do
              : actionError.message
          }
        />
      )}

      <Section title="Site">
        <Field label="Tên">{conn.name}</Field>
        <Field label="Slug" mono>{conn.slug}</Field>
        <Field label="Địa chỉ" mono breakAll colSpan>{conn.base_url}</Field>
        <Field label="Biến môi trường chứa credential" mono>{conn.secret_ref}</Field>
        <Field label="Trạng thái Site">
          <StatusPill style={pillOf(BOOLEAN_PILLS.SITE_ACTIVE, String(conn.active))} />
        </Field>
        <Field label="Tiếp nhận">
          <StatusPill style={pillOf(BOOLEAN_PILLS.INTAKE_PAUSED, String(conn.intake_paused))} />
        </Field>
        {conn.token_prefixes && conn.token_prefixes.length > 0 && (
          <div className="sm:col-span-full">
            <dt className="text-sm font-medium text-gray-500 mb-2">Tiền tố token</dt>
            <dd className="flex flex-wrap gap-2">
              {conn.token_prefixes.map((tp, idx) => (
                <span key={idx} className="font-mono text-xs bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300 px-2 py-1 rounded">
                  {tp}
                </span>
              ))}
            </dd>
          </div>
        )}
      </Section>

      <Section title="Hồ sơ đang áp dụng">
        <Field label="Hồ sơ (Profile)" mono>{conn.profile_code ?? "—"}</Field>
        <Field label="Phiên bản Policy">{conn.policy_version ?? "—"}</Field>
      </Section>

      <Section title="Lần chẩn đoán gần nhất">
        {isNeverChecked ? (
          <div className="sm:col-span-full">
            <p className="text-sm text-gray-500">Chưa từng chẩn đoán kết nối</p>
          </div>
        ) : (
          <>
            <Field label="Kết quả">
              {healthPill ? <StatusPill style={healthPill} /> : "—"}
            </Field>
            <Field label={`Thời điểm (${TIMEZONE_LABEL})`}>
              {conn.last_health_checked_at ? formatDateTime(conn.last_health_checked_at) : "—"}
            </Field>
            {conn.last_health_error !== null && (
              <Field label="Mã lỗi" colSpan>
                {conn.last_health_error}
              </Field>
            )}
          </>
        )}
      </Section>

      <section className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">Thao tác</h2>
        
        <RequireRole 
          role="operator"
          fallback={<p className="text-sm text-gray-500">Bạn đang xem với quyền chỉ đọc. Liên hệ quản trị viên để thao tác.</p>}
        >
          <div className="space-y-6">
            <div>
              <button
                type="button"
                onClick={() => testMutation.mutate()}
                disabled={isTesting || isChangingIntake}
                className="h-9 rounded-md bg-white border border-gray-300 px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-vf/30 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#111314] dark:border-gray-700 dark:text-gray-200 dark:hover:bg-white/5"
              >
                {isTesting ? "Đang chẩn đoán..." : "Chẩn đoán kết nối"}
              </button>
            </div>
            
            <div className="pt-6 border-t border-gray-100 dark:border-gray-800">
              <div className="mb-3">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Lý do <span className="text-gray-400 font-normal">(không bắt buộc)</span>
                </label>
                <textarea
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  maxLength={300}
                  rows={2}
                  aria-invalid={reasonError !== null}
                  className={`w-full rounded-md border bg-white p-2 text-sm focus:outline-none focus:ring-2 dark:bg-[#111314] dark:text-gray-100 ${
                    reasonError !== null
                      ? "border-red-400 focus:border-red-500 focus:ring-red-500/20 dark:border-red-700"
                      : "border-gray-300 focus:border-vf focus:ring-vf/20 dark:border-gray-700"
                  }`}
                  placeholder="Ghi chú nguyên nhân thay đổi trạng thái..."
                />
                <div className="mt-1 flex items-start justify-between gap-3">
                  <p className="text-xs text-red-600 dark:text-red-400">{reasonError}</p>
                  <span className={`shrink-0 text-xs ${reason.length >= 300 ? "text-red-500 font-medium" : "text-gray-500"}`}>
                    {reason.length}/300
                  </span>
                </div>
              </div>
              
              {conn.intake_paused ? (
                <button
                  type="button"
                  onClick={() => resumeMutation.mutate()}
                  disabled={isChangingIntake || isTesting}
                  className="h-9 rounded-md bg-emerald-600 px-4 text-sm font-medium text-white hover:bg-emerald-700 focus:outline-none focus:ring-2 focus:ring-emerald-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {resumeMutation.isPending ? "Đang xử lý..." : "Mở lại nhận bài"}
                </button>
              ) : confirmingPause ? (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 dark:border-red-900 dark:bg-red-500/10">
                  <p className="text-sm text-red-800 dark:text-red-300">
                    Tạm dừng nhận bài sẽ khiến toàn bộ bài mới từ Drupal không được
                    tiếp nhận cho tới khi mở lại. Tiếp tục?
                  </p>
                  <div className="mt-3 flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setConfirmingPause(false);
                        pauseMutation.mutate();
                      }}
                      disabled={isChangingIntake || isTesting}
                      className="h-9 rounded-md bg-red-600 px-4 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {pauseMutation.isPending ? "Đang xử lý..." : "Xác nhận tạm dừng"}
                    </button>
                    <button
                      type="button"
                      onClick={() => setConfirmingPause(false)}
                      className="h-9 rounded-md border border-red-200 bg-white px-4 text-sm font-medium text-red-700 hover:bg-red-50 focus:outline-none focus:ring-2 focus:ring-red-500/30 dark:border-red-800 dark:bg-transparent dark:text-red-300 dark:hover:bg-red-500/10"
                    >
                      Huỷ
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  type="button"
                  onClick={() => setConfirmingPause(true)}
                  disabled={isChangingIntake || isTesting}
                  className="h-9 rounded-md bg-red-600 px-4 text-sm font-medium text-white hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500/30 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {pauseMutation.isPending ? "Đang xử lý..." : "Tạm dừng nhận bài"}
                </button>
              )}
            </div>
          </div>
        </RequireRole>
      </section>
    </div>
  );
}
