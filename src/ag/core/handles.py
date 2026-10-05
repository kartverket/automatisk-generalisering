"""Scratch handles, the direction markers on handle parameters, and the scratch scope.

What: `ScratchHandle` names a slot in the pod's workspace; `handle()` declares one as a
class attribute; `In`, `Out`, `Mutates` and `ParentsOut` say what a parameter does with
the handle it receives; `ScratchScope` hands an operation its internal scratch.

How: a declared handle is named by `__set_name__` from the class attribute it is bound to,
once, when the class is created, and refuses to be renamed. An internal handle is built by
the scope that creates it: its namespace is the scope's and its name is the trail and leaf,
so identity is decided here and never by the scratch manager, which supplies the path. The
four markers are `Annotated` aliases over `ScratchHandle` carrying a `Direction`;
`@operation` and the port checks read the metadata back with `typing.get_args`.

Why: ports and adapters import this module and nothing else in `core` except types,
injection and errors, which keeps "a port sees handles only" an import contract rather than
a convention. The markers stay `TypeAlias` statements: a PEP 695 `type` statement wraps
the alias in a `TypeAliasType`, which hides the `Annotated` metadata from `get_origin`, and
nothing would classify. A unit test pins that. ADR-0003, ADR-0011, ADR-0014.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Annotated, TypeAlias

from ag.core.errors import InjectionError
from ag.core.injection import Injected
from ag.core.types import DataType

TRAIL_SEPARATOR = "/"
"""Joins trail and leaf into an internal handle's name. Not a legal layer-name character,
so an internal handle's name is never mistaken for the layer the scratch manager renders."""

