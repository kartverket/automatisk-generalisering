# Libraries

from collections import Counter, defaultdict
from dataclasses import dataclass
from enum import StrEnum

##########################
# Classes
##########################


class Severity(StrEnum):
    """Different statuses that a processed feature class can have"""

    SUCCESS = "SUCCESS"
    WARNING = "WARNING"
    ERROR = "ERROR"


@dataclass
class Rule:
    """
    Represents how a characteristic of a feature class should be validated.

    The key describes the characteristic that should be tested for the feature
    class being validated. Value is the different threshold values used to
    determine the status of the control, and severity describes of which level
    the feature class is qualified according to this rule.
    """

    key: str
    operator: str
    value: float | int | bool | list[float]
    severity: Severity | list[Severity]

    def __post_init__(self):
        if isinstance(self.value, list):
            if not isinstance(self.severity, list):
                raise ValueError(
                    f"List value requires list severity\n{self.key} - {self.operator}"
                )
            if len(self.severity) != len(self.value) + 1:
                raise ValueError(
                    f"Need one more severity than thresholds\n{self.key} - {self.operator}"
                )


# Operators used during evalutaion of specific rules
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
        """
        Permanent rules are rules that should be applied for the entire pipeline of a feature class, or larger parts of it
        Temporary rules are rules that should only be applied for a specific task of the pipeline, f.ex. a function that should change the feature class significantly
        """
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

    def status_update(self, stats: dict) -> tuple[Counter, str, dict]:
        """
        Validates the status of the feature class depending on the provided statistics

        Args:
            stats (dict): Dictionary describing changes in the feature class

        Returns:
            - status (Counter): Number of occurrences for each severity level
            - most_severe (str): The most severe status encountered
            - messages (dict): Dictionary containing messages for each severity level
                (if any messages exist for that severity)
        """
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

            try:
                is_dict = (
                    True if isinstance(data[list(data.keys())[0]], dict) else False
                )
            except Exception:
                is_dict = False

            if data.get("changed_type"):
                severity = Severity.ERROR
                status[severity] += 1
                messages[severity].append(
                    f"{severity}: Changed type for key '{rule.key}'"
                )
                continue

            for value in self._iter_rule_data(data):
                category = self._get_key(data, value) if is_dict else None
                severity = self._evaluate_rule(rule, value)
                status[severity] += 1
                if severity != Severity.SUCCESS:
                    messages[severity].append(
                        self._get_message(rule, severity, category)
                    )

        self.remove_temporary_rules()

        return status, self._most_severe_status(status), dict(messages)

    ##########################
    # Helper functions
    ##########################

    def _iter_rule_data(self, data: dict):
        if any(isinstance(v, dict) for v in data.values()):
            yield from data.values()
        else:
            yield data

    def _get_key(self, data: dict, value: dict) -> str | None:
        for k, v in data.items():
            if v == value:
                return k
        return None

    def _evaluate_rule(self, rule: Rule, data: dict) -> Severity:
        """
        Evaluates a rule against the provided data and returns the corresponding severity
        """
        if (
            rule.operator == "ratio"
            and isinstance(rule.value, list)
            and isinstance(rule.severity, list)
        ):
            ratio = abs(data.get("ratio", 0))
            for threshold, severity in zip(rule.value, rule.severity[:-1]):
                if ratio < threshold:
                    return severity

            return rule.severity[-1]

        if isinstance(rule.severity, list):
            return rule.severity[0]

        passed = OPERATORS[rule.operator](data, rule.value)

        if passed:
            return Severity.SUCCESS

        return rule.severity

    def _get_message(
        self, rule: Rule, severity: str, category: str | None = None
    ) -> str:
        """
        Creates a message describing a warning or error that occured
        during processing of a feature class, and where it occured
        """
        warning_message = (
            "triggered a warning"
            if severity == Severity.WARNING
            else "failed validation"
        )
        if category:
            return (
                f"{severity}: '{rule.key}' {warning_message} for category '{category}'"
            )
        return f"{severity}: '{rule.key}' {warning_message}"

    def _most_severe_status(self, status: Counter) -> str:
        """Returns the most severe status occuring during processing of a feature class"""
        for label in reversed(self.STATUS_SEVERITY):
            if status[label] > 0:
                return label
        return Severity.SUCCESS
