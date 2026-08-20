import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";

import { client, query } from "../api/client";
import type { ReviewPage } from "../api/client";
import { AsyncBoundary } from "./AsyncBoundary";

export function ReviewsPage() {
  const [params] = useSearchParams();
  const search = query({
    decision: params.get("decision") ?? undefined,
    site: params.get("site") ?? undefined,
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error } = useQuery({
    queryKey: ["reviews", search],
    queryFn: () => client.get<ReviewPage>(`/reviews${search}`),
  });

  return (
    <AsyncBoundary
      isLoading={isLoading}
      error={error}
      data={data}
      isEmpty={(page) => page.items.length === 0}
      emptyText="Chưa có review nào khớp bộ lọc"
    >
      {(page) => (
        // TODO(Antigravity): dựng bảng theo thiết kế Stitch "Reviews".
        // Dropdown lọc: dùng useFilters() trong src/api/useFilters.ts.
        // KHÔNG viết cứng danh sách trạng thái/quyết định.
        // final_score có thể null - hiện "—", đừng hiện 0.
        <pre>{JSON.stringify(page, null, 2)}</pre>
      )}
    </AsyncBoundary>
  );
}
