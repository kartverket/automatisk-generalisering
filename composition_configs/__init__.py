from importlib import import_module

# Order matters: logic_config imports type_defs and io_types from this package
# at module load time, so they must be bound as package attributes first.
core_config = import_module(".core_config", __name__)
type_defs = import_module(".type_defs", __name__)
io_types = import_module(".io_types", __name__)
logic_config = import_module(".logic_config", __name__)

__all__ = ["core_config", "logic_config", "type_defs", "io_types"]
