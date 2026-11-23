import { expect, type Locator, type Page } from "@playwright/test";

export class JudgeAppPage {
  readonly page: Page;
  readonly usernameInput: Locator;
  readonly passwordInput: Locator;
  readonly signInButton: Locator;
  readonly submitJavaButton: Locator;

  constructor(page: Page) {
    this.page = page;
    this.usernameInput = page.getByLabel("Username");
    this.passwordInput = page.getByLabel("Password");
    this.signInButton = page.getByRole("button", { name: "Sign in" });
    this.submitJavaButton = page.getByRole("button", { name: /Submit Java/i });
  }

  async gotoLogin() {
    await this.page.goto("/login", { waitUntil: "networkidle" });
    await expect(this.page.getByRole("heading", { name: "Sign in" })).toBeVisible();
  }

  async login(username: string, password: string) {
    await this.gotoLogin();
    await this.usernameInput.fill(username);
    await this.passwordInput.fill(password);
    await this.signInButton.click();
  }

  async openProblemBySlug(slug: string) {
    await this.page.goto(`/problems/${slug}`, { waitUntil: "networkidle" });
    await expect(this.submitJavaButton).toBeVisible();
  }

  async replaceMonacoCode(source: string) {
    await this.page
      .context()
      .grantPermissions(["clipboard-read", "clipboard-write"]);
    const editor = this.page.locator(".monaco-editor").first();
    await expect(editor).toBeVisible({ timeout: 30_000 });
    // Wait until Monaco's view lines render (editor fully mounted)
    await expect(editor.locator(".view-lines")).toBeVisible({ timeout: 20_000 });
    await editor.click();
    await this.page.evaluate(async (text) => {
      await navigator.clipboard.writeText(text);
    }, source);
    const mod = process.platform === "darwin" ? "Meta" : "Control";
    await this.page.keyboard.press(`${mod}+KeyA`);
    await this.page.keyboard.press("Backspace");
    await this.page.keyboard.press(`${mod}+KeyV`);
  }
}
