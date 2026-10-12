"""The `CartographicOps` Protocol: the named generalisation operators.

The one port that may import the other port modules. Its methods arrive as the operations
that call them migrate.
"""

from __future__ import annotations

from typing import Protocol


class CartographicOps(Protocol):
    """The named generalisation operators.

    Intentionally empty until its first methods land. A Protocol with no members is
    satisfied by any object, so a toolbox field typed with it gives no structural
    protection yet; nothing may rely on it for that.
    """
