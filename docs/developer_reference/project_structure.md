# Project Structure and Extending the Codebase

This document provides an overview of the current project layout and guidance on where to find existing functionality or place new code.

*Note:* The project will be reorganized toward a more standard `src/` layout in the future, but this section describes the structure as it exists today.

## High level project tree structure:
```tree
project_root/
  composition_configs/
  constants/
  custom_tools/
  file_manager/
  generalization/
```


### Composition Configs:
The location for composition configs of methods.
```tree
composition_configs/
  core_config.py
  io_types.py
  logic_config.py
  type_defs.py
  wrapper_config.py
```

- **core_config:** Contains the configs for core project modules such as `PartitionIterator` and `WorkFileManager`. 
- **io_types:** Custom file type definitions (for example Gdb, Lyrx) used for type hinting.
- **logic_config:** Logic configuration objects for specific methods.
When creating a new method configuration, place it here.
- **type_defs:** Custom string subtypes used for typing file paths and similar structures.
- **wrapper_config:** Currently unused. Will be removed or restructured as part of an upcoming refactor.


### Constants:
Reusable constants, SQL queries, predefined values, and small data structures shared across the project.

### Custom Tools:
The location for different re usable methods that used in the project. 

```tree
custom_tools/
  decorators/
  development_tools/
  general_tools/
  generalization_tools/
```

- **decorators:** Decorators used across the project.
- **development_tools:** Tools that assist development (for example helping identify unused FileManager objects).
Not used in runtime pipelines.
- **general_tools:** The location for methods and logic that is reusable regardless of generalization object or scale. 
- **generalization_tools:** The location for reusable method and logic that is object specific.

### File Manager:
The location of the logic of the `BaseFileManager` and `WorkFileManager`, and the enum class feature FileManager for different objects and scales.

```tree
file_manager/
  n100/
  n250/
  base_file_manager.py
  work_file_manager.py
```

- **n100/n250:** Enum classes defining persistent file objects for each scale.
- **base_file_manager:** Centralized logic for constructing file paths.
Handles naming rules, templates, and layout.
- **work_file_manager:** Manages temporary, method-local file paths derived from FileManager objects.

### Generalization:
The location for the different runtimes for the generalization pipelines.
```tree
generalization/
  n100/
  n250/
```

- **n100/ and n250/** These directories contain the complete generalization pipelines for different objects for each scale. Each pipeline includes a main entrypoint (`object_main.py`) and a collection of submodules, where each submodule implements one step of the overall model.


---
### Navigation

- [Developer Reference](index.md)
- [Return to README](../../README.md)
