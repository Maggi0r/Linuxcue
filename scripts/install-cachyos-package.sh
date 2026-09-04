#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v pacman >/dev/null 2>&1; then
  echo "This installer targets CachyOS/Arch systems with pacman." >&2
  exit 1
fi

wait_for_pacman_lock() {
  local lock_file="/var/lib/pacman/db.lck"
  local waited=0
  local max_wait=180

  while [[ -e "$lock_file" && "$waited" -lt "$max_wait" ]]; do
    if [[ "$waited" -eq 0 ]]; then
      echo "Pacman database is locked. Another package manager/update is probably running."
      echo "Waiting up to ${max_wait}s before continuing..."
    fi
    sleep 5
    waited=$((waited + 5))
  done

  if [[ -e "$lock_file" ]]; then
    cat >&2 <<'EOF'

Pacman database is still locked.
Close other package managers such as Discover, Pamac, Bauh, octopi, or another pacman terminal.

To inspect the lock on Arch/CachyOS:

  sudo fuser -v /var/lib/pacman/db.lck

Only if no pacman/package process is running anymore, remove the stale lock manually:

  sudo rm /var/lib/pacman/db.lck

Then rerun the linuxcue update.

EOF
    exit 1
  fi
}

echo "Synchronizing CachyOS/Arch package database and installing linuxcue dependencies..."
wait_for_pacman_lock
if ! sudo pacman -Syu --needed --noconfirm \
  base-devel \
  git \
  python \
  python-build \
  python-installer \
  python-setuptools \
  python-wheel \
  python-hidapi \
  python-numpy \
  python-pyusb \
  libpulse \
  pipewire \
  pipewire-pulse \
  wireplumber \
  pyside6 \
  qt6-declarative \
  easyeffects \
  lsp-plugins-lv2; then
  cat >&2 <<'EOF'

Dependency installation failed before linuxcue was built.
If pacman shows 404 errors, your mirror database is out of sync.
Try this in the VM, then rerun this installer:

  sudo pacman -Syyu
  bash scripts/install-cachyos-package.sh

If it still fails on CachyOS, refresh/rerank mirrors first:

  sudo cachyos-rate-mirrors
  sudo pacman -Syyu

EOF
  exit 1
fi

echo "Building linuxcue package..."
cd "$repo_root/packaging/arch"
makepkg -f --noconfirm

pkg_file="$(ls -t linuxcue-*.pkg.tar.zst | head -n 1)"
if [[ -z "${pkg_file}" ]]; then
  echo "Package build finished, but no linuxcue package was found." >&2
  exit 1
fi

echo "Installing ${pkg_file}..."
wait_for_pacman_lock
sudo pacman -U --noconfirm "$pkg_file"

echo "Reloading udev rules..."
sudo udevadm control --reload-rules || true
sudo udevadm trigger || true

echo
echo "linuxcue is installed."
echo "Start with: linuxcue qml-gui"
echo "Check devices with: linuxcue doctor"
echo "If live write cannot open a device, detach and reconnect it once."
