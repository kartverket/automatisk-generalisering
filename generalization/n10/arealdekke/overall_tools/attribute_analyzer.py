import csv
import numpy as np

from collections import defaultdict


def sort_results(data: list) -> list:
    return sorted(data, key=lambda x: (x[0], x[1], x[2], x[3], x[4]))


def write_to_file(data: list, filepath: str) -> None:
    with open(filepath, "w", encoding="utf-8") as f:
        prev_w1 = None
        type_count = 1

        groups = {}
        for w1, w2, w3, w4, c in data:
            groups.setdefault(w1, []).append((w2, w3, w4, c))

        for w1, rows in groups.items():
            max_w2 = max(max(len(r[0]) for r in rows), len("Hovedklasse"))
            max_w3 = max(max(len(r[1]) for r in rows), len("Underklasse"))
            max_w4 = max(max(len(r[2]) for r in rows), len("Grunnforhold"))

            if prev_w1 is not None:
                f.write(
                    f"---+"
                    f"{'-' * (max_w2 + 2)}+"
                    f"{'-' * (max_w3 + 2)}+"
                    f"{'-' * (max_w4 + 2)}+"
                    f"-------\n\n"
                )

            f.write(f"=== {w1} ===\n")

            f.write(
                f"Nr | "
                f"Hovedklasse".ljust(max_w2)
                + " " * (np.abs(len("Hovedklasse") - max_w2) - 1)
                + " | "
                f"Underklasse".ljust(max_w3)
                + " " * (np.abs(len("Underklasse") - max_w3) - 2)
                + " | "
                f"Grunnforhold".ljust(max_w4)
                + " " * (np.abs(len("Grunnforhold") - max_w4) - 1)
                + " | "
                f"Count\n"
            )

            f.write(
                f"---+"
                f"{'-' * (max_w2 + 2)}+"
                f"{'-' * (max_w3 + 2)}+"
                f"{'-' * (max_w4 + 2)}+"
                f"-------\n"
            )

            type_count = 1
            for w2, w3, w4, c in rows:
                f.write(
                    f"{type_count:>2} | "
                    f"{w2.ljust(max_w2)} | "
                    f"{w3.ljust(max_w3)} | "
                    f"{w4.ljust(max_w4)} | "
                    f"{c}\n"
                )
                type_count += 1

            prev_w1 = w1


def load_rules(csv_path: str) -> dict:
    rules = defaultdict(list)

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rules[row["arealdekke"]].append(row)

    return dict(rules)
