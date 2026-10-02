"""TEMPLATE — not shipped. Target module: `src/ag/ports/toolbox.py`.

The bundle of ports an operation is handed. ADR-0008.

One context object resolved once by the pod entry point and passed explicitly, rather
than three or four port parameters at 100+ call sites. Explicit rather than ambient,
because 02-runtime §2.4 already passes `ScratchScope` as a parameter and two
dependency-passing styles in one signature is worse than either used consistently.

CONSTRUCTED PER POD, BY runtime/. The entry point chooses the adapters and assembles
one Toolbox for the whole stage; nothing below `runtime/` ever constructs one, and no
operation can reach an adapter to swap it.

That is what makes a future per-stage backend override cheap: it is a field on `Stage`
and a branch in the entry point, and not one operation signature or one operation body
changes. Deliberately NOT a field today - there is one backend, and the extension point
costs nothing to leave unbuilt.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from ag.core.injection import Injected
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.geometry_ops import GeometryOps
from ag.ports.graph_ops import GraphOps
from ag.ports.table_ops import TableOps


@dataclass(frozen=True)
class Toolbox(Injected):
    """The four processing ports, as one parameter.

    NAMESPACED ACCESS, `tb.geometry.buffer(...)` AND NOT `tb.buffer(...)`. Flattening
    four ports onto one object is 50+ methods with real collisions - `count`, `delete`
    and `exists` each mean something different depending on which port they came from -
    and either breaks structural typing or means a hand-written forwarder per method,
    which is the restated-signature disease ADR-0011 exists to remove. The namespace
    also tells a reader which contract a call belongs to, which is the thing they need
    when asking what a second adapter would have to implement.

    FOUR FIELDS, NOT SIX. `ArchiveClient` and `ClusterClient` are not here. An
    operation moves data between handles; it does not transport bytes to object storage
    and it does not create Jobs. Those two are `staging/` and `orchestrator/` concerns
    and are passed to those directly. If they were here, an operation could reach them,
    and "an operation never sees a client" would stop being enforced by anything.

    INHERITS `Injected` so `@operation` admits `tb: Toolbox` as a parameter kind
    without `core/` ever importing this module - which it may not, and which would be
    a cycle if it could. ADR-0014.
    """

    geometry: GeometryOps
    table: TableOps
    cartographic: CartographicOps
    graph: GraphOps


class _NotInjected:
    """Stands in for a Toolbox that the runtime never supplied.

    `__getattr__` rather than four stub ports, so the failure names the port that was
    reached and no port has to be faked. A real object rather than None, for the same
    reason `core.operations.INJECTED` is one: the type is honest and a missed
    injection fails with a sentence rather than as `NoneType has no attribute`.
    """

    def __getattr__(self, name: str) -> object:
        raise RuntimeError(
            f"tb.{name} was reached on a Toolbox that was never injected. The stage "
            "entry point must pass its assembled Toolbox to any operation whose "
            "signature declares `tb: Toolbox = NOT_INJECTED`."
        )


NOT_INJECTED: Toolbox = cast("Toolbox", _NotInjected())
"""The default for an operation's `tb` parameter.

ONE `cast`, AND IT IS LOAD-BEARING RATHER THAN COSMETIC. `@operation` returns
`Callable[P, OperationCall]`, where P is the declared signature - so a parameter with
no default makes every declaration site a type error for omitting an argument the
declaration site must not supply. The sentinel is what lets the runtime signature
require a Toolbox while the declaration signature does not.

`Toolbox | None = None` does not work in its place: it does not remove the need for a
default, and it makes `tb.geometry` an optional-member-access error in every operation
body. ADR-0014.
"""
