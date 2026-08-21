import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import type { components } from "../api/api-types";
import { client, ConsoleApiError, query } from "../api/client";
import { useAuth } from "../auth/AuthProvider";
import { useFilters } from "../api/useFilters";
import { formatDateTime, TIMEZONE_LABEL } from "../lib/format";
import { ErrorBanner } from "../lib/ErrorBanner";
import { USER_ROLE, USER_ACTIVE, pillOf } from "../lib/status";
import { StatusPill } from "../lib/StatusPill";

type UserModel = components["schemas"]["UserModel"];
type UserPage = components["schemas"]["UserPage"];
type TemporaryPasswordResponse = components["schemas"]["TemporaryPasswordResponse"];

type ModalState = {
  type: "role" | "lock" | "unlock" | "reset";
  user: UserModel;
} | null;

export function UsersPage() {
  const [params, setParams] = useSearchParams();
  const { data: filtersData } = useFilters();
  const { user: authUser } = useAuth();

  const search = query({
    page: params.get("page") ?? undefined,
  });

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["users", search],
    queryFn: () => client.get<UserPage>(`/users${search}`),
    retry: false,
  });

  const apiError = error instanceof ConsoleApiError ? error : null;
  const is403 = apiError?.status === 403;
  const is422 = apiError?.status === 422;
  const isGenericError = error && !is403 && !is422;

  // Create form state
  const [newUsername, setNewUsername] = useState("");
  const [newRole, setNewRole] = useState("viewer");
  const [createErrors, setCreateErrors] = useState<{ username?: string; role?: string; generic?: string }>({});
  
  const [tempPassword, setTempPassword] = useState<{ username: string; pass: string } | null>(null);

  // Modal state
  const [modalState, setModalState] = useState<ModalState>(null);
  const [modalRole, setModalRole] = useState("");
  const [actionError, setActionError] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (body: { username: string; role: string }) => 
      client.post<TemporaryPasswordResponse>("/users", body),
    onSuccess: (res) => {
      setTempPassword({ username: res.user.username, pass: res.temporary_password });
      setNewUsername("");
      setNewRole("viewer");
      setCreateErrors({});
      refetch();
    },
    onError: (err) => {
      if (err instanceof ConsoleApiError) {
        if (err.code === "conflict" && err.field === "username") {
          setCreateErrors({ username: "Tên đăng nhập đã tồn tại" });
        } else if (err.code === "invalid_role" && err.field === "role") {
          setCreateErrors({ role: "Quyền không hợp lệ" });
        } else {
          setCreateErrors({ generic: err.message });
        }
      } else {
        setCreateErrors({ generic: "Đã xảy ra lỗi không xác định" });
      }
    }
  });

  const changeRoleMutation = useMutation({
    mutationFn: (body: { userId: string; role: string }) => 
      client.post<UserModel>(`/users/${body.userId}/role`, { role: body.role }),
    onSuccess: () => {
      setModalState(null);
      refetch();
    },
    onError: (err) => {
      if (err instanceof ConsoleApiError && err.code === "last_active_admin") {
        setActionError("Không thể hạ quyền hoặc khoá admin đang hoạt động cuối cùng. Hãy tạo hoặc mở khoá một admin khác trước.");
      } else {
        setActionError(err instanceof Error ? err.message : "Đã xảy ra lỗi");
      }
    }
  });

  const lockMutation = useMutation({
    mutationFn: (userId: string) => client.post<UserModel>(`/users/${userId}/lock`),
    onSuccess: () => {
      setModalState(null);
      refetch();
    },
    onError: (err) => {
      if (err instanceof ConsoleApiError && err.code === "last_active_admin") {
        setActionError("Không thể hạ quyền hoặc khoá admin đang hoạt động cuối cùng. Hãy tạo hoặc mở khoá một admin khác trước.");
      } else {
        setActionError(err instanceof Error ? err.message : "Đã xảy ra lỗi");
      }
    }
  });

  const unlockMutation = useMutation({
    mutationFn: (userId: string) => client.post<UserModel>(`/users/${userId}/unlock`),
    onSuccess: () => {
      setModalState(null);
      refetch();
    },
    onError: (err) => {
      setActionError(err instanceof Error ? err.message : "Đã xảy ra lỗi");
    }
  });

  const resetMutation = useMutation({
    mutationFn: (userId: string) => client.post<TemporaryPasswordResponse>(`/users/${userId}/reset-password`),
    onSuccess: (res) => {
      setModalState(null);
      setTempPassword({ username: res.user.username, pass: res.temporary_password });
      refetch();
    },
    onError: (err) => {
      setActionError(err instanceof Error ? err.message : "Đã xảy ra lỗi");
    }
  });

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateErrors({});
    if (!newUsername.trim()) {
      setCreateErrors({ username: "Không được để trống" });
      return;
    }
    createMutation.mutate({ username: newUsername, role: newRole });
  };

  const openModal = (type: NonNullable<ModalState>["type"], user: UserModel) => {
    setModalState({ type, user });
    if (type === "role") {
      setModalRole(user.role);
    }
    setActionError(null);
  };

  const handleModalConfirm = () => {
    if (!modalState) return;
    
    if (modalState.type === "role") {
      changeRoleMutation.mutate({ userId: modalState.user.id, role: modalRole });
    } else if (modalState.type === "lock") {
      lockMutation.mutate(modalState.user.id);
    } else if (modalState.type === "unlock") {
      unlockMutation.mutate(modalState.user.id);
    } else if (modalState.type === "reset") {
      resetMutation.mutate(modalState.user.id);
    }
  };

  const isModalLoading = changeRoleMutation.isPending || lockMutation.isPending || unlockMutation.isPending || resetMutation.isPending;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-ink dark:text-gray-100">Người dùng</h1>
        <p className="text-sm text-gray-500">Quản lý tài khoản quản trị và điều hành.</p>
      </div>

      {tempPassword && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-4 dark:border-amber-900/50 dark:bg-amber-900/20 shadow-sm relative">
          <button 
            type="button"
            className="absolute top-2 right-2 text-amber-600 hover:text-amber-800 dark:text-amber-400 dark:hover:text-amber-200"
            onClick={() => {
              setTempPassword(null);
              // useMutation giu lai `data` cua no cho toi khi unmount, nghia
              // la mat khau van con trong bo nho sau khi dong hop. reset()
              // xoa not ban thu hai do - dong tren mot minh chi xoa ban dau.
              createMutation.reset();
              resetMutation.reset();
            }}
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
          <div className="flex gap-3">
            <div className="flex-shrink-0 mt-0.5">
              <svg className="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
            </div>
            <div>
              <h3 className="text-sm font-medium text-amber-800 dark:text-amber-300">
                Mật khẩu này chỉ hiện một lần. Sao chép và gửi cho người dùng ngay.
              </h3>
              <div className="mt-2 text-sm text-amber-700 dark:text-amber-200">
                Tài khoản: <span className="font-semibold">{tempPassword.username}</span>
              </div>
              <div className="mt-2 flex items-center gap-2">
                <code className="rounded bg-white/60 dark:bg-black/20 px-2 py-1 font-mono text-sm border border-amber-200/50 dark:border-amber-700/50 select-all">
                  {tempPassword.pass}
                </code>
                <button
                  type="button"
                  onClick={() => navigator.clipboard.writeText(tempPassword.pass)}
                  className="rounded px-3 py-1 text-xs font-medium border border-amber-300 bg-white text-amber-700 hover:bg-amber-100 dark:border-amber-700 dark:bg-[#1a1c1c] dark:text-amber-300 dark:hover:bg-amber-900/50 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
                >
                  Sao chép
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {!is403 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5 dark:border-gray-800 dark:bg-[#1a1c1c]">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">Tạo tài khoản mới</h2>
          <form onSubmit={handleCreate} className="flex flex-col sm:flex-row items-start gap-4">
            <div className="w-full sm:w-64">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Tên đăng nhập</label>
              <input
                type="text"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                disabled={createMutation.isPending}
                className={`block w-full rounded-md border p-2 text-sm focus:outline-none focus:ring-2 dark:bg-[#111314] dark:text-gray-100 ${
                  createErrors.username 
                    ? "border-red-500 focus:border-red-500 focus:ring-red-500/20" 
                    : "border-gray-300 focus:border-vf focus:ring-vf/20 dark:border-gray-700"
                }`}
                placeholder="VD: nguyenvan_a"
              />
              {createErrors.username && <p className="mt-1 text-xs text-red-500">{createErrors.username}</p>}
            </div>
            <div className="w-full sm:w-48">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Quyền</label>
              <select
                value={newRole}
                onChange={(e) => setNewRole(e.target.value)}
                disabled={createMutation.isPending}
                className={`block w-full rounded-md border p-2 text-sm focus:outline-none focus:ring-2 dark:bg-[#111314] dark:text-gray-100 ${
                  createErrors.role 
                    ? "border-red-500 focus:border-red-500 focus:ring-red-500/20" 
                    : "border-gray-300 focus:border-vf focus:ring-vf/20 dark:border-gray-700"
                }`}
              >
                {filtersData?.roles.map(r => (
                  <option key={r} value={r}>{pillOf(USER_ROLE, r).label}</option>
                ))}
              </select>
              {createErrors.role && <p className="mt-1 text-xs text-red-500">{createErrors.role}</p>}
            </div>
            <div className="mt-6 flex items-start h-[38px]">
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="h-full rounded-md bg-vf px-4 text-sm font-medium text-white hover:bg-vf/90 focus:outline-none focus:ring-2 focus:ring-vf/30 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {createMutation.isPending ? "Đang xử lý..." : "Tạo"}
              </button>
            </div>
          </form>
          {createErrors.generic && <p className="mt-3 text-sm text-red-500">{createErrors.generic}</p>}
        </div>
      )}

      <div className="rounded-lg border border-gray-200 bg-white dark:border-gray-800 dark:bg-[#1a1c1c] overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-800 text-sm text-left text-ink dark:text-gray-200">
            <thead className="bg-gray-50 dark:bg-gray-800/50 text-xs font-semibold uppercase text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-4 py-3">Tên đăng nhập</th>
                <th className="px-4 py-3">Quyền</th>
                <th className="px-4 py-3">Trạng thái</th>
                <th className="px-4 py-3">Đổi mật khẩu</th>
                <th className="px-4 py-3">Tạo lúc ({TIMEZONE_LABEL})</th>
                <th className="px-4 py-3">Đăng nhập cuối ({TIMEZONE_LABEL})</th>
                <th className="px-4 py-3 text-right">Thao tác</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              {isLoading ? (
                Array.from({ length: 8 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-4 py-3"><div className="h-4 w-24 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-20 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-12 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-32 rounded bg-gray-200 dark:bg-gray-700"></div></td>
                    <td className="px-4 py-3"><div className="h-4 w-16 rounded bg-gray-200 dark:bg-gray-700 ml-auto"></div></td>
                  </tr>
                ))
              ) : is403 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-sm text-gray-500">
                    Bạn không có quyền xem danh sách người dùng.
                  </td>
                </tr>
              ) : isGenericError ? (
                <tr>
                  <td colSpan={7} className="px-4 py-6">
                    <ErrorBanner message="Không thể tải danh sách người dùng." />
                    <button onClick={() => refetch()} className="mt-4 text-sm font-medium text-vf hover:underline">Thử lại</button>
                  </td>
                </tr>
              ) : data?.items.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-4 py-8 text-center text-gray-500">
                    Chưa có tài khoản nào.
                  </td>
                </tr>
              ) : (
                data?.items.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-gray-800/50">
                    <td className="px-4 py-3 font-medium">{u.username}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <StatusPill style={pillOf(USER_ROLE, u.role)} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <StatusPill style={pillOf(USER_ACTIVE, String(u.active))} />
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      {u.must_change_password && (
                        <span className="inline-flex items-center rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/30 dark:text-amber-300">
                          Cần đổi
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">{formatDateTime(u.created_at)}</td>
                    <td className="px-4 py-3 whitespace-nowrap">{u.last_login_at ? formatDateTime(u.last_login_at) : ""}</td>
                    <td className="px-4 py-3 whitespace-nowrap text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => openModal("role", u)}
                          className="text-xs font-medium text-blue-600 hover:text-blue-800 hover:underline dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          Đổi quyền
                        </button>
                        <span className="text-gray-300 dark:text-gray-700">|</span>
                        {u.active ? (
                          <button
                            type="button"
                            onClick={() => openModal("lock", u)}
                            className="text-xs font-medium text-red-600 hover:text-red-800 hover:underline dark:text-red-400 dark:hover:text-red-300"
                          >
                            Khoá
                          </button>
                        ) : (
                          <button
                            type="button"
                            onClick={() => openModal("unlock", u)}
                            className="text-xs font-medium text-emerald-600 hover:text-emerald-800 hover:underline dark:text-emerald-400 dark:hover:text-emerald-300"
                          >
                            Mở khoá
                          </button>
                        )}
                        <span className="text-gray-300 dark:text-gray-700">|</span>
                        <button
                          type="button"
                          onClick={() => openModal("reset", u)}
                          className="text-xs font-medium text-gray-600 hover:text-gray-900 hover:underline dark:text-gray-400 dark:hover:text-gray-200"
                        >
                          Đặt lại mật khẩu
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
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
                  params.set("page", String(data.page - 1));
                  setParams(params);
                }}
                className="rounded border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-300 dark:hover:bg-white/5"
              >
                Trước
              </button>
              <button
                type="button"
                disabled={data.page >= data.total_pages}
                onClick={() => {
                  params.set("page", String(data.page + 1));
                  setParams(params);
                }}
                className="rounded border border-gray-300 bg-white px-3 py-1 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-300 dark:hover:bg-white/5"
              >
                Sau
              </button>
            </div>
          </div>
        )}
      </div>

      {modalState && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-[#1a1c1c] border border-gray-200 dark:border-gray-800">
            <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
              {modalState.type === "role" && "Đổi quyền"}
              {modalState.type === "lock" && "Khoá tài khoản"}
              {modalState.type === "unlock" && "Mở khoá tài khoản"}
              {modalState.type === "reset" && "Đặt lại mật khẩu"}
            </h3>
            
            <div className="mb-6 space-y-4 text-sm text-gray-600 dark:text-gray-300">
              {modalState.type === "role" && (
                <>
                  <p>
                    Bạn đang đổi quyền của <span className="font-semibold text-gray-900 dark:text-white">{modalState.user.username}</span> từ:
                  </p>
                  <p className="font-mono text-gray-900 dark:text-white bg-gray-100 dark:bg-gray-800 p-2 rounded">
                    {modalState.user.role} → {modalRole}
                  </p>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Chọn quyền mới</label>
                    <select
                      value={modalRole}
                      onChange={(e) => setModalRole(e.target.value)}
                      className="block w-full rounded-md border border-gray-300 p-2 text-sm focus:border-vf focus:outline-none focus:ring-2 focus:ring-vf/20 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-100"
                    >
                      {filtersData?.roles.map(r => (
                        <option key={r} value={r}>{pillOf(USER_ROLE, r).label}</option>
                      ))}
                    </select>
                  </div>
                </>
              )}

              {modalState.type === "lock" && (
                <p>Bạn có chắc chắn muốn khoá tài khoản <span className="font-semibold text-gray-900 dark:text-white">{modalState.user.username}</span>?</p>
              )}

              {modalState.type === "unlock" && (
                <p>Bạn có chắc chắn muốn mở khoá tài khoản <span className="font-semibold text-gray-900 dark:text-white">{modalState.user.username}</span>?</p>
              )}

              {modalState.type === "reset" && (
                <p>
                  Đặt lại mật khẩu cho <span className="font-semibold text-gray-900 dark:text-white">{modalState.user.username}</span>. 
                  <br /><br />
                  <span className="text-red-600 dark:text-red-400 font-medium">Lưu ý:</span> Người này sẽ bị đăng xuất khỏi mọi thiết bị hiện tại.
                </p>
              )}

              {authUser?.id === modalState.user.id && modalState.type !== "unlock" && (
                <div className="rounded bg-amber-50 p-3 text-amber-800 dark:bg-amber-900/20 dark:text-amber-300">
                  <strong>Bạn đang thao tác trên chính tài khoản của mình.</strong> Sau thao tác này bạn sẽ bị đăng xuất. Tiếp tục?
                </div>
              )}
              
              {actionError && (
                <div className="rounded bg-red-50 p-3 text-red-800 dark:bg-red-900/20 dark:text-red-300 border border-red-200 dark:border-red-900/50">
                  {actionError}
                </div>
              )}
            </div>

            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setModalState(null)}
                disabled={isModalLoading}
                className="rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-[#111314] dark:text-gray-300 dark:hover:bg-white/5 disabled:opacity-50"
              >
                Huỷ
              </button>
              <button
                type="button"
                onClick={handleModalConfirm}
                disabled={isModalLoading || (modalState.type === "role" && modalRole === modalState.user.role)}
                className={`rounded-md px-4 py-2 text-sm font-medium text-white focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:opacity-50 ${
                  modalState.type === "lock" || modalState.type === "reset"
                    ? "bg-red-600 hover:bg-red-700 focus:ring-red-500"
                    : "bg-vf hover:bg-vf/90 focus:ring-vf/30"
                }`}
              >
                {isModalLoading ? "Đang xử lý..." : "Xác nhận"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
