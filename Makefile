PACKAGES := alacritty claude git home-manager nvim zellij

.PHONY: all stow unstow restow pve-build pve-upload pve-image $(PACKAGES)

all: stow

stow:
	stow -v -t ~ $(PACKAGES)

unstow:
	stow -D -v -t ~ $(PACKAGES)

restow:
	stow -R -v -t ~ $(PACKAGES)

# Individual package targets
$(PACKAGES):
	stow -v -t ~ $@

# --- Proxmox image build/upload ---
# Override on the command line, e.g.:
#   make pve-upload PVE_HOST=root@10.0.0.5
FLAKE_DIR := home-manager/.config/home-manager
PVE_HOST ?= root@pve
PVE_DUMP_DIR ?= /var/lib/vz/dump

pve-build:
	cd $(FLAKE_DIR) && nix build .#homelab-pve-image -o $(CURDIR)/result-pve

pve-upload: pve-build
	scp -L result-pve/vzdump-qemu-*.vma.zst $(PVE_HOST):$(PVE_DUMP_DIR)/

pve-image: pve-upload
	@echo "Uploaded. On the Proxmox host run: qmrestore $(PVE_DUMP_DIR)/<vma file> <vmid>"
