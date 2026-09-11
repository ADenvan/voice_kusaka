import type { Plugin } from "@opencode-ai/plugin"
import { basename } from "node:path"
import {
  getChangedFiles,
  clearChangedFiles,
} from "./lib/changed-files-store"

/**
 * Extract changed Python source files (non-test) since the last commit via git.
 */
async function getGitChangedPyFiles($: any, directory: string): Promise<string[]> {
  try {
    const diff = await $`git -C ${directory} diff --name-only HEAD`.text()
    return diff
      .split("\n")
      .map((s: string) => s.trim())
      .filter(
        (f: string) =>
          f.endsWith(".py") &&
          !f.startsWith("test_") &&
          !f.includes("/test_")
      )
  } catch {
    return []
  }
}

/**
 * Get changed files from in-memory store (fallback when git unavailable).
 */
function getSessionChangedPyFiles(): string[] {
  return getChangedFiles().filter(
    (f) => !f.startsWith("test_") && !f.includes("/test_")
  )
}

/**
 * Parse pytest --cov terminal output and return lines mentioning given files.
 */
function filterCoverageForFiles(covOutput: string, files: string[]): string[] {
  const fileNames = files.map((f) => f.replace(/\\/g, "/"))
  return covOutput
    .split("\n")
    .filter((line) => fileNames.some((name) => line.includes(name)))
}

/**
 * Coverage Tracker Hook: after pytest runs, show coverage summary for changed files.
 */
export const CoverageTrackerPlugin: Plugin = async ({ $, directory }) => {
  return {
    "tool.execute.after": async (input: any) => {
      // Only react to bash executions that ran pytest
      if (input?.tool !== "bash" || !input?.args?.command) {
        return
      }
      const command: string = input.args.command
      if (!command.includes("pytest")) {
        return
      }

      try {
        // Prefer git diff, fallback to session store
        let changedFiles = await getGitChangedPyFiles($, directory)
        if (changedFiles.length === 0) {
          changedFiles = getSessionChangedPyFiles()
        }

        if (changedFiles.length === 0) {
          console.log("📊 No changed Python source files tracked.")
          return
        }

        console.log("📊 Running coverage report for changed files...")
        const covOutput = await $`pytest --cov=src --cov-report=term-missing --no-cov-on-fail -q`.text()

        // Print overall tail of report
        const lines = covOutput.split("\n")
        console.log("\n📊 Overall Coverage Summary:")
        console.log(lines.slice(-6).join("\n"))

        // Print per-file coverage for changed files
        const relevantLines = filterCoverageForFiles(covOutput, changedFiles)
        if (relevantLines.length > 0) {
          console.log("\n📁 Changed files coverage:")
          relevantLines.forEach((l) => console.log(l))
        } else {
          console.log("\n📁 No coverage data matched changed files.")
        }

        // Clear session store after reporting
        clearChangedFiles()
      } catch (error: any) {
        // pytest may exit non-zero on test failures
        console.error("⚠️ Coverage check failed:", error.stderr ?? error)
      }
    },
  }
}
