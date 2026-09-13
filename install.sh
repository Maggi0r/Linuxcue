#!/usr/bin/env bash
set -euo pipefail

repo_url="https://github.com/Maggi0r/Linuxcue.git"
cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/linuxcue/source"

if ! command -v pacman >/dev/null 2>&1; then
  cat >&2 <<'EOF'
linuxcue currently ships a one-click installer for Arch/CachyOS based systems.

This system does not provide pacman, so automatic installation is not available
yet. Please install manually from the repository or open a GitHub issue for your
distribution so packaging can be added.
EOF
  exit 1
fi

if ! command -v git >/dev/null 2>&1; then
  echo "Installing git first so linuxcue can download the newest source..."
  sudo pacman -Sy --needed --noconfirm git
fi

mkdir -p "$(dirname "$cache_dir")"

if [[ -d "$cache_dir/.git" ]]; then
  echo "Updating linuxcue installer source..."
  git -C "$cache_dir" fetch --all --prune
  git -C "$cache_dir" checkout main
  git -C "$cache_dir" pull --ff-only
else
  echo "Downloading linuxcue installer source..."
  rm -rf "$cache_dir"
  git clone "$repo_url" "$cache_dir"
fi

echo
echo "Starting linuxcue package installer..."
exec bash "$cache_dir/scripts/install-cachyos-package.sh"
