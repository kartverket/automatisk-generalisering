# Libraries

import json

from pathlib import Path
from collections import Counter

##########################
# Classes
##########################


class ValidatorOrchestrator:

    #TODO: Legge til og fjerne permanente og midlertidige regler

    ##########################
    # Constants
    ##########################

    STATUS_SEVERITY = ("SUCCESS", "WARNING", "ERROR")
    STATUS_THRESHOLDS = (
        (0.3, "SUCCESS"),
        (0.6, "WARNING"),
    )

    ##########################
    # Main functions
    ##########################

    def __init__(self, scale: str):
        self.scale: str = scale
        self.step: int = 0
        self.previous_path: Path = None

    def save_validation_results(
        self, results: dict, output_dir: str = "./validation_results"
    ) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.step += 1

        current_path = Path.joinpath(output_dir, f"validation_{self.step}.json")

        difference = {}
        if self.previous_path and self.previous_path.exists():
            with open(self.previous_path, "r", encoding="utf-8") as f:
                previous_payload = json.load(f)
            previous_results = previous_payload.get("results", {})
            difference = self.calculate_diff(previous_results, results)
            status_counter, overall_status = self.status_update(
                previous_results, difference
            )
        else:
            status_counter, overall_status = Counter(), "SUCCESS"

        payload = {
            "run": self.step,
            "status": overall_status,
            "status_counts": dict(status_counter),
            "results": results,
            "difference": difference,
        }

        with open(current_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        self.previous_path = current_path

    def calculate_diff(
        self,
        previous: dict,
        current: dict,
    ) -> dict:
        diff = {}

        all_keys = set(previous.keys()) | set(current.keys())

        for key in all_keys:
            old_value = previous.get(key)
            new_value = current.get(key)
            if type(new_value) not in (int, float, dict):
                continue
            if type(old_value) == type(new_value):
                if isinstance(old_value, (int, float)):
                    diff[key] = new_value - old_value
                elif isinstance(old_value, dict):
                    diff[key] = self.calculate_diff(old_value, new_value)

        return diff

    def status_update(self, previous: dict, difference: dict) -> tuple[Counter, str]:
        all_keys = set(previous.keys()) | set(difference.keys())

        status = Counter()

        for key in all_keys:
            old_value = previous.get(key)
            new_value = difference.get(key)
            if type(old_value) != type(new_value):
                continue

            if isinstance(old_value, (int, float)):
                ratio = new_value / old_value if old_value != 0 else 0
                status[self._classify_ratio(ratio)] += 1
            elif isinstance(old_value, dict):
                nested_status, _ = self.status_update(old_value, new_value)
                status.update(nested_status)

        return status, self._most_severe_status(status)

    def class_branch(self, cls):
        path = [cls]
        current = cls

        while current.__bases__ and current.__bases__[0] is not object:
            current = current.__bases__[0]
            path.append(current)

        path.reverse()

        result = [c.__name__ for c in path]

        current_level = [cls]

        while current_level:
            next_level = []
            for node in current_level:
                next_level.extend(node.__subclasses__())

            if next_level:
                result.extend([c.__name__ for c in next_level])
            current_level = next_level

        return result

    ##########################
    # Helper functions
    ##########################

    def _classify_ratio(self, ratio: float) -> str:
        for threshold, label in self.STATUS_THRESHOLDS:
            if ratio < threshold:
                return label
        return "ERROR"

    def _most_severe_status(self, status: Counter) -> str:
        for label in reversed(self.STATUS_SEVERITY):
            if status[label] > 0:
                return label
        return "SUCCESS"
