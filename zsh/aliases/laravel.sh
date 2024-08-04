kill_php_servers(){
  ps aux | grep 'php artisan serve' | grep -v '.tox' | awk '{print $2}' | xargs -I{} kill {} && echo 'All servers killed'
}
alias pask='kill_php_servers && php artisan serve'
