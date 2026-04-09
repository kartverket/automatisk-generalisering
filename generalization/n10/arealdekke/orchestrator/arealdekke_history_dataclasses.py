import yaml
from pydantic.dataclasses import dataclass
from dataclasses import asdict
from pydantic import field
from typing import (
    Dict,
    List,
    Optional,
    Tuple,
    Union,
    Any,
)


@dataclass
class Categories_progress:
    title: str
    accessibility: bool
    completed_operations: list
    path_processed_data: str


@dataclass
class Arealdekke_progress:
    file_path: str
    preprocessing_completed: list
    categories: list[Categories_progress] = field(default_factory=list)


def load_yaml(path: str) -> dict:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def save_yaml(path: str, data: dict) -> None:
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, allow_unicode=True)


def append_arealdekke(yaml_path: str, new_entry: Arealdekke_progress) -> None:
    existing = load_yaml(yaml_path)

    # Ensure the top-level key exists
    if "arealdekke" not in existing:
        existing["arealdekke"] = []

    # Convert dataclass → dict and append
    existing["arealdekke"].append(asdict(new_entry))

    save_yaml(yaml_path, existing)
