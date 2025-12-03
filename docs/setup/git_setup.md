## Overview
This guide explains how to install Git in detail (if needed) and clone the repository.  
If you are familiar with Git: the project uses a **standard Git setup** — simply clone the repository and disregard the rest of the Git setup guide.

```bash
git clone https://github.com/kartverket/automatisk-generalisering.git <local_path>
```

### 1. Install Git
- For team members at Kartverket, you'll need to use `Firmaportal` to get the software.
  - Search for `GIT` in `Firmaportal`.
  - Install `The Git Development Community - Git (x64)`.

### 2. Verify the Installation:
Open a terminal or IDE terminal and run:
```bash
git --version
```

If Git is correctly installed, the version number will be shown (e.g., git version 2.46.0).

If you see git is not recognized..., reinstall Git or ensure its binary directory is added to your system PATH. You might need to restart the computer after installation.

### 3. Configure Your User information:
If this is your first Git setup, set your username and email:

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

You can check current settings with:
```bash
git config --list
```

### 4. Clone the Repository:
Choose or create a folder where you want to keep the repository and navigate to it in the terminal:
```bash
cd <your_parent_directory>
git clone https://github.com/kartverket/automatisk-generalisering.git
```

If you prefer, you can clone the repository directly from VS Code or PyCharm instead of using the terminal:

- **VsCode**:
  * Open the Command Palette `(Ctrl + Shift + P)`.
  * Run “Git: Clone”, paste the repository URL: `https://github.com/kartverket/automatisk-generalisering.git`
  * Choose a destination folder when prompted 

- **PyCharm**:
  * On the Welcome screen, select “Get from VCS”
  * Enter the repository URL and select your target directory
  * Click **Clone**

---
### Navigation

- [Setup Guide](index.md)
- [Return to README](../../README.md)
