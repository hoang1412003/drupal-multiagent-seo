/**
 * Ham dinh dang dung chung - moi man hinh deu phu thuoc.
 *
 * Mot loi o day nhan len khap Console, va deu la loi IM LANG: hien sai gio
 * hay hien 0 thay cho null khong lam vo giao dien, chi lam nguoi doc hieu sai.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import { TIMEZONE_LABEL, formatDate, formatDateTime, formatNumber, shortId } from "./format";

afterEach(() => {
  vi.unstubAllEnvs();
});

describe("formatDateTime", () => {
  it("doi UTC sang gio dia phuong, khong hien nguyen UTC", () => {
    // Test chay o mui gio nao cung dung: so voi chinh Date cua moi truong.
    const iso = "2026-08-19T07:32:00Z";
    const d = new Date(iso);
    const pad = (n: number) => n.toString().padStart(2, "0");
    expect(formatDateTime(iso)).toBe(
      `${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()} ` +
        `${pad(d.getHours())}:${pad(d.getMinutes())}`,
    );
  });

  it("dinh dang ngay/thang/nam kieu Viet Nam, khong phai thang/ngay", () => {
    // 19/08 chu khong phai 08/19 - doc nham ngay la loi kho phat hien.
    const ket_qua = formatDateTime("2026-08-19T07:32:00Z");
    expect(ket_qua).toMatch(/^\d{2}\/\d{2}\/\d{4} \d{2}:\d{2}$/);
    expect(ket_qua.slice(3, 5)).toBe("08");
  });

  it("null, undefined va chuoi rong deu ra dau gach", () => {
    for (const v of [null, undefined, ""]) {
      expect(formatDateTime(v)).toBe("—");
    }
  });

  it("chuoi khong phai ngay thi ra dau gach, khong ra 'Invalid Date'", () => {
    expect(formatDateTime("khong-phai-ngay")).toBe("—");
  });

  it("co nhan mui gio de dat canh cot", () => {
    // Thieu nhan thi cung mot job hien 11:20 o Console va 04:20 o /admin cu.
    expect(TIMEZONE_LABEL).toBe("giờ VN");
  });
});

describe("formatDate", () => {
  it("cat lay phan ngay, khong bi lech mui gio", () => {
    // Khac formatDateTime: day la ngay theo lich, khong phai mot thoi diem.
    // Doi qua Date roi doi lai se lam 2026-08-19 thanh 18/08 o mui gio am.
    expect(formatDate("2026-08-19")).toBe("19/08/2026");
    expect(formatDate("2026-08-19T23:59:00Z")).toBe("19/08/2026");
  });

  it("null va chuoi cut deu ra dau gach", () => {
    expect(formatDate(null)).toBe("—");
    expect(formatDate("2026")).toBe("—");
  });
});

describe("formatNumber", () => {
  it("null KHONG bao gio hien thanh 0", () => {
    // final_score null = chua cham duoc. Hien 0 la noi rang da cham va duoc
    // 0 diem - hai chuyen khac han nhau.
    expect(formatNumber(null)).toBe("—");
    expect(formatNumber(undefined)).toBe("—");
  });

  it("so 0 that su van hien la 0", () => {
    expect(formatNumber(0)).toBe("0.0");
  });

  it("lam tron ve mot chu so mac dinh", () => {
    // API tra 40.9090909090909; hien tho lam cot diem lom chom.
    expect(formatNumber(40.9090909090909)).toBe("40.9");
    expect(formatNumber(40.9090909090909, 2)).toBe("40.91");
  });
});

describe("shortId", () => {
  it("rut gon UUID nhung van nhan ra duoc", () => {
    expect(shortId("a3f2b1c4-0000-4000-8000-000000009c41")).toBe("a3f2…9c41");
  });

  it("chuoi ngan thi giu nguyen, khong cat thanh vo nghia", () => {
    expect(shortId("abc123")).toBe("abc123");
  });

  it("null ra dau gach", () => {
    expect(shortId(null)).toBe("—");
  });
});
