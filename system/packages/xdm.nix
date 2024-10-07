{ pkgs ? import <nixpkgs> {} }:

pkgs.stdenv.mkDerivation rec {
  pname = "xdm";
  version = "8.0.29";

  src = pkgs.fetchurl {
    url = "https://github.com/subhra74/xdm/releases/download/8.0.29/xdman_gtk_8.0.29_amd64.deb";
    sha256 = "your-sha256-hash-here"; # Replace with the actual hash
  };

  nativeBuildInputs = [ pkgs.dpkg ];

  installPhase = ''
    mkdir -p $out
    dpkg-deb -x $src $out/
  '';

  # If your package requires additional dependencies, you can list them here
  # e.g., for including shared libraries that the .deb package depends on:
  buildInputs = [
    pkgs.libGL  # Example: add libGL as a dependency
    pkgs.libX11 # Add more libraries as needed
  ];

  # If the package requires an FHS-compatible filesystem layout (like /usr, /lib, /bin),
  # you can wrap it using buildFHSUserEnv:
  buildFHSUserEnv = pkgs.buildFHSUserEnv {
    name = "deb-fhs-env";
    targetPkgs = pkgs: [
      pkgs.libGL
      pkgs.libX11
      # Add other packages required by your .deb package here
    ];
    profile = ''
      export PATH=$out/bin:$PATH
    '';
  };
}
