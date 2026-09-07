"""TEMPLATE — not shipped. A dev script; target `tools/`.

flatten both pipelines and print what is DERIVED rather than declared.

    python example_run.py

Everything this prints was computed from declarations. Nothing in either example
file states an ordering, an edge, or the classification of a derived object.

The line that matters is the cross-pipeline edge: building_n100 reads N100_ROAD as
a StageInput, road_n100 produces a Derived and promotes it to that identity with a
Publish. Two different objects, linked by the ProductIdentity symbol both reference.
Matching on the Derived alone finds nothing and the two pipelines look independent -
which was a real bug in this package, and this file is its regression test.

Only calls implemented functions. The check_* bodies in validation.py are still
NotImplementedError.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # TEMPLATE: see conftest.py

from ag.core.types import ObjectName
from ag.pipelines.building.n100_stages import BUILDING_N100
from ag.pipelines.road.n100 import ROAD_N100
from ag.core.graph import derive_stage_dependencies, internal_handles, topological_order
from ag.core.pipeline import flatten
from ag.core.policy import ClassificationRule, classification_of, pipeline_environment
from ag.core.selection import Closure, RunRequest, select_stages

from ag.classification_rules import RULES


def short(name: str) -> str:
    """N100/building/displacement -> building/displacement"""
    return "/".join(name.split("/")[1:])


def main() -> None:
    registry = flatten([ROAD_N100, BUILDING_N100])
    dependencies = derive_stage_dependencies(registry)
    by_name = {stage.qualified_name: stage for stage in registry.stages}

    print("\n=== stage graph (derived from IO; nothing declares an edge) ===\n")
    for stage in registry.stages:
        deps = sorted(dependencies[stage.qualified_name])
        label = short(stage.qualified_name)
        if not deps:
            print(f"  {label:30} <- (external sources only)")
            continue
        for index, dep in enumerate(deps):
            cross = "   <-- CROSS-PIPELINE" if by_name[dep].key != stage.key else ""
            print(f"  {label if index == 0 else '':30} <- {short(dep)}{cross}")

    print("\n=== topological order ===\n")
    order = topological_order([s.qualified_name for s in registry.stages], dependencies)
    for index, name in enumerate(order, start=1):
        print(f"  {index}. {short(name)}")

    print("\n=== per stage: what is exported vs what dies in the pod ===\n")
    for stage in registry.stages:
        internal = sorted(w.name for w in internal_handles(stage))
        exported = sorted(o.obj.name for o in stage.outputs)
        print(
            f"  {short(stage.qualified_name):32} radius={stage.context_radius_m:>7.0f}m"
        )
        print(f"  {'':32} exported : {exported}")
        print(f"  {'':32} internal : {internal}")

    print("\n=== origin (lineage) vs classification (legality) ===\n")
    print(f"  {'object':24} {'origin':34} {'classification'}")
    print(f"  {'-' * 24} {'-' * 34} {'-' * 14}")
    produced = registry.producer_of()
    for obj in produced:
        origin = ", ".join(f"{s.dataset}/{s.scale}" for s in obj.origin)
        cls = classification_of(obj, registry, RULES).value
        print(f"  {obj.name:24} {origin:34} {cls}")

    print("\n  Note `road`: every source in its origin is CLOUD_OK, yet it computes")
    print("  PREM_ONLY - NVDB_Roads reached its stage as CONTEXT and contributed no")
    print("  data, only influence. That divergence is the whole reason origin and")
    print("  classification are separate traversals.\n")

    print("=== publications ===\n")
    for pipeline in (ROAD_N100, BUILDING_N100):
        for publish in pipeline.publishes:
            computed = classification_of(publish.obj, registry, RULES)
            effective = publish.reclassify_to or computed
            marker = "  <-- DECLASSIFIED" if publish.reclassify_to else ""
            print(
                f"  {publish.identity.dataset:22} "
                f"computed={computed.value:10} effective={effective.value}{marker}"
            )

    print("\n=== placement ===\n")
    for pipeline in (ROAD_N100, BUILDING_N100):
        roots = ", ".join(sorted(r.dataset for r in pipeline.external_inputs))
        print(f"  {pipeline.object_name:10} {pipeline_environment(pipeline).value}")
        print(f"  {'':10} derived external inputs: {roots}")

    print("\n=== run selection ===\n")
    requests = [
        ("everything", RunRequest("demo")),
        ("objects={road}", RunRequest("demo", objects=frozenset({ObjectName.ROAD}))),
        (
            "operations={thin_road_network} +DOWNSTREAM",
            RunRequest(
                "demo",
                operations=frozenset({"thin_road_network"}),
                closure=Closure.DOWNSTREAM,
            ),
        ),
        (
            "stages={displacement} +UPSTREAM",
            RunRequest(
                "demo",
                stages=frozenset({"displacement"}),
                closure=Closure.UPSTREAM,
            ),
        ),
    ]
    for label, request in requests:
        selected = select_stages(request, registry)
        ordered = [short(n) for n in order if n in selected]
        print(f"  {label:42} {ordered}")

    print()
    print("  The third selects by OPERATION rather than by object tag, which is")
    print("  sharper for 'we changed a core generalization operation': it reaches")
    print("  building/displacement through the published road product, which an")
    print("  objects={road} filter would have missed entirely.")
    print()


if __name__ == "__main__":
    main()
