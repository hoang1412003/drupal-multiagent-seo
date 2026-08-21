/**
 * Man Nguoi dung - man rui ro cao nhat cua Console.
 *
 * Moi test o day tuong ung mot loi CO THAT da phai sua tay khi review, hoac
 * mot rang buoc an toan ma anh chup man hinh khong nhin ra duoc.
 */
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";

import { UsersPage } from "./UsersPage";
import { loi, mockApi, nguoiDung, renderPage } from "../test/harness";

const FILTERS = {
  sites: [],
  job_sources: [],
  job_statuses: [],
  review_decisions: [],
  writeback_statuses: [],
  audit_actions: [],
  audit_outcomes: [],
  roles: ["viewer", "operator", "admin"],
};

function trang(items: unknown[]) {
  return { items, page: 1, page_size: 25, total: items.length, total_pages: 1 };
}

const ADMIN_ID = "00000000-0000-4000-8000-0000000000aa";

function taiKhoan(ghiDe: Record<string, unknown> = {}) {
  return {
    id: "00000000-0000-4000-8000-0000000000bb",
    username: "nguoi.khac",
    role: "viewer",
    active: true,
    must_change_password: false,
    last_login_at: "2026-08-20T03:00:00Z",
    created_at: "2026-08-19T03:00:00Z",
    updated_at: "2026-08-20T03:00:00Z",
    ...ghiDe,
  };
}

function mocDinh(ghiDe: Record<string, unknown> = {}) {
  return mockApi({
    "GET /auth/me": { body: nguoiDung("admin") },
    "GET /filters": { body: FILTERS },
    "GET /users": { body: trang([taiKhoan()]) },
    ...ghiDe,
  });
}

