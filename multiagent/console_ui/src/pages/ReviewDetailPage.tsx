import { useQuery } from "@tanstack/react-query";
import { useParams, Link } from "react-router-dom";
import { useState } from "react";

import { client, ConsoleApiError } from "../api/client";
import type { ReviewDetail } from "../api/client";
import type { components } from "../api/api-types";
import { formatDate, formatDateTime, formatNumber, shortId, TIMEZONE_LABEL } from "../lib/format";
import { REVIEW_DECISION, WRITEBACK_STATUS, pillOf } from "../lib/status";
import { StatusPill } from "../lib/StatusPill";
import { Field, Section } from "../lib/DetailLayout";

function ConfigMeta({ data }: { data: unknown }) {
  const [open, setOpen] = useState(false);
  if (data == null) return <>—</>;
  return (
    <div className="mt-1">
      <button type="button" onClick={() => setOpen(!open)} className="text-xs text-blue-600 hover:underline mb-1">
        {open ? "Thu gọn config_meta" : "Xem config_meta"}
      </button>
      {open && (
        <pre className="text-[11px] font-mono bg-gray-50 dark:bg-gray-900/50 p-3 rounded border border-gray-100 dark:border-gray-800 overflow-x-auto mt-2">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

function renderValue(val: unknown) {
  if (val === "[đã ẩn]") {
    return <span className="inline-flex items-center gap-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-white/10 dark:text-gray-400">[đã ẩn]</span>;
  }
  if (typeof val === 'object' && val !== null) {
    return JSON.stringify(val, null, 2);
  }
  return String(val);
}

function AgentDataList({ items }: { items: Record<string, unknown>[] }) {
  if (!items || items.length === 0) return <p className="text-sm text-gray-500 italic">Không có dữ liệu.</p>;
  return (
    <ul className="space-y-3">
      {items.map((row, i) => (
        <li key={i} className="rounded-md border border-gray-100 bg-gray-50/50 p-3 dark:border-gray-800 dark:bg-white/5">
          <dl className="space-y-2">
            {Object.entries(row).map(([key, val]) => (
              <div key={key} className="flex flex-col sm:flex-row sm:gap-4">
                <dt className="text-xs font-medium text-gray-500 sm:w-1/3 md:w-1/4 break-words pt-0.5">{key}</dt>
                <dd className="text-sm text-ink dark:text-gray-200 sm:w-2/3 md:w-3/4 whitespace-pre-wrap break-words">
                  {renderValue(val)}
                </dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}

function AgentCard({ agent }: { agent: components["schemas"]["AgentResultModel"] }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="rounded-lg border border-gray-200 bg-white overflow-hidden dark:border-gray-800 dark:bg-[#1a1c1c]">
      <button 
        type="button" 
        onClick={() => setOpen(!open)} 
        className="flex w-full items-center justify-between bg-gray-50/60 px-4 py-3 hover:bg-gray-100 dark:bg-white/5 dark:hover:bg-white/10 focus:outline-none focus:bg-gray-100 dark:focus:bg-white/10 transition-colors"
      >
        <div className="flex items-center gap-3">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">{agent.name}</h3>
          {agent.score !== null && (
            <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-xs font-medium text-blue-700 border border-blue-200/60 dark:bg-blue-900/20 dark:text-blue-400 dark:border-blue-800/60">
              Điểm: {agent.score}
            </span>
          )}
        </div>
        <span className="text-xs text-gray-500 font-medium tracking-wide uppercase">{open ? "Thu gọn" : "Mở rộng"}</span>
      </button>
      {open && (
         <div className="p-4 border-t border-gray-200 dark:border-gray-800 space-y-6">
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Tiêu chí (Criteria)</h4>
              <AgentDataList items={agent.criteria as Record<string, unknown>[]} />
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Vấn đề (Issues)</h4>
              <AgentDataList items={agent.issues as Record<string, unknown>[]} />
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">Bằng chứng (Evidence)</h4>
              <AgentDataList items={agent.evidence as Record<string, unknown>[]} />
            </div>
         </div>
      )}
    </div>
  );
}

/** ms -> "6,5 giây" khi >= 1000ms, nguoc lai giu "820 ms". */
function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined) return "—";
  if (ms < 1000) return `${formatNumber(ms, 0)} ms`;
  return `${formatNumber(ms / 1000, 1)} giây`;
}

export function ReviewDetailPage() {
  const { publicId } = useParams();

  const { data: review, isLoading, error, refetch } = useQuery({
    queryKey: ["review", publicId],
    queryFn: () => client.get<ReviewDetail>(`/reviews/${publicId}`),
    enabled: Boolean(publicId),
    retry: false,
  });

  const apiError = error instanceof ConsoleApiError ? error : null;
  const is403 = apiError?.status === 403;
  const is404 = apiError?.status === 404;
  const isError = error && !is403 && !is404;

  const renderSkeleton = () => (
    <div className="flex flex-col gap-6 animate-pulse">
      {[...Array(5)].map((_, i) => (
        <div key={i} className="h-40 bg-gray-200 dark:bg-gray-800 rounded-lg w-full"></div>
      ))}
    </div>
  );

  return (
    <div className="flex flex-col gap-6 max-w-5xl">
      <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold text-ink dark:text-gray-100 flex items-center gap-2">
            Chi tiết Review
            {review && (
              <span className="font-mono text-sm text-gray-500 font-normal">
                {shortId(review.public_id)}
              </span>
            )}
            {review?.is_fixture && (
              <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-white/10 dark:text-gray-400">
                mẫu
              </span>
            )}
          </h1>
          <div className="text-sm text-gray-500 mt-1">
            <Link to="/reviews" className="text-blue-600 hover:underline">&larr; Quay lại danh sách</Link>
          </div>
        </div>
      </div>

      {is403 && (
        <div className="rounded-md border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
          Bạn không có quyền xem nội dung này.
        </div>
      )}

      {is404 && (
        <div className="rounded-md border border-gray-200 bg-white p-8 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
          Không tìm thấy review
        </div>
      )}

      {isError && (
        <div className="flex items-center justify-between rounded-md border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          <span>{apiError?.message || "Đã xảy ra lỗi khi tải dữ liệu."}</span>
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

      {review && (
        <div className="flex flex-col gap-6">
          
          {review.missing_agents && review.missing_agents.length > 0 && (
            <div className="rounded-md border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-200">
              <strong className="font-semibold">Cảnh báo:</strong> Kết quả review này không đầy đủ do các agent sau không phản hồi:{" "}
              <span className="font-mono bg-amber-100 dark:bg-amber-900/40 px-1 rounded">{review.missing_agents.join(", ")}</span>
            </div>
          )}

          <Section title="Kết luận">
            <Field label="Quyết định (decision)">
              {(() => {
                if (!review.decision) return "—";
                const config = pillOf(REVIEW_DECISION, review.decision);
                return (
                  <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium ${config.bg} ${config.text}`}>
                    <span className={`h-1.5 w-1.5 rounded-full ${config.dot}`}></span>
                    {config.label}
                  </span>
                );
              })()}
            </Field>
            <Field label="Điểm (final_score)" mono>
              {formatNumber(review.final_score)}
            </Field>
            <div className="sm:col-span-1"></div> {/* Spacer for 3-col grid */}

            {review.veto_reason && (
              <Field label="Lý do phủ quyết (veto_reason)" colSpan>
                <div className="rounded bg-red-50 p-3 text-sm text-red-800 border border-red-200 dark:bg-red-900/20 dark:border-red-900/50 dark:text-red-300 font-medium">
                  {review.veto_reason}
                </div>
              </Field>
            )}

            <Field label="Ghi chú (note)" colSpan>
              {review.note ? (
                <div className="whitespace-pre-wrap">{review.note}</div>
              ) : "—"}
            </Field>
          </Section>

          <section>
            <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100 px-1">
              Kết quả từng agent
            </h2>
            {review.agents && review.agents.length > 0 ? (
              <div className="flex flex-col gap-4">
                {review.agents.map((agent, idx) => (
                  <AgentCard key={idx} agent={agent as any} />
                ))}
              </div>
            ) : (
              <div className="rounded-lg border border-gray-200 bg-white p-6 text-center text-sm text-gray-500 dark:border-gray-800 dark:bg-[#1a1c1c]">
                Không có dữ liệu agent.
              </div>
            )}
          </section>

          <Section title="Vận hành">
            <Field label="Thời lượng xử lý">
              {formatDuration(review.duration_ms)}
            </Field>
            <Field label="Model">{review.model}</Field>
            <Field label="Có dữ liệu usage">{review.usage_available ? "Có" : "Không"}</Field>
            
            <Field label="Chi phí ước tính" colSpan>
              {review.cost_estimate ? (
                <div className="rounded-md border border-gray-100 bg-gray-50 p-4 dark:border-gray-800 dark:bg-white/5 max-w-2xl">
                  <div className="flex items-center justify-between mb-3 border-b border-gray-200 dark:border-gray-700 pb-2">
                    <span className="font-medium text-ink dark:text-gray-100">
                      {review.cost_estimate.estimated_usd != null ? `${review.cost_estimate.estimated_usd} ${review.cost_estimate.currency}` : "—"}
                    </span>
                    <a href={review.cost_estimate.source} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline flex items-center gap-1">
                      Bảng giá
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                    </a>
                  </div>
                  <div className="grid grid-cols-2 gap-4 mb-2">
                    <div>
                      <span className="block text-xs text-gray-500">Token vào</span>
                      <span className="font-mono text-sm">{review.cost_estimate.input_tokens.toLocaleString()}</span>
                    </div>
                    <div>
                      <span className="block text-xs text-gray-500">Token ra</span>
                      <span className="font-mono text-sm">{review.cost_estimate.output_tokens.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="text-[11px] text-gray-400 mt-2">
                    Bảng giá v{review.cost_estimate.pricing_version} (Áp dụng từ: {formatDate(review.cost_estimate.effective_at)})
                  </div>
                  {review.cost_estimate.unknown_models && review.cost_estimate.unknown_models.length > 0 && (
                    <div className="mt-3 text-xs text-amber-600 bg-amber-50 p-2 rounded-md border border-amber-100 dark:bg-amber-900/20 dark:border-amber-900/30 dark:text-amber-400">
                      Không có giá cho models: {review.cost_estimate.unknown_models.join(", ")}
                    </div>
                  )}
                </div>
              ) : "—"}
            </Field>
          </Section>

          <Section title="Ghi ngược (Writeback)">
            <Field label="Trạng thái">
              {review.writeback_status ? (
                <StatusPill style={pillOf(WRITEBACK_STATUS, review.writeback_status)} />
              ) : "—"}
            </Field>
            {review.writeback_error && (
              <Field label="Lỗi ghi ngược (writeback_error)" colSpan mono>
                <div className="max-h-64 overflow-y-auto rounded bg-gray-50 p-3 text-xs text-red-600 whitespace-pre-wrap break-words dark:bg-gray-900/50 dark:text-red-400">
                  {review.writeback_error}
                </div>
              </Field>
            )}
          </Section>

          <Section title="Ngữ cảnh">
            <Field label="Mã review (public_id)" mono>{review.public_id}</Field>
            <Field label="Correlation ID" mono>{review.correlation_id}</Field>
            <Field label={`Thời gian chấm (${TIMEZONE_LABEL})`}>{formatDateTime(review.scored_at)}</Field>

            <Field label="Site">{review.site_name} ({review.site_slug})</Field>
            <Field label="Site ID" mono>{review.site_id}</Field>
            <Field label="Link Drupal">
              {review.drupal_url ? (
                <a href={review.drupal_url} target="_blank" rel="noreferrer" className="text-blue-600 hover:underline inline-flex items-center gap-1">
                  Mở bài viết
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                </a>
              ) : "—"}
            </Field>

            <Field label="Hồ sơ (profile)">{review.profile_code}</Field>
            <Field label="Profile ID" mono>{review.profile_id}</Field>
            <Field label="Phiên bản policy">{review.policy_version}</Field>
            
            <Field label="ID nội dung (external_content_id)" mono>{review.external_content_id}</Field>
            <Field label="Revision ID (external_revision_id)" mono>{review.external_revision_id}</Field>
            <Field label="Loại nội dung">{review.content_type}</Field>
            
            <Field label="Ngôn ngữ (langcode)">{review.langcode}</Field>
            <Field label="Dữ liệu mẫu">{review.is_fixture ? "Phải" : "Không"}</Field>
            <Field label="Cấu hình (config_meta)" colSpan>
              <ConfigMeta data={review.config_meta} />
            </Field>
          </Section>

        </div>
      )}
    </div>
  );
}
