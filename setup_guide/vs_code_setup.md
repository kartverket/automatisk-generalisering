# Setting Up VS Code for `automatic-generalization-kv`

## Objective

The objective is to configure Visual Studio Code (VS Code) to recognize the GitHub repository's root directory as the project's root. Additionally, we will import the ArcPy Python environment from ArcGIS Pro into VS Code. 
Lastly we will make sure you have created and set up the config.py file correctly.

#### <u>Note:</u> <i>It's crucial that the file locations and names align exactly with this guide for proper setup.</i>

## Steps to Configure VS Code environment:

### 1. Create or Update VS Code Settings

- Create a `.vscode` folder at the root of your project if it doesn't already exist.
- Inside `.vscode`, create a file named `settings.json` if it's not already there.
- Open `settings.json` and add or update the following content:

```json
{
  "python.envFile": "${workspaceFolder}/.env",
  "python.autoComplete.addBrackets": true,
  "python.analysis.autoSearchPaths": true,
  "python.analysis.useImportHeuristic": true,
  "terminal.integrated.env.windows": {
    "PYTHONPATH": "C:\\example\\path\\to\\the\\project"
  },
  "python.analysis.completeFunctionParens": true
}
  ```
  

This configuration guides VS Code on how to handle Python environments and modules.

### 2. Configure Python Environment Path
- Create a new `.env` file in the project's root directory.
- Locate the root directory of the GIT project and copy its path.
- Paste this path into the `.env` file like so, replacing the example path:

  ```txt
  PYTHONPATH="C:\example\path\to\the\project" 
  ```
  

### 3. Reload VS Code
- To apply these changes, you may need to reload VS Code. Close and re-open VS Code to make sure the changes are loaded in correctly.

## Steps to import ArcPy:

### 1. Locate the Python Interpreter from ArcGIS Pro

- Locate where you have installed ArcGIS Pro and find the Python environment. It should look something similar to below:

  ```txt
  "C:\ArcGIS_Pro\bin\Python\envs\arcgispro-py3\python.exe"
  ```
  
  
### 2. Configure VS Code to Use ArcGIS Pro's Python Interpreter

- In VS Code select the python interpreter used. Press ***(Ctrl+Shift+P)*** and search for `"Python: Select Interpreter"`
- If the python interpreter used by ArcGIS Pro is not suggested Select `"Enter interpreter path..."` and use the path you found previously. Select the python.exe file, and then press "Select interpreter"

### 3. Reload VS Code
- To apply these changes, you may need to reload VS Code. Close and re-open VS Code to make sure the changes are loaded in correctly.

## Creating a config.py file
The config.py file is not tracked by GIT and will contain system specific information to help connect universal scripts with unique system environments.

### 1. Create the config file

- Create a file named `config.py` located in the root directory of your project. 
- Copy the contents of the file `template_config.py` into your newly created `config.py` file.
- Update the paths inside your `config.py` file to match your local environment.

## Testing  that your environment is set up correctly. 

To test that everything is working as intended we can test a little script. Try running the script called `setup_test.py`, located under `automatic-generalization-kv\setup_guide\ `.

- Run the file to test that everyting is set up correctly.
### Interpreting the result

- If you only get print statements like `"Success on file\path\to\data"` then congratulations your setup is complete and you are ready :)
- If you get error message `ModuleNotFoundError: No module named 'config'` or `ModuleNotFoundError: No module named 'environment_setup'` then you have an issue with how you Configured your VS Code environmnet and make sure you followed the steps under **Steps to Configure VS Code environment** correctly.
- If you get an error message with `ModuleNotFoundError: No module named 'arcpy'` then you have an issue with the **Steps to import ArcPy** section and you need to make sure you followed that section correctly.
- If you get no error messages but you get some print statements similar to `"Failed on file\path\to\data"` then you have an error in the path in the config file, however all other environments are set up correctly. Make sure the path follow the template correctly.