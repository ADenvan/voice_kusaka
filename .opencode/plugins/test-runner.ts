import type { Plugin } from "@opencode-ai/plugin"
import { existsSync } from "node:fs"
import { basename, dirname, join } from "node:path"
import { addChangedFile } from "./lib/changed-files-store"

/**
 * Find a related test file for a given source file.
 */
function findRelatedTest(filePath: string, directory: string): string | null {
  const base = basename(filePath, ".py")
  const dir = dirname(filePath)
  const relativeToDir = dir.replace(directory, "").replace(/^[/\\]/, "")

  const candidates = [
    join(dir, `test_${base}.py`),
    join(directory, "tests", relativeToDir, `test_${base}.py`),
    join(directory, "tests", `test_${base}.py`),
  ]

  for (const candidate of candidates) {
    if (existsSync(candidate)) {
      return candidate
    }
  }
  return null
}

/**
 * Auto-run pytest when Python files are edited.
 */
export const TestRunnerPlugin: Plugin = async ({ $, directory }) => {
  return {
    "file.edited": async ({ filePath }: { filePath: string }) => {
      if (!filePath.endsWith(".py")) {
        return
      }

      // Track for coverage tracker fallback
      addChangedFile(filePath)

      const testsDir = join(directory, "tests")
      const hasTestsDir = existsSync(testsDir)

      try {
        // If the edited file is a test itself, run it directly
        if (basename(filePath).startsWith("test_")) {
          console.log(`🧪 Running test: ${filePath}`)
          await $`pytest ${filePath} -v`
          return
        }

        // Look for a related test file
        const relatedTest = findRelatedTest(filePath, directory)
        if (relatedTest) {
          console.log(`🧪 Running related test: ${relatedTest}`)
          await $`pytest ${relatedTest} -v`
          return
        }

        // Fall back to full suite if tests/ exists
        if (hasTestsDir) {
          console.log(`🧪 Running full test suite for changes in ${filePath}`)
          await $`pytest -v`
        }
      } catch (error) {
        // pytest exits non-zero when tests fail, which throws in Bun shell
        console.error(`⚠️ Tests failed for ${filePath}`)
      }
    },
  }
}
