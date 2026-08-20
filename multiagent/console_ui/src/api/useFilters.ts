/**
 * Gia tri hop le cho moi bo loc, lay tu server.
 *
 * KHONG viet cung danh sach trang thai/quyet dinh trong component. Enum khong
 * nam trong openapi.json (`status` khai la `str`), nen mot danh sach viet cung
 * bi sai se khong phep kiem nao bat duoc - da tung xay ra.
 */
import { useQuery } from "@tanstack/react-query";

import { client } from "./client";
import type { components } from "./api-types";

export type FiltersResponse = components["schemas"]["FiltersResponse"];
export type SiteOption = components["schemas"]["SiteOptionModel"];

export function useFilters() {
  return useQuery({
    queryKey: ["filters"],
    queryFn: () => client.get<FiltersResponse>("/filters"),
    // Gia tri hau nhu khong doi trong mot phien lam viec.
    staleTime: 10 * 60 * 1000,
  });
}
