{config, lib, pkgs, ...}:
{

  environment.systemPackages = let
    php = pkgs.php81.buildEnv { 
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
    pkgs.php81Packages.composer
    pkgs.php81Extensions.redis
    pkgs.curl
    pkgs.redis
    pkgs.php81Extensions.curl
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
