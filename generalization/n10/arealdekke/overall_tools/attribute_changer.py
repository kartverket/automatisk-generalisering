# Libraries

import os
from pathlib import Path

import arcpy

arcpy.env.overwriteOutput = True

from collections import Counter

from tqdm import tqdm

from custom_tools.decorators.timing_decorator import timing_decorator
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
    new_fields = ["arealdekke", "fremkommelighet"]
    new_type = "TEXT"

    print("✅ Data is ready.\n")

    create_new_fc(
        input_fc=input_fc,
        output_fc=output_fc,
        new_fields=new_fields,
        new_type=new_type,
    )

    change_attributes(
        input_fc=working_fc,
        output_fc=output_fc,
        new_fields=new_fields,
    )

    print("\n🎉 Finished! Attributes are updated and data is processed.\n")


# ========================
# Main functions
# ========================


def change_attributes(input_fc: str, output_fc: str, new_fields: list) -> None:
    """
    Copies all attributes from the input feature class to the output,
    and updates 'arealdekke' based on a specific rules set. The old
    value of 'arealdekke' is kept in the new field 'gammel_arealdekke'.

    Args:
        input_fc (str): Input feature class
        output_fc (str): Output feature class
        new_fields (list): List of new fields to be added and updated
    """
    print("🔄 Changes land use based on rule set...\n")

    if not arcpy.Exists(input_fc):
        raise ValueError(f"Input feature class does not exist: {input_fc}")
    if not arcpy.Exists(output_fc):
        raise ValueError(f"Output feature class does not exist: {output_fc}")

    existing_fields = [
        field.name for field in arcpy.Describe(input_fc).fields
    ]

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

    # Map rule column names to field indices
    relevant_fields = {}
    for rule_col in rule_columns[:4]:
        field_idx = None
        for i, f in enumerate(existing_fields):
            if rule_col.lower() in f.lower():
                field_idx = i + 1  # +1 because SHAPE@ is at index 0
                break
        if field_idx is None:
            raise ValueError(f"Required field '{rule_col}' not found in input feature class. Available fields: {existing_fields}")
        relevant_fields[rule_col] = field_idx

    # Include SHAPE@ to copy geometry to the output feature class
    cursor_fields = ["SHAPE@"] + existing_fields

    try:
        with arcpy.da.SearchCursor(input_fc, cursor_fields) as src:
            with arcpy.da.InsertCursor(output_fc, cursor_fields + new_fields) as ins:
                for row in tqdm(
                    src,
                    desc="Rewrites attributes",
                    total=total_count,
                    colour="yellow",
                    leave=False,
                ):
                    row = list(row)
                    # Build attribute values dictionary for lookup
                    attribute_values = {
                        col: row[relevant_fields[col]]
                        for col in rule_columns[:4]
                    }
                    land_use, accessibility = lookup(attribute_values)
                    row.extend([land_use, accessibility])
                    ins.insertRow(row)
    except Exception as e:
        print(f"❌ Error during attribute processing: {e}")
        raise

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
    system_fields = {"objectid", "shape", "shape_length", "shape_area"}
    
    for field in desc.fields:
        if field.name.lower() not in system_fields:
            arcpy.management.AddField(
                in_table=output_fc,
                field_name=field.name,
                field_type=field.type,
                field_length=field.length,
                field_precision=field.precision,
                field_scale=field.scale,
            )

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
