
## Testing  that your environment is set up correctly. 

To test that everything is working as intended we can test a little script. Try running the script called `test_setup.py`, located under `root\docs\setup` [test_setup](https://github.com/kartverket/automatisk-generalisering/blob/main/docs/setup/test_setup.py).

- Run the file to test that everyting is set up correctly.
### Interpreting the result

If you only get print statements like `"Success on file\path\to\data"` then congratulations your setup is complete and you are ready :)

- If you get error message similar to `ModuleNotFoundError: No module named 'config'` or `ModuleNotFoundError: No module named 'environment_setup'` then you have an issue with how you Configured your Code environmnet and how your environment handles relative imports from project root.
- If you get an error message with `ModuleNotFoundError: No module named 'arcpy'` then you have an issue with the python interpreter not being set correctly.

Make sure that you have done the [VsCode Arcpy setup](https://github.com/kartverket/automatisk-generalisering/blob/main/docs/setup/vs_code_setup.md) or [Pycharm Arcpy setup](https://github.com/kartverket/automatisk-generalisering/blob/main/docs/setup/pycharm_setup.md) correctly.

- If you get no error messages but you get some print statements similar to `"Failed on file\path\to\data"` then you have an error in the path in the config file, however all other environments are set up correctly. Make sure the path follow the template correctly.


[Navigate back to Setup Guide](https://github.com/kartverket/automatisk-generalisering/tree/main/docs/setup)
