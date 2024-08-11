{ config,pkgs, ...}: {
  services.nginx = {
    enable = true;
    virtualHosts."blog.test" = {
      root = "/var/www/blog";
      locations."~ \\.php$".extraConfig = ''
      fastcgi_pass  unix:${config.services.phpfpm.pools.mypool.socket};
      fastcgi_index index.php;
      '';
    };
  };
  services.mysql = {
    enable = true;
    package = pkgs.mariadb;
  };
  services.phpfpm.pools.mypool = {
    user = "nobody"; 
    settings = {
      "pm" = "dynamic";
      "listen.owner" = config.services.nginx.user;
      "pm.max_children" = 5;
      "pm.start_servers" = 2;
      "pm.min_spare_servers" = 1;
      "pm.max_spare_servers" = 3;
      "pm.max_requests" = 500;
    };
  };
}
