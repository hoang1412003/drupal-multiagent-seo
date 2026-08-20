import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { client, ConsoleApiError } from "../api/client";
import type { JobDetail } from "../api/client";
import { RequireRole } from "../auth/RequireRole";
import { formatDateTime, shortId, TIMEZONE_LABEL } from "../lib/format";
import { JOB_STATUS, WRITEBACK_STATUS, pillOf } from "../lib/status";
import { ErrorBanner } from "../lib/ErrorBanner";
import { StatusPill } from "../lib/StatusPill";

function Field({ label, children, colSpan = false, mono = false }: { label: string, children: React.ReactNode, colSpan?: boolean, mono?: boolean }) {
  return (
    <div className={colSpan ? "sm:col-span-full" : "sm:col-span-1"}>
      <dt className="text-sm font-medium text-gray-500 mb-1">{label}</dt>
      <dd className={`text-sm ${mono ? "font-mono text-xs" : ""} text-ink dark:text-gray-200 break-words`}>
        {children ?? "—"}
      </dd>
    </div>
  );
}

function Section({ title, children }: { title: string, children: React.ReactNode }) {
  return (
    <section className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
      <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">{title}</h2>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3">
        {children}
      </dl>
    </section>
  );
}

export function JobDetailPage() {
  const { publicId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const retriedFrom = (location.state as { retriedFrom?: string } | null)?.retriedFrom;
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const { data: job, isLoading, error, refetch } = useQuery({
    queryKey: ["job", publicId],
    queryFn: () => client.get<JobDetail>(`/jobs/${publicId}`),
    enabled: Boolean(publicId),
    retry: false,
  });

  const retry = useMutation({
    mutationFn: () =>
      client.post<JobDetail>(`/jobs/${publicId}/retry`, {
        confirm_cost: true,
        reason: reason.trim() === "" ? null : reason,
      }),
    onSuccess: (jobMoi) => {
      setConfirming(false);
      setRetryError(null);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      // Retry tao JOB MOI, va man hinh job moi trong GIONG HET man hinh cu.
      // Khong bao thi nguoi dung tuong bam hut. `state` di kem dieu huong nen
      // thong bao chi hien dung mot lan, tai lai trang la mat.
      navigate(`/jobs/${jobMoi.public_id}`, {
        replace: true,
        state: { retriedFrom: publicId },
      });
    },
    onError: (caught: unknown) => {
      if (caught instanceof ConsoleApiError && caught.status === 409) {
        setRetryError("Không thể thử lại job này.");
      } else {
        setRetryError(
          caught instanceof ConsoleApiError
            ? caught.message
            : "Đã xảy ra lỗi không xác định",
        );
      }
    },
  });

  const apiError = error instanceof ConsoleApiError ? error : null;
  const is403 = apiError?.status === 403;
  const is404 = apiError?.status === 404;
  const isError = error && !is403 && !is404;

  const renderSkeleton = () => (
    <div className="flex flex-col gap-6 animate-pulse">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="h-40 bg-gray-200 dark:bg-gray-800 rounded-lg w-full"></div>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-ink dark:text-gray-100 flex items-center gap-2">
            Chi tiết Job
            {job && (
              <span className="font-mono text-sm text-gray-500 font-normal">
                {shortId(job.public_id)}
              </span>
            )}
          </h1>
          <div className="text-sm text-gray-500 mt-1">
            <Link to="/jobs" className="text-blue-600 hover:underline">&larr; Quay lại danh sách</Link>
          </div>
        </div>

        {/* Retry tao JOB MOI, va man hinh job moi trong giong het man hinh cu.
            Khong bao thi nguoi dung tuong bam hut roi bam lai - ma moi lan bam
            la mot lan goi API tra phi. */}
        {retriedFrom && (
          <div
            role="status"
            className="rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800 dark:border-emerald-800 dark:bg-emerald-500/10 dark:text-emerald-300"
          >
            Đã tạo job mới từ job{" "}
            <Link to={`/jobs/${retriedFrom}`} className="font-mono underline">
              {shortId(retriedFrom)}
            </Link>
            . Đây là job vừa được tạo.
          </div>
        )}

        {job?.status === "failed" && (
          <RequireRole role="operator">
            <div className="flex flex-col items-end gap-2">
              {!confirming ? (
                <button
                  type="button"
                  className="h-9 rounded-md bg-vf px-4 text-sm font-medium text-white hover:bg-vf-hover focus:outline-none focus:ring-2 focus:ring-vf/30 dark:bg-[#3b5bdb] dark:hover:bg-[#3b5bdb]/90"
                  onClick={() => setConfirming(true)}
                >
                  Thử lại
                </button>
              ) : (
                <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-800 dark:bg-[#1a1c1c] w-full sm:w-80">
                  <p className="text-sm font-medium text-gray-900 dark:text-gray-100 mb-2">Xác nhận thử lại</p>
                  <p className="text-xs text-gray-500 mb-4">
                    Thử lại sẽ chạy lại pipeline AI và có thể phát sinh chi phí.
                  </p>
                  {retryError && (
                    <div className="mb-3 rounded-md bg-red-50 p-2 text-xs text-red-700 border border-red-200 dark:border-red-900 dark:bg-red-500/10 dark:text-red-300">
                      {retryError}
                    </div>
                  )}
                  <div className="mb-4">
                    <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                      Lý do (không bắt buộc)
                    </label>
                    <input
                      type="text"
                      className="h-8 w-full rounded-md border border-gray-300 bg-white px-2 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      disabled={retry.isPending}
                    />
                  </div>
                  <div className="flex gap-2 justify-end">
                    <button
                      type="button"
                      className="h-8 rounded-md border border-gray-300 bg-white px-3 text-xs font-medium hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent text-gray-700 dark:text-gray-300 disabled:opacity-50"
                      onClick={() => {
                        setConfirming(false);
                        setRetryError(null);
                        setReason("");
                      }}
                      disabled={retry.isPending}
                    >
                      Hủy
                    </button>
                    <button
                      type="button"
                      className="h-8 rounded-md bg-vf px-3 text-xs font-medium text-white hover:bg-vf-hover focus:outline-none focus:ring-2 focus:ring-vf/30 disabled:opacity-50 dark:bg-[#3b5bdb]"
                      onClick={() => retry.mutate()}
                      disabled={retry.isPending}
                    >
                      {retry.isPending ? "Đang xử lý..." : "Xác nhận thử lại"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </RequireRole>
        )}
      </div>

      {is403 && (
        <div className="rounded-md border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
          Bạn không có quyền xem nội dung này.
        </div>
      )}

      {is404 && (
        <div className="rounded-md border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
          Không tìm thấy job
        </div>
      )}

      {isError && (
        <ErrorBanner
            inset
            message={apiError?.message || "Đã xảy ra lỗi khi tải dữ liệu."}
            onRetry={() => refetch()}
          />
      )}

      {isLoading && renderSkeleton()}

      {job && (
        <div className="flex flex-col gap-6">
          
          <Section title="Nhận dạng">
            <Field label="Mã job (public_id)" mono>{job.public_id}</Field>
            <Field label="Correlation ID" mono>{job.correlation_id}</Field>
            <Field label="Thay thế cho job">
              {job.supersedes_job_public_id ? (
                <Link to={`/jobs/${job.supersedes_job_public_id}`} className="text-blue-600 hover:underline font-mono text-xs">
                  {job.supersedes_job_public_id}
                </Link>
              ) : "—"}
            </Field>
          </Section>

          <Section title="Trạng thái">
            <Field label="Trạng thái">
              {(() => {
                const config = JOB_STATUS[job.status] || { label: job.status, bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400" };
                return (
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${config.bg} ${config.text}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`}></span>
                    {config.label}
                  </span>
                );
              })()}
            </Field>
            <Field label="Số lần thử">{job.attempts}</Field>
            <Field label="Nguồn">{job.source}</Field>
            {/* Null thi an han khoi: mot khoi "Loi gan nhat: —" lam nguoi doc
                phai dung lai xem co loi khong, trong khi cau tra loi la khong. */}
            {job.last_error && (
              <Field label="Lỗi gần nhất (last_error)" colSpan mono>
                <div className="max-h-64 overflow-y-auto rounded bg-gray-50 p-3 text-xs text-red-600 whitespace-pre-wrap break-words dark:bg-gray-900/50 dark:text-red-400">
                  {job.last_error}
                </div>
              </Field>
            )}
          </Section>

          <Section title={`Thời gian (${TIMEZONE_LABEL})`}>
            <Field label="Thời gian tạo">{formatDateTime(job.created_at)}</Field>
            <Field label="Cập nhật lần cuối">{formatDateTime(job.updated_at)}</Field>
          </Section>

          <Section title="Nội dung">
            <Field label="ID nội dung (external_content_id)" mono>{job.external_content_id}</Field>
            <Field label="Revision ID (external_revision_id)" mono>{job.external_revision_id}</Field>
            <Field label="Loại nội dung">{job.content_type}</Field>
            <Field label="Ngôn ngữ (langcode)">{job.langcode}</Field>
          </Section>

          <Section title="Ngữ cảnh">
            <Field label="Site">{job.site_name} ({job.site_slug})</Field>
            <Field label="Site ID" mono>{job.site_id}</Field>
            <Field label="Profile ID" mono>{job.profile_id}</Field>
            <Field label="Phiên bản policy">{job.policy_version}</Field>
          </Section>

          <Section title="Kết quả">
            <Field label="Kết quả AI (run_public_id)">
              {job.run_public_id ? (
                <Link to={`/reviews/${job.run_public_id}`} className="text-blue-600 hover:underline font-mono text-xs">
                  {job.run_public_id}
                </Link>
              ) : "—"}
            </Field>
            <Field label={`Thời gian chấm (${TIMEZONE_LABEL})`}>
              {formatDateTime(job.run_scored_at)}
            </Field>
            <Field label="Có dữ liệu kết quả">{job.saved_result_available ? "Có" : "Không"}</Field>
            <Field label="Trạng thái ghi ngược (writeback_status)">
              {job.writeback_status ? (
                <StatusPill style={pillOf(WRITEBACK_STATUS, job.writeback_status)} />
              ) : "—"}
            </Field>
          </Section>

        </div>
      )}
    </div>
  );
}
