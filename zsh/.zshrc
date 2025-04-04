#Oh-my-zsh things
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git zsh-autosuggestions zsh-syntax-highlighting )
source $ZSH/oh-my-zsh.sh

#Source helpers from utils
source ~/zsh_utils/helpers.sh
#Give permission to Scripts
chmod -R +x ~/aliases
chmod -R +x ~/exports.sh
chmod -R +x ~/ssh-agent.sh
#Source Scripts
source_files_in ~/aliases/
source ~/exports.sh
source ~/ssh-agent.sh


export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"  # This loads nvm
[ -s "$NVM_DIR/bash_completion" ] && \. "$NVM_DIR/bash_completion"  # This loads nvm bash_completion
