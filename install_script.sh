#!/bin/bash

packages=("requests" "tiktoken" "PyInquirer" "urllib3")

for package in ${packages[@]}
do
   pip3 install $package --user
done


python_script_path=$(pwd)/$(ls *.py)

echo "#!/bin/sh
exec python3 $python_script_path \"\$@\"" > git-commitgpt

chmod +x git-commitgpt

echo "Add the following line to your source ~/.bashrc or ~/.zshrc to add the git command to PATH:"
echo "export PATH=\"$(pwd):\$PATH\""
