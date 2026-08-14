from __future__ import annotations

from composition_configs.logic_config import DataRef, DataRefTag


def is_gs_path(path: str) -> bool:
    return path.startswith("gs://")


def is_s3_path(path: str) -> bool:
    return path.startswith("s3://")


def is_cloud_path(path: str) -> bool:
    return is_gs_path(path) or is_s3_path(path)


def validate_dataref_for_environment(data_ref: DataRef, environment: str) -> None:
    if environment == "on_cloud" and data_ref.tag is DataRefTag.PREM_ONLY:
        raise ValueError(
            f"DataRef path '{data_ref.path}' tagged PREM_ONLY cannot be used in on_cloud mode"
        )

    if environment == "on_prem" and is_gs_path(data_ref.path):
        raise ValueError(
            f"DataRef path '{data_ref.path}' uses gs:// which is not valid in on_prem mode"
        )

    if environment == "on_cloud" and is_s3_path(data_ref.path):
        raise ValueError(
            f"DataRef path '{data_ref.path}' uses s3:// which is not valid in on_cloud mode"
        )


def validate_environment(environment: str) -> None:
    if environment not in {"on_prem", "on_cloud"}:
        raise ValueError(
            "ENVIRONMENT must be one of: on_prem, on_cloud. "
            f"Got: {environment}"
        )
