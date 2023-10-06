# Setting Up VS Code for `kv_git_projects`

## Objective

The aim of this documentation is to guide you through the process of setting up VS Code to recognize Python modules in the `kv_git_projects` repository for better IntelliSense and code completion.

## Steps

### 1. Open the Project in VS Code

- Navigate to the project root folder (`kv_git_projects`) and open it with VS Code.

### 2. Install Required Extensions

- Make sure to have the Python extension for Visual Studio Code installed. You can find it by searching for "Python" in the Extensions Marketplace.

### 3. Set Python Interpreter

- Use the Command Palette (`Ctrl+Shift+P`) and type `Python: Select Interpreter`. Choose the Python interpreter you're using for this project.

### 4. Configure Workspace Settings

- Create a `.vscode` folder at the root of your project if it doesn't already exist.
- Inside `.vscode`, create a file named `settings.json` if it's not already there.
- Open `settings.json` and add the following:

  ```json
  {
    "python.autoComplete.extraPaths": ["./"],
    "python.analysis.extraPaths": ["./"]
  }

This tells VS Code where to look for your custom modules.

### 5. Reload Window
- You may need to reload the VS Code window for changes to take effect. Use the Command Palette (Ctrl+Shift+P) and type Reload Window.