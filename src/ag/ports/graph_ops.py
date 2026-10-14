"""The `GraphOps` Protocol: graph algorithms over topology, in pure-value form.

Its methods arrive as the operations that call them migrate.
"""

from __future__ import annotations

from typing import Protocol


class GraphOps(Protocol):
    """Graph algorithms over a topology handed in as values.

    Intentionally empty until its first methods land. A Protocol with no members is
    satisfied by any object, so a toolbox field typed with it gives no structural
    protection yet; nothing may rely on it for that.
    """
