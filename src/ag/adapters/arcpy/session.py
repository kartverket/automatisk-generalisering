"""The ArcPy session: the one module of the adapter that runs tools.

What: `ArcpySession` executes a tool by name through `run_tool`, applies the project
environment standard to `arcpy.env` once on construction, and names the vendor exception
class; `guard` turns an engine failure in any other engine call into `EngineError`.
`open_session` is the composition root's way in: it is the one place under the adapter
that imports `arcpy`. The session module alone executes tools, holds engine-global state
and names vendor exceptions, and every other engine call in the adapter runs inside
`guard` (ADR-0018 AR-D23).

How: `run_tool` resolves a dotted name on the engine, calls it with keyword arguments
inside `guard`, logs the messages the result object carries, and returns the result. A
caller that needs a tool's output reads it through an accessor added here, never by
touching the engine. `guard` wraps two classes: the engine's `ExecuteError`, and an exact
`RuntimeError`, the class the engine's cursors are expected to raise for a missing field
or a locked dataset. An `AgError`, an adapter defect such as `KeyError`, and a
`RuntimeError` subclass pass through unchanged. On `ExecuteError` the tool ran, so the
engine's message buffer is its messages and is drained into the context; an exact
`RuntimeError` is taken to mean the call did not reach a tool, so the buffer, which
belongs to whatever ran last, is left out. The first run under the engine confirms or
corrects the catch set and the drain rule.

Why: the session applies the project environment standard, output coordinate system,
XY tolerance and XY resolution, so that every product is in it (ADR-0021 ST-D25). The
output coordinate system makes the engine reproject a non-conforming input silently, and
overwrite hides a scratch-name collision; both are kept. The workspace and the parallel
processing factor are not set: a handle carries its own location, and parallelism is
the runtime's.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType
from typing import Protocol

from ag.core.errors import ErrorContext
from ag.ports.errors import EngineError


@dataclass(frozen=True, slots=True, kw_only=True)
class Environment:
    """The engine-global values the session applies; one standard for the project."""

    output_epsg: int
    xy_tolerance_m: float
    xy_resolution_m: float
    overwrite_output: bool


ENVIRONMENT = Environment(
    output_epsg=25833,
    xy_tolerance_m=0.1,
    xy_resolution_m=0.01,
    overwrite_output=True,
)
"""The project environment standard. Tuned here and nowhere else."""


class _ToolResult(Protocol):
    """What a tool call returns: the engine's result object, read for its messages."""

    def getMessages(self) -> str: ...


class ArcpySession:
    """Runs tools, guards other engine calls and holds the applied environment.

    Constructed with the engine module so that a test can hand in a fake; the composition
    root constructs it through `open_session`.
    """

    def __init__(self, *, engine: ModuleType) -> None:
        self._engine = engine
        # The one place a vendor exception is named: resolved once, on construction.
        self._execute_error: type[BaseException] = getattr(engine, "ExecuteError")
        self._log = logging.getLogger(__name__)
        with self.guard("environment"):
            _apply(engine, ENVIRONMENT)
        self._environment = ENVIRONMENT

    @property
    def environment(self) -> Environment:
        """The values applied to the engine on construction."""
        return self._environment

    @contextmanager
    def guard(self, what: str, /) -> Iterator[None]:
        """Turns an engine failure inside the block into `EngineError`; `what` names
        the engine call for the context."""
        try:
            yield
        except Exception as error:
            if not _is_engine_error(error, self._execute_error):
                raise
            lines = (str(error),)
            if isinstance(error, self._execute_error):
                lines = (*lines, *_lines(self._engine.GetMessages()))
            raise EngineError(
                f"arcpy: {what} failed: {error}",
                context=ErrorContext(tool=what, tool_messages=lines),
            ) from error

    def run_tool(self, name: str, /, **arguments: object) -> object:
        """Runs the tool at the dotted `name`, such as `management.Delete`, with keyword
        arguments, and returns its result object.

        A misspelt name is an `AttributeError` and a misspelt keyword a `TypeError`,
        raised as they are: neither reached the engine.
        """
        tool = _resolve(self._engine, name)
        with self.guard(name):
            result = tool(**arguments)
            lines = _lines(result.getMessages())
        self._log.debug("%s: %s", name, lines)
        return result


def open_session() -> ArcpySession:
    """The session on the real engine, for the composition root."""
    import arcpy

    return ArcpySession(engine=arcpy)


def _is_engine_error(
    error: BaseException, execute_error: type[BaseException], /
) -> bool:
    """Whether `guard` wraps `error`: the vendor class, or an exact `RuntimeError`."""
    return isinstance(error, execute_error) or type(error) is RuntimeError


def _resolve(engine: ModuleType, name: str, /) -> Callable[..., _ToolResult]:
    """The tool at a dotted `name`; `AttributeError` when a part is missing."""
    head, *rest = name.split(".")
    tool: Callable[..., _ToolResult] = getattr(engine, head)
    for part in rest:
        tool = getattr(tool, part)
    return tool


def _apply(engine: ModuleType, environment: Environment, /) -> None:
    """Writes `environment` to the engine's global settings."""
    env = getattr(engine, "env")
    spatial_reference = getattr(engine, "SpatialReference")
    env.overwriteOutput = environment.overwrite_output
    env.outputCoordinateSystem = spatial_reference(environment.output_epsg)
    env.XYTolerance = f"{environment.xy_tolerance_m} Meters"
    env.XYResolution = f"{environment.xy_resolution_m} Meters"


def _lines(text: str, /) -> tuple[str, ...]:
    """The non-blank lines of an engine message string."""
    return tuple(line for line in text.splitlines() if line.strip())
