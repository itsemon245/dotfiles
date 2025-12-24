#Oh-my-zsh things
export ZSH="$HOME/.oh-my-zsh"
ZSH_THEME="robbyrussell"
plugins=(git zsh-autosuggestions zsh-syntax-highlighting fzf)
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
export PATH="/opt/homebrew/opt/libpq/bin:$PATH"

# Added by LM Studio CLI (lms)
export PATH="$PATH:/Users/emon/.lmstudio/bin"
# End of LM Studio CLI section


# Added by Antigravity
export PATH="/Users/emon/.antigravity/antigravity/bin:$PATH"

# Added by LM Studio CLI (lms)
export PATH="$PATH:/home/emon/.lmstudio/bin"
# End of LM Studio CLI section

