import pyperclip
import re

DRIVE_PATTERN = r"[a-zA-Z]:\\"
FILENAME_PATTERN = r'[^\\]+?\.\w+"?'
PATH_MIDDLE_PLACEHOLDER = r"path\\"


def replace_file_paths_in_text(text):
    """Function to replace file paths in the input text with placeholders."""

    # Regex to match the drive letter, intermediate directories, and the final filename with extension
    pattern = re.compile(f"({DRIVE_PATTERN}).*?({FILENAME_PATTERN})")
    return pattern.sub(replace_path_middle_with_placeholder, text)


def replace_path_middle_with_placeholder(matchobj):
    """Replace the middle part of the file path with 'path\\'."""

    drive_letter = matchobj.group(1)
    filename = matchobj.group(2)
    return f"{drive_letter}{PATH_MIDDLE_PLACEHOLDER}{filename}"


if __name__ == "__main__":
    # Gets the text from the clipboard
    input_text = pyperclip.paste()

    # Replacing paths in the input text
    output_text = replace_file_paths_in_text(input_text)

    # Replaces the clipboard content with the modified text
    pyperclip.copy(output_text)

    print(f"Modified output sent to clipboard:\n\n{output_text}")
