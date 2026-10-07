"""The bundle of ports an operation is handed.

What: `Toolbox`, the four processing ports as one frozen value, and `NOT_INJECTED`, the
default an operation signature gives its toolbox parameter.

Why: one object resolved once by the pod entry point and passed explicitly, rather than
three or four port parameters at every call site, and explicit rather than ambient because
the scratch scope is already a parameter and two dependency-passing styles in one
signature is worse than either. Namespaced access, `tb.geometry.select(...)`, because
flattening four ports onto one object is dozens of methods with real name collisions, and
because the namespace tells a reader which contract a call belongs to. Four fields, not six:
the archive and cluster clients are not here, so an operation cannot reach them and "an
operation never sees a client" stays enforced by something. Constructed per pod by the
runtime; nothing below it constructs one, and no operation can reach an adapter to swap it.
ADR-0008, ADR-0014.
"""

from __future__ import annotations

from dataclasses import dataclass

from ag.core.errors import InjectionError
from ag.core.injection import Injected
from ag.ports.cartographic_ops import CartographicOps
from ag.ports.geometry_ops import GeometryOps
from ag.ports.graph_ops import GraphOps
from ag.ports.table_ops import TableOps


@dataclass(frozen=True)
class Toolbox(Injected):
    """The four processing ports, as one parameter.

    Inherits `Injected` so `@operation` admits `tb: Toolbox` as a parameter kind without
    `core` ever importing this module, which it may not. ADR-0014.
    """

    geometry: GeometryOps
    table: TableOps
    cartographic: CartographicOps
    graph: GraphOps


class _NotInjected(Toolbox):
    """Stands in for a toolbox the runtime never supplied.

    How: a `Toolbox` subclass whose constructor sets no field, so reaching any port falls
    through to `__getattr__` and fails with a sentence naming the port. A subclass rather
    than a cast, so that it is an instance of the kind it stands in for, which is what
    `@operation` requires of a sentinel default.

    Why a sentinel and not a missing default: `@operation` keeps the declared parameter
    list, so a parameter with no default would make every declaration site a type error
    for omitting an argument it must not supply. `Toolbox | None` does not serve: it keeps
    the need for a default and makes every `tb.geometry` an optional-member access.
    """

    def __init__(self) -> None:
        pass

    def __getattr__(self, name: str) -> object:
        raise InjectionError(
            f"tb.{name} was reached on a toolbox that was never injected. The stage entry "
            "point must pass its assembled Toolbox to any operation whose signature "
            "declares `tb: Toolbox = NOT_INJECTED`."
        )

    def __repr__(self) -> str:
        return "NOT_INJECTED"

    def __hash__(self) -> int:
        return id(self)


NOT_INJECTED: Toolbox = _NotInjected()
"""The default for an operation's `tb` parameter; the entry point replaces it."""
