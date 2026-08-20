/**
 * Banner bao loi kem nut thu lai, dung chung moi man hinh.
 *
 * Truoc khi gom vao day, khoi nay bi chep o bon file - va ca bon ban chep deu
 * quen bien the `dark:` cho nut, nen o che do toi no la mot nut TRANG choi
 * tren nen toi. Chep bon lan thi mot thieu sot cung nhan len bon.
 */
type Props = {
  /** Thong bao tu server; de trong thi dung cau mac dinh. */
  message?: string | null;
  onRetry?: () => void;
  /** Canh le trong the bang: banner nam trong the nen can margin. */
  inset?: boolean;
};

export function ErrorBanner({ message, onRetry, inset = false }: Props) {
  return (
    <div
      role="alert"
      className={
        (inset ? "m-4 " : "") +
        "flex items-center justify-between gap-3 rounded-md border " +
        "border-red-200 bg-red-50 p-3 text-sm text-red-700 " +
        "dark:border-red-900 dark:bg-red-500/10 dark:text-red-300"
      }
    >
      <span>{message || "Đã xảy ra lỗi khi tải dữ liệu."}</span>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className={
            "h-9 shrink-0 rounded-md border border-red-200 bg-white px-4 " +
            "text-sm font-medium text-red-700 hover:bg-red-50 " +
            "dark:border-red-800 dark:bg-transparent dark:text-red-300 " +
            "dark:hover:bg-red-500/10"
          }
        >
          Thử lại
        </button>
      )}
    </div>
  );
}
