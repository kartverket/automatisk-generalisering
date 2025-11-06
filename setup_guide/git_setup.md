# Installing GIT and setting up environment

## Objective

The purpose of this guide is to walk you through the process of installing Git on your local environment and connecting it to the `automatic-generalization-kv` repository. Git is a vital tool for version control that allows us to collaborate on coding projects effectively.

## Steps for Installing and Setting Up GIT:

### 1. Install GIT on Your Local System

- For team members at Kartverket, you'll need to use `Firmaportal` to get the software.
  - Search for `GIT` in `Firmaportal`.
  - Install `The Git Development Community - Git (x64)`.

### 2. Basic Verification Steps:

#### General Steps:

- Open your preferred IDE. 
- Access the terminal or command prompt within the IDE. 
- Type `git --version` and press Enter.
   - If Git is installed correctly, the terminal should display the installed version number.

#### Troubleshooting:

If you encounter an error message like `git is not recognized as an internal or external command`, it usually means Git is not installed or not properly set in your system's PATH.

**Solution**
- Restart your PC and check if the issue still persist.
- Re-check the installation process.
- Confirm that Git's binary directory is added to your system's PATH variable.

### 3. Prepare Local Directory and Clone the Repository

#### Local Directory Setup:

- Choose or create a folder where you want to store the `automatic-generalization-kv` repository.
- Navigate to this directory using File Explorer or terminal.
  
#### Configuring Local Git Settings:

- Open the terminal and navigate to the directory you've chosen.
- Configure your Git username and email if you haven't already:
    ```bash
    git config --global user.name "Your Username"
    git config --global user.email "your.email@example.com"
    ```
  
#### Cloning the Repository:

- Still in the terminal, type the following command to clone the repository:
    ```bash
    git clone https://github.com/kartverket/automatisk-generalisering.git
    ```

- You should now see a new folder named `automatic-generalization-kv` inside your chosen directory. This folder is your local clone of the GitHub repository.



