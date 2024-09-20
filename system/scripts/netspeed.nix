{ pkgs }:

pkgs.writeShellScriptBin "netspeed" ''
    ${pkgs.go}/bin/go run ${./go/netspeed.go}
''
