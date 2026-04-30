.PHONY: switch build dry-run check update nixos-cle homelab-pve selfhost-pve

# Optional Home Manager profile, e.g. `make switch PROFILE=genbook`
PROFILE ?=
FLAKE := .$(if $(PROFILE),#$(PROFILE),)

switch:
	home-manager switch --flake $(FLAKE)

build:
	home-manager build --flake $(FLAKE)

dry-run:
	home-manager switch --flake $(FLAKE) --dry-run

check:
	nix flake check

update:
	nix flake update

nixos-cle:
	sudo nixos-rebuild switch --flake .#nixos-cle

homelab-pve:
	sudo nixos-rebuild switch --flake .#homelab-pve

selfhost-pve:
	sudo nixos-rebuild switch --flake .#selfhost-pve
