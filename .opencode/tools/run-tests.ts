import { tool } from "@opencode-ai/plugin"
import { execSync } from "node:child_process"
import path from "node:path"

export default tool({
  description: "Run the agenix-manager test suite with common options",

  args: {
    path: tool.schema
      .string()
      .optional()
      .describe(
        "Test file or pattern (e.g. 'test_config.py', 'tests/test_ops.py::TestDecrypt')",
      ),
    verbose: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Show verbose (-v) output"),
    quick: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Skip slow (nix eval) tests"),
    fail_fast: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Stop on first failure"),
    cli_integration: tool.schema
      .boolean()
      .optional()
      .default(false)
      .describe("Include CLI integration tests (needs CLI_TESTS=1)"),
  },

  async execute(args, context) {
    const worktree = context.worktree
    const python = path.join(worktree, ".venv/bin/python")

    let cmd = `${python} -m pytest`
    if (args.verbose) cmd += " -v"
    if (args.fail_fast) cmd += " -x"
    if (args.quick || !args.cli_integration) cmd += " --ignore=tests/test_nix_eval.py"
    if (!args.cli_integration) cmd += " --ignore=tests/test_cli_integration.py"

    if (args.path) {
      cmd += ` ${args.path}`
    } else {
      cmd += " tests/"
    }

    const env: Record<string, string> = { ...process.env as Record<string, string> }
    if (args.cli_integration) env["CLI_TESTS"] = "1"

    try {
      const out = execSync(cmd, {
        cwd: worktree,
        env,
        encoding: "utf-8",
        maxBuffer: 10 * 1024 * 1024,
      })
      return out
    } catch (e: unknown) {
      const err = e as { stdout?: string; stderr?: string; message?: string }
      return err.stdout || err.stderr || err.message || "Unknown error"
    }
  },
})
