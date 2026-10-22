# ADR-0020: Operations: declaration, injection and tuning

**Status:** Accepted, 2026-10-22.

**Scope:** `ag/core/operations.py`, `ag/core/handles.py`, `ag/core/injection.py`,
`ag/ports/toolbox.py`, the operation config classes and the tuning modules. Absorbs A1.3.

Related: ADR-0018 (the ports as a package), ADR-0019 (what crosses a port), ADR-0017 (row
shape), ADR-0021 (stages).

## Direction

1. An operation's declaration is its signature. The operation decorator reads the name, the
   handle directions and the parameter kinds from it at import, and nothing is restated as a
   string.
2. An identifier the program must match is a symbol. A value that names something outside the
   program stays a literal.
3. The runtime supplies the parameters a declaration site must not. They are recognised by a
   marker base class, never by name, and each carries a sentinel default.
4. Ports reach an operation as one explicit, frozen bundle assembled at the composition root.
   A helper receives it explicitly, as a parameter or through a constructor, never ambiently.
5. Tuning is one frozen config dataclass per operation, valued as a base plus exactly one
   scale delta, with no resolution mechanism and no scale in the config.

## OP-1 The declaration is the signature

**Direction.** The decorator type-checks the declaration site against the real signature and
classifies every parameter at decoration; a declared handle takes its name and namespace from
the class attribute it is bound to.

**Details.**

- **OP-D1** The test: could a different string literal ever be correct here, given the rest
  of the code? If no, it is an identifier and must be a symbol. If yes, it names something
  outside the program and stays a literal.
- **OP-D2** `@operation` returns an `OperationDeclaration[P]`. Calling it with the declared
  keywords at a declaration site binds handles and a config and returns an `OperationCall`.
  Its parameter list is the function's, so the declaration site is type-checked against the
  real signature and go-to-definition lands on the implementation; the name is
  `fn.__name__`; `signature.bind` runs at the declaration site, when the pipeline module is
  imported.
- **OP-D3** An operation's handle parameters are `In` or `Out`, written with the signature,
  as `Annotated` aliases over `ScratchHandle` in `core/handles.py`. `Mutates` and
  `ParentsOut` belong to port methods (ADR-0017 RS-D11) and are rejected on an operation.
- **OP-D4** `ScratchHandle.__set_name__` gives a declared handle its `name` and `namespace`
  from the class attribute it is bound to. It fires in any class body, so a stage file that
  omits the `Handles` base still gets correct handles; `Handles` is a readability marker
  nothing depends on.
- **OP-D5** Internal scratch names stay literals: `scratch("dissolved")` names nothing a
  consumer must match.
- **OP-D6** `Derived("...")` stays a literal: declared once, `eq=False`, no consumer must
  match it. Pipeline-wide uniqueness is a check, not a naming mechanism; a symbol would let a
  rename move a live object's run-scratch location and invalidate the resume window.
- **OP-D7** Failures move to import: a misspelled keyword, a missing argument, a non-handle
  passed to a handle parameter, an undeclared handle, a non-frozen config and an injected
  argument passed by hand are `TypeError` while the pipeline module is imported, in CI or at
  orchestrator startup.
- **OP-D8** `namespace` participates in handle equality, so `Stage.handles` plus the
  own-handles check catch a handle borrowed from another stage.
- **OP-D9** Introspection happens once, at import. The entry point receives an
  `OperationCall` with plain mappings and dispatches by splat, inspecting nothing.

## OP-2 Injected parameters

**Direction.** A marker base class in the core, inherited by the injected types, lets the
decorator recognise what the runtime supplies without the core naming anything in the ports
package.

**Details.**

- **OP-D10** Parameter kinds: handle parameters by their markers; `config` by the parameter
  name, because a config's type differs per operation and the name is the only handle
  available; injected kinds by subclassing `Injected`; anything else is rejected at
  decoration.
- **OP-D11** `core/injection.py` is stdlib-only and holds `Injected`. `ScratchScope` in
  `core/handles.py` and `Toolbox` in `ports/toolbox.py` inherit it; the arrow is
  `ports → core`, and the core-is-pure contract is unchanged.
- **OP-D12** The decorator classifies with `isinstance(hint, type) and issubclass(hint,
  Injected)`. The guard is load-bearing: the handle markers resolve to `Annotated[...]`,
  which is not a type.
- **OP-D13** Each injected type supplies a sentinel default, `INJECTED` for `ScratchScope`
  and `NOT_INJECTED` for `Toolbox`, and passing one at a declaration site is rejected. The
  default is forced because the declaration site shares the function's parameter list;
  without it every declaration site is a type error for omitting an argument it must not
  supply.
- **OP-D14** `NOT_INJECTED` is one `cast` over one object whose `__getattr__` raises, naming
  the port that was reached.
