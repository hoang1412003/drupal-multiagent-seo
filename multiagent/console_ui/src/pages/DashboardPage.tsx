import { useQuery } from "@tanstack/react-query";

import { client } from "../api/client";
import type { DashboardResponse } from "../api/client";
import { AsyncBoundary } from "./AsyncBoundary";

export function DashboardPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => client.get<DashboardResponse>("/dashboard"),
  });

  return (
    <AsyncBoundary isLoading={isLoading} error={error} data={data}>
      {(view) => (
        // TODO(Antigravity): dựng giao diện theo thiết kế Stitch "Dashboard".
        // Lưu ý worker_status có BA giá trị (running/stale/unavailable), gộp
        // hai cái sau lại sẽ che mất một sự cố thật.
        <pre>{JSON.stringify(view, null, 2)}</pre>
      )}
    </AsyncBoundary>
  );
}
