STOW_PACKAGES := alacritty claude git home-manager nvim zellij
PACKAGES := $(STOW_PACKAGES) codex

.PHONY: all stow unstow restow codex-clean pve-build pve-upload pve-image $(PACKAGES)

all: stow

stow:
	stow -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex

unstow:
	stow -D -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex-clean

restow:
	stow -R -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex

# Individual package targets
$(STOW_PACKAGES):
	stow -v -t ~ $@

codex:
	stow -R -v -t ~ codex

codex-clean:
	stow -D -v -t ~ codex || true

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
