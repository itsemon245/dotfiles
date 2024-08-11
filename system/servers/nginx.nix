{config, pkgs, ...}:

{
  services.nginx = {
    enable = true;
    locations."/" = {
      return = "200 '<html><body>It works</body></html>'";
      extraConfig = ''
      default_type text/html;
      '';
    };
  };
}
