# CachyOS VM Test Guide

This project is packaged for CachyOS through the included Arch-style `PKGBUILD`.
The package installs the CLI, the Tk GUI launcher, desktop entry, and udev rules
for Corsair HID access.

## One-Command Package Install

From the project root:

```bash
bash scripts/install-cachyos-package.sh
```

This installs the required CachyOS/Arch packages, builds the local `linuxcue`
package, installs it through `pacman`, reloads udev rules, and keeps the desktop
launcher on the new QML dashboard.

## Build Dependencies

```bash
sudo pacman -S --needed base-devel git python python-build python-installer python-setuptools python-wheel python-hidapi python-pyusb pyside6 qt6-declarative easyeffects lsp-plugins-lv2
```

If the GUI fails with `libtk8.6.so: cannot open shared object file`, install or
repair the Tk runtime:

```bash
sudo pacman -S --needed tk tcl
```

## Build And Install

From the project root:

```bash
bash scripts/build-cachyos-package.sh
sudo pacman -U packaging/arch/linuxcue-0.1.0-1-any.pkg.tar.zst
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Start the GUI:

```bash
linuxcue qml-gui
```

Or start from the desktop menu entry named `linuxcue`.

## Updates From GitHub

The QML dashboard checks GitHub automatically after startup. You can also use the
sidebar buttons or the CLI:

```bash
linuxcue check-update
linuxcue install-update --yes
```

`check-update` compares the newest GitHub release and the latest commit on the
default branch. `install-update` downloads `https://github.com/Maggi0r/Linuxcue`
to `~/.cache/linuxcue/source`, builds the CachyOS package, installs it through
`pacman`, and reloads the udev rules.

## Development Install

For quick VM testing without building a package:

```bash
bash scripts/install-cachyos-dev.sh
~/.local/bin/linuxcue gui
```

For the development install, also install the udev rules once:

```bash
bash scripts/install-udev-rules.sh
```

After reloading udev rules, unplug and reconnect the Corsair device or reattach
it through VirtualBox.
Then run:

```bash
~/.local/bin/linuxcue doctor
~/.local/bin/linuxcue devices
```

For Live Write, the relevant entries must show `open_ok: true`. If they still
show `open_ok: false`, try the same check once with `sudo` to confirm whether
the blocker is permissions:

```bash
sudo ~/.local/bin/linuxcue devices
```

The development installer intentionally creates the virtual environment under
`~/.local/share/linuxcue/venv` instead of `.venv`. This avoids symlink errors on
USB, NTFS, exFAT, or shared VM mounts such as `/run/media/...`.
It also creates a launcher at `~/.local/bin/linuxcue`.

If your shell does not find `linuxcue`, either run the full launcher path:

```bash
~/.local/bin/linuxcue gui
```

Or activate the venv first. For fish:

```fish
source ~/.local/share/linuxcue/venv/bin/activate.fish
linuxcue gui
```

For bash or zsh:

```bash
source ~/.local/share/linuxcue/venv/bin/activate
linuxcue gui
```

If you want a different venv location, set `LINUXCUE_VENV_DIR`:

```bash
LINUXCUE_VENV_DIR="$HOME/venvs/linuxcue" bash scripts/install-cachyos-dev.sh
~/.local/bin/linuxcue gui
```

## Install Location

The packaged install follows the Arch/CachyOS filesystem layout:

- Application code and launchers are installed below `/usr`.
- udev rules are installed to `/usr/lib/udev/rules.d/`.
- User profiles stay in `~/.config/linuxcue`.
- EasyEffects presets stay in `~/.config/easyeffects/output`.

That is preferable to a custom application folder on Arch-based systems because
`pacman` can track, remove, and upgrade every installed file cleanly.

## VirtualBox Mouse Capture

If the mouse pointer gets trapped near the middle of the VM window or only
releases after moving to a corner, this is usually a VirtualBox guest-integration
issue rather than a `linuxcue` issue.

Quick recovery:

```text
Press Right Ctrl to release the mouse from the VM.
```

VirtualBox checks:

- In the running VM menu, toggle `Input > Mouse Integration`.
- Shut down the VM and set `Settings > System > Pointing Device` to `USB Tablet`.
- Install the CachyOS/Arch guest utilities:

```bash
sudo pacman -S --needed virtualbox-guest-utils xf86-input-libinput
sudo systemctl enable --now vboxservice.service
reboot
```

If the VM runs under Wayland and the pointer still behaves strangely, log out
and test an X11 session once. Some VirtualBox pointer-integration issues are
session-specific.

## VirtualBox USB Passthrough

Live Write only works when the real Corsair USB/HID device is visible inside the
VM. Mock fixtures are used for Preview and Simulation only.

In VirtualBox:

- Shut down the VM.
- Open `Settings > USB`.
- Enable the USB controller. Prefer `USB 3.0 (xHCI)` if available.
- Add USB filters for the K95 RGB Platinum, M65 Pro RGB, Virtuoso SE, and the
  Virtuoso wireless receiver.
- Start the VM and reconnect the devices if they still stay attached to the
  host.

Inside CachyOS, check what the VM can see:

