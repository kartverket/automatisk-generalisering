# ADR-0011: Declarations come from signatures and class attributes, not from strings

**Status:** Accepted

## Context

This ADR records the argument that used to live in `operations.py` docstrings, so that
module can describe what the code does rather than what it replaced.

The test applied throughout: *could a different string literal ever be correct here,
given the rest of the code?* If no — only one is ever right and the system misbehaves
when it differs — it is an **identifier** and must be a symbol. If yes — it names
something outside the program — it is a **value** and stays a literal.

### What the design had before

Every operation carried a hand-written factory twin:

```python
def thin_road_network(*, roads, output, minimum_length_m) -> OperationCall:
    return OperationCall(
        operation="thin_road_network",          # the function's name, retyped
        fn=_thin_road_network,
        inputs={"roads": roads},                # a parameter name, retyped
        outputs={"output": output},
        parameters={"minimum_length_m": minimum_length_m},
        wants_scratch=True,                     # a fact about the signature
    )
```

Four restatements of one signature, none checkable. Renaming `roads` fixes the
factory's local parameter and leaves the dict key alone; the failure is
`TypeError: unexpected keyword argument` inside a pod, after fan-out has moved the
data.

Declared handles were module-level constants:

```python
RANKED = ScratchHandle("ranked")
```

— the name stated twice, with `check_handle_names_unique_per_stage` policing
collisions after the fact.

### What the current codebase does today

The same disease, in two places:

- `WorkFileManager.setup_work_file_paths(instance=self, file_structure=[...])` binds
  paths by scanning `instance.__dict__` for an attribute whose *value* equals the
  string. The name is written three times, pyright sees `str` forever even after the
  attribute becomes a `GdbFilePath`, and two attributes holding the same string mean
  the second silently keeps the raw literal.
- `PartitionInputConfig(entries=[InputEntry(object=..., tag=...)])` plus
  `InjectIO(object=..., tag="input")` — IO in a list, referenced by a string pair
  resolved at runtime by `extract_key_by_alias`, which raises on mismatch.

Both are the pattern the refactor exists to remove, so neither is a hypothetical.

## Decision

Three mechanisms, all in `core/operations.py`.

**`@operation`.** `Callable[P, OperationCall]` preserves the parameter list and
changes only the return type, so the declaration site is type-checked against the real
signature. Direction is carried by `In` / `Out` annotations; the operation name comes
from `fn.__name__`; `wants_scratch` from the presence of a `ScratchScope` parameter.
`signature.bind` runs at declaration time.

**`ScratchHandle.__set_name__`.** A declared handle takes its `name` and `namespace`
from the class attribute it is bound to.

**Internal scratch names stay literals.** `scratch("dissolved")` names nothing any
consumer must match; it renders into a layer name in a workspace that dies with the
pod, read only by a human looking at a scratch dump.

**`Derived("selected_roads")` stays a literal too.** Declared once, `eq=False`, and no
consumer requires it to match its symbol. Uniqueness within the pipeline *is* required
— `locations.scratch_location` builds a path from it — but that is a check, not a
naming mechanism. Converting it would additionally mean an LSP rename moved a live
object's run-scratch location and invalidated the resume window for in-flight runs.

## Consequences

**Failures move to import.** A misspelled keyword, a missing argument, a non-handle
passed to an `In`, an undeclared handle, a non-frozen config, a `scratch=` at a
declaration site: all `TypeError` while the pipeline module is being imported, which is
CI or orchestrator startup. Previously several of these were pod-time failures and one
(`wants_scratch` out of sync) was silent.

**Two validation checks were deleted, not fixed.**

- `check_handle_names_unique_per_stage` — two attributes in one class body cannot
  share a name. It was also *wrong*: its filter excluded `input<-` uses but not
  `output->`, so it flagged every `StageOutput` naming a handle an operation writes,
  which is the required wiring. It reported six false positives on the road example.
- `check_sources_agree` — an `ExternalSource` is declared once, in `sources.py`. See
  ADR-0012.

**`namespace` participates in equality.** Without it `Network.ranks` and
`ConflictResolution.ranks` compare and hash equal, so any pipeline-wide structure keyed
by handle conflates them. With it, `Stage.handles` plus `check_stage_uses_own_handles`
catch a handle borrowed from another stage — previously undetectable statically and a
missing-dataset failure in the pod.

**`__set_name__` rather than `Handles.__init_subclass__`.** `type.__new__` calls it for
any object in any class body, so a stage file that omits the marker base still gets
correct handles. Under the earlier `__init_subclass__` mechanism that omission left
every handle with `name=""`, silently rendering paths like `.../network//`. `Handles`
is now a readability marker that nothing depends on.

**Introspection happens once, at import.** The recorded objection — that the entry
point should not inspect a signature to decide what to pass — still holds: the entry
point receives an `OperationCall` with plain mappings and dispatches by splat.

**Configs are one frozen dataclass per operation, named `config`, enforced at
decoration.** So `OperationCall.parameters` is uniformly `{"config": ...}` or empty,
and a run manifest gets a JSON-able tuning record from `dataclasses.asdict` with no
special-casing. Without enforcement, `minimum_length_m=400` returns at the first
deadline. See ADR-0013 for the tuning layout.

**Two earlier ADRs now carry a stale parenthetical.** Neither decision is affected, and neither
ADR is edited — recorded here instead, per the immutability convention.

- ADR-0003's consequences say `ports/` may import `core.handles`. The three mechanisms live in
  one module, `core.operations`, so that is the import path; the decision — `ScratchHandle`, not
  `DataObject`, at the port boundary — stands unchanged.
- ADR-0005's context gives helper membership as "no `OperationCall` factory". The test is now
  "not decorated with `@operation`"; the decision — `helpers/` as the package name — stands
  unchanged.

## Rejected: a composition dataclass per operation

Considered: `Operation(inputs=..., outputs=..., config=...)` as a dataclass instead of
a decorated function.

The **config** half was adopted — config has a genuinely different reason to change
(retuned per scale without the operation changing), so it earns its own record.

The **IO** half was rejected. `inputs` and `outputs` change exactly when the signature
changes, so wrapping them in their own dataclasses is structure with no second reason
to change; and as an *iterable* it is strictly worse than a magic string. Given
`inputs=[merged, ranks, merge_report]`, swapping the last two produces no error
anywhere — all three are `ScratchHandle`, all three type-check, and the operation runs
with the wrong data. Position is an unnamed identifier. That is precisely the shape
`PartitionInputConfig` + `InjectIO` already has in the current codebase.

At the declaration surface the class form also costs three levels of nesting per
operation in the file a reviewer reads to understand the pipeline. Nothing stops an
operation's *implementation* from being a private class — the decorator constrains only
the declaration.

A `Protocol`-typed `Operation` with `.run()` would be the right shape if operations
needed to be substitutable per scale. Nothing in this design takes an operation
polymorphically, so it is not built.
