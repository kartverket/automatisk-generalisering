"""TEMPLATE — not shipped. Target module: `src/ag/core/operations.py`.

Operations: the leaf processing units, and the scratch boundary.

THE RULE THIS MODULE ENFORCES

    An operation only ever sees ScratchHandles and one config object. Never a
    DataObject, never a URI, never a client, never a partition index, never a
    context radius, never a scale.

An operation is dumb on purpose. It runs a fixed sequence of GP tools against
whatever it is handed. It does not know the data is a partition, does not know how
many partitions exist, does not know whether its input came from GCS or Scality, and
does not know how much halo was included. That ignorance is what lets an operation
run on a laptop against a directory of gdbs with no credentials and no cluster - see
test_example_road_operations.py, which does exactly that in half a page.

TWO IO VOCABULARIES, DELIBERATELY DIFFERENT TYPES

    DataObject     what a STAGE declares. ExternalSource, ProductIdentity or
                   Derived. Has an identity, a lineage, a legality, and (for the
                   first two) a remote location. The dependency graph is computed
                   over these.

    ScratchHandle  what an OPERATION receives. A named slot in the pod's ephemeral
                   workspace. No identity, no location, no legality - just a place.

They cannot be confused because they are different types, and pipeline.StageInput is
the only place one is bound to the other.

THE POD BOUNDARY: NOTHING IS RESOLVED FROM A STRING ACROSS IT

A worker pod re-imports the pipeline module and gets the same Python objects the
planner had. It never receives a name to look something up by. That already follows
from OperationCall holding a live `fn`, and it constrains two things:

  - handles resolve by SYMBOL. A pod does not map "ranked" onto a handle; it
    receives the handle.
  - config objects must be IMPORTABLE AND RECONSTRUCTIBLE in the pod image. A
    config built at runtime from something only the orchestrator has would break
    this without any type error.

NO IDENTIFIER IS EVER WRITTEN TWICE

The test: could a different string literal ever be correct here, given the rest of
the code? If no - only one is ever right and the system misbehaves when it differs -
it is an IDENTIFIER and must be a symbol. If yes - it names something outside the
program - it is a VALUE and stays a literal.

Three consequences, all of them mechanisms here:

    @operation     the function's own signature is the declaration. Parameter names,
                   direction, the operation name and whether it wants a scratch scope
                   are all READ FROM IT. A renamed parameter is an LSP error at every
                   declaration site.

    __set_name__   a declared handle's name and namespace come from the class
                   attribute it is bound to, so the name exists once and uniqueness
                   within the stage is a property of the Python namespace.

    scratch("x")   internal scratch names STAY literals, deliberately. Nothing in the
                   program consumes them: they render into a layer name in a workspace
                   that dies with the pod, and the only reader is a human looking at a
                   scratch dump. A mismatch between `dissolved = scratch("dissolved")`
                   and its variable produces an oddly labelled temp file and nothing
                   else. This is the case that passes the test as a value.

Derived's `name` is the fourth case and it is also a value; see its docstring for why
it is deliberately NOT given this treatment.

TWO KINDS OF SCRATCH HANDLE, AND THEY LIVE IN DIFFERENT WORKSPACES

    declared   stage inputs, inter-operation handles, stage outputs. Class
               attributes in the stage file, so they are statically unique and need
               NO trail - their names stay short (`ranked`, `merged`, `snapped`).
               They live in the STAGE workspace, because operation B must be able to
               read what operation A wrote.

    internal   created inside an operation, between its own GP tools, via a
               ScratchScope. These carry the trail and live in that OPERATION's
               workspace.

An operation cannot tell them apart, deliberately - a declared handle arrives as a
parameter, an internal one comes from `scratch(...)`, and both are the same type.

VALIDATION LAYERING. The rule the whole design follows:

    Nothing that can fail at import may be deferred to plan.
    Nothing that can fail at plan may be deferred to the pod.

Everything this module enforces - annotation shape, config shape, undeclared
handles, a scratch scope passed at declaration time - fails at IMPORT, because the
declaration is evaluated at import. See validation.py for what necessarily waits for
plan, and stage_entry.py for the one sweep that can only happen in the pod.

The argument for why this replaced a hand-written factory per operation lives in
docs/refactor/decisions/0011-operation-decorator-and-handle-namespaces.md.
"""

