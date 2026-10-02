// Serve the Monaco editor from this app instead of a CDN, so the code editor
// works in labs without internet access and always matches the installed
// monaco-editor version. Runs before `dev` and `build` (see package.json).
import { existsSync } from "node:fs";
import { cp, mkdir, rm } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const root = dirname(dirname(fileURLToPath(import.meta.url)));
// monaco-editor comes with @monaco-editor/react; look it up from there. Its
// package "exports" hide package.json, so search the node_modules paths.
const reactPkg = require.resolve("@monaco-editor/react/package.json");
const searchPaths = createRequire(reactPkg).resolve.paths("monaco-editor") ?? [];
const source = searchPaths
  .map((dir) => join(dir, "monaco-editor", "min", "vs"))
  .find((dir) => existsSync(join(dir, "loader.js")));
if (!source) {
  throw new Error("monaco-editor/min/vs not found; run npm install.");
}
const target = join(root, "public", "monaco", "vs");

await rm(target, { recursive: true, force: true });
await mkdir(dirname(target), { recursive: true });
await cp(source, target, { recursive: true });
console.log(`Monaco copied to ${target}`);
