# IO (Input/Output) and File Management

This section explains how input and output file handling is organized in the project.
The goal is to ensure consistent, refactor-friendly IO across all modules.

## File Manager Responsibilities

### BaseFileManager
Responsible for **constructing file paths**.
It contains the logic that defines how paths are built (templates, naming rules, folder layouts).
By centralizing this, file location changes or new file types can be introduced without modifying processing code.

### FileManager
A collection of enum classes (for example `Road_N100`) representing **persistent, project-level files**.
Each enum entry defines a file whose lifetime extends beyond a single method and can be accessed across different models, scripts, or execution stages.
These entries wrap fully defined file objects created through `BaseFileManager`.

### WorkFileManager
Responsible for **method-local** files.
It creates temporary or intermediate paths derived from a `FileManager` reference. These files only exist within the scope of a single method call.

### Scope, not storage type
Both managers may reference temporary memory-based or disk-based files.
The distinction is **scope** not storage:

- `FileManager` → global / persistent files
- `WorkFileManager` → local / temporary / method-scoped files

In short:
- `FileManager` = files that exist **between** methods.
- `WorkFileManager` = files that exist **inside** methods.

## IO Practices

- **No hardcoded paths**
  Do not create string paths directly.
    All IO must go through `FileManager` (persistent) or `WorkFileManager` (intermediate).

- **Pass file objects, not strings**
  Methods receive file objects, not literal paths.
  This ensures consistent path handling and avoids environment-specific issues.

---
### Navigation

- [Developer Reference](docs/developer_reference/index.md)
- [Return to README](README.md)
