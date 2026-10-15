"""Example of redirecting a runtime dataset to a geoprocessing output."""

import arcpy

from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from data_orchestrator_2.runtime.pipeline import Pipeline


def main() -> None:
    """Copy a dataset, update its runtime path, and validate the output."""
    pipeline = Pipeline(ObjectType.ROAD, Scale.N100)

    pipeline.validInput()

    print(pipeline)

    if pipeline.error or pipeline.warning:
        if pipeline.error:
            pipeline.errorReport()
        if pipeline.warning:
            pipeline.warningReport()
        return

    output_path = r"C:\GIS_Files\ag_outputs\n100\road.gdb\road_input"

    if arcpy.Exists(output_path):
        print(f"\nDeleting existing output at {output_path}\n")
        arcpy.management.Delete(output_path)

    dataset = pipeline.getDataset(FeatureClassName.ELVEG_AND_STI)
    arcpy.management.CopyFeatures(dataset.path, output_path)
    dataset.set_path(output_path)

    pipeline.validProcessing()

    print(pipeline)

    if pipeline.error or pipeline.warning:
        if pipeline.error:
            pipeline.errorReport()
        if pipeline.warning:
            pipeline.warningReport()
        return

    return


"""
    dataset = pipeline.datasets[FeatureClassName.ELVEG_AND_STI]
    fields = dataset.definition.getFieldsFor(FieldUsage.INPUT)
    field_names = ", ".join(field.name.value for field in fields)
    print(f"{dataset.definition.name.value}: {dataset.path}")
    print(f"Input fields: {field_names}")

    for result in validate_pipeline(pipeline, FieldUsage.INPUT):
        print(result)

    output_path = r"..."

    if arcpy.Exists(output_path):
        arcpy.management.Delete(output_path)

    arcpy.management.CopyFeatures(dataset.path, output_path)
    dataset.set_path(output_path)

    fields = dataset.definition.getFieldsFor(FieldUsage.PROCESSING)
    field_names = ", ".join(field.name.value for field in fields)
    print(f"{dataset.definition.name.value}: {dataset.path}")
    print(f"Processing fields: {field_names}")

    for result in validate_pipeline(pipeline, FieldUsage.PROCESSING):
        print(result)

    fm.remove_none_geometry(dataset=dataset)
    fm.clean_columns(dataset=dataset, usage=FieldUsage.PROCESSING)
"""

if __name__ == "__main__":
    main()
