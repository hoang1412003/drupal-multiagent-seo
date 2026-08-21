/**
 * Man Ket noi.
 *
 * Cam bay quan trong nhat o day KHONG nhin thay duoc tren anh chup: neu chan
 * doan chay tu dong khi mo trang thi giao dien trong y het, nhung moi lan mo
 * trang la mot lan goi that sang Drupal va mot dong trong so kiem toan.
 */
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { ConnectionPage } from "./ConnectionPage";
import { loi, mockApi, nguoiDung, renderPage } from "../test/harness";

function ketNoi(ghiDe: Record<string, unknown> = {}) {
  return {
    slug: "drupal-vn-primary",
    name: "Drupal Viet Nam primary",
    base_url: "http://drupal.ddev.site",
    secret_ref: "DRUPAL",
    active: true,
    intake_paused: false,
    profile_code: "cam-nang-vn",
    policy_version: "cam-nang-vn-v1",
    token_prefixes: ["vfp_abc123"],
    last_health_status: "ok",
    last_health_checked_at: "2026-08-21T02:14:00Z",
    last_health_error: null,
    ...ghiDe,
  };
}

function mocDinh(role = "operator", ghiDe: Record<string, unknown> = {}) {
  return mockApi({
    "GET /auth/me": { body: nguoiDung(role) },
    "GET /connection": { body: ketNoi() },
    ...ghiDe,
  });
}

