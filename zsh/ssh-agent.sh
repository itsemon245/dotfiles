eval "$(ssh-agent -s)" > /dev/null 2>&1
chmod 600 ~/.ssh/default
ssh-add ~/.ssh/default > /dev/null 2>&1
