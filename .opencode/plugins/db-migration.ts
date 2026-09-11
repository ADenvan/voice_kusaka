import type { Plugin } from "@opencode-ai/plugin"
import { existsSync } from "node:fs"
import { join } from "node:path"

/**
 * Check whether a file looks like a schema or migration file.
 */
function isSchemaOrMigration(filePath: string): boolean {
  const lowered = filePath.toLowerCase()
  return (
    lowered.endsWith(".sql") ||
    lowered.includes("schema") ||
    lowered.includes("migration") ||
    (lowered.includes("model") && lowered.endsWith(".py"))
  )
}

/**
 * Validate SQLite schema by running it against an in-memory database.
 */
async function validateSqlSchema(
  $: any,
  filePath: string
): Promise<{ ok: boolean; message: string }> {
  try {
    // Use Python's sqlite3 to validate SQL syntax safely
    const script = `
import sqlite3, sys
conn = sqlite3.connect(':memory:')
with open(r'${filePath.replace(/\\/g, "\\\\")}', 'r', encoding='utf-8') as f:
    conn.executescript(f.read())
conn.close()
print('OK')
`
    const result = await $`python -c ${script}`.text()
    if (result.includes("OK")) {
      return { ok: true, message: "SQL schema is valid" }
    }
    return { ok: false, message: "SQL validation returned unexpected output" }
  } catch (error: any) {
    return { ok: false, message: String(error.stderr ?? error) }
  }
}

/**
 * Warn if a SQLite database exists that may need migration.
 */
function findExistingDbs(directory: string): string[] {
  const dbs: string[] = []
  // Simple check for common DB names at project root
  const commonNames = ["payroll.db", "database.db", "app.db", "data.sqlite", "data.sqlite3"]
  for (const name of commonNames) {
    const path = join(directory, name)
    if (existsSync(path)) {
      dbs.push(path)
    }
  }
  return dbs
}

/**
 * DB Migration Hook: validates schema files and warns about stale DBs.
 */
export const DBMigrationPlugin: Plugin = async ({ $, directory }) => {
  return {
    "file.edited": async ({ filePath }: { filePath: string }) => {
      if (!isSchemaOrMigration(filePath)) {
        return
      }

      console.log(`🗄️ Schema/migration file changed: ${filePath}`)

      // Validate SQL syntax if it's an .sql file
      if (filePath.toLowerCase().endsWith(".sql")) {
        const validation = await validateSqlSchema($, filePath)
        if (validation.ok) {
          console.log(`✅ ${validation.message}`)
        } else {
          console.error(`❌ ${validation.message}`)
        }
      }

      // Warn if existing DBs may need migration
      const existingDbs = findExistingDbs(directory)
      if (existingDbs.length > 0) {
        console.warn(
          `⚠️ Existing databases may need migration: ${existingDbs.join(", ")}`
        )
      }
    },
  }
}
