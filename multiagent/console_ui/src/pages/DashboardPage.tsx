import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";

import { client, query, ConsoleApiError } from "../api/client";
import type { DashboardResponse } from "../api/client";
import { formatDate, formatDateTime, formatNumber } from "../lib/format";
import { useFilters } from "../api/useFilters";

const JOB_STATUS_CONFIG: Record<string, { label: string, dot: string, bg: string, text: string }> = {
  queued: { label: "Trong hàng đợi", dot: "bg-amber-500", bg: "bg-amber-50 dark:bg-amber-500/15", text: "text-amber-700 dark:text-amber-300" },
  running: { label: "Đang chạy", dot: "bg-blue-500", bg: "bg-blue-50 dark:bg-blue-500/15", text: "text-blue-700 dark:text-blue-300" },
  done: { label: "Hoàn thành", dot: "bg-emerald-500", bg: "bg-emerald-50 dark:bg-emerald-500/15", text: "text-emerald-700 dark:text-emerald-300" },
  failed: { label: "Thất bại", dot: "bg-red-500", bg: "bg-red-50 dark:bg-red-500/15", text: "text-red-700 dark:text-red-300" },
  superseded: { label: "Bị thay thế", dot: "bg-gray-400", bg: "bg-gray-100 dark:bg-gray-500/15", text: "text-gray-600 dark:text-gray-300" },
};

const DECISION_CONFIG: Record<string, { label: string, dot: string, bg: string, text: string }> = {
  publish: { label: "Xuất bản", dot: "bg-emerald-500", bg: "bg-emerald-50 dark:bg-emerald-500/15", text: "text-emerald-700 dark:text-emerald-300" },
  needs_revision: { label: "Cần sửa", dot: "bg-amber-500", bg: "bg-amber-50 dark:bg-amber-500/15", text: "text-amber-700 dark:text-amber-300" },
  rejected: { label: "Từ chối", dot: "bg-red-500", bg: "bg-red-50 dark:bg-red-500/15", text: "text-red-700 dark:text-red-300" },
  unknown: { label: "Chưa rõ", dot: "bg-gray-400", bg: "bg-gray-100 dark:bg-gray-500/15", text: "text-gray-600 dark:text-gray-300" },
};

const WORKER_STATUS_CONFIG: Record<string, { label: string, dot: string, bg: string, text: string }> = {
  running: { label: "Hoạt động", dot: "bg-emerald-500", bg: "bg-emerald-50 dark:bg-emerald-500/15", text: "text-emerald-700 dark:text-emerald-300" },
  // stale = tung chay roi im lang -> DAY LA SU CO, mau do.
  stale: { label: "Mất tín hiệu", dot: "bg-red-500", bg: "bg-red-50 dark:bg-red-500/15", text: "text-red-700 dark:text-red-300" },
  // unavailable = chua bao gio bao cao -> chua chac la su co, mau xam.
  unavailable: { label: "Chưa từng chạy", dot: "bg-gray-400", bg: "bg-gray-100 dark:bg-gray-500/15", text: "text-gray-600 dark:text-gray-300" },
};

const WRITEBACK_LABEL: Record<string, string> = {
  succeeded: "Thành công",
  failed: "Thất bại",
  superseded: "Bị thay thế",
  pending: "Đang chờ",
  unknown: "Chưa rõ",
};

