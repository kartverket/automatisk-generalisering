# CLAUDE.md

Instructions for Claude Code in this repository. For project-specific behavior this file
wins over personal or global instructions and over `.github/copilot-instructions.md`.

## Sandbox

Agents in this repository run under [cplt](https://github.com/navikt/cplt) with the
`strict` preset and Bubblewrap required (`sandbox.use_bubblewrap = true`). The repo policy
is `.cplt.toml`. The preset, Bubblewrap and the domain allowlist are set in each
developer's global cplt configuration; `.cplt.toml` cannot enforce them.

| Allowed | Blocked |
| --- | --- |
| Read and write the project directory and the session scratch directory (`$TMPDIR`) | Writing anywhere else outside the project directory (tool caches, system temp directories without exec, and Claude Code's own state excepted) |
| The project toolchain through `uv run --locked` | SSH keys, cloud credentials, Docker and git credentials, GitHub tokens in environment variables |
| Outbound HTTPS through cplt's proxy to the preset's domain allowlist | Any other domain, non-HTTPS ports, UDP, localhost services, the Docker socket |
| Read-only git | `git push` (cplt's git guard) |

- A denied file, command or connection is policy. Stop and report what was blocked and
  why you needed it.
- `gh`'s token file (`~/.config/gh/hosts.yml`) is readable by design. Do not read it, and
  do not use `gh`.
- Web search may work, since it runs through Claude's API. Fetching pages from domains
  outside the allowlist (`WebFetch`, `curl`) is blocked. If you need a specific page,
  report the URL.
- Do not read or suggest edits to `.env`, `.env.*`, files matching `*.key`, `*.pem` or
  `*.secret`, or anything under a `secrets/` or `credentials/` directory, even if they
  exist and are readable.
  The sandbox does not block all of these inside the project directory on every
  platform.

## Checks

Pre-commit, CI and a manual run all execute `.pre-commit-config.yaml`. Every hook is
check-only: no hook rewrites source files. Their only side effects are tool caches and
`uv` syncing `.venv` to `uv.lock`.

- **Full check**, before reporting work as done:

  ```bash
  uv run --locked --extra dev pre-commit run --all-files
  ```

- **Fast check**, while working: the `entry` command of the relevant hook, for example
  `uv run --locked --extra dev pyright` or `uv run --locked --extra dev pytest -m "not arcpy"`.
- Always go through `uv run --locked --extra dev`. Do not use `uv run --no-sync`,
  `.venv/bin/...`, or tools from `PATH`; tool versions must come from `uv.lock`.
- ArcPy-marked tests are excluded by marker. Do not remove the marker or change the test
  selection to make tests pass.
- Do not add, remove or upgrade dependencies. If a task needs one, stop and say which
  package and why.

## Git

The default branch is `main`.

Under the `strict` preset, cplt's git guard refuses every `git push`, other remote writes
(`request-pull`, `send-pack`, `subtree push`), and changes to the `origin` URL or to URL
rewrite rules. It allows ordinary local operations (commit, branch, merge, rebase, reset,
stash and the like), so the rules below are not enforced by the sandbox. Follow them anyway.

- Allowed: read-only git (`status`, `diff`, `log`, `show`, `blame`).
- Only when asked by name: staging (`git add`, `git mv`, `git rm`).
- Never: `commit`, `stash`, `merge`, `rebase`, `cherry-pick`, `revert`, `reset`, `tag`,
  `fetch`, `pull`; creating or switching branches; `git worktree` or worktree-isolated
  subagents.
- Never discard working-tree changes (`git restore`, `git checkout -- <path>`,
  `git clean`). Uncommitted work belongs to the maintainer.
- Never edit files under `.git/` or change git configuration, in particular
  `core.hooksPath`. On Linux the sandbox cannot block writes to `.git/config`.

## Files that need an explicit request

Do not edit these unless the task explicitly asks for it. If a change seems necessary,
propose it instead:

- `.cplt.toml`, `CLAUDE.md`, `.claude/`, `.github/`
- `.pre-commit-config.yaml`, `.importlinter`, `pyproject.toml`, `uv.lock`
- `tests/conftest.py`, `tools/`
- Any script a hook in `.pre-commit-config.yaml` invokes, including those under
  `docs/refactor/`

These control what runs outside the sandbox on developers' machines and in CI.

## Design records

- The A/B decision record (`DECISIONS.md`) and the task list live in
  `docs/refactor/temp/`. That directory is staging and will move; follow the new
  location if it has. A-items are decided, B-items are open. Do not change a decided
  A-item; if your work conflicts with one, stop and report the conflict.
- Numbered ADRs live in `docs/refactor/decisions/`. An A-item is authoritative until it
  has landed at its destination. Once an entry records that it moved to an ADR, the ADR
  wins and the A-item is only a pointer. ADRs are never edited; a new ADR supersedes an
  old one.
- The `check-consistency` and `check-terminology` hooks enforce consistency between the
  records and the terminology.

## Code conventions

- Python version and tool settings: as pinned in `pyproject.toml`.
- Pyright as configured in `pyproject.toml`: standard mode, strict on `src/`, `tests/`
  and `tools/`. Type hints are mandatory, including return types.
- Ruff is the only formatter and linter.
- Prefer keyword arguments; use positional only where an API or a hot loop requires it.
- Core logic never imports `arcpy` or other third-party libraries directly. Ports are
  narrow `typing.Protocol` classes; adapters conform structurally. Prefer composition
  config over inheritance. `.importlinter` is authoritative for import boundaries.
- Use the simplest type construct that expresses intent: builtin, `TypeAlias`,
  `TypedDict`, `dataclass`, `Protocol`, in that order.
- Pipeline entry points are guarded by `if __name__ == "__main__":`.
- Docstrings follow `docs/contributing/docstring.md`.

## Reporting

End each task with:

1. What changed (files and why).
2. The full check result per hook.
3. Anything blocked by the sandbox, and anything you were unsure about or did not do.
4. When work is ready: the files to stage and a suggested commit message. Then stop.