from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, is_dataclass, replace
from enum import Enum
from typing import (
    Annotated,
    ParamSpec,
    TypeAlias,
    get_args,
    get_origin,
    get_type_hints,
)

from ag.core.types import DataType, OperationName, ParamName


@dataclass(frozen=True)
class ScratchHandle:
    """A named slot in the pod's ephemeral workspace.

    Two states of the same object:

      - DECLARATION time: `path` is None. Just a name, used to wire operations to
        each other. Constructed at import, safe to evaluate with no filesystem and
        no arcpy.
      - RUNTIME: the ScratchFileManager materializes it, returning a copy with
        `path` filled in. That is what an operation function actually receives.

    Frozen in both states - materialize() returns a new instance rather than
    mutating, so a declaration can never be corrupted by a run.

    EQUALITY IS (name, data_type, namespace), with `path` compare=False. Two of
    those are load bearing:

      `path` compare=False, so a materialized copy compares equal to the declaration
      it came from. The stage entry point builds {declared: materialized} and looks
      the declared handle up.

      `namespace` in the comparison, so `Network.ranks` and `ConflictResolution.ranks`
      are DIFFERENT handles. Without it they compare equal and hash equal, and any
      pipeline-wide structure keyed by handle silently conflates them - a
      cross-stage writer check reports a false double-writer for two stages that each
      have a `final`, and a {handle: obj} lineage map merges two unrelated entries.
    """

    name: str = ""
    data_type: DataType = DataType.FEATURE_CLASS
    namespace: str = ""
    path: str | None = field(default=None, compare=False)

    def __set_name__(self, owner: type, name: str) -> None:
        """Stamp the name and namespace from the class attribute this is bound to.

        Called by type.__new__ for EVERY object in ANY class body, which is why this
        is `__set_name__` and not `Handles.__init_subclass__`. A stage file that
        writes `class Network:` without the marker base still gets correct handles;
        under the old mechanism that omission silently left every handle with
        `name=""`, rendering paths like `.../network//`.

        `owner.__qualname__` rather than `__name__` so two classes named `Selection`
        in different modules do not collide.
        """
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "namespace", owner.__qualname__)

    def materialize(self, path: str) -> ScratchHandle:
        """Called by the ScratchFileManager, never by an operation."""
        return replace(self, path=path)

    def __fspath__(self) -> str:
        """So an operation can pass it straight to arcpy without unwrapping."""
        if self.path is None:
            raise RuntimeError(
                f"ScratchHandle({self.name!r}) was never materialized - this is a "
                "declaration, not a file. The stage entry point materializes every "
                "handle before calling any operation."
            )
        return self.path

    def __repr__(self) -> str:
        if self.namespace:
            return f"ScratchHandle({self.namespace}.{self.name})"
        return f"ScratchHandle({self.name!r}, UNDECLARED)"


def handle(data_type: DataType = DataType.FEATURE_CLASS) -> ScratchHandle:
    """Declare a handle whose name and namespace come from its class attribute.

    Only meaningful inside a class body. Outside one, `__set_name__` never fires and
    the result has an empty name and namespace - which is rejected at every choke
    point (see _expect_declared).
    """
    return ScratchHandle(data_type=data_type)


class Handles:
    """An optional marker for a stage's handle class. Readability only.

    ONE CLASS PER STAGE. Two handles in one class body cannot share a name, so
    within a stage there is nothing to check - that is what deleted
    check_handle_names_unique_per_stage. Two stages may each have a `ranked`: they
    live in different workspaces, and `namespace` keeps them distinct as values.

    NOTHING DEPENDS ON THIS BASE. Naming is done by ScratchHandle.__set_name__,
    which fires in any class body. Subclassing it documents intent and gives a
    reader something to grep for; omitting it costs nothing.
    """


class Direction(Enum):
    """Whether a handle parameter is read or written.

    It has to live somewhere: check_one_writer_per_handle, check_operation_order and
    check_stage_io_is_wired all depend on it, and no runtime inspection of a
    ScratchHandle can recover it. Putting it in the annotation means the signature
    states it - `output_lines: Out` rather than a naming convention - and pyright
    still sees a plain ScratchHandle at every call site.
    """

    IN = "in"
    OUT = "out"


In: TypeAlias = Annotated[ScratchHandle, Direction.IN]
"""A handle this operation reads."""

Out: TypeAlias = Annotated[ScratchHandle, Direction.OUT]
"""A handle this operation writes."""


