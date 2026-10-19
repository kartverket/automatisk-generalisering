"""Column names the ports own.

What: the two columns of a parents table, the relation a `MINT` method writes to its
`ParentsOut` parameter when a caller asks for one.

Why: the names are the port's, not an engine's, so every adapter writes the same table
and the layer above reads it without knowing which engine produced it. Both columns hold
the port's native indices at the port; the layer above maps them to ids. ADR-0017 RS-6.
"""

from __future__ import annotations

from ag.ports.attributes import FieldName

PARENT_ID: FieldName = "parent_id"
"""The native index of a subject row that contributed to the child."""

CHILD_ID: FieldName = "child_id"
"""The native index of the output row the parent contributed to."""
