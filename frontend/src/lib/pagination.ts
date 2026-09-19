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
