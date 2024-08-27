{ pkgs }:

pkgs.writeShellApplication {
  name = "netspeed";
  runtimeInputs = [ pkgs.go ];
  text = ''
    go build -o $out/netspeed ${./go/netspeed.go}
  '';
}
