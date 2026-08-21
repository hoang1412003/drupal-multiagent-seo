/**
 * Bang nhan trang thai - module bi chep lai nhieu nhat va lech nhieu nhat.
 *
 * Loi lap lai suot 10 nhiem vu: gia tri co that o server nhung KHONG co nhan
 * tieng Viet, nen no hien nguyen van tieng Anh mau xam giua mot giao dien
 * tieng Viet. `tsc` khong bat duoc vi Record<string, PillStyle> chap nhan
 * bang thieu.
 *
 * Danh sach gia tri o day phai khop voi server. Phia Python da co
 * scripts/test_console_api_readonly.py doi chieu EVALUATION_STATUS voi
 * evaluation.STATUSES; day la lop kiem tuong ung cho cac bang con lai.
 */
import { describe, expect, it } from "vitest";

import {
  AUDIT_OUTCOME,
  BOOLEAN_PILLS,
  EVALUATION_STATUS,
  JOB_STATUS,
  REVIEW_DECISION,
  USER_ACTIVE,
  USER_ROLE,
  WORKER_STATUS,
  WRITEBACK_STATUS,
  pillOf,
} from "./status";
import type { PillStyle } from "./status";

/** Gia tri hop le, chep tu hang so o server. Xem admin/queries.py va rbac.py. */
const TU_SERVER: Record<string, [Record<string, PillStyle>, string[]]> = {
  JOB_STATUS: [JOB_STATUS, ["queued", "running", "failed", "done", "superseded"]],
  REVIEW_DECISION: [REVIEW_DECISION, ["publish", "needs_revision", "rejected", "unknown"]],
  WRITEBACK_STATUS: [
    WRITEBACK_STATUS,
    ["succeeded", "failed", "superseded", "pending", "unknown"],
  ],
  WORKER_STATUS: [WORKER_STATUS, ["running", "stale", "unavailable"]],
  AUDIT_OUTCOME: [AUDIT_OUTCOME, ["success", "denied", "failed"]],
  EVALUATION_STATUS: [EVALUATION_STATUS, ["valid", "pending", "historical_invalid"]],
  USER_ROLE: [USER_ROLE, ["viewer", "operator", "admin"]],
  USER_ACTIVE: [USER_ACTIVE, ["true", "false"]],
};

/** Chu cai chi co trong tieng Viet co dau. */
const CO_DAU = /[ăâđêôơưàáảãạằắẳẵặầấẩẫậèéẻẽẹềếểễệìíỉĩịòóỏõọồốổỗộờớởỡợùúủũụừứửữựỳýỷỹỵ]/i;

describe("bang nhan trang thai", () => {
  for (const [ten, [bang, gia_tri]] of Object.entries(TU_SERVER)) {
    it(`${ten} co nhan cho moi gia tri server co the tra ve`, () => {
      const thieu = gia_tri.filter((v) => !(v in bang));
      expect(thieu, `${ten} thieu nhan cho: ${thieu.join(", ")}`).toEqual([]);
    });

    it(`${ten} khong de lot nhan tieng Anh tho`, () => {
      for (const v of gia_tri) {
        const nhan = bang[v]?.label ?? "";
        expect(nhan, `${ten}.${v} van la gia tri tho`).not.toBe(v);
        // Nhan phai la tieng Viet: hoac co dau, hoac la tu khong dau hop le.
        expect(nhan.length, `${ten}.${v} co nhan rong`).toBeGreaterThan(0);
      }
    });


    it(`${ten} khong co hai gia tri nao trong giong het nhau`, () => {
      // Chuyen tu test_admin_dashboard.py (2026-08-21). Vi du cu the: `stale`
      // la worker tung chay roi im lang - mot SU CO. `unavailable` la chua bao
      // gio bat - binh thuong. Cho chung cung nhan hoac cung mau se lam su co
      // trong giong binh thuong.
      const nhan = gia_tri.map((v) => bang[v]?.label);
      expect(new Set(nhan).size, `${ten} co nhan trung nhau: ${nhan.join(", ")}`)
        .toBe(gia_tri.length);
    });

    it(`${ten} co du bon thuoc tinh mau cho moi nhan`, () => {
      // Thieu mot thuoc tinh thi class Tailwind thanh "undefined" va o che do
      // toi no ra mot vet trang - da xay ra voi ErrorBanner truoc khi gom.
      for (const v of gia_tri) {
        const pill = bang[v];
        expect(Object.keys(pill).sort()).toEqual(["bg", "dot", "label", "text"]);
        expect(pill.bg).toContain("dark:");
        expect(pill.text).toContain("dark:");
      }
    });
  }

  it("it nhat mot nua so nhan co dau tieng Viet", () => {
    // Phep kiem tho nhung du de bat mot bang bi chep nguyen tu tieng Anh.
    const tat_ca = Object.values(TU_SERVER).flatMap(([bang, gia_tri]) =>
      gia_tri.map((v) => bang[v]?.label ?? ""),
    );
    const co_dau = tat_ca.filter((n) => CO_DAU.test(n));
    expect(co_dau.length).toBeGreaterThan(tat_ca.length / 2);
  });
});

describe("pillOf", () => {
  it("gia tri null hay rong van hien duoc, khong lam vo giao dien", () => {
    for (const v of [null, undefined, ""]) {
      const pill = pillOf(JOB_STATUS, v);
      expect(pill.label).toBe("—");
      expect(pill.bg).toContain("dark:");
    }
  });

  it("gia tri la thi hien nguyen van, khong nem loi", () => {
    // Server them trang thai moi ma UI chua kip cap nhat: van phai hien duoc.
    const pill = pillOf(JOB_STATUS, "trang_thai_moi_toanh");
    expect(pill.label).toBe("trang_thai_moi_toanh");
  });

  it("BOOLEAN_PILLS dung duoc voi String(boolean)", () => {
    // Cac trang goi pillOf(BOOLEAN_PILLS.X, String(giaTri)) - khoa phai la
    // chuoi "true"/"false", khong phai boolean.
    expect(pillOf(BOOLEAN_PILLS.INTAKE_PAUSED, String(true)).label).toMatch(/tạm dừng/i);
    expect(pillOf(BOOLEAN_PILLS.INTAKE_PAUSED, String(false)).label).toMatch(/nhận/i);
    expect(pillOf(BOOLEAN_PILLS.SITE_ACTIVE, String(true)).label).toMatch(/bật/i);
  });
});
