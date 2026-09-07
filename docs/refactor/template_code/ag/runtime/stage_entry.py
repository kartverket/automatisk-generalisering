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

from ag.core.types import DataType
from ag.core.operations import OperationCall, ScratchHandle
from ag.core.pipeline import Stage
from ag.staging.scratch import ScratchFileManager


class OutputMissing(RuntimeError):
    """An operation returned without producing something it declared."""


def run_operations(stage: Stage, sfm: ScratchFileManager) -> None:
    """Materialize every declared handle once, then run the operations in order.

    ONE MATERIALIZATION PASS for the whole stage, not one per operation: a declared
    handle lives in the STAGE workspace precisely so operation B can read what
    operation A wrote, and materializing per operation would make that impossible to
    express.

    The dispatch is a dictionary splat. No positional convention, no signature
    inspection - @operation already resolved the parameter names at import.
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
        if call.wants_scratch:
            kwargs["scratch"] = sfm.scope_for(call.operation)
        call.fn(**kwargs, **call.parameters)
        sweep_outputs(call, materialized)


def sweep_outputs(
    call: OperationCall,
    materialized: Mapping[ScratchHandle, ScratchHandle],
) -> None:
    """After every operation: each declared output exists, with the declared type.

    THIS IS THE ONLY THING THAT VERIFIES DataType AT ALL. It is carried on every
    handle, used to pick a join rule and a payload shape, and until here nothing ever
    confirmed the data matches it.

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
        if not _exists(actual):
            raise OutputMissing(
                f"{call.operation} declared {param}={declared.name!r} but nothing "
                f"exists at {actual.path}. The tool completed without writing - an "
                "empty selection and a silent no-op look identical from here."
            )
        found = _data_type_of(actual)
        if found is not declared.data_type:
            raise OutputMissing(
                f"{call.operation} declared {param}={declared.name!r} as "
                f"{declared.data_type.value} but produced {found.value} at "
                f"{actual.path}. This is what the DataType on a handle is for; "
                "nothing else in the design checks it."
            )


def _exists(handle: ScratchHandle) -> bool:
    raise NotImplementedError("arcpy.Exists(handle)")


def _data_type_of(handle: ScratchHandle) -> DataType:
    raise NotImplementedError(
        "map arcpy.Describe(handle).dataType onto DataType: FeatureClass -> "
        "FEATURE_CLASS, Table -> TABLE, RasterDataset -> RASTER"
    )
