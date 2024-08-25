{ pkgs }:

pkgs.writeShellScriptBin "speedmeter" ''
    echo "hello world" | ${pkgs.cowsay}/bin/cowsay | ${pkgs.lolcat}/bin/lolcat
''
