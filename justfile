set shell := ["bash", "-euo", "pipefail", "-c"]

# Recipes run on a Linux/macOS build host with Docker; installation runs on the Thor.
default:
    @just --list

# Syntax/unit checks; never touches a device or downloads media.
check:
    python3 -m unittest discover -s tests -v
    python3 tools/thor.py check

# Check host prerequisites and show pinned inputs.
doctor:
    python3 tools/thor.py doctor

# Download the pinned upstream source into ignored .build/ (no system install).
source:
    python3 tools/thor.py source

# Build patched x86-64 Wine, PE helpers and a private rootfs. May take hours.
build-wine: source
    python3 tools/thor.py build-wine

# Build native ARM64 compositor, Xvfb, cursor tools and Python Xlib.
build-native: source
    python3 tools/thor.py build-native

build: build-wine build-native

# Test the fresh native build in a GPU-less container; never touches a Thor.
smoke-native:
    python3 tools/thor.py smoke-native

# Fresh ARM64 Fedora user/Box64/Wine test; requires build + ReactOS extraction.
test-container:
    python3 tools/thor.py test-container

# shell: reactos, xp or win7. XP/Win7 require your own mounted media/ISO path.
extract shell media="": source
    python3 tools/thor.py extract {{quote(shell)}} {{quote(media)}}

# Read-only device prerequisites. Set THOR_HOST, optionally THOR_USER and THOR_SSH_KEY.
preflight:
    python3 tools/thor.py preflight

# Upload private runtimes/tools into the login user's home; no session switch.
deploy:
    python3 tools/thor.py deploy

# Create a NEW independent prefix (refuses existing), e.g. just prefix win7.
prefix shell:
    python3 tools/thor.py prefix {{quote(shell)}}

# Add SDDM entries/root switching helpers. No default changes or desktop restart.
register shell:
    python3 tools/thor.py register {{quote(shell)}}

# Private headless tests only; refuses an active prefix. Can play startup audio.
test-headless shell:
    python3 tools/thor.py test-headless {{quote(shell)}}

# Checks the already-running standalone shell, briefly opening test windows.
test-live shell:
    python3 tools/thor.py test-live {{quote(shell)}}

# DESTRUCTIVE TO OPEN APPS: requires THOR_ALLOW_SWITCH=1; unplug DisplayPort first.
switch shell:
    python3 tools/thor.py switch {{quote(shell)}}

# Recovery closes the current desktop; requires THOR_ALLOW_SWITCH=1.
rescue:
    python3 tools/thor.py rescue

# Read-only public-source inventory/credential and binary checks (not a guarantee).
audit:
    python3 tools/audit-public.py
