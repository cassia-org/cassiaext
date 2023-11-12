{pkgs ? import <nixpkgs> {}}:
pkgs.mkShell {
  NIX_LD = pkgs.lib.fileContents "${pkgs.stdenv.cc}/nix-support/dynamic-linker";
  nativeBuildInputs = with pkgs; [
    wayland-scanner
    python3
  ];
  depsBuildBuild = with pkgs; [
    ninja
    meson
    pkg-config
    autoconf
    automake
    cmake
    xorg.utilmacros
    xorg.fontutil
    xorg.xtrans
    texinfo
    bison
    glslang
    jq
  ];
}