_SEGMENT = re.compile(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*")
"""A scope label, tag or leaf: letters, digits and single underscores, so it renders into
a layer name as it is, never contains the trail separator, and never collides with the
separator the renderer uses."""


@dataclass(frozen=True)
class ScratchHandle:
    """A named slot in the pod's ephemeral workspace.

    What: one object in two states. At declaration `path` is None: a name used to wire
    operations together, constructed at import with no filesystem and no engine. At
    runtime the scratch manager returns a copy with `path` filled in, and that copy is
    what an operation receives.

    Why: frozen in both states, so a run can never corrupt a declaration. Equality is
    (name, data_type, namespace) with `path` excluded, so a materialised copy equals the
    declaration it came from and the stage entry point can look one up by the other.
    `namespace` is in the comparison so that two stages' `final` handles are different
    values; without it every structure keyed by handle conflates them. ADR-0011.
    """

    name: str = ""
    data_type: DataType = DataType.FEATURE_CLASS
    namespace: str = ""
    path: str | None = field(default=None, compare=False)

    def __set_name__(self, owner: type, name: str) -> None:
        """Stamps name and namespace from the class attribute this handle is bound to.

        How: `type.__new__` calls this once for every object in a class body, while the
        class is being created and before anything can hash the handle, so a handle
        class needs no base. The namespace is the owner's module and qualified name, so
        two `Network` classes in different stage modules get different handles.

        Why: a handle that is already named refuses. One object bound in two class bodies
        would otherwise end with the second namespace in both places, and the first class
        would be wiring a handle that is not its own.
        """
        if self.name or self.namespace:
            raise TypeError(
                f"{owner.__module__}.{owner.__qualname__}.{name} is bound to a handle "
                f"that is already named {self!r}. Each class attribute needs its own "
                "handle(); one object cannot be two handles."
            )
        object.__setattr__(self, "name", name)
        object.__setattr__(
            self, "namespace", f"{owner.__module__}.{owner.__qualname__}"
        )

    def materialize(self, path: str) -> ScratchHandle:
        """Returns the runtime copy with `path` set. Called by the scratch manager only."""
        return replace(self, path=path)

    def __fspath__(self) -> str:
        """Lets an operation pass the handle straight to an engine as a path."""
        if self.path is None:
            raise InjectionError(
                f"{self!r} was never materialised: this is a declaration, not a file. "
                "The stage entry point materialises every handle before calling any "
                "operation."
            )
        return self.path

    def __repr__(self) -> str:
        where = f", path={self.path!r}" if self.path is not None else ""
        if self.namespace:
            return f"ScratchHandle({self.namespace}.{self.name}{where})"
        return f"ScratchHandle({self.name!r}, UNDECLARED{where})"


def handle(data_type: DataType = DataType.FEATURE_CLASS) -> ScratchHandle:
    """Declares a handle whose name and namespace come from its class attribute.

    Only meaningful inside a class body. Outside one `__set_name__` never fires, the
    handle stays unnamed, and `@operation` rejects it at the first declaration site.
    """
    return ScratchHandle(data_type=data_type)


class Handles:
    """An optional marker base for a stage's handle class. Readability only.

    Why: naming is done by `ScratchHandle.__set_name__`, which fires in any class body,
    so nothing depends on this base. Two handles in one class body cannot share a name,
    and two stages may each have a `ranked` because `namespace` keeps them distinct.
    Subclassing documents intent and gives a reader something to grep for.
    """


class Direction(Enum):
    """What a parameter does with the handle it receives.

    `IN` and `OUT` are the operation vocabulary: the stage wiring and the dependency graph
    are derived from them. `MUTATES` and `PARENTS_OUT` are port vocabulary only: a port
    method that changes its input in place, and the optional table of parent rows a
    minting method writes when asked. An operation signature may carry neither.

    Why: direction lives in the annotation so the signature states it (`output: Out`)
    rather than a naming convention, while the type checker still sees a plain
    `ScratchHandle` at every call site.
    """

    IN = "in"
    OUT = "out"
    MUTATES = "mutates"
    PARENTS_OUT = "parents_out"


In: TypeAlias = Annotated[ScratchHandle, Direction.IN]
"""A handle the function reads."""

Out: TypeAlias = Annotated[ScratchHandle, Direction.OUT]
"""A handle the function writes, creating the dataset."""

Mutates: TypeAlias = Annotated[ScratchHandle, Direction.MUTATES]
"""A handle a port method changes in place. Port methods only."""

ParentsOut: TypeAlias = Annotated[ScratchHandle | None, Direction.PARENTS_OUT]
"""The parents table a minting port method writes when a caller asks for one, else None.
Port methods only."""


MaterializeFn: TypeAlias = Callable[[tuple[str, ...], str, DataType], str]
"""(trail, leaf name, data type) to the path of a new internal scratch dataset.

Supplied by the scratch manager, which owns workspaces, layer names and name budgets and
renders the trail into a layer name its own way. It returns the path only: the handle's
name and namespace are the scope's to decide, so identity never depends on how a manager
renders a name. It must raise on a repeated (trail, leaf) within one operation rather than
return a second path, because the two handles would be equal and name different files.
"""


@dataclass(kw_only=True, eq=False)
class ScratchScope(Injected):
    """A trail-bound factory for internal scratch. What an operation is handed.

    What: `scratch("dissolved")` creates one internal scratch handle at this point in the
    trail; `scratch.child("build_topology")` descends one level for a helper, which then
    receives a scope exactly as an operation does and never learns its own trail.

    How: a handle a scope creates is named by its trail and leaf and stamped with the
    scope's `namespace`, which the stage entry point sets to the identity of the call it
    binds the scope to. Leaf names stay literals: nothing else in the program reads them,
    and whether a rendered layer name collides with another in the workspace is the
    scratch manager's to catch.

    Why: the namespace is what keeps `scratch("x")` from two operations two different
    values, and the trail in the name is what keeps `scratch("x")` and
    `scratch.child("h")("x")` apart; the id-map cache and the facade key on handle
    equality and would otherwise conflate them. Identity equality (`eq=False`) because a
    scope is a live allocator bound to one call, not a value, and it counts the labels it
    has issued. Inherits `Injected` so `@operation` recognises it with no name
    convention. ADR-0014.
    """

    namespace: str
    trail: tuple[str, ...]
    materialize: MaterializeFn
    _issued: set[str] = field(default_factory=set[str], repr=False)

    def __call__(
        self, name: str, data_type: DataType = DataType.FEATURE_CLASS
    ) -> ScratchHandle:
        """Creates one internal scratch handle at this point in the trail.

        The leaf is validated like a label: a separator inside it would make
        `scratch("a/b")` equal to `scratch.child("a")("b")`.
        """
        _check_segment(text=name, what="leaf")
        path = self.materialize(self.trail, name, data_type)
        return ScratchHandle(
            name=TRAIL_SEPARATOR.join((*self.trail, name)),
            data_type=data_type,
            namespace=self.namespace,
            path=path,
        )

    def child(self, label: str, tag: str | None = None) -> ScratchScope:
        """Descends one level, giving a repeated label the first unused index.

        How: the segment is the label, or the label and tag joined by an underscore. A
        segment already issued in this scope takes the lowest suffix `_2`, `_3`, ... not
        yet issued, so `child("a")`, `child("a")` and `child("a", tag="2")` are three
        segments. The first occurrence is unnumbered, so adding a second call later does
        not rename the first.

        Why: the same helper is legitimately called more than once in one scope, and the
        index is deterministic because call order does not vary between runs. Erroring
        would fail a long run over something the system resolves correctly.
        """
        if self.materialize is _unbound:
            raise InjectionError(
                f"scratch.child({label!r}) was called on a scope the runtime never "
                "bound. The stage entry point must hand its own scope to any operation "
                "whose signature declares `scratch: ScratchScope = INJECTED`."
            )
        _check_segment(text=label, what="label")
        if tag is not None:
            _check_segment(text=tag, what="tag")
        key = f"{label}_{tag}" if tag else label
        segment = key
        count = 1
        while segment in self._issued:
            count += 1
            segment = f"{key}_{count}"
        self._issued.add(segment)
        return ScratchScope(
            namespace=self.namespace,
            trail=self.trail + (segment,),
            materialize=self.materialize,
        )


def _check_segment(*, text: str, what: str) -> None:
    """Rejects a label, tag or leaf that cannot be one part of a layer name."""
    if _SEGMENT.fullmatch(text) is None:
        raise ValueError(
            f"scope {what} {text!r} must be letters, digits and single underscores; "
            "it becomes part of a layer name."
        )


def _unbound(trail: tuple[str, ...], leaf: str, data_type: DataType) -> str:
    """The materialiser of `INJECTED`: any call means the runtime never bound a scope."""
    raise InjectionError(
        f"scratch({leaf!r}) was called on a scope the runtime never bound. The stage "
        "entry point must hand its own scope to any operation whose signature declares "
        "`scratch: ScratchScope = INJECTED`."
    )


INJECTED = ScratchScope(namespace="", trail=(), materialize=_unbound)
"""The default for an operation's `scratch` parameter.

Why a sentinel and not a missing default: `@operation` keeps the declared parameter list,
so a parameter with no default would make every declaration site a type error for omitting
an argument it must not supply. The sentinel lets the runtime signature require a scope
while the declaration signature does not; the entry point replaces it, and passing it at a
declaration site is rejected. A real scope rather than None, so the type is honest and a
missed injection fails with a sentence at the first `scratch(...)` call. ADR-0014.
"""
