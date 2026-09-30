# Contribution Guide

### 1. Code Style & Formatting

- Code under `src/`, `tests/` and `tools/` is formatted by `ruff format` and type-checked by
  pyright in strict mode; the legacy packages are formatted by Black until they are migrated.
- uv manages the environment and the tools; see [setup and toolchain](toolchain.md).
- Every check runs as a pre-commit hook and again on every pull request; see
  [testing and checks](testing.md) for running them by hand.
- Python 3.13 is the target; see [the Python target](python-version.md).
- Use type hinting

### 2. Naming Conventions

- Use descriptive names, no abbreviations unless absolutely necessary.
- Prefer clarity over brevity.
- Avoid single-letter variables except for trivial loops.

### 3. Docstring
Please read our [docstring documentation](docstring.md)
### 4. Branching & Git Workflow

- Create a feature branch for each task or fix.
- Always pull using rebase to keep history linear.
- PR titles should clearly describe the contribution.
- PRs will be merged into main with squash merge.

### 5. Pull Requests & Reviews

- Every PR must be reviewed by a team member.
- The author merges their own PR after approval.
- The author is responsible for writing the PR summary.
- Delete inactive feature branches.

---
### Navigation

- [Return to README](../../README.md)
