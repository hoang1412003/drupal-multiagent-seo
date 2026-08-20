/**
 * Pill trang thai, dung chung moi man hinh.
 *
 * Markup nay truoc do bi chep lai o bon file. Chep bon lan la bon co hoi lech
 * nhau, va da lech that: man Dashboard tung de `unavailable` mau do trong khi
 * dac ta noi mau xam.
 */
import type { PillStyle } from "./status";

export function StatusPill({ style }: { style: PillStyle }) {
  return (
    <span
      className={
        "inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 " +
        `text-xs font-medium ${style.bg} ${style.text}`
      }
    >
      <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
      {style.label}
    </span>
  );
}
