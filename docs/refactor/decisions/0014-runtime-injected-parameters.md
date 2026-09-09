# ADR-0014: Runtime-injected parameters are recognised by a marker base class

**Status:** Accepted

**Extends:** ADR-0011, which established that `@operation` reads an operation's shape off its
signature. This settles how it recognises the parameters the *runtime* supplies rather than the
declaration site.

## Context

`@operation` classifies every parameter of an operation function at decoration time. Until now
there were four kinds:

| kind | recognised by | supplied by |
|---|---|---|
| `In` / `Out` | an `Annotated` marker carrying a `Direction` | the declaration site |
| `config` | **the parameter name** `config` | the declaration site |
| `ScratchScope` | `hint is ScratchScope` | the pod entry point |
| anything else | — | rejected at decoration |

[02-runtime §2.4](../02-runtime.md#24-operations) requires a fifth: `tb: Toolbox`, the bundle of
ports an operation calls instead of a vendor library (ADR-0008). Adding it exposed a problem the
`ScratchScope` case had hidden, because `ScratchScope` happens to live in `core/`.

**`Toolbox` lives in `ports/`, and `core/` may not import it.**
[03-architecture §4.1](../03-architecture.md#41-the-rules) gives `core/` stdlib only, and the
existing `core-is-pure` contract in `.importlinter` names `ag.ports` as forbidden. A direct
import from `core.operations` would be a `core → ports → core` cycle, since `ports/` imports
`ScratchHandle` from `core.operations` (ADR-0003).

Three ways out were considered. Two are recorded as rejected below.

## Decision

**A marker base class in `core/`, imported by the injected types rather than the reverse.**

```python
# core/injection.py — stdlib only, no imports at all
class Injected:
    """Marker: the runtime supplies this parameter; a declaration site must not."""
```

`ScratchScope` (in `core/operations.py`) and `Toolbox` (in `ports/toolbox.py`) both inherit it.
The arrow is `ports → core`, which ADR-0003 already sanctions, and `core/` imports nothing new.

**`@operation` classifies with `isinstance(hint, type) and issubclass(hint, Injected)`.** The
`isinstance` guard is load-bearing: `In` and `Out` resolve to `Annotated[...]`, which is not a
type, and bare `issubclass` raises `TypeError` on it.

This works because `get_type_hints(fn)` resolves the annotation against `fn.__globals__` — the
*operation module's* namespace, which imports `Toolbox` normally. `core.operations` receives an
already-resolved class object and asks a question about it. It never needs the name, and
`from __future__ import annotations` in any of the three modules does not change that.

**Each injected type supplies a sentinel default, and passing one at a declaration site is
rejected.** `scratch: ScratchScope = INJECTED` and `tb: Toolbox = NOT_INJECTED`.

The sentinel is not stylistic. `@operation` returns `Callable[P, OperationCall]`, and `P` is
taken from the declared signature, so a parameter with no default makes every declaration site
a type error for omitting an argument the declaration site must not supply. The sentinel is what
lets the runtime signature require the value while the declaration signature does not.

`NOT_INJECTED` is one `cast` over one object whose `__getattr__` raises, naming the port that
was reached — not four casts over four fields.

**`Toolbox | None = None` does not replace it, and this is recorded so it is not re-proposed.**
It does not avoid a single cast, because it does not avoid the *default*: the default is forced
by `Callable[P, OperationCall]`, whatever its type, and `None` is simply a different value in
the same slot. What it adds is a cost — `tb` becomes `Toolbox | None` inside the function body,
so every `tb.geometry.buffer(...)` is an optional-member-access error in all 15 operations
unless each one opens with an `assert tb is not None`. One `cast` in one sentinel module, or an
assertion in every operation: the cast is the smaller lie and it is contained where a reader
looking for it will be.

**`OperationCall` carries one mapping, `injected: Mapping[type[Injected], ParamName]`,** read
from the signature at decoration — `{ScratchScope: "scratch", Toolbox: "tb"}`. Not a boolean per
kind, for three reasons, and the third is a bug it fixes:

- `core/` never names `Toolbox`. A `toolbox_param` field on a `core/` dataclass would put a
  `ports/` word where `core/` cannot import the thing it refers to.
- Adding a kind changes nothing in `core/`. The entry point supplies what it knows how to build.
- **The parameter name stops being load-bearing.** Under `wants_scratch: bool` the entry point
  hardcoded `kwargs["scratch"]`, so an operation writing `scope: ScratchScope = INJECTED`
  classified correctly, reported `wants_scratch`, and then never received a scope — it kept the
  sentinel and failed at the first `scratch(...)` call, in a pod. That was live in the template.

`wants_scratch` survives as a property over the mapping, because `ScratchScope` is a `core/`
type and reads better than a lookup at the two sites that ask. There is deliberately no
`wants_toolbox` twin: `core/` cannot name `Toolbox`, and the entry point that can just asks the
mapping. The entry point still inspects nothing at dispatch — the constraint ADR-0011 recorded
as still holding.

**Two parameters of the same injected kind are rejected at decoration.** The entry point
supplies one of each, so a second would silently receive the same object.

## Consequences

**Two special cases became one mechanism.** `hint is ScratchScope` is gone. Adding a sixth
parameter kind — a future run-scoped resource, say — is now inheriting from `Injected`, not
editing a classifier.

**The rejection message improves.** `@operation` can now distinguish "this parameter is
supplied by the runtime and you must not pass it" from "this parameter is not a recognised
kind", and say so.

**`core/injection.py` exists to be imported upward.** It is the only module in `core/` whose
purpose is to be depended on by a higher layer, and it holds one class with no methods. That is
the cost of the layering rule, paid once, in nine lines.

**Operation modules import one more name.** `NOT_INJECTED` joins `INJECTED` in the import at
the head of every operation module. It is operation-facing — it appears in operation
*definitions*, not at declaration sites — and is re-exported from `ports/__init__.py` with the
rest of the operation-facing vocabulary.

**`@operation` gains no import from `ports/`.** The `core-is-pure` contract keeps `ag.ports` in
its forbidden list unchanged, and this ADR's decision is what makes that possible.

## Rejected: classify by parameter name

`TOOLBOX_PARAM = "tb"`, matching `CONFIG_PARAM = "config"`. Cheapest, and needs no marker class.

Rejected because **the `config` precedent does not transfer.** `config` is name-classified
because its *type differs per operation* — `ThinRoadConfig`, `SnapConfig`, `SimplifyConfig` —
so there is nothing to match against and the name is the only available handle. `Toolbox` is one
type. Where a type exists, matching on it is strictly better:

- `toolbox: Toolbox` and `tb: Toolbox` both work; the parameter name stops being load-bearing.
- `tb: SomethingElse` fails loudly at decoration instead of silently receiving a `Toolbox` at
  dispatch — the exact failure mode ADR-0011 exists to eliminate.
- The list of magic names does not grow. Name-matching scales to a sixth kind by adding a sixth
  name; a marker class scales by inheritance.

## Rejected: move `Toolbox` into `core/`

This removes the cycle by removing the boundary. `Toolbox`'s four fields are typed by the six
port `Protocol`s, so moving it drags `ports/` into `core/` behind it, and `core/` stops being
the stdlib-only planning layer that
[02-runtime §2.6](../02-runtime.md#26-declarations-must-be-constructible-without-touching-data)
depends on. A `TYPE_CHECKING` import plus a string comparison was rejected for the obvious
reason: the name does not exist at runtime, which is when the classifier runs.