/** ms -> "7,7 giây" khi >= 1000ms, nguoc lai giu "820 ms". */
function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${formatNumber(ms, 0)} ms`;
  return `${formatNumber(ms / 1000, 1)} giây`;
}

export function DashboardPage() {
  const [params, setParams] = useSearchParams();
  const { data: filtersData } = useFilters();

  // If no params, default to last 7 days when creating search query? No, just pass them as is. The API defaults to 7 days.
  const search = query({
    from: params.get("from") ?? undefined,
    to: params.get("to") ?? undefined,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["dashboard", search],
    queryFn: () => client.get<DashboardResponse>(`/dashboard${search}`),
    retry: false,
  });

  const [dateFrom, setDateFrom] = useState(params.get("from") ?? "");
  const [dateTo, setDateTo] = useState(params.get("to") ?? "");

  useEffect(() => {
    setDateFrom(params.get("from") ?? "");
    setDateTo(params.get("to") ?? "");
  }, [params]);

  const handleApplyFilters = () => {
    const newParams = new URLSearchParams();
    if (dateFrom) newParams.set("from", dateFrom);
    if (dateTo) newParams.set("to", dateTo);
    setParams(newParams);
  };

  const handleClearFilters = () => {
    setParams(new URLSearchParams());
  };

  const apiError = error instanceof ConsoleApiError ? error : null;
  const is403 = apiError?.status === 403;
  const is422 = apiError?.status === 422;
  const isError = error && !is403 && !is422;

  const renderSkeleton = () => (
    <div className="flex flex-col gap-6 animate-pulse mt-4">
      <div className="h-20 bg-gray-200 dark:bg-gray-800 rounded-lg w-full"></div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="h-32 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
        <div className="h-32 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
        <div className="h-32 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="h-40 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
        <div className="h-40 bg-gray-200 dark:bg-gray-800 rounded-lg"></div>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Tổng quan</h1>
        <p className="text-sm text-gray-500">Trạng thái hệ thống và hiệu suất AI.</p>
      </div>

      <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-[#1a1c1c]">
        <div className="flex flex-col sm:flex-row items-start sm:items-center gap-4">
          <div className="flex items-center gap-3">
            <div>
              <label className="sr-only">Từ ngày</label>
              <input
                type="date"
                className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
              />
            </div>
            <span className="text-gray-500 text-sm">đến</span>
            <div>
              <label className="sr-only">Đến ngày</label>
              <input
                type="date"
                className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
              />
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              className="h-9 rounded-md bg-vf px-4 text-sm font-medium text-white hover:bg-vf-hover focus:outline-none focus:ring-2 focus:ring-vf/30 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#3b5bdb] dark:hover:bg-[#3b5bdb]/90"
              onClick={handleApplyFilters}
            >
              Cập nhật
            </button>
            {(params.has("from") || params.has("to")) && (
              <button
                type="button"
                className="h-9 rounded-md border border-gray-300 bg-white px-4 text-sm hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent"
                onClick={handleClearFilters}
              >
                Xóa lọc
              </button>
            )}
          </div>
          {is422 && (
            <div className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-700 ml-auto">
              {apiError?.message || "Lỗi thời gian đã chọn."}
            </div>
          )}
        </div>
      </div>

      {is403 && (
        <div className="rounded-md border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
          Bạn không có quyền xem nội dung này.
        </div>
      )}

      {isError && (
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <span>{apiError?.message || "Đã xảy ra lỗi khi tải dữ liệu tổng quan."}</span>
          <button
            type="button"
            className="h-9 rounded-md border border-red-200 bg-white px-4 text-sm font-medium text-red-700 hover:bg-red-50"
            onClick={() => refetch()}
          >
            Thử lại
          </button>
        </div>
      )}

      {isLoading && renderSkeleton()}

      {data && !isLoading && !is403 && !isError && (
        <div className="flex flex-col gap-8">
          
          <section className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">
              Hàng đợi hiện tại — toàn thời gian
            </h2>
            <div className="flex flex-wrap gap-6">
              {(filtersData?.job_statuses ?? []).map((status) => {
                const count = data.queue_counts[status] || 0;
                const config = JOB_STATUS_CONFIG[status] || { label: status, text: "text-gray-700", bg: "bg-gray-100", dot: "bg-gray-400" };
                return (
                  <div key={status} className="flex items-center gap-2">
                    <span className={`flex h-2.5 w-2.5 rounded-full ${config.dot}`}></span>
                    <span className="text-sm font-medium text-gray-600 dark:text-gray-400">{config.label}:</span>
                    <span className="text-lg font-semibold tabular-nums text-ink dark:text-gray-100">{count}</span>
                  </div>
                );
              })}
            </div>
          </section>

          <section>
            <div className="mb-4">
              <h2 className="text-lg font-semibold text-ink dark:text-gray-100">
                Kết quả từ {formatDate(data.date_from)} đến {formatDate(data.date_to)}
              </h2>
              <p className="text-sm text-gray-500 mt-1">
                Lưu ý: Dữ liệu bên dưới đã lọc theo thời gian và không bao gồm dữ liệu mẫu (mẫu test).
              </p>
            </div>

            {data.total_reviews === 0 ? (
              <div className="rounded-lg border border-gray-200 bg-white p-12 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
                Không có dữ liệu trong khoảng đã chọn
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                
                {/* 1. Tổng số review */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c] flex flex-col justify-center">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-2">Tổng số review</h3>
                  <div className="text-3xl font-semibold tabular-nums text-ink dark:text-gray-100">
                    {data.total_reviews}
                  </div>
                </div>

                {/* 2. Thời lượng */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c] flex flex-col justify-center">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-2">Thời lượng xử lý</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-500 mb-1">Trung vị (P50)</div>
                      <div className="text-xl font-semibold tabular-nums text-ink dark:text-gray-100">
                        {formatDuration(data.duration_p50_ms)}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-500 mb-1">Phân vị 95</div>
                      <div className="text-xl font-semibold tabular-nums text-ink dark:text-gray-100">
                        {formatDuration(data.duration_p95_ms)}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 3. Chi phí ước tính */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c] flex flex-col justify-center">
                  <div className="flex items-start justify-between">
                    <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-2">Chi phí ước tính</h3>
                    <a href={data.cost_estimate.source} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                      Bảng giá
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                  </div>
                  <div className="text-2xl font-semibold tabular-nums text-ink dark:text-gray-100">
                    {data.cost_estimate.estimated_usd != null ? `${data.cost_estimate.estimated_usd} ${data.cost_estimate.currency}` : "—"}
                  </div>
                  <div className="text-[11px] text-gray-400 mt-1">
                    Giá version {data.cost_estimate.pricing_version} (áp dụng từ {formatDate(data.cost_estimate.effective_at)})
                  </div>
                  <div className="mt-3 grid grid-cols-2 gap-2 border-t border-gray-100 pt-3 dark:border-gray-800">
                    <div>
                      <div className="text-[10px] uppercase tracking-wide text-gray-500">Tokens In</div>
                      <div className="text-sm font-medium tabular-nums text-gray-700 dark:text-gray-300">{data.cost_estimate.input_tokens.toLocaleString()}</div>
                    </div>
                    <div>
                      <div className="text-[10px] uppercase tracking-wide text-gray-500">Tokens Out</div>
                      <div className="text-sm font-medium tabular-nums text-gray-700 dark:text-gray-300">{data.cost_estimate.output_tokens.toLocaleString()}</div>
                    </div>
                  </div>
                  {data.cost_estimate.unknown_models && data.cost_estimate.unknown_models.length > 0 && (
                    <div className="mt-2 text-xs text-amber-600 bg-amber-50 p-1.5 rounded-md dark:bg-amber-900/20 dark:text-amber-400">
                      Cảnh báo: Không có giá cho models: {data.cost_estimate.unknown_models.join(", ")}
                    </div>
                  )}
                </div>

                {/* 4. Quyết định */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-4">Quyết định</h3>
                  <div className="flex flex-col gap-3">
                    {(filtersData?.review_decisions ?? []).map((decision) => {
                      const count = data.decision_counts[decision] || 0;
                      const config = DECISION_CONFIG[decision] || { label: decision, dot: "bg-gray-400" };
                      return (
                        <div key={decision} className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            <span className={`h-2 w-2 rounded-full ${config.dot}`}></span>
                            <span className="text-sm text-gray-600 dark:text-gray-400">{config.label}</span>
                          </div>
                          <span className="text-sm font-medium tabular-nums text-ink dark:text-gray-100">{count}</span>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* 5. Ghi ngược (Writeback) */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-4">Ghi ngược (Writeback)</h3>
                  <div className="mb-4">
                    <div className="text-sm text-gray-500 mb-1">Tỷ lệ thành công</div>
                    <div className="text-xl font-semibold tabular-nums text-ink dark:text-gray-100">
                      {data.writeback_success_rate != null
                        ? `${formatNumber(data.writeback_success_rate * 100, 1)}%`
                        : "—"}
                    </div>
                  </div>
                  <div className="space-y-2 text-sm border-t border-gray-100 pt-3 dark:border-gray-800">
                    {Object.entries(data.writeback_counts).map(([status, count]) => (
                      <div key={status} className="flex justify-between">
                        <span className="text-gray-600 dark:text-gray-400">{WRITEBACK_LABEL[status] ?? status}</span>
                        <span className="font-medium tabular-nums text-ink dark:text-gray-100">{count as number}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 6. Trạng thái hạ tầng */}
                <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
                  <h3 className="text-xs font-medium uppercase tracking-wide text-gray-500 mb-4">Trạng thái hạ tầng</h3>
                  
                  <div className="mb-5">
                    <div className="text-sm text-gray-500 mb-1.5">Worker</div>
                    {(() => {
                      const st = WORKER_STATUS_CONFIG[data.worker_status] || { label: data.worker_status, bg: "bg-gray-100", text: "text-gray-600", dot: "bg-gray-400" };
                      return (
                        <div className="mb-2">
                          <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${st.bg} ${st.text}`}>
                            <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`}></span>
                            {st.label}
                          </span>
                        </div>
                      );
                    })()}
                    <div className="text-xs text-gray-500 mt-1">
                      Hoạt động: <span className="font-medium text-gray-700 dark:text-gray-300">{data.worker_running}</span> · 
                      Stale: <span className="font-medium text-gray-700 dark:text-gray-300">{data.worker_stale}</span>
                    </div>
                    {data.worker_last_seen_at && (
                      <div className="text-xs text-gray-500 mt-1">
                        Hoạt động lần cuối: {formatDateTime(data.worker_last_seen_at)}
                      </div>
                    )}
                  </div>

                  <div className="border-t border-gray-100 pt-4 dark:border-gray-800">
                    <div className="text-sm text-gray-500 mb-1.5">Connector (CMS)</div>
                    <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium bg-gray-100 text-gray-700 dark:bg-white/10 dark:text-gray-300">
                      {data.connector_status}
                    </span>
                  </div>
                </div>

              </div>
            )}
          </section>

        </div>
      )}
    </div>
  );
}
