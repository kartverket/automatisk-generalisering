# Libraries

import arcpy
import os

arcpy.env.overwriteOutput = True

from collections import Counter
from tqdm import tqdm

from composition_configs import core_config, logic_config
from config import attribute_text_file, attribute_csv_file
from custom_tools.decorators.timing_decorator import timing_decorator
from custom_tools.general_tools.partition_iterator import PartitionIterator
from env_setup import environment_setup
from file_manager.n10.file_manager_land_use import Land_use_N10
from generalization.n10.arealdekke.attribute_analyzer import (
    sort_results,
    write_to_file,
    load_rules,
)
from input_data import input_n10, input_n100, input_test_data

# ========================
# Program
# ========================


@timing_decorator
def attribute_changer():
    """
    Main program changing attributes for N10 land use using partition iterator.
    """
    print("\n🚀 Starts changing attribute information for land use (N10)...\n")

    environment_setup.main()

    print("📦 Fetches and prepares data...\n")

    working_fc = input_test_data.arealdekke  # input_n10.arealdekkeflate
    clip_fc = Land_use_N10.attribute_changer__n10_land_use.value
    MUNICIPALITY = None
    new_field = "gammel_arealdekke"
    new_type = "TEXT"

    if MUNICIPALITY:
        clip_data(input_fc=working_fc, output_fc=clip_fc, area=MUNICIPALITY)
        working_fc = clip_fc
        print("\n✅ Data is ready.\n")
    else:
        print("✅ Data is ready.\n")

    partition_area_attribute_changer = prepare_partition_iterator(
        input_fc=working_fc, new_field=new_field, new_type=new_type
    )

    partition_area_attribute_changer.run()

    print("\n🎉 Finished! Attributes are updated and data is processed.\n")


# ========================
# Main functions
# ========================


@timing_decorator
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
    arcpy.management.MakeFeatureLayer(
        input_n100.AdminFlate, clip_lyr, f"NAVN = '{area}'"
    )
    arcpy.analysis.Clip(
        in_features=input_fc,
        clip_features=clip_lyr,
        out_feature_class=output_fc,
    )
    print("📍 Clipping completed.\n")


