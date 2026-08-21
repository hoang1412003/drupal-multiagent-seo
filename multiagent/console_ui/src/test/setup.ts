/** Chay truoc moi file test. Xem vite.config.ts muc `test.setupFiles`. */
import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, expect } from "vitest";

afterEach(() => {
  cleanup();
});

/**
 * Chan `fetch` that o cap toan cuc.
 *
 * Test nao quen khai bao route se NEM LOI thay vi lang le nhan `undefined` -
 * mot test im lang di qua vi khong co du lieu la test khong kiem gi ca.
 */
const chuaKhaiBao = () => {
  throw new Error(
    "Test goi ra mang ma chua khai bao route. Dung mockApi() trong harness.tsx.",
  );
};
globalThis.fetch = chuaKhaiBao as unknown as typeof fetch;

expect.extend({});
