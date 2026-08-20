import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";

import { client, query, ConsoleApiError } from "../api/client";
import type { components } from "../api/api-types";
import { useFilters } from "../api/useFilters";
import { formatDateTime, shortId, TIMEZONE_LABEL } from "../lib/format";
import { AUDIT_OUTCOME, pillOf } from "../lib/status";
import { ErrorBanner } from "../lib/ErrorBanner";

type AuditPageResponse = components["schemas"]["AuditPage"];

function MetadataCell({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  
  if (!text) return <span className="text-gray-400 dark:text-gray-600">—</span>;
  
  const isLong = text.length > 60; // Nguong hien nut Xem

  return (
    <div className="flex flex-col gap-1 items-start max-w-full">
      {expanded ? (
        <pre className="text-xs font-mono bg-gray-50 dark:bg-gray-800/50 p-2.5 rounded-md border border-gray-200 dark:border-gray-700 whitespace-pre-wrap break-words w-full max-w-2xl text-gray-800 dark:text-gray-300">
          {text}
        </pre>
      ) : (
        <div className="truncate max-w-[24rem] text-sm text-gray-600 dark:text-gray-300" title={text}>
          {text}
        </div>
      )}
      {isLong && (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="text-xs font-medium text-vf hover:underline dark:text-[#3b5bdb]"
        >
          {expanded ? "Thu gọn" : "Xem"}
        </button>
      )}
    </div>
  );
}

export function AuditPage() {
  const [params, setParams] = useSearchParams();
  const { data: filtersData } = useFilters();

  const search = query({
    action: params.get("action") ?? undefined,
    outcome: params.get("outcome") ?? undefined,
    actor: params.get("actor") ?? undefined,
    from: params.get("from") ?? undefined,
    to: params.get("to") ?? undefined,
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["audit", search],
    queryFn: () => client.get<AuditPageResponse>(`/audit${search}`),
    retry: false,
  });

  const [filterAction, setFilterAction] = useState(params.get("action") ?? "");
  const [filterOutcome, setFilterOutcome] = useState(params.get("outcome") ?? "");
  const [filterActor, setFilterActor] = useState(params.get("actor") ?? "");
  const [filterDateFrom, setFilterDateFrom] = useState(params.get("from") ?? "");
  const [filterDateTo, setFilterDateTo] = useState(params.get("to") ?? "");

  useEffect(() => {
    setFilterAction(params.get("action") ?? "");
    setFilterOutcome(params.get("outcome") ?? "");
    setFilterActor(params.get("actor") ?? "");
    setFilterDateFrom(params.get("from") ?? "");
    setFilterDateTo(params.get("to") ?? "");
  }, [params]);

  const handleApplyFilters = () => {
    const newParams = new URLSearchParams();
    if (filterAction) newParams.set("action", filterAction);
    if (filterOutcome) newParams.set("outcome", filterOutcome);
    if (filterActor) newParams.set("actor", filterActor);
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
          {Array.from({ length: 7 }).map((_, j) => (
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
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Nhật ký thao tác</h1>
        <p className="text-sm text-gray-500">Truy vết hành động của người dùng trên hệ thống.</p>
      </div>

      <div className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-[#1a1c1c]">
        {is422 && (
          <ErrorBanner message={apiError?.message || "Lỗi bộ lọc."} />
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Hành động</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterAction}
              onChange={(e) => setFilterAction(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.audit_actions.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Kết quả</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterOutcome}
              onChange={(e) => setFilterOutcome(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.audit_outcomes.map((s) => (
                <option key={s} value={s}>{AUDIT_OUTCOME[s]?.label || s}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Người thực hiện</label>
            <input
              type="text"
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterActor}
              onChange={(e) => setFilterActor(e.target.value)}
              placeholder="Tên đăng nhập"
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
          <ErrorBanner
            inset
            message={apiError?.message || "Đã xảy ra lỗi khi tải danh sách."}
            onRetry={() => refetch()}
          />
        )}

        <div className="overflow-x-auto">
          <table className="w-full text-left">
            <thead className="border-b border-gray-200 bg-gray-50/60 px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500 whitespace-nowrap dark:border-gray-800 dark:bg-white/5">
              <tr>
                <th className="px-3 py-2 font-medium">
                  Thời gian{" "}
                  <span className="font-normal normal-case text-gray-400">
                    ({TIMEZONE_LABEL})
                  </span>
                </th>
                <th className="px-3 py-2 font-medium">Người thực hiện</th>
                <th className="px-3 py-2 font-medium">Hành động</th>
                <th className="px-3 py-2 font-medium">Đối tượng</th>
                <th className="px-3 py-2 font-medium">Kết quả</th>
                <th className="px-3 py-2 font-medium w-full">Chi tiết</th>
                <th className="px-3 py-2 text-right font-medium">Mã</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {is403 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-sm text-gray-500">
                    Bạn không có quyền xem nhật ký hệ thống.
                  </td>
                </tr>
              ) : isLoading ? (
                renderSkeleton()
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-3 py-8 text-center text-sm text-gray-500">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <span className="opacity-70">Chưa có bản ghi nào khớp bộ lọc</span>
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
                data?.items.map((item) => {
                  const outPill = pillOf(AUDIT_OUTCOME, item.outcome);
                  return (
                    <tr key={item.id}>
                      <td className="px-3 py-2.5 text-sm whitespace-nowrap align-top">{formatDateTime(item.created_at)}</td>
                      <td className="px-3 py-2.5 text-sm whitespace-nowrap align-top">{item.actor_username}</td>
                      <td className="px-3 py-2.5 text-sm whitespace-nowrap align-top">
                        <span className="inline-flex items-center rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-300">
                          {item.action}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 align-top whitespace-nowrap">
                        <div className="text-sm">{item.target_type}</div>
                        {item.target_id && (
                          <div className="text-xs text-gray-400 font-mono mt-0.5">{shortId(item.target_id)}</div>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-sm whitespace-nowrap align-top">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${outPill.bg} ${outPill.text}`}>
                          <span className={`h-1.5 w-1.5 rounded-full ${outPill.dot}`}></span>
                          {outPill.label}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 align-top">
                        <MetadataCell text={item.metadata_text} />
                      </td>
                      <td className="px-3 py-2.5 text-right text-sm font-mono text-gray-500 whitespace-nowrap align-top">
                        {item.id}
                      </td>
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
              Trang {data.page} / {data.total_pages} · {data.total} bản ghi
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
