eval "$(ssh-agent -s)" > /dev/null 2>&1

_github_ssh_key="$HOME/.ssh/gh_itsemon245"
if [ -r "$_github_ssh_key" ]; then
    chmod 600 "$_github_ssh_key"
    ssh-add "$_github_ssh_key" > /dev/null 2>&1
fi
unset _github_ssh_key
