import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { client, query } from "../api/client";
import type { JobPage } from "../api/client";
import { AsyncBoundary } from "./AsyncBoundary";

export function JobsPage() {
  const [params] = useSearchParams();
  const search = query({
    status: params.get("status") ?? undefined,
    site: params.get("site") ?? undefined,
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["jobs", search],
    queryFn: () => client.get<JobPage>(`/jobs${search}`),
  });

  return (
    <AsyncBoundary
      isLoading={isLoading}
      error={error}
      data={data}
      isEmpty={(page) => page.items.length === 0}
      emptyText="Chưa có job nào khớp bộ lọc"
    >
      {(page) => (
        // TODO(Antigravity): dựng bảng theo thiết kế Stitch "Jobs".
        // Dữ liệu đã có trong page.items; KHÔNG gọi fetch trực tiếp.
        <pre>{JSON.stringify(page, null, 2)}</pre>
      )}
    </AsyncBoundary>
  );
}