MaterializeFn: TypeAlias = Callable[[tuple[str, ...], str, DataType], ScratchHandle]
"""(trail, leaf name, data type) -> a materialized handle.

Injected into ScratchScope by the ScratchFileManager. Keeps the trail logic here,
in the operation vocabulary, while paths, workspaces and budgets stay in staging.py.
"""


@dataclass
class ScratchScope:
    """A trail-bound factory for internal scratch. What an operation is handed.

        @operation
        def thin_road_network(*, roads: In, output: Out, scratch: ScratchScope = INJECTED):
            dissolved = scratch("dissolved")
            _build_topology(roads=dissolved, scratch=scratch.child("build_topology"))

    A helper tool receives a scope exactly the way an operation does - derive
    downward. A helper never learns its own trail, so it stays reusable from
    anywhere.

    A STATEFUL BUILDER, NOT A VALUE, and deliberately not frozen. `child()` mutates
    `_child_counts` to auto-index repeated labels, so freezing it would be a lie -
    and a misleading one next to ScratchHandle above, whose frozen-ness is sold as
    "a declaration can never be corrupted by a run". A scope is not a declaration;
    it is a live allocator bound to one operation's workspace for the length of one
    call.

    WHY THIS EXISTS AT ALL: the dev never invents a unique name. They write
    `scratch("merged")` and the scope prefixes it. Two tools can both call something
    "merged" and never collide, because their trails differ.

    THE LEAF NAMES STAY LITERALS. Nothing else in the program reads them and no
    consumer requires a match, so they are labels, not identifiers. Collisions are
    caught at runtime by the ScratchFileManager rather than statically, because a
    helper's rendered name genuinely is not knowable until it is called.
    """

    trail: tuple[str, ...]
    materialize: MaterializeFn
    _child_counts: dict[str, int] = field(
        default_factory=dict, repr=False, compare=False
    )

    def __call__(
        self, name: str, data_type: DataType = DataType.FEATURE_CLASS
    ) -> ScratchHandle:
        """Create one internal scratch file at this point in the trail."""
        return self.materialize(self.trail, name, data_type)

    def child(self, label: str, tag: str | None = None) -> ScratchScope:
        """Descend one level.

        AUTO-INDEXED, because the same helper is legitimately called more than once
        in one scope - a tool run over two different inputs, say. The index attaches
        to the SCOPE LABEL, not to the leaf:

            scratch.child("build_topology")           -> ..._build_topology__nodes
            scratch.child("build_topology")           -> ..._build_topology_2__nodes
            scratch.child("build_topology", "north")  -> ..._build_topology_north__nodes

        First occurrence is UNNUMBERED: one call is the common case, `_1` would be
        noise, and it means adding a second call later does not rename the first.

        Auto-index rather than error because the ordinal is meaningful and
        DETERMINISTIC - call order does not vary between runs, so the same failure
        produces the same path and two runs' file listings still diff. Erroring would
        fail a long run over something the system can resolve correctly.

        A repeated LEAF name within one scope is still an error - that is a genuine
        mistake, not a legitimate repeat. See ScratchFileManager.
        """
        key = f"{label}_{tag}" if tag else label
        count = self._child_counts.get(key, 0) + 1
        self._child_counts[key] = count
        segment = key if count == 1 else f"{key}_{count}"
        return ScratchScope(trail=self.trail + (segment,), materialize=self.materialize)


def _unbound(trail: tuple[str, ...], leaf: str, data_type: DataType) -> ScratchHandle:
    raise RuntimeError(
        f"scratch({leaf!r}) was called on an unbound scope. The stage entry point "
        "must pass sfm.scope_for(call.operation) for any operation whose signature "
        "declares `scratch: ScratchScope = INJECTED`."
    )


INJECTED = ScratchScope(trail=(), materialize=_unbound)
"""The default for an operation's `scratch` parameter.

It exists so the DECLARATION site may omit the argument while the runtime signature
still requires a scope. The entry point overwrites it, and passing one at a
declaration site is rejected. A real ScratchScope rather than None, so the type is
honest and a missed injection fails loudly at the first scratch(...) call rather
than as an AttributeError.
"""


CONFIG_PARAM = "config"
"""The one non-IO parameter an operation may take. See @operation."""


