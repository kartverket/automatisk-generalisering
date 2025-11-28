# Runtime Entrypoints

This section describes how runnable scripts in the project should be structured.

### 1. Running `environment_setup`
Every script that is meant to be run directly must import and execute the `environment_setup.main()` module before using any project functionality.

### 2. Use the `if __name__ == "__main__"` convetion
All code entry points must be placed in standard Python guard.

```Python
if __name__ == "__main__":
      main()
```

No logic should run on import

### 3. Use `main()` as an entrypoint
An entrypoint should define a `main()` function. 

```Python
from env_setup import environment_setup

def main():
      environment_setup.main()
      some_model()

  if __name__ == "__main__":
      main()
```
```
