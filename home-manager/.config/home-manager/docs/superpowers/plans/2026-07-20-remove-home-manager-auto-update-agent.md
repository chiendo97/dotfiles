# Remove Home Manager Auto-Update Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove the scheduled macOS Home Manager updater, update all flake inputs manually, and activate the upgraded `chiendo97` profile.

**Architecture:** Home Manager remains the source of truth for launchd services. Removing the agent declaration and activating the profile lets Home Manager unload and delete the obsolete plist; the unrelated Podman agent remains declaratively managed.

**Tech Stack:** Nix flakes, Home Manager, macOS launchd, Git

---

### Task 1: Remove the Auto-Update Agent Declaration

**Files:**
- Modify: `home.nix:491-514`

- [x] **Step 1: Record the pre-change service state**

Run:

```bash
launchctl print "gui/$(id -u)/com.home-manager.auto-update"
test -e "$HOME/Library/LaunchAgents/com.home-manager.auto-update.plist"
```

Expected: `launchctl print` identifies the loaded agent and `test` exits 0.

- [x] **Step 2: Delete only the auto-update declaration**

Delete this complete block from `home.nix`:

```nix
  launchd.agents.home-manager-auto-update = lib.mkIf pkgs.stdenv.isDarwin {
    enable = true;
    config = {
      Label = "com.home-manager.auto-update";
      ProgramArguments = [
        "/bin/sh"
        "-c"
        ''
          export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$PATH"
          cd ~/.config/home-manager && \
          nix flake update 2>&1 | tee /tmp/home-manager-update.log && \
          home-manager switch --flake . 2>&1 | tee -a /tmp/home-manager-update.log
        ''
      ];
      StartCalendarInterval = [
        {
          Hour = 9;
          Minute = 0;
        }
      ];
      StandardOutPath = "/tmp/home-manager-auto-update.out.log";
      StandardErrorPath = "/tmp/home-manager-auto-update.err.log";
    };
  };
```

- [x] **Step 3: Verify the source-level removal is surgical**

Run:

```bash
! rg -n 'home-manager-auto-update|com\.home-manager\.auto-update' home.nix
rg -n 'launchd\.agents\.podman-machine|com\.podman\.machine' home.nix
git diff --check -- home.nix
```

Expected: the removed agent has no matches, both Podman identifiers remain, and `git diff --check` exits 0.

### Task 2: Update and Build the Flake

**Files:**
- Modify: `flake.lock`

- [x] **Step 1: Update all flake inputs**

Run:

```bash
nix flake update
```

Expected: the command exits 0 and records updated input revisions in `flake.lock` when newer revisions exist.

- [x] **Step 2: Evaluate the upgraded macOS profile**

Run:

```bash
nix eval .#homeConfigurations.chiendo97.activationPackage.drvPath
```

Expected: the command exits 0 and prints a `/nix/store/...-home-manager-generation.drv` path.

- [x] **Step 3: Build the upgraded macOS profile**

Run:

```bash
home-manager build --flake .#chiendo97
```

Expected: the command exits 0 and creates or updates the `result` symlink.

### Task 3: Activate and Verify the Cutover

**Files:**
- Runtime removal: `$HOME/Library/LaunchAgents/com.home-manager.auto-update.plist`

- [x] **Step 1: Activate the upgraded profile**

Run:

```bash
home-manager switch --flake .#chiendo97
```

Expected: activation exits 0 and reports removal of the obsolete `com.home-manager.auto-update` service.

- [x] **Step 2: Verify the agent and plist are gone**

Run:

```bash
! launchctl print "gui/$(id -u)/com.home-manager.auto-update"
test ! -e "$HOME/Library/LaunchAgents/com.home-manager.auto-update.plist"
```

Expected: `launchctl print` reports that the service could not be found and the plist absence check exits 0.

- [x] **Step 3: Verify the Podman agent remains managed**

Run:

```bash
launchctl print "gui/$(id -u)/com.podman.machine"
test -e "$HOME/Library/LaunchAgents/com.podman.machine.plist"
```

Expected: both commands exit 0.

- [x] **Step 4: Review and commit the scoped result**

Run:

```bash
git diff --check
git status --short
git diff -- home.nix flake.lock
git add -- home.nix flake.lock docs/superpowers/plans/2026-07-20-remove-home-manager-auto-update-agent.md
git diff --cached --check
git commit -m "home-manager: remove automatic flake updater"
```

Expected: only the intended source, lock file, and implementation plan are committed; unrelated untracked files remain untouched.
