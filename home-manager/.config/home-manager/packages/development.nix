{ pkgs }:
let
  bun_1_3_14 = pkgs.bun.overrideAttrs (
    finalAttrs: previousAttrs: {
      version = "1.3.14";
      src =
        finalAttrs.passthru.sources.${pkgs.stdenv.hostPlatform.system}
          or (throw "Unsupported system: ${pkgs.stdenv.hostPlatform.system}");
      passthru = previousAttrs.passthru // {
        sources = {
          "aarch64-darwin" = pkgs.fetchurl {
            url = "https://github.com/oven-sh/bun/releases/download/bun-v${finalAttrs.version}/bun-darwin-aarch64.zip";
            hash = "sha256-2LliIYKK1vl6x6wKt+lYcjQa92MAHogD6CZ2UsJlJiA=";
          };
          "aarch64-linux" = pkgs.fetchurl {
            url = "https://github.com/oven-sh/bun/releases/download/bun-v${finalAttrs.version}/bun-linux-aarch64.zip";
            hash = "sha256-on/7Y6gxA3WDbg1vZorhf6jY0YuIw3yCHGUzGXOhmjs=";
          };
          "x86_64-darwin" = pkgs.fetchurl {
            url = "https://github.com/oven-sh/bun/releases/download/bun-v${finalAttrs.version}/bun-darwin-x64-baseline.zip";
            hash = "sha256-PjWtb1OXGpg0v55nhuKt9ytfGSHMmpxf3gc9KXKUQHY=";
          };
          "x86_64-linux" = pkgs.fetchurl {
            url = "https://github.com/oven-sh/bun/releases/download/bun-v${finalAttrs.version}/bun-linux-x64.zip";
            hash = "sha256-lR7iruhV8IWVruxiJSJqKY0/6oOj3NZGXAnLzN9+hI8=";
          };
        };
      };
    }
  );
in
with pkgs;
[
  bun_1_3_14
  cht-sh
  cmake
  delta
  fixjson
  gcc
  glab
  gnumake
  lazygit
  nodejs
  pnpm
  rumdl
  rustup
  tree-sitter
  zk
]