describe("UsersPage", () => {
  beforeEach(() => {
    // Moi test tu khai bao route cua no; setup.ts da chan fetch that.
  });

  it("o chon Quyen hien nhan tieng Viet, khong phai gia tri tho", async () => {
    // Loi that: o chon hien `viewer` / `operator` / `admin` trong khi cot ngay
    // ben duoi hien "Chi xem" / "Quan tri" - lech nhau trong cung mot man.
    mocDinh();
    renderPage(<UsersPage />);

    const o_chon = await screen.findByLabelText(/Quyền/i);
    const nhan = within(o_chon).getAllByRole("option").map((o) => o.textContent);

    expect(nhan).toEqual(["Chỉ xem", "Vận hành", "Quản trị"]);
    for (const tho of ["viewer", "operator", "admin"]) {
      expect(nhan).not.toContain(tho);
    }
  });

  it("danh sach quyen lay tu /filters, khong go cung trong trang", async () => {
    // Neu ai do go cung ba gia tri vao file trang, doi bang o server se khong
    // lam test nay do - nen test doi bang cach TRA VE mot danh sach khac.
    mocDinh({
      "GET /filters": { body: { ...FILTERS, roles: ["viewer", "admin"] } },
    });
    renderPage(<UsersPage />);

    const o_chon = await screen.findByLabelText(/Quyền/i);
    await waitFor(() =>
      expect(within(o_chon).getAllByRole("option")).toHaveLength(2),
    );
  });

  it("khong co o nhap mat khau trong bieu mau tao", async () => {
    // Server tu sinh mat khau tam. Them o nhap la tu mo duong cho mat khau
    // yeu lot vao he thong.
    mocDinh();
    renderPage(<UsersPage />);
    await screen.findByLabelText(/Quyền/i);

    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(screen.queryByLabelText(/mật khẩu/i)).toBeNull();
  });

  it("dong hop mat khau tam thi xoa no khoi bo nho", async () => {
    // Loi that: dong hop chi xoa useState, con useMutation van giu `data`
    // cua no - mat khau ton tai o hai cho, dong nut chi xoa mot.
    const nguoi_dung = userEvent.setup();
    mocDinh({
      "POST /users": {
        status: 201,
        body: {
          user: taiKhoan({ username: "moi.tao" }),
          temporary_password: "MAT-KHAU-TAM-BI-MAT",
        },
      },
    });
    const { container } = renderPage(<UsersPage />);

    await nguoi_dung.type(await screen.findByLabelText(/Tên đăng nhập/i), "moi.tao");
    await nguoi_dung.click(screen.getByRole("button", { name: /^Tạo$/ }));

    // Hien mot lan, co nut sao chep.
    expect(await screen.findByText("MAT-KHAU-TAM-BI-MAT")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Sao chép/i })).toBeInTheDocument();

    await nguoi_dung.click(screen.getByRole("button", { name: /đóng|close/i }));

    await waitFor(() =>
      expect(screen.queryByText("MAT-KHAU-TAM-BI-MAT")).not.toBeInTheDocument(),
    );
    // Va khong con dau vet o bat ky dau trong cay DOM.
    expect(container.innerHTML).not.toContain("MAT-KHAU-TAM-BI-MAT");
  });

  it("loi admin cuoi cung hien huong dan rieng, khong phai banner chung", async () => {
    const nguoi_dung = userEvent.setup();
    mocDinh({
      "GET /users": { body: trang([taiKhoan({ id: ADMIN_ID, username: "admin", role: "admin" })]) },
      "POST /users/{id}/lock": loi(
        409,
        "last_active_admin",
        "Không thể hạ quyền hoặc khoá admin đang hoạt động cuối cùng",
      ),
    });
    renderPage(<UsersPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /^Khoá$/ }));
    await nguoi_dung.click(screen.getByRole("button", { name: /Xác nhận/i }));

    // Cau huong dan phai noi ro phai lam gi tiep, khong chi bao "co loi".
    expect(await screen.findByText(/admin đang hoạt động cuối cùng/i)).toBeInTheDocument();
    expect(screen.getByText(/tạo hoặc mở khoá một admin khác/i)).toBeInTheDocument();
  });

  it("canh bao khi thao tac tren chinh tai khoan cua minh", async () => {
    // Khoa chinh minh khien bi dang xuat ngay sau do. So bang ID, khong phai
    // ten: MeResponse co truong `id` dung de lam viec nay.
    const nguoi_dung = userEvent.setup();
    mocDinh({
      "GET /users": { body: trang([taiKhoan({ id: ADMIN_ID, username: "admin", role: "admin" })]) },
    });
    renderPage(<UsersPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /^Khoá$/ }));
    expect(screen.getByText(/chính tài khoản của mình/i)).toBeInTheDocument();
    expect(screen.getByText(/sẽ bị đăng xuất/i)).toBeInTheDocument();
  });

  it("khong canh bao khi thao tac tren tai khoan nguoi khac", async () => {
    const nguoi_dung = userEvent.setup();
    mocDinh(); // taiKhoan() mac dinh co id khac ADMIN_ID
    renderPage(<UsersPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /^Khoá$/ }));
    expect(screen.queryByText(/chính tài khoản của mình/i)).not.toBeInTheDocument();
  });

  it("khoa phai hoi lai truoc khi goi API", async () => {
    const nguoi_dung = userEvent.setup();
    const api = mocDinh();
    renderPage(<UsersPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /^Khoá$/ }));
    // Moi bam nut trong bang: chua duoc goi API.
    expect(api.soLan("/users/00000000-0000-4000-8000-0000000000bb/lock")).toBe(0);
    expect(screen.getByRole("button", { name: /Xác nhận/i })).toBeInTheDocument();
  });

  it("hien dung mot nut Khoa hoac Mo khoa, khong hien ca hai", async () => {
    mocDinh({ "GET /users": { body: trang([taiKhoan({ active: false })]) } });
    renderPage(<UsersPage />);

    expect(await screen.findByRole("button", { name: /Mở khoá/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^Khoá$/ })).not.toBeInTheDocument();
  });

  it("username trung thi to do dung o Ten dang nhap", async () => {
    const nguoi_dung = userEvent.setup();
    mocDinh({
      "POST /users": loi(409, "conflict", "Tên đăng nhập đã tồn tại", "username"),
    });
    renderPage(<UsersPage />);

    await nguoi_dung.type(await screen.findByLabelText(/Tên đăng nhập/i), "trung");
    await nguoi_dung.click(screen.getByRole("button", { name: /^Tạo$/ }));

    expect(await screen.findByText(/Tên đăng nhập đã tồn tại/i)).toBeInTheDocument();
  });

  it("khong hien cot nao lien quan toi mat khau", async () => {
    // UserModel co y khong co truong nao ve mat khau. Cot nhu vay xuat hien
    // nghia la ai do da them truong vao API.
    mocDinh();
    renderPage(<UsersPage />);
    await screen.findByRole("table");

    const tieu_de = screen
      .getAllByRole("columnheader")
      .map((th) => th.textContent ?? "");
    // "Đổi mật khẩu" la cot must_change_password - hop le. Cot bi cam la cot
    // hien chinh mat khau hay do manh cua no.
    for (const cam of [/độ mạnh/i, /^mật khẩu$/i, /hash/i]) {
      expect(tieu_de.some((t) => cam.test(t.trim()))).toBe(false);
    }
  });
});
