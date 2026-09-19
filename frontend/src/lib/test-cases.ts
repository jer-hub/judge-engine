import { apiFetch } from "@/lib/api";
import type { Paginated } from "@/lib/types";

export type TestCase = {
  id: number;
  problem: number;
  order: number;
  input_data: string;
  expected_output: string;
  is_sample: boolean;
  points: number;
};

export type TestCaseInput = Omit<TestCase, "id"> & { id?: number };

export function listTestCases(problemId: number) {
  return apiFetch<Paginated<TestCase>>(`/test-cases/?problem=${problemId}&page_size=100`);
}

export function createTestCase(body: TestCaseInput) {
  return apiFetch<TestCase>("/test-cases/", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateTestCase(id: number, body: Partial<TestCaseInput>) {
  return apiFetch<TestCase>(`/test-cases/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function deleteTestCase(id: number) {
  return apiFetch<null>(`/test-cases/${id}/`, { method: "DELETE" });
}

export function reorderTestCases(items: Array<{ id: number; order: number }>) {
  return apiFetch<{ updated: number }>("/test-cases/reorder/", {
    method: "POST",
    body: JSON.stringify({ items }),
  });
}
