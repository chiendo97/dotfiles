.PHONY: all stow unstow restow

all: stow

stow:
	stow -v -t ~ config

unstow:
	stow -D -v -t ~ config

restow:
	stow -R -v -t ~ config
