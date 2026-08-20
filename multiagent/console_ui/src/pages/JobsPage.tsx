import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";

import { client, query, ConsoleApiError } from "../api/client";
import type { JobPage } from "../api/client";
import { useFilters } from "../api/useFilters";
import { formatDateTime, shortId, TIMEZONE_LABEL } from "../lib/format";

const STATUS_CONFIG: Record<string, { label: string, dot: string, bg: string, text: string }> = {
  queued: { label: "Trong hàng đợi", dot: "bg-amber-500", bg: "bg-amber-50 dark:bg-amber-500/15", text: "text-amber-700 dark:text-amber-300" },
  running: { label: "Đang chạy", dot: "bg-blue-500", bg: "bg-blue-50 dark:bg-blue-500/15", text: "text-blue-700 dark:text-blue-300" },
  done: { label: "Hoàn thành", dot: "bg-emerald-500", bg: "bg-emerald-50 dark:bg-emerald-500/15", text: "text-emerald-700 dark:text-emerald-300" },
  failed: { label: "Thất bại", dot: "bg-red-500", bg: "bg-red-50 dark:bg-red-500/15", text: "text-red-700 dark:text-red-300" },
  superseded: { label: "Bị thay thế", dot: "bg-gray-400", bg: "bg-gray-100 dark:bg-gray-500/15", text: "text-gray-600 dark:text-gray-300" },
};

