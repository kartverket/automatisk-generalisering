# Libraries

import os
from pathlib import Path

import arcpy

arcpy.env.overwriteOutput = True

from collections import Counter

from tqdm import tqdm

from composition_configs import core_config, logic_config
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from file_manager.n10.file_manager_arealdekke import Arealdekke_N10
from generalization.n10.arealdekke.overall_tools.attribute_analyzer import (
    load_rules,
    sort_results,
    write_to_file,
)

# ========================
# Program
# ========================


@timing_decorator
def attribute_changer(input_fc: str, output_fc: str):
    """
    Main program changing attributes for N10 land use using partition iterator.
    """
    print("\n🚀 Starts changing attribute information for land use (N10)...\n")

    print("📦 Fetches and prepares data...\n")

    working_fc = input_fc
    clip_fc = Arealdekke_N10.attribute_changer__n10_land_use.value
    MUNICIPALITY = None
    new_fields = ["arealdekke", "fremkommelighet"]
    new_type = "TEXT"

    if MUNICIPALITY:
        clip_data(input_fc=working_fc, output_fc=clip_fc, area=MUNICIPALITY)
        working_fc = clip_fc
    print("✅ Data is ready.\n")

    partition_area_attribute_changer = prepare_partition_iterator(
        input_fc=working_fc, new_fields=new_fields, new_type=new_type, output_fc=output_fc
    )

    partition_area_attribute_changer.run()

    print("\n🎉 Finished! Attributes are updated and data is processed.\n")


# ========================
# Main functions
# ========================


def clip_data(input_fc: str, output_fc: str, area: str) -> None:
    """
    Clips relevant data to desired area.

    Args:
        input_fc (str): Feature class containing the input data
        output_fc (str): Feature class to store the relevant data in
        area (str): Municipality name to clip data to
    """
    print("📥 Reads raw data...")

    print(f"✂️ Clips data according to municipality: {area}")
    clip_lyr = "clip_lyr"
    """arcpy.management.MakeFeatureLayer(
        input_n100.AdminFlate, clip_lyr, f"NAVN = '{area}'"
    )"""
    arcpy.analysis.Clip(
        in_features=input_fc,
        clip_features=clip_lyr,
        out_feature_class=output_fc,
    )
    arcpy.management.Delete(clip_lyr)
    print("📍 Clipping completed.\n")


def prepare_partition_iterator(
    input_fc: str,
    new_fields: list,
    new_type: str,
    output_fc: str,
) -> PartitionIterator:
    """
    Initializes the partition iterator with correct configurations.

    Args:
        input_fc (str): The feature class with the input data
        new_fields (list): List of field name(s) of the new field(s) in the fc to be created
        new_type (str): Field type of the new field in the fc to be created

    Returns:
        PartitionIterator: A PartitionIterator instance modified for attribute modification of land use
    """
    print("⚙️ Initializing partition iterator...")
    print("📥 Loading input configuration...")

    # Constants
    arealdekke = "arealdekke"
    arealdekke_attributt = "arealdekke_attributt"

    # Input data
    print(f"🗂️ Setting up input entry for: {arealdekke}")
    partition_area_input_config = core_config.PartitionInputConfig(
        entries=[
            core_config.InputEntry.processing_input(object=arealdekke, path=input_fc)
        ]
    )

    # Output data
    print(f"📤 Preparing output configuration for: {arealdekke_attributt}")
    partition_area_output_config = core_config.PartitionOutputConfig(
        entries=[
            core_config.OutputEntry.vector_output(
                object=arealdekke,
                tag=arealdekke_attributt,
                path=output_fc,
            )
        ]
    )

    # Documentation of the partitions
    print("📝 Linking documentation directory...")
    partition_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_area_input_config,
        output_config=partition_area_output_config,
        documentation_directory=Arealdekke_N10.attribute_changer_documentation__n10_land_use.value,
    )

    # Method Config
    print("🔧 Injecting method configurations...")
    partition_input = core_config.InjectIO(object=arealdekke, tag="input")
    partition_ouput = core_config.InjectIO(object=arealdekke, tag=arealdekke_attributt)

    arealdekke_init_config = logic_config.AttributeChangerInitKwargs(
        input_feature=partition_input,
        output_feature=partition_ouput,
        new_fields=new_fields,
        new_type=new_type,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Arealdekke_N10.attribute_changer_root__n10_land_use.value
        ),
    )

    print("🧩 Registering attribute changer methods...")
    arealdekke_method = core_config.FuncMethodEntryConfig(
        func=change_attributes, params=arealdekke_init_config
    )

    partition_area_method_config = core_config.MethodEntriesConfig(
        entries=[arealdekke_method]
    )

    # Run Config
    print("🚀 Defining run configuration...")
    partition_area_run_config = core_config.PartitionRunConfig(
        max_elements_per_partition=500_000,
        context_radius_meters=0,
        run_partition_optimization=False,
    )

    # WorkFileConfig:
    print("📁 Setting up workfile configuration...")
    partition_area_workfile_config = core_config.WorkFileConfig(
        root_file=Arealdekke_N10.attribute_changer_partition_root__n10_land_use.value,
    )

    # PartitionIterator Config:
    print("🔄 Creating PartitionIterator instance...")
    partition_area_attribute_changer = PartitionIterator(
        partition_io_config=partition_area_io_config,
        partition_method_inject_config=partition_area_method_config,
        partition_iterator_run_config=partition_area_run_config,
        work_file_manager_config=partition_area_workfile_config,
    )

    print("✅ Partition iterator ready.\n")
    return partition_area_attribute_changer


