import { useQuery } from "@tanstack/react-query";
import { useParams } from "react-router-dom";

import { client } from "../api/client";
import type { ReviewDetail } from "../api/client";
import { AsyncBoundary } from "./AsyncBoundary";

export function ReviewDetailPage() {
  const { publicId } = useParams();

  const { data, isLoading, error } = useQuery({
    queryKey: ["review", publicId],
    queryFn: () => client.get<ReviewDetail>(`/reviews/${publicId}`),
    enabled: Boolean(publicId),
  });

  return (
    <AsyncBoundary isLoading={isLoading} error={error} data={data}>
      {(review) => (
        // TODO(Antigravity): dựng giao diện theo thiết kế Stitch "Review detail".
        // Màn hình này CHỈ ĐỌC - không có nút duyệt/từ chối trong API.
        // CẤM dangerouslySetInnerHTML: agents[].criteria/issues/evidence bắt
        // nguồn từ output của model.
        <pre>{JSON.stringify(review, null, 2)}</pre>
      )}
    </AsyncBoundary>
  );
}