export function JobsPage() {
  const [params, setParams] = useSearchParams();
  const { data: filtersData } = useFilters();

  // TEN THAM SO PHAI KHOP openapi.json: external_id (khong phai
  // external_content_id), from/to (khong phai date_from/date_to). Server tu
  // choi ten la bang 422 nen go sai se thay ngay, khong con im lang.
  const search = query({
    status: params.get("status") ?? undefined,
    site: params.get("site") ?? undefined,
    source: params.get("source") ?? undefined,
    external_id: params.get("external_id") ?? undefined,
    from: params.get("from") ?? undefined,
    to: params.get("to") ?? undefined,
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["jobs", search],
    queryFn: () => client.get<JobPage>(`/jobs${search}`),
    retry: false,
  });

  const [filterStatus, setFilterStatus] = useState(params.get("status") ?? "");
  const [filterSite, setFilterSite] = useState(params.get("site") ?? "");
  const [filterSource, setFilterSource] = useState(params.get("source") ?? "");
  const [filterExtId, setFilterExtId] = useState(params.get("external_id") ?? "");
  const [filterDateFrom, setFilterDateFrom] = useState(params.get("from") ?? "");
  const [filterDateTo, setFilterDateTo] = useState(params.get("to") ?? "");

  useEffect(() => {
    setFilterStatus(params.get("status") ?? "");
    setFilterSite(params.get("site") ?? "");
    setFilterSource(params.get("source") ?? "");
    setFilterExtId(params.get("external_id") ?? "");
    setFilterDateFrom(params.get("from") ?? "");
    setFilterDateTo(params.get("to") ?? "");
  }, [params]);

  const handleApplyFilters = () => {
    const newParams = new URLSearchParams();
    if (filterStatus) newParams.set("status", filterStatus);
    if (filterSite) newParams.set("site", filterSite);
    if (filterSource) newParams.set("source", filterSource);
    if (filterExtId) newParams.set("external_id", filterExtId);
    if (filterDateFrom) newParams.set("from", filterDateFrom);
    if (filterDateTo) newParams.set("to", filterDateTo);
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
    <>
      {Array.from({ length: 12 }).map((_, i) => (
        <tr key={i} className="border-b border-gray-100 dark:border-gray-800">
          {Array.from({ length: 8 }).map((_, j) => (
            <td key={j} className="px-3 py-2.5">
              <div className="h-4 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
            </td>
          ))}
        </tr>
      ))}
    </>
  );

  return (
    <>
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Job Queue</h1>
        <p className="text-sm text-gray-500">Giám sát và quản lý các tác vụ xử lý hàng loạt.</p>
      </div>

      <div className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-[#1a1c1c]">
        {is422 && (
          <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {apiError?.message || "Lỗi bộ lọc."}
          </div>
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-6">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Trạng thái</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.job_statuses.map((s) => (
                <option key={s} value={s}>{STATUS_CONFIG[s]?.label || s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Site</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterSite}
              onChange={(e) => setFilterSite(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.sites.map((s) => (
                <option key={s.slug} value={s.slug}>{s.name} {s.active ? "" : "(đã tắt)"}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Nguồn</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterSource}
              onChange={(e) => setFilterSource(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.job_sources.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">ID nội dung</label>
            <input
              type="text"
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterExtId}
              onChange={(e) => setFilterExtId(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Từ ngày</label>
            <input
              type="date"
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterDateFrom}
              onChange={(e) => setFilterDateFrom(e.target.value)}
            />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Đến ngày</label>
            <input
              type="date"
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterDateTo}
              onChange={(e) => setFilterDateTo(e.target.value)}
            />
          </div>
        </div>
        <div className="flex justify-end gap-3">
          <button
            type="button"
            className="h-9 rounded-md border border-gray-300 bg-white px-4 text-sm hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent"
            onClick={handleClearFilters}
          >
            Đặt lại
          </button>
          <button
            type="button"
            className="h-9 rounded-md bg-vf px-4 text-sm font-medium text-white hover:bg-vf-hover focus:outline-none focus:ring-2 focus:ring-vf/30 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-[#3b5bdb] dark:hover:bg-[#3b5bdb]/90"
            onClick={handleApplyFilters}
          >
            Lọc
          </button>
        </div>
      </div>

      <div className="flex flex-col overflow-hidden rounded-lg border border-gray-200 bg-white dark:border-gray-800 dark:bg-[#1a1c1c]">
        {isError && (
          <div className="m-4 flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            <span>{apiError?.message || "Đã xảy ra lỗi khi tải danh sách."}</span>
            <button
              type="button"
              className="h-9 rounded-md border border-red-200 bg-white px-4 text-sm font-medium text-red-700 hover:bg-red-50"
              onClick={() => refetch()}
            >
              Thử lại
            </button>
          </div>
        )}

        <div className="overflow-x-auto">
          <table className="w-full whitespace-nowrap text-left">
            <thead className="border-b border-gray-200 bg-gray-50/60 px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:border-gray-800 dark:bg-white/5">
              <tr>
                <th className="px-3 py-2 font-medium">Mã job</th>
                <th className="px-3 py-2 font-medium">
                  Thời gian tạo{" "}
                  <span className="font-normal normal-case text-gray-400">
                    ({TIMEZONE_LABEL})
                  </span>
                </th>
                <th className="px-3 py-2 font-medium">Site</th>
                <th className="px-3 py-2 font-medium">ID nội dung</th>
                <th className="px-3 py-2 font-medium">Trạng thái</th>
                <th className="px-3 py-2 text-right font-medium">Số lần thử</th>
                <th className="px-3 py-2 font-medium">Nguồn</th>
                <th className="px-3 py-2 font-medium">Phiên bản policy</th>
              </tr>
            </thead>
            <tbody>
              {is403 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                    Bạn không có quyền xem nội dung này.
                  </td>
                </tr>
              ) : isLoading ? (
                renderSkeleton()
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={8} className="px-3 py-8 text-center text-sm text-gray-500">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <span className="opacity-70">Chưa có job nào khớp bộ lọc</span>
                      <button
                        type="button"
                        className="h-9 rounded-md border border-gray-300 bg-white px-4 text-sm hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent"
                        onClick={handleClearFilters}
                      >
                        Xóa bộ lọc
                      </button>
                    </div>
                  </td>
                </tr>
              ) : (
                data?.items.map((job) => {
                  const st = STATUS_CONFIG[job.status] || {
                    label: job.status,
                    dot: "bg-gray-400",
                    bg: "bg-gray-100",
                    text: "text-gray-600",
                  };
                  return (
                    <tr key={job.public_id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="px-3 py-2.5 text-xs font-mono">
                        <Link to={`/jobs/${job.public_id}`} className="hover:underline text-ink dark:text-gray-100">{shortId(job.public_id)}</Link>
                      </td>
                      <td className="px-3 py-2.5 text-sm">{formatDateTime(job.created_at)}</td>
                      <td className="px-3 py-2.5 text-sm">{job.site_slug}</td>
                      <td className="px-3 py-2.5 text-xs font-mono">{job.external_content_id}</td>
                      <td className="px-3 py-2.5 text-sm">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${st.bg} ${st.text}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`}></span>
                          {st.label}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-right text-sm tabular-nums">{job.attempts}</td>
                      <td className="px-3 py-2.5 text-sm">{job.source}</td>
                      <td className="px-3 py-2.5 text-sm">{job.policy_version}</td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {data && data.total_pages > 0 && !is403 && (
          <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3 dark:border-gray-800">
            <span className="text-sm text-gray-500">
              Trang {data.page} / {data.total_pages} · {data.total} kết quả
            </span>
            <div className="flex gap-2">
              <button
                type="button"
                disabled={data.page <= 1}
                onClick={() => {
                  const newParams = new URLSearchParams(params);
                  newParams.set("page", String(data.page - 1));
                  setParams(newParams);
                }}
                className="h-9 rounded-md border border-gray-300 bg-white px-4 text-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-transparent"
              >
                Trước
              </button>
              <button
                type="button"
                disabled={data.page >= data.total_pages}
                onClick={() => {
                  const newParams = new URLSearchParams(params);
                  newParams.set("page", String(data.page + 1));
                  setParams(newParams);
                }}
                className="h-9 rounded-md border border-gray-300 bg-white px-4 text-sm hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-transparent"
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
