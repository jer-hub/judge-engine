import { expect, test } from "@playwright/test";

import { JudgeAppPage } from "./pages/JudgeAppPage";

const A_PLUS_B_SOLUTION = `import java.util.*;
public class Solution {
  public static void main(String[] args) {
    Scanner sc = new Scanner(System.in);
    System.out.println(sc.nextInt() + sc.nextInt());
  }
}
`;

test.describe("Contestant critical smoke flow", () => {
  test("rejects invalid credentials with accessible alert", async ({ page }) => {
    const app = new JudgeAppPage(page);
    // Use a separate username so alice's per-user login throttle stays untouched.
    await app.login(`e2e-invalid-${Date.now()}`, "wrong-password-123");

    const formAlert = page.locator('form [role="alert"]');
    await expect(formAlert).toBeVisible();
    await expect(formAlert).not.toBeEmpty();
  });

  test("logs in as student, enters contest context if active, submits A Plus B, and reaches Accepted", async ({
    page,
  }) => {
    const app = new JudgeAppPage(page);
    const username = process.env.E2E_STUDENT_USER || "alice";
    const password = process.env.E2E_STUDENT_PASSWORD || "demo123";

    await app.login(username, password);
    await expect(page).toHaveURL(/\/problems/);

    // Navigate to A Plus B without ?contest= first to verify contest-context recovery banner.
    await app.openProblemBySlug("a-plus-b");
    await expect(page.getByRole("heading", { name: /A Plus B/i }).first()).toBeVisible();

    // Wait briefly for problem detail active_contests banner if Demo Cup is live.
    const switchToContest = page.getByRole("link", { name: /^Open in /i }).first();
    if (await switchToContest.isVisible()) {
      await switchToContest.click();
      await expect(page).toHaveURL(/\/problems\/a-plus-b\?contest=\d+/);
      await expect(page.getByRole("link", { name: "Scoreboard" })).toBeVisible();
    }

    await app.replaceMonacoCode(A_PLUS_B_SOLUTION);

    const enterFullscreen = page.getByRole("button", { name: "Enter fullscreen" });
    if (await enterFullscreen.isVisible()) {
      await enterFullscreen.click();
    }
    await expect(app.submitJavaButton).toBeEnabled();
    await app.submitJavaButton.click();

    // Poll until live SubmissionStatus card displays Accepted from the Docker sandbox.
    const submissionSection = page.locator("section").filter({ hasText: /Submission #/i });
    await expect(submissionSection).toBeVisible({ timeout: 30_000 });
    await expect(submissionSection.getByText("Accepted").first()).toBeVisible({
      timeout: 60_000,
    });
  });
});
