import { useQuery } from "@tanstack/react-query";
import type { components } from "../api/api-types";
import { client } from "../api/client";
import { formatDateTime, TIMEZONE_LABEL } from "../lib/format";
import { ErrorBanner } from "../lib/ErrorBanner";
import { BOOLEAN_PILLS, pillOf } from "../lib/status";
import { StatusPill } from "../lib/StatusPill";

type ConfigKbResponse = components["schemas"]["ConfigKbResponse"];

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
      {children}
    </section>
  );
}

function Card({ children, isError = false }: { children: React.ReactNode, isError?: boolean }) {
  return (
    <div className={`p-4 rounded-md border ${isError ? "border-red-300 bg-red-50 dark:border-red-900/50 dark:bg-red-900/10" : "border-gray-100 bg-gray-50/50 dark:border-gray-800 dark:bg-gray-800/30"} mb-4 last:mb-0`}>
      <dl className="grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-4">
        {children}
      </dl>
    </div>
  );
}

export function ConfigKbPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["configKb"],
    queryFn: () => client.get<ConfigKbResponse>("/config-kb"),
    retry: false,
  });

  const renderSkeleton = () => (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Cấu hình & Kho tri thức</h1>
        <p className="text-sm text-gray-500">Xem chi tiết chính sách và thiết lập AI.</p>
      </div>
      <Section title="File chính sách">
        <div className="h-32 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
      </Section>
      <Section title="Site và hồ sơ">
        <div className="h-32 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
      </Section>
      <Section title="Kho tri thức">
        <div className="h-32 w-full animate-pulse rounded bg-gray-200 dark:bg-gray-700"></div>
      </Section>
    </div>
  );

  if (isLoading) return renderSkeleton();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Cấu hình & Kho tri thức</h1>
        <p className="text-sm text-gray-500">Xem chi tiết chính sách và thiết lập AI.</p>
      </div>

      {error && <ErrorBanner message="Không thể tải dữ liệu cấu hình." />}

      {!error && (
        <>
          <Section title="File chính sách">
            {(!data?.policy_files || data.policy_files.length === 0) ? (
              <p className="text-sm text-gray-500">Chưa có dữ liệu</p>
            ) : (
              data.policy_files.map((pf, idx) => (
                <Card key={idx} isError={Boolean(pf.error)}>
                  {pf.error && (
                    <div className="sm:col-span-full mb-2 flex items-start gap-2 text-sm text-red-700 dark:text-red-400">
                      <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                      </svg>
                      <span>Lỗi đọc file: {pf.error}</span>
                    </div>
                  )}
                  <Field label="Nhãn">{pf.label}</Field>
                  <Field label="Đường dẫn">{pf.relative_path}</Field>
                  <Field label="Mã SHA-256" mono>
                    <span title={pf.sha256}>{pf.sha256 ? pf.sha256.substring(0, 12) : "—"}</span>
                  </Field>
                  <Field label={`Cập nhật lúc (${TIMEZONE_LABEL})`}>{formatDateTime(pf.modified_at)}</Field>
                  {!pf.error && pf.metadata && pf.metadata.length > 0 && (
                    <div className="sm:col-span-full mt-2">
                      <dt className="text-sm font-medium text-gray-500 mb-2">Metadata</dt>
                      <dd>
                        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                          {pf.metadata.map((m, mIdx) => (
                            <li key={mIdx} className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-[#111314] px-2 py-1.5 rounded border border-gray-200 dark:border-gray-700 break-all">
                              <span className="font-medium text-gray-500 dark:text-gray-400 mr-2">{m.label}:</span>
                              {m.value && m.value.length > 32 ? (
                                <span className="font-mono text-xs">{m.value}</span>
                              ) : (m.value ?? "—")}
                            </li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                  )}
                </Card>
              ))
            )}
          </Section>

          <Section title="Site và hồ sơ">
            {(!data?.profile_assignments || data.profile_assignments.length === 0) ? (
              <p className="text-sm text-gray-500">Chưa có dữ liệu</p>
            ) : (
              data.profile_assignments.map((pa, idx) => (
                <Card key={idx}>
                  <Field label="Site">{pa.site_name} <span className="text-gray-400 text-xs ml-1">({pa.site_slug})</span></Field>
                  <Field label="Connector">{pa.connector_type}</Field>
                  <Field label="Trạng thái Site">
                    <StatusPill style={pillOf(BOOLEAN_PILLS.SITE_ACTIVE, String(pa.site_active))} />
                  </Field>
                  <Field label="Tiếp nhận">
                    <StatusPill style={pillOf(BOOLEAN_PILLS.INTAKE_PAUSED, String(pa.intake_paused))} />
                  </Field>
                  <Field label="Hồ sơ (Profile)" mono>{pa.profile_code}</Field>
                  <Field label="Thị trường (Market)" mono>{pa.market_code}</Field>
                  <Field label="Ngôn ngữ" mono>{pa.language_code}</Field>
                  <Field label="Loại nội dung">{pa.content_type}</Field>
                  <Field label="Trạng thái hồ sơ">{pa.profile_status}</Field>
                  <Field label="Phiên bản Policy">{pa.policy_version}</Field>
                  
                  {pa.policy_metadata && pa.policy_metadata.length > 0 && (
                    <div className="sm:col-span-full mt-2">
                      <dt className="text-sm font-medium text-gray-500 mb-2">Policy Metadata</dt>
                      <dd>
                        <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2">
                          {pa.policy_metadata.map((m, mIdx) => (
                            <li key={mIdx} className="text-sm text-gray-700 dark:text-gray-300 bg-white dark:bg-[#111314] px-2 py-1.5 rounded border border-gray-200 dark:border-gray-700 break-all">
                              <span className="font-medium text-gray-500 dark:text-gray-400 mr-2">{m.label}:</span>
                              {m.value && m.value.length > 32 ? (
                                <span className="font-mono text-xs">{m.value}</span>
                              ) : (m.value ?? "—")}
                            </li>
                          ))}
                        </ul>
                      </dd>
                    </div>
                  )}
                </Card>
              ))
            )}
          </Section>

          <Section title="Kho tri thức">
            {(!data?.kb_summary || data.kb_summary.length === 0) ? (
              <p className="text-sm text-gray-500">Chưa có dữ liệu</p>
            ) : (
              data.kb_summary.map((kb, idx) => (
                <Card key={idx}>
                  <Field label="Collection">{kb.collection}</Field>
                  <Field label="Loại nội dung">{kb.content_type}</Field>
                  <Field label="Ngôn ngữ" mono>{kb.langcode}</Field>
                  <div className="sm:col-span-1">
                    <dt className="text-sm font-medium text-gray-500 mb-1">Số lượng Chunk</dt>
                    <dd className="text-sm text-right tabular-nums text-ink dark:text-gray-200">{kb.chunk_count ?? "—"}</dd>
                  </div>
                  <Field label="Mô hình nhúng (Embedding)">{kb.embedding_model ?? "—"}</Field>
                  <Field label="Chiều nhúng">{kb.embedding_dimension ?? "—"}</Field>
                  <Field label="Metadata trích xuất" colSpan>{kb.metadata_excerpt}</Field>
                </Card>
              ))
            )}
          </Section>
        </>
      )}
    </div>
  );
}
