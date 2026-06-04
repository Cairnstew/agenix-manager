import { tool } from "@opencode-ai/plugin"
import { execSync } from "node:child_process"
import path from "node:path"

function run(cmd: string, worktree: string): string {
  try {
    return execSync(cmd, {
      cwd: worktree,
      encoding: "utf-8",
      maxBuffer: 10 * 1024 * 1024,
    })
  } catch (e: unknown) {
    const err = e as { stdout?: string; stderr?: string; message?: string }
    return err.stdout || err.stderr || err.message || "Unknown error"
  }
}

export default tool({
  description: "Run Ruff linter and MyPy type checker on the project source",

  args: {
    fix: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Apply Ruff auto-fixes where possible"),
    typecheck: tool.schema
      .boolean()
      .optional()
      .default(true)
      .describe("Also run mypy type checking"),
  },

  async execute(args, context) {
    const worktree = context.worktree
    const src = path.join(worktree, "src")
    const python = path.join(worktree, ".venv/bin/python")
    const results: string[] = []

    // ── Ruff ────────────────────────────────────────────────────────
    let ruffCmd = `${python} -m ruff check "${src}"`
    if (args.fix) ruffCmd += " --fix"
    results.push(">>> Ruff")
    results.push(run(ruffCmd, worktree))

    // ── MyPy ────────────────────────────────────────────────────────
    if (args.typecheck) {
      results.push("")
      results.push(">>> MyPy")
      results.push(run(`${python} -m mypy "${src}"`, worktree))
    }

    return results.join("\n")
  },
})
