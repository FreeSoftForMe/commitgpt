# Git Commit Message Generator

This tool helps you automatically generate meaningful commit messages for your Git commits based on the changes in your code. It uses the OpenAI API to generate these messages.

## Installation

1. Ensure you have Python 3 and pip installed on your system.
2. Clone this repository and navigate to the directory containing the scripts.
3. Grant execution permissions to the installation script with the command `chmod +x install_script.sh`.
4. Run the installation script with the command `./install_script.sh`. This will install the necessary Python packages and create a command `git-commitgpt` that runs the `gitcommit.py` script.
5. Add the current directory to your PATH. You can do this by adding the following line to your `.bashrc` or `.zshrc` file (replace `/path/to/script` with the absolute path to the directory containing the `git-commitgpt` command):
   ```bash
   export PATH="/path/to/script:$PATH"
   ```

## Usage

1. After making changes to your code, instead of using `git commit`, use the `git-commitgpt` command. 
2. If your changes result in more tokens than specified in the configuration, you'll be asked to confirm whether you want to proceed.
3. You'll then be prompted to choose a commit message from the suggestions provided by the OpenAI API or to enter your own message.
4. After you choose a message, the tool will make a Git commit with that message.

Please ensure you have set your OpenAI API key in the `config.json` file before using this tool. The key should be set against the "OPENAI_API_KEY" field.