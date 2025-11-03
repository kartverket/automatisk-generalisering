from importlib import import_module

core_config = import_module(".core_config", __name__)
logic_config = import_module(".logic_config", __name__)
type_defs = import_module(".type_defs", __name__)
io_types = import_module(".io_types", __name__)

__all__ = ["core_config", "logic_config", "type_defs", "io_types"]