OperationFn: TypeAlias = Callable[..., None]
"""The runtime callable.

Signature convention: keyword-only; In/Out for every IO argument; at most one
`config`; an optional `scratch: ScratchScope = INJECTED`. Nothing else.

    @operation
    def simplify_road_geometry(
        *, roads: In, output: Out, collapsed_points: Out, config: SimplifyConfig
    ) -> None:
        arcpy.cartography.SimplifyLine(in_features=roads, out_feature_class=output, ...)

Note what is absent: no DataRef, no read/write callables, no run id, no partition
index, no context radius, no scale. Keeping them out is what makes the declaration
authoritative and lets one function serve N50 and N100.

ANNOTATIONS MUST RESOLVE AT IMPORT. Under `from __future__ import annotations` every
annotation is a string, and @operation resolves them with get_type_hints against the
operation module's globals at decoration time. So an operation signature may not use
a type imported under `if TYPE_CHECKING`, or one defined inside a function - either
is a NameError at import rather than a type-checker complaint. Currently satisfied
everywhere; invisible until violated, hence written down.
"""


@dataclass(frozen=True)
class OperationCall:
    """One operation, wired to ScratchHandles.

    `inputs` and `outputs` are keyed by the PARAMETER NAME in the function
    signature, so the entry point dispatches without a positional convention. See
    stage_entry.run_operations for the dispatch and for the post-operation output
    sweep that verifies each declared output actually exists with the declared type.

    NOBODY CONSTRUCTS THIS BY HAND. @operation builds it from the signature, so the
    parameter-name keys cannot drift from the parameters they name.

    `parameters` IS UNIFORMLY `{"config": <frozen dataclass>}` OR EMPTY, enforced at
    decoration. That uniformity is what lets a run manifest call
    dataclasses.asdict on it and get a JSON-able tuning record per operation with no
    special-casing.

    NO ROLE HERE. processing-versus-context is a fan-out concern and lives on
    StageInput. An operation is not told which of its inputs was partitioned,
    because it must behave identically either way.

    NO HALO HERE EITHER. Context radius is a stage parameter.
    """

    operation: OperationName
    fn: OperationFn
    inputs: Mapping[ParamName, ScratchHandle]
    outputs: Mapping[ParamName, ScratchHandle]
    parameters: Mapping[ParamName, object] = field(default_factory=dict)
    wants_scratch: bool = False
    """True if `fn` takes a `scratch: ScratchScope` keyword. Read from the signature
    at decoration time, so the entry point never inspects anything at dispatch."""

    def reads(self) -> tuple[ScratchHandle, ...]:
        return tuple(self.inputs.values())

    def writes(self) -> tuple[ScratchHandle, ...]:
        return tuple(self.outputs.values())

    def handles(self) -> tuple[ScratchHandle, ...]:
        return self.reads() + self.writes()


# ---------------------------------------------------------------------------
# @operation
# ---------------------------------------------------------------------------

P = ParamSpec("P")


def operation(fn: Callable[P, None]) -> Callable[P, OperationCall]:
    """Turn an operation function into its own declaration factory.

    `Callable[P, OperationCall]` preserves the parameter list exactly and changes
    only the return type, so at the declaration site

        thin_road_network(roads=Network.merged, output=Network.thinned,
                          config=tuning.THIN_ROAD)

    is type-checked against the real signature: a misspelled or renamed keyword is
    an error in the editor, go-to-definition lands on the implementation, and the
    operation name flowing into ScratchFileManager.operation_workspace comes from
    `fn.__name__`.

    WHAT IT REJECTS AT IMPORT

      - a parameter with no annotation, or one that is not In, Out, ScratchScope or
        `config`. Without this, `minimum_length_m=400` returns at the first deadline
        and `parameters` stops being a uniform tuning record.
      - a positional-or-keyword parameter. Operations are keyword-only so that every
        argument names the parameter it binds to.
      - at a DECLARATION site: a misspelled or missing keyword (via signature.bind),
        a non-ScratchHandle for an In/Out, an undeclared handle, a config that is not
        a frozen dataclass, and a `scratch=` argument. The last one type-checks -
        the sentinel default keeps it in P - and passing a scope before there is a
        workspace to allocate in is always a mistake.

    All of it fires while the pipeline module is being imported, which is CI or
    orchestrator startup, rather than in a pod three hours in.
    """
    signature = inspect.signature(fn)
    directions, scratch_param, config_param = _classify(fn, signature)
    name = fn.__name__

    def declare(*args: P.args, **kwargs: P.kwargs) -> OperationCall:
        try:
            bound = signature.bind(*args, **kwargs)
        except TypeError as error:
            raise TypeError(f"{name}: {error}") from None
        if scratch_param is not None and scratch_param in bound.arguments:
            raise TypeError(
                f"{name}: {scratch_param!r} must not be passed at a declaration "
                "site. The stage entry point injects the scope; there is no "
                "workspace to allocate in when this module is imported."
            )
        inputs: dict[ParamName, ScratchHandle] = {}
        outputs: dict[ParamName, ScratchHandle] = {}
        parameters: dict[ParamName, object] = {}
        for param, value in bound.arguments.items():
            direction = directions.get(param)
            if direction is Direction.IN:
                inputs[param] = _expect_declared(name, param, value)
            elif direction is Direction.OUT:
                outputs[param] = _expect_declared(name, param, value)
            elif param == config_param:
                parameters[param] = _expect_config(name, value)
        return OperationCall(
            operation=name,
            fn=fn,
            inputs=inputs,
            outputs=outputs,
            parameters=parameters,
            wants_scratch=scratch_param is not None,
        )

    functools.update_wrapper(declare, fn)
    return declare


