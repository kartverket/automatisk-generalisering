"""TEMPLATE — not shipped. Target module: `src/ag/runtime/stage_entry.py`.

What runs inside a partition pod. The dispatch loop and the output sweep.

This is the whole of it. A worker materializes its handles, runs the stage's
operations in listed order against one workspace with no transfer between them, and
checks after each one that what was declared actually appeared.

An operation running here does not know it is in a pod, does not know the data is a
partition, and does not know K. It sees ScratchHandles and a config.

THE LAST LAYER OF THE VALIDATION RULE

    Nothing that can fail at import may be deferred to plan.
    Nothing that can fail at plan may be deferred to the pod.

Everything shape-related failed at import (@operation) and everything wiring-related
failed at plan (validation.py). What is left here is the one class of failure that
genuinely cannot be known earlier: whether a GP tool did what it said.
"""

from __future__ import annotations

from collections.abc import Mapping

from ag.core.injection import Injected
from ag.core.operations import OperationCall, ScratchHandle, ScratchScope
from ag.core.pipeline import Stage
from ag.ports.toolbox import Toolbox
from ag.staging.scratch import ScratchFileManager


class OutputMissing(RuntimeError):
    """An operation returned without producing something it declared."""


def run_operations(stage: Stage, sfm: ScratchFileManager, tb: Toolbox) -> None:
    """Materialize every declared handle once, then run the operations in order.

    ONE MATERIALIZATION PASS for the whole stage, not one per operation: a declared
    handle lives in the STAGE workspace precisely so operation B can read what
    operation A wrote, and materializing per operation would make that impossible to
    express.

    ONE TOOLBOX FOR THE WHOLE STAGE, assembled by the caller - `runtime/` is a
    composition root and the only layer that may choose an adapter (ADR-0008). It is
    a parameter rather than something built here so that the K-invariance harness and
    a laptop test can drive this function with fakes and no special-casing: that is
    what makes `tests/invariance/` a primary adapter rather than a mock
    (03-architecture §4.5).

    A FUTURE PER-STAGE BACKEND OVERRIDE lands here and nowhere else - read a field off
    `stage`, assemble a different Toolbox, pass it. No operation signature and no
    operation body changes.

    The dispatch is a dictionary splat. No positional convention and no signature
    inspection - @operation resolved the parameter names at import, including what
    each operation calls its scratch scope and its toolbox.
    """
    materialized = {
        declared: sfm.handle(declared) for declared in set(stage.all_handles())
    }
    sfm.create_workspaces()

    for call in stage.operations:
        kwargs: dict[str, object] = {
            name: materialized[h] for name, h in call.inputs.items()
        }
        kwargs |= {name: materialized[h] for name, h in call.outputs.items()}
        kwargs |= {
            param: _supply(kind, call, sfm, tb) for kind, param in call.injected.items()
        }
        call.fn(**kwargs, **call.parameters)
        sweep_outputs(call, materialized, tb)


def _supply(
    kind: type[Injected], call: OperationCall, sfm: ScratchFileManager, tb: Toolbox
) -> Injected:
    """Build the one runtime-supplied value of `kind` that this operation asked for.

    THE ONLY PLACE THAT KNOWS BOTH SIDES. `core/` knows a parameter is injected and
    what the operation calls it; this function knows what to put there, because it is
    in the composition root where a ScratchFileManager and a Toolbox both exist. A
    sixth injected kind is a branch here plus a base class there, and nothing between.
    """
    if kind is ScratchScope:
        return sfm.scope_for(call.operation)
    if kind is Toolbox:
        return tb
    raise TypeError(
        f"{call.operation} declares an injected parameter of kind "
        f"{kind.__name__}, which this entry point does not know how to supply. "
        "Anything inheriting Injected must be buildable here."
    )


def sweep_outputs(
    call: OperationCall,
    materialized: Mapping[ScratchHandle, ScratchHandle],
    tb: Toolbox,
) -> None:
    """After every operation: each declared output exists, with the declared type.

    THIS IS THE ONLY THING THAT VERIFIES DataType AT ALL. It is carried on every
    handle, used to pick a join rule and a payload shape, and until here nothing ever
    confirmed the data matches it.

    IT GOES THROUGH `tb.table`, NOT arcpy. `TableOps.exists` and `data_type_of` exist
    on that port for this caller: without them, the two `arcpy.Exists` /
    `arcpy.Describe` calls this function needs would be the one vendor import left in
    `runtime/`, and "only adapters import a vendor library" (03-architecture §4.1)
    would be false by two lines. The sweep is also the reason the methods belong on
    TableOps rather than GeometryOps - it runs over feature classes, tables and
    rasters alike, and "does this dataset exist" is the schema conversation.

    IT COVERS THE TWO ARCPY FAILURE MODES THAT DO NOT RAISE:

      a tool that produces NOTHING. Several GP tools complete successfully having
      written no rows, or having written nothing at all when a selection was empty.
      The operation returns, the next one reads a dataset that is not there, and the
      error names the CONSUMER - two operations away from the cause.

      a tool that produces the WRONG KIND OF THING. FeatureToPoint where a line was
      declared, a table where a feature class was declared. Downstream it surfaces as
      a geometry-type error inside some later tool, or not at all until fan-in tries
      to merge K partitions of two different shapes.

    Sweeping after EACH operation rather than at the end of the stage is what makes
    the error name the operation that caused it. That is most of the value: a stage
    is four operations deep with several intermediates, and "thin_road_network did
    not write dropped" is a different afternoon from "the stage failed".
    """
    for param, declared in call.outputs.items():
        actual = materialized[declared]
        if not tb.table.exists(input=actual):
            raise OutputMissing(
                f"{call.operation} declared {param}={declared.name!r} but nothing "
                f"exists at {actual.path}. The tool completed without writing - an "
                "empty selection and a silent no-op look identical from here."
            )
        found = tb.table.data_type_of(input=actual)
        if found is not declared.data_type:
            raise OutputMissing(
                f"{call.operation} declared {param}={declared.name!r} as "
                f"{declared.data_type.value} but produced {found.value} at "
                f"{actual.path}. This is what the DataType on a handle is for; "
                "nothing else in the design checks it."
            )
