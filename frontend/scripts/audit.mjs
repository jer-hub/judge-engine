// `npm audit --audit-level=high`, with a short list of reviewed exceptions.
// Each exception expires: after that date the advisory fails CI again, so it
// gets looked at instead of lingering forever.
import { execSync } from "node:child_process";

const ALLOWED = {
  // braces (via micromatch/fast-glob): no patched release exists, and
  // @next/eslint-plugin-next pins fast-glob 3.3.1. Lint tooling only; it is
  // not in the production image and never sees user input.
  "GHSA-vfj7-8cjw-p6xm": "2027-01-01",
};
const FAIL_AT = new Set(["high", "critical"]);

let raw;
try {
  raw = execSync("npm audit --json", { encoding: "utf8" });
} catch (err) {
  raw = err.stdout; // npm audit exits non-zero whenever it finds anything
}
const report = JSON.parse(raw);
const today = new Date().toISOString().slice(0, 10);

const blocking = new Map();
const allowed = new Set();
for (const vuln of Object.values(report.vulnerabilities ?? {})) {
  for (const via of vuln.via) {
    if (typeof via !== "object" || !FAIL_AT.has(via.severity)) continue;
    const id = via.url?.split("/").pop() ?? String(via.source);
    if (ALLOWED[id] && today < ALLOWED[id]) {
      allowed.add(`${id} (until ${ALLOWED[id]})`);
    } else {
      blocking.set(id, `${via.severity}: ${via.name} - ${via.title} ${via.url ?? ""}`);
    }
  }
}

for (const id of allowed) console.log(`Allowed: ${id}`);
if (blocking.size > 0) {
  console.error("Vulnerabilities at high severity or above:");
  for (const line of blocking.values()) console.error(`  ${line}`);
  process.exit(1);
}
console.log("No unreviewed high or critical vulnerabilities.");
