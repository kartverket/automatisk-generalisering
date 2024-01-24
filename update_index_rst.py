import os

# Define the directory where auto-generated docs are stored
docs_dir = "generated_docs"
# List of .rst files to ignore
ignore_files = ["conf.rst", "update_index_rst.rst"]

# Gather all .rst files in the specified directory, excluding those in ignore_files
entries = [
    "   generated_docs/" + f.replace(".rst", "")  # Maintain indentation for toctree
    for f in os.listdir(docs_dir)
    if f.endswith(".rst") and f not in ignore_files
]

# Join the entries with newlines to form the toctree content
toctree_entries = "\n".join(entries) + "\n"

# Open index.rst to read its contents
with open("index.rst", "r") as file:
    lines = file.readlines()

# Find where the auto-generated toctree section starts and ends based on markers
start_marker = "# Start of auto-generated docs"
end_marker = "# End of auto-generated docs"
start_line = next(i for i, line in enumerate(lines) if start_marker in line) + 1
end_line = next(i for i, line in enumerate(lines) if end_marker in line)


# Remove existing auto-generated toctree entries
del lines[start_line:end_line]

# Insert the new auto-generated toctree entries
lines[start_line:start_line] = [toctree_entries]

# Write the modified contents back to index.rst
with open("index.rst", "w") as file:
    file.writelines(lines)
