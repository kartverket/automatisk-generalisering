#!/usr/bin/env sh
# Formats the whole repository with the pinned ruff through uv, from anywhere in the
# repository: import sorting, then formatting. docs/contributing/toolchain.md says which
# editor settings do the same on save.
set -eu
cd "$(git rev-parse --show-toplevel)"
uv run --locked --extra dev ruff check --fix --select I .
uv run --locked --extra dev ruff format .
