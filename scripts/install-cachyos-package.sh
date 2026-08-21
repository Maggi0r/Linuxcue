#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if ! command -v pacman >/dev/null 2>&1; then
  echo "This installer targets CachyOS/Arch systems with pacman." >&2
  exit 1
fi

echo "Installing linuxcue build/runtime dependencies..."
sudo pacman -S --needed \
  base-devel \
  python \
  python-build \
  python-installer \
  python-wheel \
  python-hidapi \
  python-pyusb \
  pyside6 \
  qt6-declarative \
  easyeffects \
  lsp-plugins-lv2

echo "Building linuxcue package..."
cd "$repo_root/packaging/arch"
makepkg -f

pkg_file="$(ls -t linuxcue-*.pkg.tar.zst | head -n 1)"
if [[ -z "${pkg_file}" ]]; then
  echo "Package build finished, but no linuxcue package was found." >&2
  exit 1
fi

echo "Installing ${pkg_file}..."
sudo pacman -U --needed "$pkg_file"

echo "Reloading udev rules..."
sudo udevadm control --reload-rules || true
sudo udevadm trigger || true

echo
echo "linuxcue is installed."
echo "Start with: linuxcue qml-gui"
echo "Check devices with: linuxcue doctor"
echo "If live write cannot open a device, detach and reconnect it once."
