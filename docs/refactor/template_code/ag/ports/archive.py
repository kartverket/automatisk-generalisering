"""TEMPLATE — not shipped. Target module: `src/ag/ports/archive.py`.

Object storage transport. Two methods.

THE SMALLEST PORT, AND IT JUSTIFIES ITSELF ON THE SECOND-IMPLEMENTATION TEST ALONE:
this system writes to Scality on-prem (`s3://`) and GCS in the cloud (`gs://`), so
the second implementation is not foreseeable - it already exists. That is the same
test 02-runtime §10 uses to keep other things off the port list.

NO PATH BUILDING HERE. Every remote path is built in `ag.core.locations`, for the
reason that module gives: fan-out writes partition i's payload where worker i will
look, and worker i writes its output where fan-in will look, so three components
independently compute the same name. A client that also built paths would be a fourth.

TRANSPORT OF ARCHIVED LOGS REUSES THIS. That is why there is no log port (ADR-0006).
"""

from __future__ import annotations

from typing import Protocol

from ag.core.types import Location


class ArchiveClient(Protocol):
    """Object storage transport, one local path at a time.

    LOCAL PATHS ARE `str`, NOT `ScratchHandle`. A handle names a slot in a workspace
    under a join rule that only `staging/` knows; what crosses to object storage is a
    file or a packed directory, which is a path. `staging/transfer.py` is the one
    place the two meet, and it is the only caller of this port.
    """

    def upload(self, *, local_path: str, location: Location) -> None: ...

    def download(self, *, location: Location, local_path: str) -> None: ...
