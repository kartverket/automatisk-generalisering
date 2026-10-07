"""The `GeometryOps` Protocol: operations on spatial datasets.

Its methods arrive one at a time as their callers do, with the vocabulary from open
standards rather than from one engine. The selection predicate algebra it takes lives in
`ag.ports.predicates`.
"""

from __future__ import annotations

from typing import Protocol


class GeometryOps(Protocol):
    """Operations on spatial datasets.

    Intentionally empty until its first methods land. A Protocol with no members is
    satisfied by any object, so a toolbox field typed with it gives no structural
    protection yet; nothing may rely on it for that.
    """