def _classify(
    fn: Callable[..., object],
    signature: inspect.Signature,
) -> tuple[Mapping[ParamName, Direction], ParamName | None, ParamName | None]:
    """Read the shape of an operation off its annotations, once, at decoration."""
    name = fn.__name__
    hints = get_type_hints(fn, include_extras=True)
    directions: dict[ParamName, Direction] = {}
    scratch_param: ParamName | None = None
    config_param: ParamName | None = None

    for param, parameter in signature.parameters.items():
        if parameter.kind is not inspect.Parameter.KEYWORD_ONLY:
            raise TypeError(
                f"{name}: parameter {param!r} is not keyword-only. Operations take "
                "keyword arguments only, so that every argument at a declaration "
                "site names the parameter it binds to."
            )
        hint = hints.get(param)
        if hint is None:
            raise TypeError(
                f"{name}: parameter {param!r} has no annotation. @operation reads "
                "direction and shape from the annotations; an unannotated parameter "
                "cannot be classified."
            )
        if hint is ScratchScope:
            scratch_param = param
        elif _direction_of(hint) is not None:
            direction = _direction_of(hint)
            assert direction is not None
            directions[param] = direction
        elif param == CONFIG_PARAM:
            config_param = param
        else:
            raise TypeError(
                f"{name}: parameter {param!r} is neither In, Out, ScratchScope nor "
                f"{CONFIG_PARAM!r}. Tuning values go in one frozen dataclass passed "
                f"as {CONFIG_PARAM}, so that a run manifest can record what tuning "
                "produced an output without special-casing each operation."
            )
    return directions, scratch_param, config_param


def _direction_of(hint: object) -> Direction | None:
    if get_origin(hint) is not Annotated:
        return None
    for meta in get_args(hint)[1:]:
        if isinstance(meta, Direction):
            return meta
    return None


def _expect_declared(
    operation_name: str, param: ParamName, value: object
) -> ScratchHandle:
    if not isinstance(value, ScratchHandle):
        raise TypeError(
            f"{operation_name}: {param!r} is declared In or Out, so it must be a "
            f"ScratchHandle - got {type(value).__name__}. A DataObject belongs on a "
            "StageInput or StageOutput, never in an operation call."
        )
    if not value.namespace:
        raise TypeError(
            f"{operation_name}: {param!r} received an undeclared handle. handle() "
            "is only legal as a class attribute - outside a class body __set_name__ "
            "never fires, so the handle has no name and would render a path ending "
            "in a separator."
        )
    return value


def _expect_config(operation_name: str, value: object) -> object:
    if not is_dataclass(value) or isinstance(value, type):
        raise TypeError(
            f"{operation_name}: {CONFIG_PARAM} must be a frozen dataclass INSTANCE - "
            f"got {type(value).__name__}. A dataclass is what makes the tuning "
            "record serializable and gives __post_init__ somewhere to constrain a "
            "value."
        )
    if not value.__dataclass_params__.frozen:  # type: ignore[attr-defined]
        raise TypeError(
            f"{operation_name}: {CONFIG_PARAM} of type "
            f"{type(value).__name__} is not frozen. A config is shared between "
            "declaration sites and re-imported in every pod; a mutable one can be "
            "edited by one operation and silently change another's tuning."
        )
    return value
