PACKAGES := alacritty git home-manager nvim zellij

.PHONY: all stow unstow restow $(PACKAGES)

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
