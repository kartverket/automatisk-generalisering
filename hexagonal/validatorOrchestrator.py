# Libraries

import json

from pathlib import Path

##########################
# Classes
##########################


class ValidatorOrchestrator:

    def __init__(self):
        self.step: int = 0
        self.previous_path: Path = None

    def save_validation_results(
        self, results: dict, output_dir: str = "./validation_results"
    ) -> None:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        self.step += 1

        current_path = Path.joinpath(output_dir, f"validation_{self.step}.json")

        payload = {
            "run": self.step,
            "results": results,
            "diff": {},
        }

        if self.previous_path and self.previous_path.exists():
            with open(self.previous_path, "r", encoding="utf-8") as f:
                previous_results = json.load(f)
            previous_results = previous_results.get("results", {})
            payload["diff"] = self.calculate_diff(previous_results, results)

        if payload["diff"]:
            for key in payload["results"]:
                if payload["diff"].get(key):
                    payload["results"][key] = [
                        payload["results"][key],
                        payload["diff"].get(key),
                    ]
                else:
                    payload["results"][key] = payload["results"][key]

        payload.pop("diff", None)

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
            if type(old_value) == type(new_value):
                if isinstance(old_value, int) or isinstance(old_value, float):
                    diff[key] = new_value - old_value
                else:
                    diff[key] = None
            else:
                diff[key] = None

        return diff

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
