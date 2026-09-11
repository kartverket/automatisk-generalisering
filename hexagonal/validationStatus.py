# Libraries

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum

##########################
# Classes
##########################


class Severity(StrEnum):
    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class Rule:
    key: str
    operator: str
    value: float | int | bool | list[float]
    severity: Severity | list[Severity]

    def __post_init__(self):
        if isinstance(self.value, list):
            if not isinstance(self.severity, list):
                raise ValueError("List value requires list severity")
            if len(self.severity) != len(self.value) + 1:
                raise ValueError("Need one more severity than thresholds")


OPERATORS = {
    "eqn": lambda d, v: d["new"] == v,
    "eqd": lambda d, v: d["diff"] == v,
    "neq": lambda d, v: d["new"] != v,
    "gt": lambda d, v: d["new"] > v,
    "lt": lambda d, v: d["new"] < v,
    "ratio_gt": lambda d, v: abs(d["ratio"]) > v,
    "ratio_lt": lambda d, v: abs(d["ratio"]) < v,
}


class ValidationStatus:

    def __init__(self):
        self.permanent_rules: list[Rule] = []
        self.temporary_rules: list[Rule] = []

    ##########################
    # Constants
    ##########################

    STATUS_SEVERITY = (Severity.SUCCESS, Severity.WARNING, Severity.ERROR)

    ##########################
    # Main function
    ##########################

    def add_permanent_rule(self, rule: Rule | list[Rule]) -> None:
        if isinstance(rule, list):
            self.permanent_rules.extend(rule)
        else:
            self.permanent_rules.append(rule)

    def remove_permanent_rule(self, rule: Rule) -> None:
        if rule in self.permanent_rules:
            self.permanent_rules.remove(rule)

    def add_temporary_rule(self, rule: Rule | list[Rule]) -> None:
        if isinstance(rule, list):
            self.temporary_rules.extend(rule)
        else:
            self.temporary_rules.append(rule)

    def remove_temporary_rules(self) -> None:
        self.temporary_rules.clear()

    ##########################
    # Main validation
    ##########################

    def status_update(self, stats: dict) -> tuple[Counter, str]:
        status = Counter()
        messages = defaultdict(list)

        for rule in self.permanent_rules + self.temporary_rules:
            data = stats.get(rule.key)

            if data is None:
                severity = Severity.ERROR
                status[severity] += 1
                messages[severity].append(
                    f"{severity}: Missing data for key '{rule.key}'"
                )
                continue
            elif data.get("changed_type"):
                severity = Severity.ERROR
                status[severity] += 1
                messages[severity].append(
                    f"{severity}: Changed type for key '{rule.key}'"
                )
                continue

            for value in self._iter_rule_data(data):
                severity = self._evaluate_rule(rule, value)
                status[severity] += 1
                if severity != Severity.SUCCESS:
                    messages[severity].append(self._get_message(rule, severity))

        self.remove_temporary_rules()

        return status, self._most_severe_status(status), dict(messages)

    ##########################
    # Helper functions
    ##########################

    def _iter_rule_data(self, data):
        if any(isinstance(v, dict) for v in data.values()):
            yield from data.values()
        else:
            yield data

    def _evaluate_rule(self, rule: Rule, data: dict) -> Severity:
        if rule.operator == "ratio":
            ratio = abs(data.get("ratio", 0))
            for threshold, severity in zip(rule.value, rule.severity[:-1]):
                if ratio < threshold:
                    return severity

            return rule.severity[-1]

        passed = OPERATORS[rule.operator](data, rule.value)

        if passed:
            return Severity.SUCCESS

        return rule.severity

    def _get_message(self, rule: Rule, severity: str) -> str:
        return f"{severity}: Rule '{rule.key}' failed"

    def _most_severe_status(self, status: Counter) -> str:
        for label in reversed(self.STATUS_SEVERITY):
            if status[label] > 0:
                return label
        return Severity.SUCCESS
