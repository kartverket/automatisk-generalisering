import os

docs_dir = "generated_docs"
ignore_files = ["conf.rst"]  # conf.py shouldn't be present in generated_docs

entries = [
    "   generated_docs/" + f.replace(".rst", "")
    for f in os.listdir(docs_dir)
    if f.endswith(".rst") and f not in ignore_files
]

toctree_entries = "\n".join(entries) + "\n\n"

with open("index.rst", "r") as file:
    lines = file.readlines()

start_line = None
end_line = None

# Find the toctree directive and the end of its section
for i, line in enumerate(lines):
    if "   :caption: Contents:" in line:
        start_line = i + 1
    elif start_line and (line.strip() == "" or line.startswith("   #")):
        end_line = i
        break

if start_line is not None and end_line is not None:
    # Remove old toctree entries
    del lines[start_line:end_line]
    # Insert new toctree entries
    lines[start_line:start_line] = [toctree_entries]
else:
    print("Error: Could not find the toctree section in index.rst")

# Write the updated content back to index.rst
with open("index.rst", "w") as file:
    file.writelines(lines)
