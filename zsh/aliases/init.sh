# ls
alias l='ls -lh'
alias ll='ls -lah'
alias la='ls -A'
alias lm='ls -m'
alias lr='ls -R'
alias lg='ls -l --group-directories-first'

alias rm-nvim-swap='rm -rf ~/.local/state/nvim/swap'
alias sail='[ -f sail ] && bash sail || bash vendor/bin/sail'
alias a='php artisan'
alias n='npm run'
[ "$TERM" = "xterm-kitty" ] && alias ssh="kitty +kitten ssh"
alias bfg='java -jar ~/.local/bin/bfg.jar'
alias cast='scrcpy --no-audio-playback'
alias nsh="nix-shell --run $SHELL"
