{ pkgs }:
pkgs.writeShellScriptBin "mem" ''
    free --giga -h | grep "Mem:" | awk '{print $NF}'
''
