import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { useState, useEffect } from "react";

import { client, query, ConsoleApiError } from "../api/client";
import type { ReviewPage } from "../api/client";
import { useFilters } from "../api/useFilters";
import { formatDateTime, formatNumber, shortId, TIMEZONE_LABEL } from "../lib/format";
import { REVIEW_DECISION } from "../lib/status";
import { ErrorBanner } from "../lib/ErrorBanner";

export function ReviewsPage() {
  const [params, setParams] = useSearchParams();
  const { data: filtersData } = useFilters();

  const search = query({
    decision: params.get("decision") ?? undefined,
    site: params.get("site") ?? undefined,
    external_id: params.get("external_id") ?? undefined,
    from: params.get("from") ?? undefined,
    to: params.get("to") ?? undefined,
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["reviews", search],
    queryFn: () => client.get<ReviewPage>(`/reviews${search}`),
    retry: false,
  });

  const [filterDecision, setFilterDecision] = useState(params.get("decision") ?? "");
  const [filterSite, setFilterSite] = useState(params.get("site") ?? "");
  const [filterExtId, setFilterExtId] = useState(params.get("external_id") ?? "");
  const [filterDateFrom, setFilterDateFrom] = useState(params.get("from") ?? "");
  const [filterDateTo, setFilterDateTo] = useState(params.get("to") ?? "");

  useEffect(() => {
    setFilterDecision(params.get("decision") ?? "");
    setFilterSite(params.get("site") ?? "");
    setFilterExtId(params.get("external_id") ?? "");
    setFilterDateFrom(params.get("from") ?? "");
    setFilterDateTo(params.get("to") ?? "");
  }, [params]);

  const handleApplyFilters = () => {
    const newParams = new URLSearchParams();
    if (filterDecision) newParams.set("decision", filterDecision);
    if (filterSite) newParams.set("site", filterSite);
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
          {Array.from({ length: 10 }).map((_, j) => (
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
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">AI Reviews</h1>
        <p className="text-sm text-gray-500">
          Danh sách kết quả AI duyệt nội dung. Danh sách này gồm mọi thời điểm
          và cả dữ liệu mẫu, nên tổng số ở đây không khớp với &ldquo;Tổng số
          review&rdquo; trên Tổng quan &mdash; trang đó chỉ tính 7 ngày gần nhất
          và bỏ dữ liệu mẫu.
        </p>
      </div>

      <div className="flex flex-col gap-4 rounded-lg border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-[#1a1c1c]">
        {is422 && (
          <ErrorBanner message={apiError?.message || "Lỗi bộ lọc."} />
        )}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-5">
          <div>
            <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-gray-500">Quyết định</label>
            <select
              className="h-9 w-full rounded-md border border-gray-300 bg-white px-3 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314]"
              value={filterDecision}
              onChange={(e) => setFilterDecision(e.target.value)}
            >
              <option value="">Tất cả</option>
              {filtersData?.review_decisions.map((s) => (
                <option key={s} value={s}>{REVIEW_DECISION[s]?.label || s}</option>
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
          <ErrorBanner
            inset
            message={apiError?.message || "Đã xảy ra lỗi khi tải danh sách."}
            onRetry={() => refetch()}
          />
        )}

        <div className="overflow-x-auto">
          <table className="w-full whitespace-nowrap text-left">
            <thead className="border-b border-gray-200 bg-gray-50/60 px-3 py-2 text-left text-xs font-medium uppercase tracking-wide text-gray-500 dark:border-gray-800 dark:bg-white/5">
              <tr>
                <th className="px-3 py-2 font-medium">Mã review</th>
                <th className="px-3 py-2 font-medium">
                  Thời gian chấm{" "}
                  <span className="font-normal normal-case text-gray-400">
                    ({TIMEZONE_LABEL})
                  </span>
                </th>
                <th className="px-3 py-2 font-medium">Site</th>
                <th className="px-3 py-2 font-medium">ID nội dung</th>
                <th className="px-3 py-2 font-medium">Quyết định</th>
                <th className="px-3 py-2 text-right font-medium">Điểm</th>
                <th className="px-3 py-2 font-medium">Hồ sơ</th>
                <th className="px-3 py-2 font-medium">Phiên bản policy</th>
                <th className="px-3 py-2 font-medium">Model</th>
                <th className="px-3 py-2 font-medium">Dữ liệu mẫu</th>
              </tr>
            </thead>
            <tbody>
              {is403 ? (
                <tr>
                  <td colSpan={10} className="px-3 py-8 text-center text-sm text-gray-500">
                    Bạn không có quyền xem nội dung này.
                  </td>
                </tr>
              ) : isLoading ? (
                renderSkeleton()
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={10} className="px-3 py-8 text-center text-sm text-gray-500">
                    <div className="flex flex-col items-center justify-center gap-3">
                      <span className="opacity-70">Chưa có review nào khớp bộ lọc</span>
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
                data?.items.map((review) => {
                  let badge = null;
                  if (review.decision) {
                    const st = REVIEW_DECISION[review.decision] || {
                      label: review.decision,
                      dot: "bg-gray-400",
                      bg: "bg-gray-100",
                      text: "text-gray-600",
                    };
                    badge = (
                      <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${st.bg} ${st.text}`}>
                        <span className={`h-1.5 w-1.5 rounded-full ${st.dot}`}></span>
                        {st.label}
                      </span>
                    );
                  } else {
                    badge = <span className="text-gray-400">—</span>;
                  }
                  
                  return (
                    <tr key={review.public_id} className="border-b border-gray-100 dark:border-gray-800">
                      <td className="px-3 py-2.5 text-xs font-mono">
                        <Link to={`/reviews/${review.public_id}`} className="hover:underline text-ink dark:text-gray-100">{shortId(review.public_id)}</Link>
                      </td>
                      <td className="px-3 py-2.5 text-sm">{formatDateTime(review.scored_at)}</td>
                      <td className="px-3 py-2.5 text-sm">{review.site_slug}</td>
                      <td className="px-3 py-2.5 text-xs font-mono">{review.external_content_id}</td>
                      <td className="px-3 py-2.5 text-sm">{badge}</td>
                      <td className="px-3 py-2.5 text-right text-sm font-mono tabular-nums">
                        {formatNumber(review.final_score)}
                      </td>
                      <td className="px-3 py-2.5 text-sm">{review.profile_code}</td>
                      <td className="px-3 py-2.5 text-sm">{review.policy_version}</td>
                      <td className="px-3 py-2.5 text-sm">
                        <span className="block max-w-[150px] truncate" title={review.model}>
                          {review.model}
                        </span>
                      </td>
                      <td className="px-3 py-2.5 text-sm">
                        {review.is_fixture && (
                          <span className="inline-flex items-center rounded bg-gray-100 px-1.5 py-0.5 text-[10px] font-medium text-gray-600 dark:bg-white/10 dark:text-gray-300">
                            mẫu
                          </span>
                        )}
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
