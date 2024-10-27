{config, lib, pkgs, ...}:
{

  environment.systemPackages = let
    version = "82";
    php = pkgs."php${version}".buildEnv {
      extensions = ({enabled, all}: enabled ++ (with all; [
        bcmath
        gd
        opcache
        mbstring
        pdo
        pdo_mysql
        mysqli
        redis
        curl
        zip
      ]));
      extraConfig = ''
        post_max_size = 220M
        upload_max_filesize = 200M
        memory_limit = 200M

      '';
    };
  in [
    php
    pkgs."php${version}Packages".composer
    pkgs."php${version}Extensions".redis
    pkgs.curl
    pkgs.redis
    pkgs."php${version}Extensions".curl
    pkgs.ffmpeg_7
    pkgs.nodejs_22
    pkgs.python3
  ];
    services.redis.servers."default".enable=true;
  services.redis.servers."default".port=6379;
  services.phpfpm.phpOptions = ''
    extension=${pkgs.phpExtensions.redis}/lib/php/extensions/redis.so

  '';
}
