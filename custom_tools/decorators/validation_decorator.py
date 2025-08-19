import inspect
import dataclasses
from typing import Any, Optional, get_type_hints, Type

from composition_configs import core_config
from composition_configs import type_defs


def validate_method_param_class(
    param_dataclass: Type[Any],
    target_callable: Any,
    allowed_type_subs: Optional[dict[type, tuple[type, ...]]] = None,
) -> None:
    if not dataclasses.is_dataclass(param_dataclass):
        raise TypeError(f"{param_dataclass} must be a dataclass")

    param_fields = param_dataclass.__annotations__
    method_sig = inspect.signature(target_callable)
    method_params = method_sig.parameters

    method_param_names = [name for name in method_params if name not in ("self", "cls")]

    method_annots = get_type_hints(target_callable)

    missing = set(method_param_names) - set(param_fields)
    extra = set(param_fields) - set(method_param_names)

    if missing or extra:
        raise ValueError(
            f"Mismatch in param dataclass: missing={missing}, extra={extra}"
        )

    allowed_type_subs = allowed_type_subs or {}

    for field_name in method_param_names:
        method_type = method_annots.get(field_name)
        param_type = param_fields.get(field_name)

        if method_type is None or param_type is None:
            continue

        if param_type == method_type:
            continue

        accepted = allowed_type_subs.get(method_type, ())
        if param_type not in accepted:
            raise TypeError(
                f"Type mismatch for field '{field_name}': "
                f"expected {method_type}, got {param_type}"
            )


def validated_against(target_callable: Any):
    def decorator(cls: type):
        validate_method_param_class(
            param_dataclass=cls,
            target_callable=target_callable,
            allowed_type_subs={
                type_defs.GdbFilePath: (core_config.InjectIO, type_defs.GdbFilePath),
                str: (core_config.InjectIO, str),
            },
        )
        return cls

    return decorator
