{ pkgs,server, ...}:
let
  memoryLimit = server.memoryLimit;
  executionTime = server.executionTime;
  # oldPkgs = import
  #   (builtins.fetchTarball {
  #     url = "https://github.com/NixOS/nixpkgs/archive/99c08670066b13ab8347c6de087cc915fae99165.tar.gz";
  #     sha256 = "sha256:0wd5h8na7dlqdyvcvqlkgw84sj956yiq39jkljm0z7v7sg6dgwjs";
  #   }) {};
  #     oldPhp = oldPkgs.php;
  old = import
    (fetchTarball  {
      url = "https://github.com/NixOS/nixpkgs/archive/73bc3300ad02be21998a7c0e987592ca66df73f3.tar.gz";
      sha256 = "sha256:0wd5h8na7dlqdyvcvqlkgw84sj956yiq39jkljm0z7v7sg6dgwjs";
    }){inherit (pkgs) system;};
  version = "82";
  currentPhp = pkgs."php${version}";
in {
  environment.systemPackages = let
    php = currentPhp.buildEnv {
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
        post_max_size = ${memoryLimit}
        upload_max_filesize = ${memoryLimit}
        memory_limit = ${memoryLimit}
        max_execution_time = ${executionTime}
      '';
    };
  in [
    php
    pkgs."php${version}Packages".psalm
    pkgs."php${version}Packages".composer
    pkgs.curl
    pkgs.redis
    pkgs.ffmpeg_7
    pkgs.nodejs_22
    pkgs.python3
    pkgs.go
  ];
    services.redis.servers."default".enable=true;
  services.redis.servers."default".port=6379;
  services.phpfpm.phpOptions = ''
    extension=${pkgs.phpExtensions.redis}/lib/php/extensions/redis.so

  '';
}