describe("ConnectionPage", () => {
  it("KHONG tu goi chan doan khi mo trang", async () => {
    // Day la cam bay so 1 cua dac ta. Chan doan goi that sang Drupal va ghi
    // mot dong kiem toan moi lan - no phai la hanh dong CO CHU Y.
    const api = mocDinh();
    renderPage(<ConnectionPage />);

    await screen.findByText("Drupal Viet Nam primary");
    // Cho them mot nhip de bat ca truong hop goi tre trong useEffect.
    await new Promise((r) => setTimeout(r, 50));

    expect(api.soLan("/connection/test")).toBe(0);
  });

  it("chi goi chan doan khi nguoi dung bam nut", async () => {
    const nguoi_dung = userEvent.setup();
    const api = mocDinh("operator", {
      "POST /connection/test": {
        body: { ok: true, error_code: null, connection: ketNoi() },
      },
    });
    renderPage(<ConnectionPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /Chẩn đoán/i }));
    await waitFor(() => expect(api.soLan("/connection/test")).toBe(1));
    expect(await screen.findByText(/Kết nối đạt/i)).toBeInTheDocument();
  });

  it("ket noi hong hien ma loi, khong hien 'dat'", async () => {
    // Dung truong `ok` chu khong so sanh chuoi last_health_status.
    const nguoi_dung = userEvent.setup();
    mocDinh("operator", {
      "POST /connection/test": {
        body: {
          ok: false,
          error_code: "auth_failed",
          connection: ketNoi({ last_health_status: "auth_failed", last_health_error: "auth_failed" }),
        },
      },
    });
    renderPage(<ConnectionPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /Chẩn đoán/i }));
    expect(await screen.findByText(/chưa đạt/i)).toBeInTheDocument();
    // Hien o hai cho: pill Ket qua va truong Ma loi - dung nhu thiet ke.
    expect(screen.getAllByText(/auth_failed/).length).toBeGreaterThan(0);
  });

  it("tam dung phai hoi lai truoc khi goi API", async () => {
    const nguoi_dung = userEvent.setup();
    const api = mocDinh();
    renderPage(<ConnectionPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /Tạm dừng nhận bài/i }));
    // Chua duoc goi API: moi bam nut mo hop xac nhan.
    expect(api.soLan("/connection/pause")).toBe(0);
    expect(screen.getByText(/toàn bộ bài mới từ Drupal/i)).toBeInTheDocument();

    await nguoi_dung.click(screen.getByRole("button", { name: /Xác nhận tạm dừng/i }));
    await waitFor(() => expect(api.soLan("/connection/pause")).toBe(1));
  });

  it("bam Huy trong hop xac nhan thi khong goi API", async () => {
    const nguoi_dung = userEvent.setup();
    const api = mocDinh();
    renderPage(<ConnectionPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /Tạm dừng nhận bài/i }));
    await nguoi_dung.click(screen.getByRole("button", { name: /^Huỷ$/ }));

    expect(api.soLan("/connection/pause")).toBe(0);
    expect(screen.queryByText(/toàn bộ bài mới từ Drupal/i)).not.toBeInTheDocument();
  });

  it("mo lai nhan bai KHONG hoi lai", async () => {
    // Mo lai dua he thong ve trang thai binh thuong, hoi lai chi lam phien.
    const nguoi_dung = userEvent.setup();
    const api = mocDinh("operator", {
      "GET /connection": { body: ketNoi({ intake_paused: true }) },
      "POST /connection/resume": { body: ketNoi({ intake_paused: false }) },
    });
    renderPage(<ConnectionPage />);

    await nguoi_dung.click(await screen.findByRole("button", { name: /Mở lại nhận bài/i }));
    await waitFor(() => expect(api.soLan("/connection/resume")).toBe(1));
  });

  it("hien dung mot nut Tam dung hoac Mo lai", async () => {
    mocDinh("operator", { "GET /connection": { body: ketNoi({ intake_paused: true }) } });
    renderPage(<ConnectionPage />);

    expect(await screen.findByRole("button", { name: /Mở lại nhận bài/i })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Tạm dừng nhận bài/i })).not.toBeInTheDocument();
  });

  it("viewer khong thay nut nao, thay dong chu chi doc", async () => {
    // An nut khong phai la phan quyen - server van kiem. Nhung hien nut ma
    // bam vao bi 403 thi la giao dien noi doi.
    mocDinh("viewer");
    renderPage(<ConnectionPage />);

    expect(await screen.findByText(/quyền chỉ đọc/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Chẩn đoán/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Tạm dừng/i })).not.toBeInTheDocument();
  });

  it("404 hien man hinh rong, KHONG hien banner do", async () => {
    // Chua cau hinh site nao khong phai su co he thong.
    mocDinh("admin", { "GET /connection": loi(404, "not_found", "Chưa cấu hình site nào") });
    renderPage(<ConnectionPage />);

    expect(await screen.findByText(/Chưa cấu hình site nào/i)).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Chẩn đoán/i })).not.toBeInTheDocument();
  });

  it("loi khac 404 thi hien banner kem thong bao that cua server", async () => {
    mocDinh("admin", {
      "GET /connection": loi(500, "internal", "Cơ sở dữ liệu không phản hồi"),
    });
    renderPage(<ConnectionPage />);

    const banner = await screen.findByRole("alert");
    // Khong duoc nuot thong bao cua server thanh mot cau chung chung.
    expect(banner).toHaveTextContent(/Cơ sở dữ liệu không phản hồi/i);
  });

  it("chua tung chan doan thi hien mot dong, khong hien ba dau gach", async () => {
    mocDinh("admin", {
      "GET /connection": {
        body: ketNoi({
          last_health_status: null,
          last_health_checked_at: null,
          last_health_error: null,
        }),
      },
    });
    renderPage(<ConnectionPage />);

    expect(await screen.findByText(/Chưa từng chẩn đoán/i)).toBeInTheDocument();
  });

  it("secret_ref hien nguyen van kem nhan noi ro no la ten bien", async () => {
    // Che no di thi nguoi van hanh mat thong tin can de doi chieu cau hinh,
    // ma cung chang giau duoc gi: no la TEN bien, khong phai gia tri.
    mocDinh("admin");
    renderPage(<ConnectionPage />);

    expect(await screen.findByText("DRUPAL")).toBeInTheDocument();
    expect(screen.getByText(/biến môi trường/i)).toBeInTheDocument();
  });
});
