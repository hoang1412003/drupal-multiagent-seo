import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/api-types";
import { client } from "../api/client";
import { formatDateTime, TIMEZONE_LABEL } from "../lib/format";
import { ErrorBanner } from "../lib/ErrorBanner";
import { EVALUATION_STATUS, pillOf } from "../lib/status";
import { StatusPill } from "../lib/StatusPill";
import { Field, Panel } from "../lib/DetailLayout";

type EvaluationResponse = components["schemas"]["EvaluationResponse"];

export function EvaluationPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["evaluation"],
    queryFn: () => client.get<EvaluationResponse>("/evaluation"),
    retry: false,
  });

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Kết quả đo</h1>
        <p className="text-sm text-gray-500">Xem báo cáo các phép đo đánh giá mô hình.</p>
      </div>
      <div className="h-48 w-full animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"></div>
      <div className="h-48 w-full animate-pulse rounded-lg bg-gray-200 dark:bg-gray-700"></div>
    </div>
  );

  if (isLoading) return renderSkeleton();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Kết quả đo</h1>
        <p className="text-sm text-gray-500">Xem báo cáo các phép đo đánh giá mô hình.</p>
      </div>

      {error && <ErrorBanner message="Không thể tải dữ liệu đánh giá." />}

      {!error && (!data?.experiments || data.experiments.length === 0) && (
        <Panel>
          <p className="text-sm text-gray-500">Chưa có dữ liệu</p>
        </Panel>
      )}

      {!error && data?.experiments && data.experiments.map((exp) => (
        <Panel key={exp.experiment} className="mb-6 last:mb-0">
          {exp.provenance_warning && (
            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800 dark:border-amber-900/50 dark:bg-amber-900/20 dark:text-amber-300 flex items-start gap-2">
              <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <span>{exp.provenance_warning}</span>
            </div>
          )}
          
          <div className="flex items-start justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{exp.experiment}</h2>
            {exp.has_evidence && (
              <a 
                href={`/api/console/v1/evaluation/evidence/${exp.experiment}`}
                className="inline-flex h-8 items-center justify-center rounded-md border border-gray-300 bg-white px-3 text-sm font-medium hover:bg-gray-50 dark:border-gray-700 dark:bg-transparent dark:hover:bg-white/5 transition-colors"
                download
              >
                Tải bằng chứng
              </a>
            )}
          </div>
          
          <dl className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            <Field label="Trạng thái">
              <StatusPill style={pillOf(EVALUATION_STATUS, exp.status)} />
            </Field>
            <Field label={`Chạy lúc (${TIMEZONE_LABEL})`}>{formatDateTime(exp.run_at)}</Field>
            <Field label="Model">{exp.model}</Field>
            <Field label="Đường dẫn điểm (Score Path)">{exp.score_path_snapshot}</Field>
            <Field label="Commit Hash (Head Commit)" mono>{exp.head_commit}</Field>
            <Field label="Phiên bản Prompt (Prompt Version)" mono>{exp.prompt_version}</Field>
            <Field label="Đường dẫn bằng chứng">{exp.evidence_path}</Field>
            <Field label="Metadata hoàn chỉnh">{exp.metadata_complete ? "Có" : "Không"}</Field>
            
            <div className="sm:col-span-full mt-2">
              <dt className="text-sm font-medium text-gray-500 mb-2">Tóm tắt kết quả (Summary)</dt>
              <dd className="text-sm text-ink dark:text-gray-200 bg-gray-50 dark:bg-[#111314] p-4 rounded-md border border-gray-200 dark:border-gray-700 whitespace-pre-wrap break-words">
                {exp.summary ?? "—"}
              </dd>
            </div>
          </dl>
        </Panel>
      ))}
    </div>
  );
}
