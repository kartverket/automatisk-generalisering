## Setting up ArcPy python interpreter

Make sure you have ArcGIS Pro installed locally.

1. Locate the ArcGIS Pro install’s Python environment. By default:
```text
C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3\python.exe
```

2. In VS Code: `Ctrl + Shift + P` → `>Python: Select Interpreter` → either choose from the list or enter path manually.

## Ensuring VS Code Recognizes the Project Root

This section covers how to make VS Code correctly resolve relative imports.  

These steps are only needed if VS Code fails to recognize the repository root as the workspace root.

---

### Create or Update `.vscode/settings.json`

1. At the project root, ensure you have a folder named `.vscode/`.  
2. Inside that folder, create or edit a file named `settings.json`.  
3. Add or update the following configuration:

```json
{
  "python.envFile": "${workspaceFolder}/.env",
  "python.analysis.autoSearchPaths": true,
  "python.analysis.extraPaths": [
    "${workspaceFolder}"
  ],
  "python.autoComplete.addBrackets": true,
  "python.analysis.completeFunctionParens": true
}
```


---
### Navigation

- [Setup Guide](docs/setup/index.md)
- [Return to README](README.md)
