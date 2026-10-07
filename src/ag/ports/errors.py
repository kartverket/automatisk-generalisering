"""What a caller can see go wrong in a port call.

What: `PortError`, the base of every error a port method raises on purpose, and its
members: the three parents conditions, the wrapped engine failure, and the broken
precondition.

Why: adding a port method adds none of these. Its failure modes are an engine failure, a
caller breaking the docstring, or one of the parents conditions; a new type is justified
only by a new recovery, a caller that would catch it differently from its siblings. An
adapter's own defect is a sibling of this base elsewhere, never a subclass, so code that
handles a port condition can never swallow a bug in the adapter.
"""

from __future__ import annotations

from ag.core.errors import AgError


class PortError(AgError):
    """Base of what a caller can see from a port call."""


class EmptyGeometryError(PortError):
    """A subject row has an empty shape, which the engine would drop or corrupt silently.

    Raised before the tool runs, with the row indices in the context.
    """


class UnmatchedInputError(PortError):
    """An input row that is not degenerate found no place in a minting method's output."""


class ParentsUnavailableError(PortError):
    """The caller asked for a parents table from a method this adapter cannot honour it
    for. Raised rather than returning an empty table."""


class EngineError(PortError):
    """The engine's tool failed. The tool and its messages are in the context; the message
    names the engine."""


class PortContractError(PortError):
    """The caller broke a precondition the method's docstring states."""
