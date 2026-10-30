"""`ArcpyPortBase`, the one class of the ArcPy adapter that holds the session.

Every group class subclasses it, so `self._session` is typed in each, and it is the only
port class in the adapter that holds state: the group classes hold Protocol methods and
no state, and the session holds the engine's.
"""

from __future__ import annotations

from ag.adapters.arcpy.session import ArcpySession


class ArcpyPortBase:
    """Holds the session every port class of the ArcPy adapter shares."""

    def __init__(self, *, session: ArcpySession) -> None:
        self._session = session
