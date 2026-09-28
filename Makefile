STOW_PACKAGES := agents alacritty git hermes home-manager nvim opencode pi tmux usql zellij
PACKAGES := $(STOW_PACKAGES) codex herdr

.PHONY: all stow unstow restow codex-clean pve-build pve-upload pve-image $(PACKAGES)

all: stow

stow:
	stow -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex
	$(MAKE) herdr

unstow:
	stow -D -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex-clean

restow:
	stow -R -v -t ~ $(STOW_PACKAGES)
	$(MAKE) codex
	$(MAKE) herdr

# Individual package targets
$(STOW_PACKAGES):
	stow -v -t ~ $@

codex:
	stow -R -v -t ~ codex

codex-clean:
	stow -D -v -t ~ codex || true

# ~/.config/herdr is a live dir (sockets, logs); sync the config file instead of stowing.
herdr:
	cp -f herdr/.config/herdr/config.toml ~/.config/herdr/config.toml
	herdr server reload-config 2>/dev/null || true

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
