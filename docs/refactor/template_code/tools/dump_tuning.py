"""TEMPLATE — not shipped. A dev script; target `tools/`.

Print every resolved config for a scale and object.

    python dump_tuning.py n100 road

WHY THIS IS TEN LINES AND NOT A RESOLVER

Everything in a tuning module is module-level `replace` evaluated at import, so this
READS the answer rather than simulating one. That is the property worth protecting,
and this script is what makes it verifiable rather than aspirational: if anyone ever
adds a `resolve(operation, scale, object)` that walks defaults and overrides, this
stops being a ten-line read of a module and the reason will be obvious.

IT IS ALSO THE ARTIFACT CARTOGRAPHERS AND REVIEWERS WILL USE. "What is N100's road
thinning length" should be answerable without reading Python, and road_n100's Publish
cites two tuning values in its declassification argument - so the resolved values
belong in that review, not just the deltas.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(
    0, str(Path(__file__).resolve().parent.parent)
)  # TEMPLATE: see conftest.py

import argparse
import importlib
import json
from dataclasses import asdict, is_dataclass


def resolved(scale: str, object_name: str) -> dict[str, object]:
    """Every public config in `ag.operations.<object>.tuning.<scale>`, fully resolved.

    `*_BASE` names are skipped: a scale module imports the bases it deltas from, so
    they land in its namespace, and printing them would put two values for the same
    config side by side - exactly the "answered in two places" confusion the
    base-plus-one-delta rule exists to avoid.
    """
    module = importlib.import_module(f"ag.operations.{object_name}.tuning.{scale}")
    return {
        name: asdict(value)
        for name, value in vars(module).items()
        if not name.startswith("_")
        and not name.endswith("_BASE")
        and is_dataclass(value)
        and not isinstance(value, type)
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("scale", help="n50, n100, ...")
    parser.add_argument("object_name", help="road, building, ...")
    args = parser.parse_args()
    print(json.dumps(resolved(args.scale, args.object_name), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
