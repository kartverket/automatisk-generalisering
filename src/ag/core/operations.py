"""The `@operation` decorator and the declaration it produces.

What: `@operation` turns an operation function into its own declaration factory. Calling
the decorated function at a declaration site binds handles to it and returns an
`OperationCall`, which the stage entry point later dispatches. The function's signature is
the declaration, read once at decoration.

How: parameters are classified from their resolved annotations: `In` and `Out` handles,
one frozen `config` dataclass, and runtime-injected kinds recognised by subclassing
`Injected`. Everything that can fail is rejected while the module is being imported: an
unannotated or positional parameter, a loose tuning value, a port-only marker, a default on
a handle or config, an injected kind without its sentinel, two parameters of one injected
kind; and, at a declaration site, a misspelled keyword, an undeclared handle, a config of
the wrong type or one that cannot be hashed, or an injected argument passed by hand.

Why: an operation sees handles, one config and the ports the runtime injects, and learns
nothing about where or on what it runs; that ignorance is what lets one function serve
every scale and run under any adapter. Reading the declaration off the signature means no
identifier is written twice, so a renamed parameter is a type error at every declaration
site rather than a pod-time failure. ADR-0011, ADR-0014.
"""

from __future__ import annotations

import inspect
import types
from collections.abc import Callable, Mapping
from dataclasses import dataclass, is_dataclass
from types import MappingProxyType
from typing import (
    Annotated,
    TypeAlias,
    TypeGuard,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from ag.core.handles import Direction, ScratchHandle, ScratchScope
from ag.core.injection import Injected
from ag.core.types import OperationName, ParamName

CONFIG_PARAM = "config"
"""The one non-IO parameter an operation may take.

Why: classified by name, unlike the injected parameters, because a config's type differs
per operation and the name is the only handle available. The injected kinds are each one
type, so they are matched on it. ADR-0014.
"""

OperationFn: TypeAlias = Callable[..., None]
"""The runtime callable: keyword-only, `In` or `Out` for every IO argument, at most one
`config`, and whatever the runtime injects with its sentinel default.

Annotations must resolve at import. `@operation` resolves them with `get_type_hints`
against the operation module's globals, so a signature may not use a type imported under
`if TYPE_CHECKING` or defined inside a function.
"""

_PORT_ONLY = frozenset({Direction.MUTATES, Direction.PARENTS_OUT})
_EMPTY = inspect.Parameter.empty


@dataclass(frozen=True, eq=False)
class OperationCall:
    """One operation, wired to scratch handles.

    What: `inputs` and `outputs` are keyed by parameter name, so the entry point
    dispatches with no positional convention. `parameters` is `{"config": <frozen
    dataclass>}` or empty, so a run manifest can serialise it uniformly. `injected` says
    which runtime-supplied kinds `fn` wants and what it calls each. All four are
    read-only views.

    Why: nobody constructs this by hand; `@operation` builds it from the signature, so
    the keys cannot drift from the parameters they name. Identity equality: two calls of
    one operation over the same handles are two calls, not one value. No input role and
    no halo here: both are stage concerns, and an operation must behave identically either
    way. `injected` is keyed by type and carries the name so that `core` never names the
    toolbox, adding a kind changes nothing here, and the parameter name stops being
    load-bearing. ADR-0014.
    """

    operation: OperationName
    qualified_name: str
    fn: OperationFn
    inputs: Mapping[ParamName, ScratchHandle]
    outputs: Mapping[ParamName, ScratchHandle]
    parameters: Mapping[ParamName, object]
    injected: Mapping[type[Injected], ParamName]

    @property
    def wants_scratch(self) -> bool:
        """Whether `fn` takes a scratch scope. No toolbox twin: `core` cannot name it."""
        return ScratchScope in self.injected

    def reads(self) -> tuple[ScratchHandle, ...]:
        return tuple(self.inputs.values())

    def writes(self) -> tuple[ScratchHandle, ...]:
        return tuple(self.outputs.values())

    def handles(self) -> tuple[ScratchHandle, ...]:
        return self.reads() + self.writes()


@dataclass(frozen=True, slots=True, kw_only=True)
class _Shape:
    """What `_classify` reads off one signature."""

    directions: Mapping[ParamName, Direction]
    injected: Mapping[type[Injected], ParamName]
    config_type: type | None


class OperationDeclaration[**P]:
    """What `@operation` returns: the function, its classified shape, and the factory.

    What: calling it with the declared keywords binds handles and a config to the
    operation and returns an `OperationCall`. Its parameter list is the function's, so a
    declaration site is type-checked against the real signature, and go-to-definition
    lands on the implementation. `name` is the function's name and the stem of its
    workspace; `qualified_name` is module and function, for logs and error context.

    Why: a class rather than a closure wrapped with `functools.update_wrapper`, so the
    shape read at decoration (`fn`, `directions`, `injected`, `config_type`) is typed
    and reachable, where `__wrapped__` is not visible to the type checker.
    """

    def __init__(self, *, fn: Callable[P, None]) -> None:
        self.fn = fn
        self.name: OperationName = fn.__name__
        self.qualified_name = f"{fn.__module__}.{fn.__qualname__}"
        self.signature = inspect.signature(fn)
        shape = _classify(fn=fn, signature=self.signature)
        self.directions: Mapping[ParamName, Direction] = MappingProxyType(
            dict(shape.directions)
        )
        self.injected: Mapping[type[Injected], ParamName] = MappingProxyType(
            dict(shape.injected)
        )
        self.config_type = shape.config_type

    def __call__(self, *args: P.args, **kwargs: P.kwargs) -> OperationCall:
        """Binds one declaration site's arguments and returns the call record."""
        try:
            bound = self.signature.bind(*args, **kwargs)
        except TypeError as error:
            raise TypeError(f"{self.name}: {error}") from None
        for param in self.injected.values():
            if param in bound.arguments:
                raise TypeError(
                    f"{self.name}: {param!r} must not be passed at a declaration site; "
                    "the stage entry point injects it. A declaration is evaluated at "
                    "import, where there is no workspace to allocate in and no adapter "
                    "chosen."
                )
        inputs: dict[ParamName, ScratchHandle] = {}
        outputs: dict[ParamName, ScratchHandle] = {}
        parameters: dict[ParamName, object] = {}
        for param, value in bound.arguments.items():
            direction = self.directions.get(param)
            if direction is Direction.IN:
                inputs[param] = _expect_declared(
                    operation=self.name, param=param, value=value
                )
            elif direction is Direction.OUT:
                outputs[param] = _expect_declared(
                    operation=self.name, param=param, value=value
                )
            elif param == CONFIG_PARAM and self.config_type is not None:
                parameters[param] = _expect_config(
                    operation=self.name, value=value, config_type=self.config_type
                )
        return OperationCall(
            operation=self.name,
            qualified_name=self.qualified_name,
            fn=self.fn,
            inputs=MappingProxyType(inputs),
            outputs=MappingProxyType(outputs),
            parameters=MappingProxyType(parameters),
            injected=self.injected,
        )


def operation[**P](fn: Callable[P, None]) -> OperationDeclaration[P]:
    """Turns an operation function into its own declaration factory.

    What it rejects at import: a parameter with no annotation, or one that is not `In`,
    `Out`, `config` or a subclass of `Injected`; the bare `Injected` base, or a union
    containing an injected kind; an injected parameter without a default that is an
    instance of its kind; two parameters of one injected kind; a `Mutates` or `ParentsOut`
    marker, which belong to port methods; a default on a handle or on `config`; a `config`
    whose annotation is not a frozen dataclass type compared by value; a positional
    parameter. At a declaration site: a misspelled or missing keyword, an undeclared
    handle, a config that is not an instance of the declared type or cannot be hashed,
    and any injected argument.

    Why: all of it fires while the pipeline module is being imported, which is CI or
    orchestrator startup, rather than in a pod three hours in. ADR-0011.
    """
    return OperationDeclaration(fn=fn)


def _classify(*, fn: Callable[..., object], signature: inspect.Signature) -> _Shape:
    """Reads the shape of an operation off its annotations, once, at decoration.

    How: `get_type_hints(..., include_extras=True)` resolves each annotation against the
    operation module's namespace, which imports the toolbox normally, so this function
    receives resolved objects and asks `issubclass(hint, Injected)`; without
    `include_extras` the `Annotated` metadata would be stripped and no handle would
    classify. The `isinstance(hint, type)` guard is load-bearing: `In` and `Out` resolve
    to `Annotated[...]`, which is not a type, and `issubclass` raises on it. ADR-0014.
    """
    name = fn.__name__
    hints = get_type_hints(fn, include_extras=True)
    directions: dict[ParamName, Direction] = {}
    injected: dict[type[Injected], ParamName] = {}
    config_type: type | None = None

    for param, parameter in signature.parameters.items():
        if parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
            raise TypeError(
                f"{name}: parameter {param!r} is not keyword-only. Operations take "
                "keyword arguments only, so that every argument at a declaration site "
                "names the parameter it binds to."
            )
        hint: object = hints.get(param)
        if hint is None:
            raise TypeError(
                f"{name}: parameter {param!r} has no annotation. @operation reads "
                "direction and kind from the annotations; an unannotated parameter "
                "cannot be classified."
            )
        if hint is Injected:
            raise TypeError(
                f"{name}: parameter {param!r} is annotated with the bare Injected base. "
                "Annotate the concrete kind the runtime supplies, with its sentinel as "
                "the default."
            )
        direction = _direction_of(hint=hint)
        union_kind = _injected_kind_in_union(hint=hint)
        kind = _injected_kind(hint=hint)
        if kind is not None:
            if kind in injected:
                raise TypeError(
                    f"{name}: parameters {injected[kind]!r} and {param!r} are both "
                    f"{kind.__name__}. The entry point supplies one of each kind, so a "
                    "second would silently receive the same object."
                )
            if not isinstance(parameter.default, kind):
                raise TypeError(
                    f"{name}: parameter {param!r} is {kind.__name__}, which the runtime "
                    "injects, so it needs that kind's sentinel as its default; without "
                    "one every declaration site is a type error for omitting an "
                    "argument it must not supply."
                )
            injected[kind] = param
        elif union_kind is not None:
            raise TypeError(
                f"{name}: parameter {param!r} is annotated {hint!r}, a union containing "
                f"the injected kind {union_kind}. An injected parameter is annotated with its "
                "kind alone; the runtime always supplies it, so it is never optional."
            )
        elif direction in _PORT_ONLY:
            raise TypeError(
                f"{name}: parameter {param!r} is annotated with the port-only marker "
                f"{_marker_name(direction)}. An operation declares In and Out only; "
                "whether a method changes its input in place or can write a parents "
                "table is a fact about a port method, read by the lineage layer, not "
                "about an operation."
            )
        elif direction is not None:
            if parameter.default is not _EMPTY:
                raise TypeError(
                    f"{name}: parameter {param!r} has a default. A handle is bound at "
                    "the declaration site, and a defaulted one would never reach the "
                    "dependency graph."
                )
            directions[param] = direction
        elif param == CONFIG_PARAM:
            if parameter.default is not _EMPTY:
                raise TypeError(
                    f"{name}: {CONFIG_PARAM} has a default. A config is bound at the "
                    "declaration site, and a defaulted one would never reach the run "
                    "manifest."
                )
            if not _is_frozen_dataclass_type(hint):
                raise TypeError(
                    f"{name}: {CONFIG_PARAM} is annotated {hint!r}, which is not a "
                    "frozen dataclass type with equality. A frozen dataclass compared "
                    "by value is what makes the tuning record serialisable, hashable by "
                    "its fields and safe to share between declaration sites and pods."
                )
            config_type = hint
        else:
            raise TypeError(
                f"{name}: parameter {param!r} is annotated {hint!r}, which is not a "
                f"recognised kind. An operation takes In and Out handles, one frozen "
                f"{CONFIG_PARAM} dataclass, and whatever the runtime injects. Tuning "
                f"values go in the {CONFIG_PARAM} rather than as loose parameters, so a "
                "run manifest can record what tuning produced an output without "
                "special-casing each operation."
            )
    return _Shape(directions=directions, injected=injected, config_type=config_type)


def _direction_of(*, hint: object) -> Direction | None:
    """The `Direction` carried in an `Annotated` hint, or None for any other hint."""
    if get_origin(hint) is not Annotated:
        return None
    for meta in get_args(hint)[1:]:
        if isinstance(meta, Direction):
            return meta
    return None


def _injected_kind(*, hint: object) -> type[Injected] | None:
    """The hint itself when it is a subclass of `Injected`, else None.

    The `isinstance` guard is load-bearing: `In` and `Out` resolve to `Annotated[...]`,
    which is not a type, and `issubclass` raises on it.
    """
    if isinstance(hint, type) and issubclass(hint, Injected):
        return hint
    return None


def _injected_kind_in_union(*, hint: object) -> str | None:
    """The name of an `Injected` subclass inside a union hint, or None."""
    if get_origin(hint) not in (Union, types.UnionType):
        return None
    for member in get_args(hint):
        if isinstance(member, type) and issubclass(member, Injected):
            return member.__name__
    return None


def _is_frozen_dataclass_type(hint: object) -> TypeGuard[type]:
    """Whether `hint` is a class decorated `@dataclass(frozen=True)` with `eq` on.

    Both flags matter: with `eq=False` a frozen dataclass hashes by identity, so a list
    field would pass the hashability check at the declaration site.
    """
    if not isinstance(hint, type) or not is_dataclass(hint):
        return False
    # `__dataclass_params__` is undocumented and unknown to the type checker, so it is
    # read by name rather than as an attribute the checker would have to be told about.
    params = getattr(hint, "__dataclass_params__")
    frozen: bool = params.frozen
    eq: bool = params.eq
    return frozen and eq


def _marker_name(direction: Direction) -> str:
    """The alias a port signature spells a port-only direction with."""
    return "Mutates" if direction is Direction.MUTATES else "ParentsOut"


def _expect_declared(
    *, operation: str, param: ParamName, value: object
) -> ScratchHandle:
    """Checks that an `In` or `Out` argument is a handle declared in a class body."""
    if not isinstance(value, ScratchHandle):
        raise TypeError(
            f"{operation}: {param!r} is declared In or Out, so it must be a "
            f"ScratchHandle; got {type(value).__name__}. A DataObject belongs on a "
            "StageInput or StageOutput, never in an operation call."
        )
    if not value.namespace:
        raise TypeError(
            f"{operation}: {param!r} received an undeclared handle. handle() is only "
            "legal as a class attribute; outside a class body __set_name__ never fires, "
            "so the handle has no name and would render a path ending in a separator."
        )
    return value


def _expect_config(*, operation: str, value: object, config_type: type) -> object:
    """Checks that a `config` argument is a hashable instance of the declared type."""
    if not isinstance(value, config_type):
        raise TypeError(
            f"{operation}: {CONFIG_PARAM} must be an instance of "
            f"{config_type.__name__}; got {type(value).__name__}."
        )
    try:
        hash(value)
    except TypeError:
        raise TypeError(
            f"{operation}: {CONFIG_PARAM} of type {config_type.__name__} is not "
            "hashable. A config must be hashable: a frozen dataclass whose fields are "
            "themselves immutable, so tuples rather than lists, dicts or sets."
        ) from None
    return value
