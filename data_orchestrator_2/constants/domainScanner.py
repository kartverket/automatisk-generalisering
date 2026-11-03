# Libraries

from collections import defaultdict
from datetime import date

import arcpy

from custom_tools.general_tools.validation import (
    feature_class_exists,
    fetch_existing_fields,
)

######################
# Constants
######################


path = r"C:\GIS_Files\ag_inputs\raw_data\area.gdb\ArealdekkeFlate"
output_path = r"Kolonneanalyse_AG.txt"


######################
# Functionality
######################


def scan_field_values(feature_class: str) -> dict[str, list[str]]:
    """Collect the distinct values registered in each attribute field."""
    if not feature_class_exists(feature_class):
        raise FileNotFoundError(f"Feature class '{feature_class}' does not exist")

    field_names = sorted(field.name for field in fetch_existing_fields(feature_class))
    values: dict[str, set[str]] = defaultdict(set)

    docu = True
    total_rows = int(arcpy.management.GetCount(feature_class)[0])
    n = 0

    print(f"Total rows to process: {total_rows}")

    with arcpy.da.SearchCursor(feature_class, field_names) as cursor:
        for row in cursor:
            if docu:
                n += 1
                if n % 10_000 == 0:
                    print(f"Processed {n} of {total_rows} rows")
            for field_name, value in zip(field_names, row, strict=True):
                values[field_name].add("None" if value is None else str(value))

    return {field_name: list(values[field_name])[:100] for field_name in field_names}


def write_field_values(
    field_values: dict[str, list[str]], feature_class: str, output: str
) -> None:
    """Write each field and its sorted distinct values to a text file."""
    lines: list[str] = [
        f"Rapport generert: {date.today()}",
        f"Feature class: {feature_class}",
    ]

    for field_name in sorted(field_values, key=str.lower):
        sorted_values = sorted(field_values[field_name], key=str.lower)
        lines.append(f"\n{field_name}: {', '.join(sorted_values)}")

    with open(output, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"Rapport skrevet til '{output}'")


def main() -> None:
    field_values = scan_field_values(path)
    write_field_values(field_values, feature_class=path, output=output_path)


if __name__ == "__main__":
    main()
