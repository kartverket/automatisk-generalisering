from dataclasses import is_dataclass, asdict
from typing import Any, Mapping, Optional, Union, Dict, List, Sequence
import inspect

from composition_configs import core_config


def _ensure_str_keys(m: Mapping[Any, Any]) -> None:
    bad = [type(k).__name__ for k in m.keys() if not isinstance(k, str)]
    if bad:
        raise TypeError(f"kwargs keys must be str; got non-str keys: {bad[:3]}...")


def to_kwargs_or_empty(obj: Optional[Union[Mapping[str, Any], Any]]) -> Dict[str, Any]:
    """
    Coerce params to a **kwargs-compatible dict.
    - None -> {}
    - dataclass -> asdict(...)
    - Mapping -> must have str keys
    """
    if obj is None:
        return {}
    if is_dataclass(obj) and not isinstance(obj, type):
        d = asdict(obj)
        _ensure_str_keys(d)
        return d
    if isinstance(obj, Mapping):
        _ensure_str_keys(obj)
        return dict(obj)
    raise TypeError(f"Expected mapping-like params, got {type(obj).__name__}")


def _is_dc_instance(x: Any) -> bool:
    return is_dataclass(x) and not isinstance(x, type)


def ensure_dataclass_list(params: core_config.ParamPayload) -> List[Any]:
    """
    Accept only:
      - None -> []
      - dataclass instance -> [instance]
      - (list|tuple) of dataclass instances -> list(instances)
    Everything else -> TypeError
    """
    if params is None:
        return []

    if _is_dc_instance(params):
        return [params]

    if isinstance(params, (list, tuple)):
        items = list(params)
        if not all(_is_dc_instance(it) for it in items):
            bad = [type(it).__name__ for it in items if not _is_dc_instance(it)][:3]
            raise TypeError(
                f"Only dataclass instances allowed as positional params; got {bad}..."
            )
        return items

    raise TypeError(
        f"Params must be dataclass instance(s); got {type(params).__name__}"
    )


def validate_positional_arity(fn: Any, n: int, *, allow_varargs=True) -> None:
    """
    Ensure `fn` can accept `n` positional args (ignoring 'self').
    """
    sig = inspect.signature(fn)
    params = [p for name, p in sig.parameters.items() if name != "self"]
    pos_ok = 0
    has_varargs = False
    for p in params:
        if p.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        ):
            pos_ok += 1
        elif p.kind == inspect.Parameter.VAR_POSITIONAL:
            has_varargs = True
    if n <= pos_ok:
        return
    if allow_varargs and has_varargs:
        return
    raise TypeError(
        f"{getattr(fn,'__name__',fn)} does not accept {n} positional dataclass arg(s)"
    )


def _dc_to_log_dict(dc: Any, jsonifier) -> Dict[str, Any]:
    """
    Log-friendly serialization:
      { "__dataclass__": "ClassName", "fields": {k: jsonified(v), ... } }
    """
    d = asdict(dc)
    return {
        "config_class": type(dc).__name__,
        "arguments": {k: jsonifier(v) for k, v in d.items()},
    }


def payload_log(
    params: core_config.ParamPayload, jsonifier
) -> Optional[List[Dict[str, Any]]]:
    """
    Return a list of dataclass-log dicts (or None).
    """
    dcs = ensure_dataclass_list(params)
    if not dcs:
        return None
    return [_dc_to_log_dict(dc, jsonifier) for dc in dcs]
