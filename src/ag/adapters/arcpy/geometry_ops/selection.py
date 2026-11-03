"""The selection group of the ArcPy `GeometryOps`: `select`.

The predicate is checked once against the input's described schema before anything
runs, then compiled to a WHERE clause and handed to the engine's select tool, one call
and no layer state; the TRUE rows are written as a new dataset with fresh native
indices. A table input goes to the table form of the tool. ADR-0019 PC-D15.
"""

from __future__ import annotations

import os

from ag.adapters._shared.preconditions import distinct_paths
from ag.adapters.arcpy._base import ArcpyPortBase
from ag.adapters.arcpy.support.dataset_schema import describe
from ag.adapters.arcpy.support.predicate_compiler import check, where_clause
from ag.core.handles import ScratchHandle
from ag.core.types import DataType
from ag.ports.predicates import Predicate


class Selection(ArcpyPortBase):
    """The selection methods of `GeometryOps`, through the session."""

    def select(
        self, *, input: ScratchHandle, where: Predicate, output: ScratchHandle
    ) -> None:
        """Writes the rows of `input` for which `where` is TRUE to `output`."""
        distinct_paths(handles=(input, output))
        source, target = os.fspath(input), os.fspath(output)
        dataset = describe(self._session, source)
        check(where, dataset=dataset)
        clause = where_clause(where, session=self._session, dataset=dataset)
        if dataset.schema.data_type is DataType.FEATURE_CLASS:
            self._session.run_tool(
                "analysis.Select",
                in_features=source,
                out_feature_class=target,
                where_clause=clause,
            )
        else:
            self._session.run_tool(
                "analysis.TableSelect",
                in_table=source,
                out_table=target,
                where_clause=clause,
            )
