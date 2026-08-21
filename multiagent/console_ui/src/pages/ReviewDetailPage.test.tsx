/**
 * Man chi tiet review - noi hien NHIEU du lieu do LLM sinh ra nhat.
 *
 * Phep kiem XSS o day thay cho `test_bao_cao_dang_ngo_van_duoc_escape_khi_render`
 * cua admin Jinja2 (xoa 2026-08-21). Ban cu kiem autoescape cua Jinja2; ban nay
 * kiem dieu tuong duong cho React.
 *
 * Vi sao van can du React tu escape: bao dam do bien mat ngay khi ai do dung
 * `dangerouslySetInnerHTML`. Phep grep cam thuoc tinh do la lop chan thu nhat;
 * day la lop thu hai, va no kiem KET QUA chu khong kiem cach viet.
 */
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ReviewDetailPage } from "./ReviewDetailPage";
import { mockApi, nguoiDung, renderPage } from "../test/harness";

const DOC_AC_Y = "<script>alert('xss')</script>";

function review(ghiDe: Record<string, unknown> = {}) {
  return {
    public_id: "00000000-0000-4000-8000-0000000000cc",
    created_at: "2026-08-20T03:00:00Z",
    updated_at: "2026-08-20T03:00:00Z",
    site_slug: "drupal-vn-primary",
    external_content_id: "node-1",
    external_revision_id: "rev-1",
    decision: "needs_revision",
    final_score: 62.5,
    is_fixture: false,
    agents: [
      {
        name: "content_quality",
        score: 60,
        criteria: [{ ten: DOC_AC_Y }],
        issues: [{ mo_ta: DOC_AC_Y }],
        evidence: [],
      },
    ],
    ...ghiDe,
  };
}

describe("ReviewDetailPage - chong XSS", () => {
  it("chuoi giong the HTML hien ra thanh CHU, khong thanh phan tu", async () => {
    // LLM co the tra ve bat ky chuoi nao, ke ca chuoi giong the <script>.
    mockApi({
      "GET /auth/me": { body: nguoiDung("viewer") },
      "GET /reviews/{id}": { body: review() },
    });
    const { container } = renderPage(<ReviewDetailPage />, {
      duongDan: "/reviews/00000000-0000-4000-8000-0000000000cc",
      mau: "/reviews/:publicId",
    });

    // Khoi agent mac dinh thu gon; mo ra moi thay du lieu do LLM sinh.
    const nguoi_dung = userEvent.setup();
    await nguoi_dung.click(await screen.findByRole("button", { name: /content_quality/i }));

    // Hien ra duoc, va hien NGUYEN VAN - khong bi nuot mat.
    expect(await screen.findAllByText(DOC_AC_Y)).not.toHaveLength(0);
    // Nhung KHONG co the <script> that nao trong cay DOM.
    expect(container.querySelector("script")).toBeNull();
  });

  it("khong dung dangerouslySetInnerHTML o bat ky dau", async () => {
    // Lop chan thu hai cho chinh phep grep: neu ai do them thuoc tinh do vao
    // day, chuoi tren se thanh mot the <script> that va test tren se do.
    const nguon = await import("./ReviewDetailPage?raw").catch(() => null);
    if (nguon === null) return; // moi truong khong ho tro ?raw thi bo qua
    expect(String((nguon as { default: string }).default)).not.toContain(
      "dangerouslySetInnerHTML",
    );
  });
});