def change_attributes(init: logic_config.AttributeChangerInitKwargs) -> None:
    """
    Copies all attributes from the input feature class to the output,
    and updates 'arealdekke' based on a specific rules set. The old
    value of 'arealdekke' is kept in the new field 'gammel_arealdekke'.

    Args:
        init (logic_config.AttributeChangerInitKwargs):
            A specific initialization object for partition iterator
            with attribute changer. The element contains:
                - input_feature
                - output_feature
                - new_fields
                - new_type
                - work_file_manager_config
    """
    print("🔄 Changes land use based on rule set...\n")

    input_fc = init.input_feature
    output_fc = init.output_feature
    new_fields = init.new_fields
    new_type = init.new_type

    existing_fields = [
        field.name for field in arcpy.Describe(input_fc).fields
    ]

    create_new_fc(
        input_fc=input_fc,
        output_fc=output_fc,
        new_fields=new_fields,
        new_type=new_type,
    )

    print("🔧 Updates 'arealdekke' based on rule set...")

    rule_set, rule_columns = load_rules(
        Path.joinpath(Path(__file__).parent, "attribute_prioritizing.csv")
    )

    def field_match(rule_value: str, actual_value: str):
        return (
            rule_value == "*"
            or rule_value == actual_value
            or (
                rule_value.endswith("*")
                and actual_value.startswith(rule_value[:-1])
            )
        )
    
    def match(rule, attribute_values):
        return all(
            field_match(rule[col], attribute_values[col])
            for col in rule_columns[:4]
        )

    def lookup(attribute_values):
        a = attribute_values[rule_columns[0]]

        candidate_rules = []
        candidate_rules.extend(rule_set.get(a, []))

        for pattern, rules in rule_set.items():
            if pattern.endswith("*") and a.startswith(pattern[:-1]):
                candidate_rules.extend(rules)

        for rule in candidate_rules:
            if match(rule, attribute_values):
                return [rule[col] for col in rule_columns[4:]]

        return [a, None]

    total_count = int(arcpy.management.GetCount(input_fc)[0])

    relevant_fields = {
        col: None for col in rule_columns[:4]
    }
    for field in relevant_fields:
        for i, f in enumerate(existing_fields):
            if field in f.lower():
                relevant_fields[field] = i
                break

    control = 0
    attribute_replace = {"objectid": "OID@", "shape": "SHAPE@"}
    keys = attribute_replace.keys()
    for i in range(len(existing_fields)):
        field = existing_fields[i].lower()
        if field in keys:
            existing_fields[i] = attribute_replace[field]
            control += 1
        if control == 2:
            break

    with arcpy.da.SearchCursor(input_fc, existing_fields) as src:
        with arcpy.da.InsertCursor(output_fc, existing_fields + new_fields) as ins:
            for row in tqdm(
                src,
                desc="Rewrites attributes",
                total=total_count,
                colour="yellow",
                leave=False,
            ):
                row = list(row)
                land_use, accessibility = lookup({
                    col: row[relevant_fields[col]]
                    for col in rule_columns[:4]
                })
                row.extend([land_use, accessibility])
                ins.insertRow(row)

    print("✅ Attributes updated.\n")