- **OP-D15** `OperationCall.injected: Mapping[type[Injected], ParamName]`, read at
  decoration. The core never names `Toolbox`; adding a kind changes nothing in the core; the
  parameter name is not load-bearing.
- **OP-D16** `wants_scratch` is a property over the mapping. There is no `wants_toolbox`.
- **OP-D17** Rejected at decoration: two parameters of one injected kind, the bare `Injected`
  base as an annotation, and a union containing an injected kind.
- **OP-D18** `NOT_INJECTED` is re-exported from `ports/__init__.py` with the operation-facing
  vocabulary.

## OP-3 The toolbox

**Direction.** A frozen bundle of the ports is assembled at the composition root and passed
explicitly to every operation; a helper receives it explicitly, as a parameter or through a
constructor, never ambiently.

**Details.**

- **OP-D19** `Toolbox` is the bundle: `geometry`, `table`, `cartographic` and `graph`, the
  four processing ports, as one frozen value assembled once by the pod entry point.
- **OP-D20** `Toolbox` and `ScratchScope` are passed the same way, explicitly, and derived
  downward into helpers.
- **OP-D21** A large tool binds `tb` and `scratch` once in a plain class constructor rather
  than threading them through many signatures: constructor injection, not ambient state.
- **OP-D22** Tests stay stateless: a fake `Toolbox` is constructed and passed, with no global
  to set or reset.
- **OP-D23** The observability context (ADR-0018 AR-D19) travels in a `ContextVar`. It
  carries no capability, so it is not a second dependency-passing style.

## OP-4 Config and tuning

**Direction.** Config fields live beside the operation because they change with it; values
live in tuning modules because they change per scale; base plus exactly one delta, read, not
resolved.

**Details.**

- **OP-D24** One frozen config dataclass per operation, passed as the parameter named
  `config`, enforced at decoration.
- **OP-D25** Layout: the config classes beside the operations in `operations/<object>/`;
  `operations/<object>/tuning/__init__.py` holds the base configs with every field stated
  once; `tuning/<scale>.py` one `replace` delta each; `tuning/scale/<scale>.py` cartographic
  constants shared across objects.
- **OP-D26** No resolution mechanism: nothing walks object defaults, then scale defaults,
  then overrides. Sharing happens because a line of code references a constant.
- **OP-D27** Base plus exactly one delta: object base, then scale delta, and that is the end.
  Wanting a third layer is a signal to promote a value to a named constant in `tuning/scale/`.
- **OP-D28** No defaults on config dataclass fields. Every field is stated in the base; a
  scale is a `replace` diff.
- **OP-D29** Scale constants are named after the cartographic concept
  (`MINIMUM_VISIBLE_LENGTH_M`), never the consuming parameter.
- **OP-D30** No `scale` field in any config. The scale selects which config and is never in
  it, so an operation cannot branch on it and one function serves every scale.
- **OP-D31** `OperationCall.parameters` is uniformly `{"config": ...}` or empty, so a run
  manifest gets a JSON-able tuning record from `dataclasses.asdict`.
- **OP-D32** `__post_init__` is where a constraint on a value goes. A stage cannot check that
  a tolerance is positive; a config can.
- **OP-D33** A sub-config shared across operations earns nesting, kept to one level. Declared
  once per scale and referenced from both configs, disagreement is unrepresentable.
- **OP-D34** A config unchanged at a scale is re-exported, not omitted. A `None` placeholder
  is a trap.

## Rejected

- **OP-R1** A composition dataclass for an operation's IO. `inputs` and `outputs` change
  exactly when the signature changes; as an iterable, position is an unnamed identifier, so
  swapping two handles of one type runs with the wrong data; three levels of nesting at the
  declaration surface. The config half is OP-4. Reopened by operations needing to be
  substitutable per scale.
- **OP-R2** Alternatives to the marker base class: classifying injected parameters by name;
  moving the bundle into the core. The `config` precedent does not transfer, since `config`
  is name-classified only because its type differs per operation; the bundle's fields are
  typed by the port Protocols, so the ports follow it into the core. Classifying by name
  changes Direction 3. Moving the bundle into the core changes the core-is-pure import rule
  (OP-D11, `.importlinter` row 3).
- **OP-R4** `Toolbox | None = None` as the default. It does not avoid the default, and makes
  every port access an optional-member error unless every operation asserts. Reopened by a
  typing feature that narrows the parameter to `Toolbox` inside the body without an assertion
  in every operation.
- **OP-R5** A module-level bundle singleton set at pod startup. It prevents two pipelines
  running different adapters in one process, which is the incremental-port path, and hides
  the dependency from the signature. Reopened by the parameter proving worse in practice than
  predicted once real operations exist.
- **OP-R6** A layered tuning resolver. Sharing becomes a lookup nobody can read, and the
  resolved value stops being a read. Reopening this changes Direction 5.
