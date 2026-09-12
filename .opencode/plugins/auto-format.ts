import type { Plugin } from "@opencode-ai/plugin"
import { addChangedFile } from "./lib/changed-files-store"

/**
 * Auto-format Python files with ruff after editing.
 */
export const AutoFormatPlugin: Plugin = async ({ $ }) => {
  return {
    "file.edited": async ({ filePath }: { filePath: string }) => {
      if (!filePath.endsWith(".py")) {
        return
      }

      // Track for coverage tracker fallback
      addChangedFile(filePath)

      try {
        await $`ruff format ${filePath}`
        console.log(`✅ Formatted: ${filePath}`)
      } catch (error) {
        console.error(`❌ Format failed for ${filePath}:`, error)
      }
    },
  }
}
