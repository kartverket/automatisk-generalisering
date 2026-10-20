# ADR-0016: Stage inputs have a declared role and a derived spatiality

**Status:** Accepted (decided 2026-10-12, recorded here 2026-10-16)

**Relates to:** ADR-0003 (operations see no partition and no context radius), ADR-0012
(`ExternalSource` carries `data_type`, `location` and `classification`), ADR-0013 (tuning
values are config dataclass fields).

## Context

A stage declares its inputs with a role, `PROCESSING` or `CONTEXT`, and fan-out is the one
component that reads it. The design documents described the role as "how fan-out treats the
input", said context inputs were "selected within the context radius" without saying of what,
never said that both roles reach a pod with halo overlap, and treated a non-spatial lookup
table as "context in the operative sense", deriving a role from the data. Two consequences
followed. The port-level `subject` and `context` of the row-shape grammar were equated with the
stage-level roles, which is wrong in both directions. And a fixture declared a stage output
built only from context inputs, which a decided item was then changed to admit.

The legacy partition iterator did the right thing: it filtered every context input to within
the search distance of the processing inputs before partitioning, gave each partition the
processing rows within the search distance of its polygon, and selected context per partition
the same way. It declared vector data only. The new runtime also carries tables, symbology
files and rasters, and a role alone cannot say how each is moved.

## Decision

A stage input has two independent properties.

**The input role is declared per stage input and answers one question: may this input's
rows become stage output?** Roles belong to the stage input, not to the object. The same
water layer is `PROCESSING` in the stage that generalises it and `CONTEXT` in the stage that
moves buildings away from it.

**Whether an input is spatial is read from its object's `DataType` and never declared.**
`FEATURE_CLASS` and `RASTER` are spatial; `TABLE` and `SYMBOLOGY` are not. `DataType` carries a
`spatial` property so that no module re-derives the distinction.

**Fan-out's transfer follows from both.**

| | spatial | non-spatial |
|---|---|---|
| PROCESSING | partitioned, with halo overlap | rejected at declaration |
| CONTEXT | context filter, then partitioned with the same overlap | sent whole to every pod, written once at a shared key |

The context filter keeps the `CONTEXT` rows within the stage's context radius of any
`PROCESSING` row, before partitioning; at 0 m it keeps the rows that intersect a `PROCESSING`
row. The filter distance is the context radius, with no second number. Overlap applies to both
partitioned roles: a `PROCESSING` row within the radius of a partition but outside it reaches
that partition too and fan-in discards it; a `CONTEXT` row within the radius of a partition
reaches it. Non-spatial `PROCESSING` is rejected when the `StageInput` is constructed, because
there is nothing to partition and the model defines no behaviour for it.

**Only rows originating from `PROCESSING` inputs may become stage outputs**, and stage outputs
are the only data that leaves a stage. A `CONTEXT` row may affect an output and never becomes
one. Scratch intermediates built from `CONTEXT` rows are legal inside a stage and reach the
scratch dump like every other handle. An object derived from `CONTEXT` rows that a later stage
must read is produced in a stage where its source is `PROCESSING`. This is enforced by review
of the stage declarations until a static check exists; the check needs an operation-level
subject marker the declarations do not yet carry.

**The context radius is a claim about the logic.** Operations never see partitions
(ADR-0003), so the radius is the one place a stage author reasons about partition boundaries.
A 0 m radius states that nothing in the stage consults a neighbour; the model does not guard
it, and a reviewer can challenge it.

**Rasters are spatial** and take either role; transfer is tile selection or clipping to the
partition plus its halo, not row filtering. The mechanism is open until a stage declares a
raster input.

**Symbology files are non-spatial `CONTEXT` inputs.** A `.lyrx` file is a symbology blueprint
with no data, consumed by arcpy tools such as resolve road conflicts. It is declared as an
`ExternalSource` with `data_type=DataType.SYMBOLOGY`, a settable location and a
classification, and reaches every pod whole. All tables and all symbology files are stage
inputs with a settable storage location, never baked into the container image: some carry
attributes that must stay on-prem, and one rule for all of them is more consistent than a
split by author. The member is `SYMBOLOGY`, not a generic `FILE`, so the next file kind gets
its own decision. Numeric symbol dimensions are a different thing: a project-wide Python
resource that reaches operations as config dataclass fields varying by pipeline (ADR-0013),
never a stage input. Deriving them from `.lyrx` files is possible later and not planned.

**The port-level `subject` and `context` of the row-shape grammar relate to the stage roles;
they are not the same thing.** The grammar declares, per port method, which input parameter's
rows carry identity into an output. The roles declare, per stage input, which rows may become
stage output. A port subject may be fed from a `CONTEXT` stage input (a displacement feature
buffered from context roads), and a port context from a `PROCESSING`-derived intermediate (that
displacement feature read by `propagate_displacement`). What holds at both levels: only the
subject carries identity into outputs, and a context influences without contributing identity.
The word `context` is shared for that reason and for no other.

**Rejected.** A third role for the non-spatial case: it duplicates what `DataType` already
says, mixes two questions in one enum, and each candidate word collides with an existing use.
A generic `FILE` data type: it invites opaque inputs. The trade accepted: at a stage
declaration a reader must know the data type to see that a table is sent whole, so the
`InputRole` docstring states both transfers side by side.

## Consequences

- `DataType` has four members and a `spatial` property; `InputRole` has two members and a
  docstring that states the rule and the four transfers.
- `StageInput` rejects a non-spatial object with role `PROCESSING` at construction, with a
  break-it case. No other guard: a 0 m radius with spatial context is legal.
- Fan-out reads three declared facts, the role, the radius and the object's data type, and
  nothing else; fan-in discards halo copies of `PROCESSING` rows and keeps non-spatial outputs
  by id ownership.
- A stage output built only from context inputs is a declaration error found in review. The
  building displacement fixture keeps its displacement feature as a scratch handle.
- Every table and every symbology file is an `ExternalSource` with a location and a
  classification, and a classification of `PREM_ONLY` on one of them pins the stage on-prem
  like any other input.
- Open: a static check for the output rule (an operation-level subject marker), and the raster
  transfer mechanism.
