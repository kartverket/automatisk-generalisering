"""

import sys
print(f"Python Executable: {sys.executable}")
print(f"Python Version: {sys.version}")

print("sys.path contains:")
for path in sys.path:
    print(f"  - {path}")

import os
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")


print("Imported Modules:")
for module in sorted(sys.modules.keys()):
    print(f"  - {module}")


"""

import sys

 

print(f"Python Executable: {sys.executable}")

 

print(f"Python Version: {sys.version}")

 

 

print("sys.path contains:")

 

for path in sys.path:

    print(f"  - {path}")

 
import os

 

print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'Not set')}")