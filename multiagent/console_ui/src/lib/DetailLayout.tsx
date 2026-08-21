/**
 * Khung the va cap nhan-gia tri cho cac man chi tiet, dung chung moi man hinh.
 *
 * Truoc khi gom vao day, `Section` va `Field` bi chep o NAM file va da bat dau
 * lech: ban cua man Ket noi them `breakAll`, ban cua man Cau hinh/KB bo han
 * the `<dl>`, ban cua man Ket qua do doi ten thanh `Card` va bo tieu de. Bon
 * bien the cua cung mot khung the la bon co hoi lech tiep.
 *
 * Day la module gom chung thu TU, sau format.ts, status.ts va ErrorBanner.tsx.
 * Ca ba cai truoc deu ra doi sau khi ban chep thu tu lech - lan nay gom som
 * hon mot nhip.
 *
 * Nguon cua bang mau va class: docs/console-ui/design-system.md.
 */
import type { ReactNode } from "react";

const VO_THE =
  "rounded-lg border border-gray-200 bg-white p-5 " +
  "dark:border-gray-800 dark:bg-[#1a1c1c]";

/**
 * Vo the tron co vien. `title` khong bat buoc: man Ket qua do dung the khong
 * tieu de, con man Cau hinh/KB dung the co tieu de nhung KHONG phai danh sach
 * cap nhan-gia tri, nen no khong dung duoc `Section`.
 */
export function Panel({
  title,
  className = "",
  children,
}: {
  title?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className={className ? `${VO_THE} ${className}` : VO_THE}>
      {title && (
        <h2 className="mb-4 text-sm font-semibold uppercase tracking-wider text-gray-900 dark:text-gray-100">
          {title}
        </h2>
      )}
      {children}
    </section>
  );
}

/**
 * The co tieu de, ben trong la luoi cap nhan-gia tri.
 *
 * `columns` mac dinh 3 vi ba man co truoc (Job detail, Review detail, Cau
 * hinh/KB) deu dung 3 va da duoc kiem bang anh chup. Man Ket noi co nhom sau
 * truong nen dung 4; de mac dinh thanh 4 se doi bo cuc cua ba man kia o man
 * hinh rong ma khong ai yeu cau.
 */
export function Section({
  title,
  columns = 3,
  children,
}: {
  title: string;
  columns?: 3 | 4;
  children: ReactNode;
}) {
  return (
    <Panel title={title}>
      <dl
        className={
          columns === 4
            ? "grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"
            : "grid grid-cols-1 gap-x-6 gap-y-5 sm:grid-cols-2 lg:grid-cols-3"
        }
      >
        {children}
      </dl>
    </Panel>
  );
}

/**
 * Mot cap nhan-gia tri trong `Section`.
 *
 * `breakAll` danh cho chuoi dai khong co khoang trang (URL, ma bam SHA-256):
 * `break-words` khong ngat duoc chung nen chung tran ra ngoai the.
 */
export function Field({
  label,
  children,
  colSpan = false,
  mono = false,
  breakAll = false,
}: {
  label: string;
  children: ReactNode;
  colSpan?: boolean;
  mono?: boolean;
  breakAll?: boolean;
}) {
  return (
    <div className={colSpan ? "sm:col-span-full" : "sm:col-span-1"}>
      <dt className="text-sm font-medium text-gray-500 mb-1">{label}</dt>
      <dd
        className={`text-sm ${mono ? "font-mono text-xs" : ""} text-ink dark:text-gray-200 ${
          breakAll ? "break-all" : "break-words"
        }`}
      >
        {children ?? "—"}
      </dd>
    </div>
  );
}
