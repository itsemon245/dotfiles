{ config,pkgs, lib, ...}: 
let
  app = "phpmyadmin";
  domain = "${app}.local";
  dataDir = "/var/www/${app}";
  memoryLimit = "200M";
in{
  services.nginx.virtualHosts = {
    ${domain} = {
      root = "${dataDir}";
      listen = [
        {
          port = 82;
          addr = "0.0.0.0";
          ssl = false;

        }
      ];
      extraConfig = ''
        index index.php;
        client_max_body_size ${memoryLimit};
      '';

      locations."~ ^(.+\\.php)(.*)$"  = {
        extraConfig = ''
            # Check that the PHP script exists before passing it
            try_files $fastcgi_script_name =404;
            include ${config.services.nginx.package}/conf/fastcgi_params;
            fastcgi_split_path_info  ^(.+\.php)(.*)$;
            fastcgi_pass unix:${config.services.phpfpm.pools.${app}.socket};
            fastcgi_param  SCRIPT_FILENAME  $document_root$fastcgi_script_name;
            fastcgi_param  PATH_INFO        $fastcgi_path_info;
            include ${pkgs.nginx}/conf/fastcgi.conf;            
        '';
      };
    };
  };
  services.phpfpm.pools.${app} = {
    user = app;
    settings = {
      "pm" = "dynamic";
      "listen.owner" = config.services.nginx.user;
      "listen.group" = config.services.nginx.group;
      "listen.mode" = "0660";
      "pm.max_children" = 5;
      "pm.start_servers" = 2;
      "pm.min_spare_servers" = 1;
      "pm.max_spare_servers" = 3;
      "pm.max_requests" = 500;
      "php_admin_value[error_log]" = "stderr";
      "php_admin_flag[log_errors]" = true;
      "catch_workers_output" = true;
      "php_value[upload_max_filesize]" = "${memoryLimit}";
      "php_value[post_max_size]" = "${memoryLimit}";
      "php_value[memory_limit]" = "${memoryLimit}";
    };
    phpEnv."PATH" = lib.makeBinPath [ pkgs.php81 ];
  };
  systemd.services."phpfpm-${app}".serviceConfig.ProtectHome = lib.mkForce false;
  users.users.${app} = {
    isSystemUser = true;
    group  = app;
  };

  users.groups.${app}.members = [ "${app}" ];
  users.users.nginx.extraGroups = [ "${app}"];
  networking.extraHosts =
    ''
    127.0.0.1 ${domain}
    '';
}
