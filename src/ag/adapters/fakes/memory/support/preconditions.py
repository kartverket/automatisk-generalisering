"""Preconditions more than one method group of the in-memory adapter checks.

What: `distinct_paths`, which refuses a call whose handles share a path.

Why: a method that reads a dataset and writes the same path would replace its input
mid-call, and two outputs on one path would leave only the second; the port docstrings
state the precondition and the adapter enforces it before touching the store. Paths are
compared, not handles, because handle equality leaves the path out and the store is
keyed by path.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

from ag.core.errors import ErrorContext
from ag.core.handles import ScratchHandle
from ag.ports.errors import PortContractError


def distinct_paths(*, handles: Iterable[ScratchHandle]) -> None:
    """Raises `PortContractError` when two of `handles` name the same path."""
    seen: dict[str, ScratchHandle] = {}
    for handle in handles:
        path = os.fspath(handle)
        if path in seen:
            raise PortContractError(
                f"{handle!r} and {seen[path]!r} both name {path!r}; the input and every "
                "output of one call are different datasets.",
                context=ErrorContext(handle=path),
            )
        seen[path] = handle