```bash
lsusb | grep -i corsair
~/.local/bin/linuxcue doctor
~/.local/bin/linuxcue devices
```

If Live Write says `could not open it` or `open failed`, the device is visible
but not writable. Try:

```bash
bash scripts/install-udev-rules.sh
```

Then detach/reattach the USB device in VirtualBox. As a temporary diagnostic
only, you can check whether it is purely a permission problem by running:

```bash
sudo ~/.local/bin/linuxcue devices
```

If `sudo ~/.local/bin/linuxcue devices` shows `open_ok: true` while the normal
user shows `open_ok: false`, udev permissions are the blocker. Do not use the
GUI as root permanently; use it only as a short diagnostic.

Expected IDs for the current target hardware are:

```text
K95 RGB Platinum: 1b1c:1b2d
M65 Pro RGB:      1b1c:1b2e
Virtuoso SE HID:  1b1c:0a3d
Receiver:         1b1c:0a46
```

## First Device Check

Run these commands with the K95 RGB Platinum, M65 Pro RGB, Virtuoso SE, and the
Virtuoso RGB Wireless USB Receiver attached:

```bash
linuxcue doctor
linuxcue devices
linuxcue targets
linuxcue probe-template
```

The current product IDs are safe mock/default values until they are verified
against real `lsusb` and HID output from your VM.

## Current Live-Writing Status

`linuxcue` already builds HID-like packets for the supported devices and exposes
live-write commands:

```bash
linuxcue write-k95-live k95-default
linuxcue write-m65-live m65-default
linuxcue write-virtuoso-live virtuoso-default
```

The packet generation is implemented, but real hardware writes still need VM
testing because the final Corsair report IDs and product IDs may differ by
firmware revision.

If Live Write completes without an error but nothing visibly changes, the HID
device path is working, but the packet format is still only an experimental
placeholder. The next implementation step is to capture and map the real
Corsair feature reports for each device and firmware revision.

## Safe HID Mapping

Use this before deeper reverse engineering. It only opens HID endpoints and
reads feature reports; it does not write to the device.

```bash
~/.local/bin/linuxcue map-devices > linuxcue-hid-map.json
```

In the GUI, use `Map Devices`; the result appears in the Preview tab. Send the
sections for the K95, M65, Virtuoso SE, and receiver back into the development
thread so the backend packet builders can be replaced with real report formats.

Profiles can be deleted in the GUI with `Delete Profile` or from the CLI:

```bash
~/.local/bin/linuxcue delete-profile profile-name
```

For larger scans:

```bash
~/.local/bin/linuxcue map-devices --max-report-id 64 --report-length 128 > linuxcue-hid-map-wide.json
```

Current observations from the first VM map:

- K95 RGB Platinum exposes `interface 0` as keyboard input and `interface 1` as the likely control/feature endpoint.
- K95 `interface 1` can read feature reports `0x01` through `0x10`; the first capture returned zero-filled payloads.
- Virtuoso receiver `0x0a46` exposes readable feature report `0x0c`.
- Virtuoso USB headset `0x0a3d` opens on interfaces `3` and `4`, but the first capture did not expose readable feature reports from `0x00` through `0x10`.

Current observations from the HID descriptor capture:

- K95 RGB Platinum `interface 1` exposes 64-byte input, output, and feature reports without an explicit report ID. linuxcue therefore writes K95 lighting frames as report ID `0x00` with a 64-byte payload.
- Virtuoso SE and the Virtuoso wireless receiver expose vendor output report ID `0x02` with 63-byte payloads on the `0xff42` control page. linuxcue uses that shape for headset and receiver live writes.
- Virtuoso receiver feature report `0x0c` is useful as a readable status/control candidate, but it is not treated as the main live-write report.
- Virtuoso EQ presets are represented as 10-band values in linuxcue. The descriptor gives us the safe HID envelope; exact Corsair EQ command bytes still need before/after captures from iCUE to become verified rather than experimental.

Analyze an existing map file:

```bash
~/.local/bin/linuxcue analyze-map linuxcue-hid-map.json
```

Show the current linuxcue capability map:

```bash
~/.local/bin/linuxcue capabilities
```

Show targeted before/after capture scenarios for command-byte mapping:

```bash
~/.local/bin/linuxcue capture-plan
~/.local/bin/linuxcue capture-plan --target virtuoso-se --capability eq-presets
```

Compare two capture exports after changing exactly one iCUE setting:

```bash
~/.local/bin/linuxcue diff-captures before.json after.json
```

Capture Linux HID report descriptors:

```bash
~/.local/bin/linuxcue capture-descriptors > linuxcue-hid-descriptors.json
```

Analyze an existing descriptor capture:

```bash
~/.local/bin/linuxcue analyze-descriptors linuxcue-hid-descriptors.json
```

Use this when feature-report reads are all zero-filled. The descriptor capture
helps identify report sizes, report IDs, and whether the endpoint expects input,
output, or feature reports.


cd ~/Downloads/iCue\ unter\ Linux
bash scripts/install-cachyos-dev.sh
~/.local/bin/linuxcue capture-descriptors > linuxcue-hid-descriptors.json
