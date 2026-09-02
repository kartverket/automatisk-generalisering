import csv
from collections import defaultdict


def sort_results(data: list) -> list:
    return sorted(data, key=lambda x: tuple(x))


def write_to_file(
    data: list,
    filepath: str,
    headers: list[str],
) -> None:
    """
    Write data to a formatted file with arbitrary number of columns.

    Args:
        data: List of tuples with arbitrary number of elements.
              First element is used as group key, last element is count
        filepath: Output file path
        headers: List of column headers (excluding count)
    """
    if not data or headers is None:
        return

    # Calculate number of columns (total elements - 1 for group key)
    num_cols = len(data[0]) - 1

    # If headers don't match data columns (excluding count), adjust
    if len(headers) != num_cols - 1:
        headers = [f"Col{i}" for i in range(1, num_cols)]

    with open(filepath, "w", encoding="utf-8") as f:
        prev_group_key = None

        # Group by first element
        groups = {}
        for row in data:
            group_key = row[0]
            row_data = row[1:]
            groups.setdefault(group_key, []).append(row_data)

        # Calculate column widths for all columns
        col_widths = []
        for col_idx in range(num_cols - 1):
            max_width = len(headers[col_idx])
            for rows_in_group in groups.values():
                for row in rows_in_group:
                    max_width = max(max_width, len(str(row[col_idx])))
            col_widths.append(max_width)

        # Write groups
        for group_key, rows in groups.items():
            # Separator between groups
            if prev_group_key is not None:
                separator = "---+" + "+".join("-" * (w + 2) for w in col_widths) + "+-------\n\n"
                f.write(separator)

            f.write(f"=== {group_key} ===\n")

            # Header row
            header_row = "Nr | " + " | ".join(
                h.ljust(col_widths[i]) for i, h in enumerate(headers)
            ) + " | Count\n"
            f.write(header_row)

            # Header separator
            separator = "---+" + "+".join("-" * (w + 2) for w in col_widths) + "+-------\n"
            f.write(separator)

            # Data rows
            for row_num, row in enumerate(rows, 1):
                row_str = f"{row_num:>2} | " + " | ".join(
                    str(row[col_idx]).ljust(col_widths[col_idx]) for col_idx in range(num_cols - 1)
                ) + f" | {row[-1]}\n"
                f.write(row_str)

            prev_group_key = group_key


def load_rules(csv_path: str, group_by_column: str | None = None) -> tuple[dict, list[str]]:
    rules = defaultdict(list)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames

        # Use provided column or default to first column
        group_key = group_by_column or fieldnames[0]

        for row in reader:
            rules[row[group_key]].append(row)

    return dict(rules), fieldnames
