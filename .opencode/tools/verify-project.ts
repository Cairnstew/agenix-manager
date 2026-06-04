import { tool } from "@opencode-ai/plugin"
import { execSync } from "node:child_process"
import fs from "node:fs"
import path from "node:path"

export default tool({
  description:
    "Verify project consistency: Python version sync, lock-file freshness, and agent rules compliance",

  args: {
    fix: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Attempt auto-fixes where possible"),
  },

  async execute(args, context) {
    const worktree = context.worktree
    const issues: string[] = []
    const fixes: string[] = []

    // ── 1. Python version sync ──────────────────────────────────────
    const pyprojectPath = path.join(worktree, "pyproject.toml")
    const flakePath = path.join(worktree, "flake.nix")

    let pyprojectVer = ""
    let flakeVer = ""
    try {
      const pyproject = fs.readFileSync(pyprojectPath, "utf-8")
      const m = pyproject.match(/requires-python\s*=\s*"~=(\d+\.\d+)/)
      if (m) pyprojectVer = m[1]
    } catch { /* file missing */ }

    try {
      const flake = fs.readFileSync(flakePath, "utf-8")
      const m = flake.match(/python\s*=\s*pkgs\.python(\d{3})/)
      if (m) {
        const v = m[1]
        flakeVer = `${v[0]}.${v[1]}${v[2] === "0" ? "" : v[2]}`
      }
    } catch { /* file missing */ }

    if (pyprojectVer && flakeVer && pyprojectVer !== flakeVer) {
      issues.push(
        `Python version mismatch: pyproject.toml says ${pyprojectVer}, flake.nix says ${flakeVer}`,
      )
      fixes.push(
        "Run: sed -i 's/python = pkgs.python3[0-9][0-9]/python = pkgs.python3'`echo "3'${pyprojectVer//./}"`'/ flake.nix",
      )
    } else if (!pyprojectVer || !flakeVer) {
      issues.push(
        "Could not determine Python version from one or both files",
      )
    } else {
      issues.push(`✅ Python version: ${pyprojectVer} (in sync)`)
    }

    // ── 2. uv.lock freshness ───────────────────────────────────────
    const uvLockPath = path.join(worktree, "uv.lock")
    try {
      const uvStat = fs.statSync(uvLockPath)
      const pyprojectStat = fs.statSync(pyprojectPath)
      if (uvStat.mtimeMs < pyprojectStat.mtimeMs) {
        issues.push("⚠️  uv.lock is older than pyproject.toml — run `uv lock`")
      } else {
        issues.push("✅ uv.lock is up to date")
      }
    } catch {
      issues.push("⚠️  uv.lock not found — run `uv lock`")
    }

    // ── 3. flake.lock freshness ────────────────────────────────────
    const flakeLockPath = path.join(worktree, "flake.lock")
    try {
      const flakeLockStat = fs.statSync(flakeLockPath)
      const flakeStat = fs.statSync(flakePath)
      if (flakeLockStat.mtimeMs < flakeStat.mtimeMs) {
        issues.push("⚠️  flake.lock is older than flake.nix — run `nix flake lock`")
        fixes.push("Run: nix flake lock")
      } else {
        issues.push("✅ flake.lock is up to date")
      }
    } catch {
      issues.push("⚠️  flake.lock not found — run `nix flake lock`")
      fixes.push("Run: nix flake lock")
    }

    // ── 4. secrets.nix git tracking ────────────────────────────────
    try {
      const gitOut = execSync(
        "git ls-files --error-unmatch secrets/secrets.nix 2>/dev/null || echo NOT_TRACKED",
        { cwd: worktree, encoding: "utf-8" },
      )
      if (gitOut.includes("NOT_TRACKED")) {
        issues.push(
          "⚠️  secrets/secrets.nix is not git-tracked (see AGENTS.md rule 6)",
        )
        fixes.push("Run: git add secrets/secrets.nix")
      } else {
        issues.push("✅ secrets/secrets.nix is git-tracked")
      }
    } catch {
      // secrets dir may not exist yet — not an error
      issues.push("ℹ️  secrets/ directory not found (expected for fresh clones)")
    }

    return [
      "## Project consistency report",
      ...issues.map((l) => `  ${l}`),
      "",
      fixes.length > 0
        ? `## Suggested fixes\n${fixes.map((f) => `  ${f}`).join("\n")}`
        : "## No fixes needed",
    ].join("\n")
  },
})
