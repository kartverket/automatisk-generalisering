"""The generic port facade: one wrapper over any handle-bearing port, no lineage logic yet.

What: `wrap(protocol, port)` returns an object typed as the port that forwards every
Protocol method to `port`, calling a `before` hook with a `PortCall` and an `after` hook
with the call and its result. `PortCall` records the Protocol, the method name, the row
shape the Protocol declares for the method, and the keyword arguments of the call.

How: `PortFacade.__getattr__` resolves a name on every attribute access and caches no
forwarder; the Protocol's member set is read once, at construction. A name that is not a
member raises `AttributeError`, so the facade exposes the Protocol surface and nothing
else, and no public name reaches the inner port. The row shape is read from the Protocol
class, never from the port, so an adapter carries no declaration and cannot drift from
the contract (ADR-0017 RS-D10); a method with no declaration, a query, records an empty
mapping. The forwarder takes keyword arguments only, so `PortCall.kwargs` is the whole
call, which holds because port parameters are keyword-only (ADR-0019 PC-D4); a
positional call fails at the facade before the port is reached. An exception from the
port propagates and `after` is not called; whether the lineage layer needs to see a
failed call is decided with it.

Why: one generic facade rather than a delegating wrapper per method (ADR-0017 RS-R4),
at the cost of one `cast`, in `wrap`, where the wrapper is handed out as the port type.
The composition root calls `wrap` per port and holds no cast of its own. The hooks are a
test seam for this first version: how the facade obtains its lineage session and call
identity, and how it supplies its own parents table on a minting call, is decided with
the lineage logic, and nothing is to be built on the hook signature.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TypeAlias, TypeVar, cast, get_protocol_members

from ag.ports.row_shape import Rows

P = TypeVar("P")


@dataclass(frozen=True)
class PortCall:
    """One call through the facade, as the hooks see it.

    `rows` is the method's `__row_shape__` as the Protocol declares it, empty for a query.
    `kwargs` is every argument of the call, since the forwarder admits no positional one.
    """

    protocol: type
    method: str
    rows: Mapping[str, Rows]
    kwargs: Mapping[str, object]


Before: TypeAlias = Callable[[PortCall], None]
"""Called with the `PortCall` before the port method runs."""

After: TypeAlias = Callable[[PortCall, object], None]
"""Called with the `PortCall` and the port method's result after it returns."""

_NO_ROWS: Mapping[str, Rows] = MappingProxyType({})


def _no_before(call: PortCall) -> None:
    """The default `before` hook: does nothing."""


def _no_after(call: PortCall, result: object) -> None:
    """The default `after` hook: does nothing."""


class PortFacade:
    """Forwards the members of one Protocol to one port, through the hooks.

    Built by `wrap`, which is where it is handed out as the port type. Only the Protocol's
    members resolve to a forwarder, and the facade adds no public name. Its state is
    private, and the lint rule on private member access keeps domain code from reaching
    through it to the port.
    """

    def __init__(
        self, *, protocol: type, port: object, before: Before, after: After
    ) -> None:
        self._protocol = protocol
        self._members = get_protocol_members(protocol)
        self._port = port
        self._before = before
        self._after = after

    def __getattr__(self, name: str) -> Callable[..., object]:
        if name.startswith("_"):
            # A dunder probe (copy, pickle, inspection) wants a plain miss, raised before
            # any state is read: a copy in the making has none yet.
            raise AttributeError(name)
        if name not in self._members:
            raise AttributeError(
                f"{self._protocol.__name__} has no member {name!r}; the facade exposes "
                "the Protocol surface and nothing else."
            )
        declaration = getattr(self._protocol, name)
        rows: Mapping[str, Rows] = getattr(declaration, "__row_shape__", _NO_ROWS)
        target: Callable[..., object] = getattr(self._port, name)

        def forward(*args: object, **kwargs: object) -> object:
            if args:
                raise TypeError(
                    f"{self._protocol.__name__}.{name} takes keyword arguments only; "
                    f"{len(args)} positional argument(s) were given."
                )
            call = PortCall(
                protocol=self._protocol,
                method=name,
                rows=rows,
                kwargs=MappingProxyType(dict(kwargs)),
            )
            self._before(call)
            result = target(**kwargs)
            self._after(call, result)
            return result

        return forward


def wrap(
    protocol: type[P],
    port: P,
    *,
    before: Before = _no_before,
    after: After = _no_after,
) -> P:
    """A facade over `port`, typed as `protocol`. The one `cast` in the package.

    `protocol` must be a Protocol class; a non-Protocol fails at construction.
    """
    return cast(P, PortFacade(protocol=protocol, port=port, before=before, after=after))