@timing_decorator
def prepare_partition_iterator(
    input_fc: str, new_field: str, new_type: str
) -> PartitionIterator:
    """
    Initializes the partition iterator with correct configurations.

    Args:
        input_fc (str): The feature class with the input data
        new_field (str): Field name of the new field in the fc to be created
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
                path=Land_use_N10.attribute_changer_output__n10_land_use.value,
            )
        ]
    )

    # Documentation of the partitions
    print("📝 Linking documentation directory...")
    partition_area_io_config = core_config.PartitionIOConfig(
        input_config=partition_area_input_config,
        output_config=partition_area_output_config,
        documentation_directory=Land_use_N10.attribute_changer_documentation__n10_land_use.value,
    )

    # Method Config
    print("🔧 Injecting method configurations...")
    partition_input = core_config.InjectIO(object=arealdekke, tag="input")
    partition_ouput = core_config.InjectIO(object=arealdekke, tag=arealdekke_attributt)

    arealdekke_init_config = logic_config.AttributeChangerInitKwargs(
        input_feature=partition_input,
        output_feature=partition_ouput,
        existing_fields=[f.name for f in arcpy.Describe(input_fc).fields],
        new_field=new_field,
        new_type=new_type,
        work_file_manager_config=core_config.WorkFileConfig(
            root_file=Land_use_N10.attribute_changer_root__n10_land_use.value
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
        root_file=Land_use_N10.attribute_changer_partition_root__n10_land_use.value,
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


@timing_decorator
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
                - existing_fields
                - new_field
                - new_type
                - work_file_manager_config
    """
    print("🔄 Changes land use based on rule set...\n")

    input_fc = init.input_feature
    output_fc = init.output_feature
    existing_fields = init.existing_fields
    new_field = init.new_field
    new_type = init.new_type
    create_new_fc(
        input_fc=input_fc,
        output_fc=output_fc,
        new_field=new_field,
        new_type=new_type,
    )

    print("🔧 Updates 'arealdekke' based on rule set...")

    rule_set = load_rules(attribute_csv_file)

    def match(rule, a, h, u, g):
        return (
            (rule["arealdekke"] == a or rule["arealdekke"] == "*")
            and (rule["hovedklasse"] == h or rule["hovedklasse"] == "*")
            and (rule["underklasse"] == u or rule["underklasse"] == "*")
            and (rule["grunnforhold"] == g or rule["grunnforhold"] == "*")
        )

    def lookup(a, h, u, g):
        if a not in rule_set:
            return a

        for rule in rule_set[a]:
            if match(rule, a, h, u, g):
                return rule["ny_arealdekke"]

        return a

    total_count = int(arcpy.management.GetCount(input_fc)[0])

    relevant_fields = {
        "arealdekke": None,
        "hovedklasse": None,
        "underklasse": None,
        "grunnforhold": None,
    }
    for field in relevant_fields:
        for i, f in enumerate(existing_fields):
            if field in f.lower():
                relevant_fields[field] = i
                break

    control = 0
    attribute_replace = {
        "objectid": "OID@",
        "shape": "SHAPE@"
    }
    keys = attribute_replace.keys()
    for i in range(len(existing_fields)):
        field = existing_fields[i].lower()
        if field in keys:
            existing_fields[i] = attribute_replace[field]
            control += 1
        if control == 2:
            break

    with arcpy.da.SearchCursor(input_fc, existing_fields) as src:
        with arcpy.da.InsertCursor(
            output_fc, existing_fields + [new_field]
        ) as ins:
            for row in tqdm(
                src,
                desc="Rewrites attributes",
                total=total_count,
                colour="yellow",
                leave=False,
            ):
                row = list(row)
                row.append(row[relevant_fields["arealdekke"]])
                row[relevant_fields["arealdekke"]] = lookup(
                    a=row[relevant_fields["arealdekke"]],
                    h=row[relevant_fields["hovedklasse"]],
                    u=row[relevant_fields["underklasse"]],
                    g=row[relevant_fields["grunnforhold"]],
                )
                ins.insertRow(row)

    print("✅ Attributes updated.\n")


# ========================
# Helper functions
# ========================


def create_new_fc(
    input_fc: str, output_fc: str, new_field: str | None, new_type: str | None
):
    """
    Creates a new fc with the same attributes as
    the input, included a new one if desired.

    Args:
        input_fc (str): The feature class with the original table
        output_fc (str): The feature class to create
        new_field (str, optional): Field name of new field to be created (default: None)
        new_type (str, optional): Type of the new field (default: None)
    """
    # 1) Fetch fc setup-data / -details
    print("\n📄 Reading input feature class structure...")
    desc = arcpy.Describe(input_fc)

    # 2) Create new, empty fc
    print(f"🆕 Creating new feature class: {output_fc}")
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
    if new_field and new_type:
        arcpy.management.AddField(
            in_table=output_fc, field_name=new_field, field_type=new_type
        )

    print("✅ Feature class structure ready.\n")


def write_unique_combinations_and_counts_to_file(
    fc: str, attribute_list: list
) -> None:
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

    write_to_file(result, attribute_text_file)

    print("\n📘 Finished writing combinations.\n")


# ========================


if __name__ == "__main__":
    #####################################################
    # Print all unique combinations of 'arealdekke' and
    # 'arealbruk_hovedklasse' along with their counts
    if False:
        write_unique_combinations_and_counts_to_file(
            fc=input_n10.arealdekkeflate,
            attribute_list=[
                "arealdekke",
                "arealbruk_hovedklasse",
                "arealbruk_underklasse",
                "grunnforhold",
            ],
        )
    #####################################################

    attribute_changer()
