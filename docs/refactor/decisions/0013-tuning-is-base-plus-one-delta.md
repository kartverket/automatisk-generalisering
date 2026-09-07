# ADR-0013: Tuning is base plus one delta, with no resolution mechanism

**Status:** Accepted

## Context

Every operation has values that are tuned per scale — a minimum length, a tolerance, a
clearance. Under the earlier model they were loose keyword arguments on the operation
call, so they lived inline in the stage declaration, had nowhere to be validated, and
could not be compared across scales without grepping for numeric literals.

The current codebase has the beginning of the right shape — `ThinRoadNetworkKwargs`,
`RemoveRoadTrianglesKwargs` — but each one mixes IO, plumbing and tuning in a single
flat record:

```python
@dataclass(frozen=True)
class ThinRoadNetworkKwargs:
    input_road_line: io_types.GdbIOArg          # IO
    output_road_line: io_types.GdbIOArg         # IO
    work_file_manager_config: ...               # plumbing
    minimum_length: int                         # tuning
    invisibility_field_name: str                # tuning
    hierarchy_field_name: str                   # tuning
```

That mixing is why none of them can be a named scale-level value: they need paths,
which are not known where tuning is written.

## Decision

**One frozen config dataclass per operation, passed as a parameter named `config`,
enforced at decoration.** Field definitions live next to the operation, because the
fields change when the operation changes. Values live in tuning modules, because they
change per scale.

```
operations/road/
    __init__.py             the operations, and the config CLASSES beside them
    tuning/
        __init__.py         BASE configs - every field stated exactly once
        n50.py              one `replace` delta
        n100.py             one `replace` delta
tuning/scale/
    n100.py                 cartographic constants shared across objects
```

**No resolution mechanism.** There is deliberately no
`resolve(operation, scale, object)` walking object defaults, then scale defaults, then
overrides. Sharing happens because a line of code references a constant.

**Base plus exactly one delta.** Object base → scale delta, and that is the end.

**No defaults on config dataclass fields.** State every field in the base; express a
scale as a `replace` diff.

**Name scale constants after the cartographic concept**, not the consuming parameter:
`MINIMUM_VISIBLE_LENGTH_M`, never `THIN_MIN_LENGTH`.

**No `scale` field in any config.**

## Consequences

**`OperationCall.parameters` is uniformly `{"config": <frozen dataclass>}` or empty.**
A run manifest gets a JSON-able tuning record per operation from `dataclasses.asdict`
with no special-casing. That uniformity is the reason for enforcing the shape at
decoration rather than trusting convention — without it, `minimum_length_m=400` returns
at the first deadline.

**`__post_init__` is the first place in the design with anywhere to put a constraint on
a value.** A stage cannot check that a tolerance is positive; a config can.

**Handing an operation the wrong config is a pyright error at the call site** — the
same guarantee `In`/`Out` gives handles.

**An operation still cannot know its scale.** If it could read the scale it could
branch on it, and "one function serves N50 and N100" would stop being enforced by
anything. The scale selects *which* config; it is never *in* the config.

**A sub-config shared across operations is the case that earns nesting.**
`NetworkWeightsConfig` is read by both `calculate_road_hierarchy`, which assigns ranks,
and `thin_road_network`, which spends them. If the two disagree, thinning drops
arterials and keeps farm tracks with no error. Declared once per scale and referenced
from both configs, disagreement is unrepresentable. Keep it to one level:
`replace(BASE, weights=replace(BASE.weights, ...))` is tolerable once and unreadable
twice.

**Wanting a third layer is a signal, not a requirement.** It means a value should be
promoted to a named constant in `tuning/scale/` where the sharing is legible.

**A config unchanged at a scale is re-exported, not omitted.** `JOIN_ADMIN =
JOIN_ADMIN_BASE` reads as a deliberate "no change" and keeps the pipeline module
reading every config from one place. A `None` placeholder would be a trap.

**`dump_tuning.py <scale> <object>` prints the resolved result.** Ten lines, because
everything is module-level `replace` evaluated at import — so it is a read, not a
simulation. That is what makes the no-resolution-mechanism rule verifiable rather than
aspirational: the day someone adds a resolver, this stops being a ten-line read and the
reason is obvious. It is also the artifact cartographers and reviewers will actually
use, and it matters for review specifically because `road_n100`'s declassification
argument cites two tuning values by name.
