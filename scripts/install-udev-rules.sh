#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
rules_source="$repo_root/packaging/arch/99-linuxcue.rules"
rules_target="/usr/lib/udev/rules.d/99-linuxcue.rules"

if [[ ! -f "$rules_source" ]]; then
  echo "linuxcue udev rules not found: $rules_source" >&2
  echo "Please run this from a complete linuxcue project copy that includes packaging/arch/99-linuxcue.rules." >&2
  exit 1
fi

sudo install -Dm644 "$rules_source" "$rules_target"
sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Installed linuxcue udev rules to $rules_target"
echo "Now detach/reattach the Corsair USB device in VirtualBox, or unplug and reconnect it."
