import { apiFetch } from "@/lib/api";
import type { Paginated } from "@/lib/types";

/** The backend's max_page_size (config/pagination.py). */
const MAX_PAGE_SIZE = 100;

export type ListQueryParams = Record<
  string,
  string | number | boolean | null | undefined
>;

export function buildListQuery(
  basePath: string,
  params: ListQueryParams = {},
): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  const path = basePath.endsWith("/") ? basePath : `${basePath}/`;
  return qs ? `${path}?${qs}` : path;
}

/**
 * Every page of a list endpoint merged into one result, for pickers and
 * validation that must see all rows (a school can have 100+ students).
 */
export async function fetchAllPages<T>(
  basePath: string,
  params: ListQueryParams = {},
): Promise<Paginated<T>> {
  const results: T[] = [];
  for (let page = 1; ; page++) {
    const data = await apiFetch<Paginated<T>>(
      buildListQuery(basePath, { ...params, page_size: MAX_PAGE_SIZE, page }),
    );
    results.push(...data.results);
    // `next` is an absolute backend URL, so only use it as a "more" flag.
    if (!data.next) return { count: data.count, next: null, previous: null, results };
  }
}

export function pageRange(
  count: number,
  page: number,
  pageSize: number,
): { from: number; to: number; totalPages: number } {
  if (count <= 0 || pageSize <= 0) {
    return { from: 0, to: 0, totalPages: 0 };
  }
  const totalPages = Math.max(1, Math.ceil(count / pageSize));
  const safePage = Math.min(Math.max(1, page), totalPages);
  const from = (safePage - 1) * pageSize + 1;
  const to = Math.min(count, safePage * pageSize);
  return { from, to, totalPages };
}
