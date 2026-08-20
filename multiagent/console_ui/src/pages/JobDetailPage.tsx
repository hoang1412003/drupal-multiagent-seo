import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { client, ConsoleApiError } from "../api/client";
import type { JobDetail } from "../api/client";
import { RequireRole } from "../auth/RequireRole";
import { AsyncBoundary } from "./AsyncBoundary";

export function JobDetailPage() {
  const { publicId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [reason, setReason] = useState("");
  const [confirming, setConfirming] = useState(false);
  const [retryError, setRetryError] = useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["job", publicId],
    queryFn: () => client.get<JobDetail>(`/jobs/${publicId}`),
    enabled: Boolean(publicId),
  });

  const retry = useMutation({
    mutationFn: () =>
      client.post<JobDetail>(`/jobs/${publicId}/retry`, {
        // Cong an toan cua server: retry chay lai pipeline goi API TRA PHI.
        // Chi gui true sau khi nguoi dung bam xac nhan trong hop thoai.
        confirm_cost: true,
        reason: reason.trim() === "" ? null : reason,
      }),
    onSuccess: (jobMoi) => {
      setConfirming(false);
      setRetryError(null);
      queryClient.invalidateQueries({ queryKey: ["jobs"] });
      // Retry tao JOB MOI. O lai trang cu se lam nguoi dung tuong khong co
      // tac dung.
      navigate(`/jobs/${jobMoi.public_id}`, { replace: true });
    },
    onError: (caught: unknown) => {
      setRetryError(
        caught instanceof ConsoleApiError
          ? caught.message
          : "Đã xảy ra lỗi không xác định",
      );
    },
  });

  return (
    <AsyncBoundary isLoading={isLoading} error={error} data={data}>
      {(job) => (
        <>
          {/* TODO(Antigravity): dựng giao diện theo thiết kế Stitch "Job detail".
              Trường null hiện "—", không hiện ô trống và không hiện "N/A". */}
          <pre>{JSON.stringify(job, null, 2)}</pre>

          {job.status === "failed" && (
            <RequireRole role="operator">
              {confirming ? (
                <div role="dialog" aria-label="Xác nhận thử lại">
                  <p>
                    Thử lại sẽ chạy lại pipeline AI và có thể phát sinh chi phí.
                  </p>
                  {retryError && <p role="alert">{retryError}</p>}
                  <label>
                    Lý do (không bắt buộc)
                    <input value={reason} onChange={(e) => setReason(e.target.value)} />
                  </label>
                  <button
                    type="button"
                    onClick={() => retry.mutate()}
                    disabled={retry.isPending}
                  >
                    {retry.isPending ? "Đang thử lại…" : "Xác nhận thử lại"}
                  </button>
                  <button type="button" onClick={() => setConfirming(false)}>
                    Hủy
                  </button>
                </div>
              ) : (
                <button type="button" onClick={() => setConfirming(true)}>
                  Thử lại
                </button>
              )}
            </RequireRole>
          )}
        </>
      )}
    </AsyncBoundary>
  );
}
