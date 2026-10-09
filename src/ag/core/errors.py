"""The root of the exception hierarchy, and the one error raised from `core` itself.

What: `AgError` is the base every layer's error module subclasses; `ErrorContext` is what
every `AgError` carries; `fill_context` is the one way a layer adds what it knows to a
passing error; `InjectionError` says a value the runtime should have supplied never was.

Why: one root lets a caller catch anything this system raised without naming layers, and
one context shape lets a failure be localised from its record without a re-run. The
injection sentinels that raise `InjectionError` live in `core` and `ports`, so the type
cannot live in `runtime`. Import-time declaration errors stay `TypeError` and
`ValueError`: they fire while a module is being imported, which is what those builtins
mean.
"""

from __future__ import annotations

import operator
from collections.abc import Iterable
from dataclasses import dataclass
from itertools import islice

ROW_INDEX_CAP = 20
"""How many row indices an `ErrorContext` keeps; `row_count` carries the total."""


@dataclass(frozen=True, slots=True, kw_only=True)
class ErrorContext:
    """Where an error happened, filled by whichever layer knows each field.

    The adapter knows `method`, `tool`, `tool_messages` and `row_indices`; the lineage
    facade knows `handle` and `port`; the stage runner knows `operation`. Layers add
    fields through `fill_context` only, which never overwrites one already set.
    `row_indices` is a sample of at most `ROW_INDEX_CAP` rows on every construction
    path, and `row_count` is the total, derived from the indices when not given. Both
    sequences are normalised to tuples, the indices to plain `int` through
    `operator.index`, so an adapter may hand over engine integers or an array and the
    context stays hashable, while a float row position fails instead of truncating. A
    bare string passed as `tool_messages` is one message, not its characters.
    """

    operation: str | None = None
    port: str | None = None
    method: str | None = None
    handle: str | None = None
    row_indices: tuple[int, ...] = ()
    row_count: int | None = None
    tool: str | None = None
    tool_messages: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        indices = tuple(operator.index(index) for index in self.row_indices)
        object.__setattr__(self, "tool_messages", _as_messages(self.tool_messages))
        if indices and self.row_count is None:
            object.__setattr__(self, "row_count", len(indices))
        object.__setattr__(self, "row_indices", indices[:ROW_INDEX_CAP])


class AgError(Exception):
    """Base of every error this package raises on purpose."""

    def __init__(self, message: str, *, context: ErrorContext | None = None) -> None:
        super().__init__(message)
        self.context = ErrorContext() if context is None else context


class InjectionError(AgError):
    """A runtime-supplied value was used before the runtime supplied it.

    Raised when an unmaterialised handle is used as a path, or a scratch scope is called
    before the stage entry point bound one to the operation.
    """


def fill_context(
    error: AgError,
    *,
    operation: str | None = None,
    port: str | None = None,
    method: str | None = None,
    handle: str | None = None,
    row_indices: Iterable[int] | None = None,
    row_count: int | None = None,
    tool: str | None = None,
    tool_messages: Iterable[str] | None = None,
) -> None:
    """Adds to `error.context` whatever the caller knows, filling empty fields only.

    How: a field already set on the error is kept, so an error thrown inside a helper
    keeps the innermost method whatever the layers above add. `row_indices` and
    `row_count` are one pair: both are taken from the caller only when the error has
    neither, so an inner layer's count is never paired with an outer layer's rows. The
    sample is cut to `ROW_INDEX_CAP`; a caller that knows the total passes `row_count`
    and the indices are then read only up to the cap, so a large failure can hand over
    a generator without materialising it.

    Why: one place for the fill-if-empty rule, so no layer builds a context by hand or
    replaces fields another layer filled.
    """
    current = error.context
    # Explicit None tests: an array-like argument may refuse to be tested for truth.
    offered_rows: Iterable[int] = () if row_indices is None else row_indices
    offered_messages = _as_messages(tool_messages)
    if current.row_indices or current.row_count is not None:
        indices: tuple[int, ...] = current.row_indices
        row_count = current.row_count
    elif row_count is not None:
        indices = tuple(islice(offered_rows, ROW_INDEX_CAP))
    else:
        indices = tuple(offered_rows)
    error.context = ErrorContext(
        operation=_first(current.operation, operation),
        port=_first(current.port, port),
        method=_first(current.method, method),
        handle=_first(current.handle, handle),
        row_indices=indices,
        row_count=row_count,
        tool=_first(current.tool, tool),
        tool_messages=current.tool_messages or offered_messages,
    )


def _as_messages(value: Iterable[str] | None) -> tuple[str, ...]:
    """Tool messages as a tuple; a bare string is one message, not its characters."""
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    return tuple(value)


def _first[T](current: T | None, offered: T | None) -> T | None:
    """The value already set, else the one offered."""
    return offered if current is None else current