# ========================
# Helper functions
# ========================


def create_new_fc(
    input_fc: str, output_fc: str, new_fields: list = None, new_type: str = None
):
    """
    Creates a new fc with the same attributes as
    the input, included a new one if desired.

    Args:
        input_fc (str): The feature class with the original table
        output_fc (str): The feature class to create
        new_fields (list, optional): List of field name(s) of new field(s) to be created (default: None)
        new_type (str, optional): Type of the new field (default: None)
    """
    # 1) Fetch fc setup-data / -details
    print("\n📄 Reading input feature class structure...")
    desc = arcpy.Describe(input_fc)

    # 2) Create new, empty fc
    print(f"🆕 Creating new feature class:\n  - {output_fc}")
    arcpy.management.CreateFeatureclass(
        out_path=os.path.dirname(output_fc),
        out_name=os.path.basename(output_fc),
        geometry_type=desc.shapeType,
        spatial_reference=desc.spatialReference,
    )
    print("📁 Base feature class created.")

    # 3) Copy fields from input fc
    print("📋 Copying fields from input...\n")
    existing_fields = {f.name.lower() for f in arcpy.Describe(output_fc).fields}

    for field in desc.fields:
        if field.name.lower() not in existing_fields:
            arcpy.management.AddField(
                in_table=output_fc,
                field_name=field.name,
                field_type=field.type,
                field_length=field.length,
                field_precision=field.precision,
                field_scale=field.scale,
            )
            existing_fields.add(field.name.lower())

    # 4) Add new field
    if new_fields and new_type:
        for field in new_fields:
            arcpy.management.AddField(
                in_table=output_fc, field_name=field, field_type=new_type
            )

    print("✅ Feature class structure ready.\n")


def write_unique_combinations_and_counts_to_file(fc: str, attribute_list: list) -> None:
    """
    Prints the unique combinations of specific attributes along
    with the number of features with these combination.

    Args:
        fc (str): Feature class with relevant attributes
        attribute_list (list): List of attributes to compare combinations
    """
    counter = Counter()

    print(f"🔍 Scanning dataset for combinations of {attribute_list}...")

    with arcpy.da.SearchCursor(fc, attribute_list) as cursor:
        for row in cursor:
            counter[tuple(row)] += 1

    print("📑 Counting complete. Writing results...\n")

    result = []

    for combo, count in counter.items():
        r = [c if c else "None" for c in combo] + [count]
        result.append(r)

    result = sort_results(result)

    """
    attribute_text_file = r""
    write_to_file(result, attribute_text_file, attribute_list[1:])
    """

    print("\n📘 Finished writing combinations.\n")


# =======================
# Slett alt under dette
# =======================

def list_feature_classes(folder: str) -> list[str]:
    """Return full paths to all feature classes in a folder or geodatabase."""
    if not arcpy.Exists(folder):
        raise ValueError(f"Folder or geodatabase does not exist: {folder}")

    feature_classes = []
    for directory, _, names in arcpy.da.Walk(folder, datatype="FeatureClass"):
        feature_classes.extend(os.path.join(directory, name) for name in names)

    return feature_classes


if __name__ == "__main__":
    #"""
    folder = r""
    feature_classes = list_feature_classes(folder)
    #"""
    """
    fc = r""
    write_unique_combinations_and_counts_to_file(fc, ["arealdekkeNiva1", "arealdekkeNiva2", "arealbrukLandHovedklasse", "arealbrukLandUnderklasse", "grunnforhold"])
    #"""
    #fc = r"C:\GIS_Files\ag_inputs\raw_data\area.gdb\Arealdekke_Test"
    #"""
    k = 1
    n = len(feature_classes)

    for feature_class in feature_classes:
        print(f"Processing feature class {k}/{n}: {feature_class}")
        attribute_changer(
            input_fc=feature_class,
            output_fc=f"{feature_class}_attributes_changed",
        )
        k += 1
    #"""
