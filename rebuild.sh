#!/usr/bin/env bash
set -e

# Get the directory where this script is located
DOTFILES_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DOTFILES_DIR"

# Parse command line arguments
UPDATE_FLAKE=false
STOW_ONLY=false

while [[ $# -gt 0 ]]; do
	case $1 in
	--stow)
		STOW_ONLY=true
		shift
		;;
	--update)
		UPDATE_FLAKE=true
		shift
		;;
	--help | -h)
		echo "Usage: $0 [--stow] [--update]"
		echo ""
		echo "Rebuild dotfiles: Home Manager switch + GNU Stow"
		echo ""
		echo "Options:"
		echo "  --stow     Stow only (skip Home Manager)"
		echo "  --update   Update flake inputs + uv/cargo tools before rebuilding"
		echo "  --help     Show this help message"
		exit 0
		;;
	*)
		echo "Unknown option: $1"
		echo "Use --help for usage information"
		exit 1
		;;
	esac
done

OS="$(uname -s)"
echo "Rebuilding dotfiles..."
echo "Platform: $OS"

# Resolve the Home Manager flake directory
HM_DIR="$DOTFILES_DIR/home-manager/.config/home-manager"

# --- Home Manager ---
if [[ "$STOW_ONLY" != "true" ]] && command -v home-manager &>/dev/null; then
	echo ""
	echo "Home Manager: applying configuration..."

	if [[ "$UPDATE_FLAKE" == "true" ]]; then
		echo "Updating flake inputs..."
		nix flake update --flake "$HM_DIR"
		echo "Flake inputs updated."
	fi

	# Auto-detect config name from $USER
	home-manager switch --flake "$HM_DIR"
	echo "Home Manager: done."

	# Upgrade external tools when updating
	if [[ "$UPDATE_FLAKE" == "true" ]]; then
		if command -v uv &>/dev/null; then
			echo ""
			echo "Upgrading uv tools..."
			uv tool upgrade --all
		fi
		if command -v cargo-binstall &>/dev/null; then
			echo ""
			echo "Upgrading cargo tools..."
			cargo binstall -y cargo-binstall mdterm meread xleak
		fi
	fi
elif [[ "$STOW_ONLY" != "true" ]]; then
	echo ""
	echo "home-manager not found, skipping. Use --stow for stow-only mode."
fi

# --- GNU Stow ---
echo ""
echo "Stow: symlinking packages..."
make -C "$DOTFILES_DIR" restow
echo "Stow: done."

echo ""
echo "Rebuild complete!"
