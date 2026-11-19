"""`WorkspaceFormat`: how a workspace holds its named layers, as a port signature names it.

What: the closed set of formats `TableOps.create_workspace` takes, one member per format
some adapter creates, and `suffix`, the one spelling of the file suffix a member's path
ends in.

Why: it lives under `ports/` because a port signature names it; the join rule, name
legality and the name budget of a workspace path stay with the scratch manager, which
chooses every path and asks the port to create what it named. A member is a format some
adapter creates: the conformance cases run over every member, so a member no adapter
creates fails everywhere until each adapter creates or refuses it. ADR-0019 PC-D32,
PC-R8.
"""

from __future__ import annotations

from enum import Enum


class WorkspaceFormat(Enum):
    """How named layers are held; the value is the suffix the path ends in."""

    FILE_GDB = "gdb"
    """A file geodatabase: a directory the engine owns, holding feature classes and
    tables."""

    @property
    def suffix(self) -> str:
        """The suffix a workspace path of this format ends in, with its dot."""
        return f".{self.value}"
