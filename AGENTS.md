# Rules

## Language Strategy
- **User interaction language**: Russian (all plans, explanations, and dialogue).
- User-facing docs (README): Russian

## Core Directives

### Must Always
- Before writing any code, check if this task requires **planning** (architecture, design, or unclear scope). If yes, then first we break the task down into stages..
- For implementation, use the `build` agent. It can write code, run tests, and refactor.
- Write tests before implementation (TDD) and verify critical paths.
- Validate inputs and keep security checks intact.
- Prefer immutable updates over mutating shared state.
- Follow existing repository patterns before inventing new ones.
- Keep contributions focused, reviewable, and well-described.

## Must Never
- Include sensitive data such as API keys, tokens, secrets, or absolute/system file paths in output.
- Submit untested changes.
- Bypass security checks or validation hooks.
- Duplicate existing functionality without a clear reason.
- Ship code without checking the relevant test suite.

## Agent Dispatch Logic
- **Plan** → use when: task is ambiguous, involves architecture, database schema, new feature design, or integration with external systems. Plan agent is read-only and produces a structured plan.
- **Build** → use for: coding, testing, refactoring, bug fixing. This is the default agent for development work.

## Agent Format
- Agents live in `agents/*.md`.
- Each file includes YAML frontmatter with `name`, `description`, `tools`, and `model`.
- File names are lowercase with hyphens and must match the agent name.
- Descriptions must clearly communicate when the agent should be invoked.

## Conventions
- **Type hints**: required on all functions (`mypy --strict`).
- **Docstrings**: Google convention, short description before every function.
- **Line length**: 100 (ruff formatter).
- **Quotes**: double quotes.
- **Naming**: descriptive English names.
- **No `print()` statements** — use `logging`.
- **Immutability**: prefer immutable updates over mutating shared state.
- **Functions**: keep under 50 lines when possible.
- **Security**: no hardcoded secrets; use `os.environ`. Parameterized SQL queries only.

## Testing
- **Framework**: pytest, minimum 80% coverage.
- **Workflow**: write test → run (FAIL) → implement → run `pytest --cov` (PASS, 80%+).
- Use in-memory SQLite for database tests.

## Security
- Never ask the user to paste secrets into chat.
- Use `.env` for local secrets, GitHub Actions Secrets for CI/CD.
- Always request confirmation before deploying or pushing to `main`/production.
- Ensure secret patterns are gitignored (`.env`, `*.key`, `credentials.json`, etc.).
