"""Example of redirecting a runtime dataset to a geoprocessing output."""

import arcpy

import data_orchestrator_2.fieldManager as fm
from data_orchestrator_2.constants.common import Scale
from data_orchestrator_2.constants.featureClasses import FeatureClassName, ObjectType
from data_orchestrator_2.runtime.pipeline import Pipeline
from data_orchestrator_2.schemas.fields import FieldUsage
from data_orchestrator_2.schemas.pipelines import get_pipeline
from data_orchestrator_2.validator import validate_pipeline


def main() -> None:
    """Copy a dataset, update its runtime path, and validate the output."""
    pipeline = Pipeline(get_pipeline(ObjectType.ROAD, Scale.N100))

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


if __name__ == "__main__":
    main()
