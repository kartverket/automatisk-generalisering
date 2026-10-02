#!/usr/bin/env sh
# Formats both scopes with the pinned tools through uv, from anywhere in the repository:
# import sorting and then ruff format for src/, tests/ and tools/; Black for the legacy
# packages until they are migrated. docs/contributing/toolchain.md says which editor
# settings do the same on save.
set -eu
cd "$(git rev-parse --show-toplevel)"
uv run --locked --extra dev ruff check --fix --select I src tests tools
uv run --locked --extra dev ruff format src tests tools
uv run --locked --extra dev black --extend-exclude '^/(src|tests|tools|docs)/' .
