# linuxcue

`linuxcue` is an early MVP for a Linux-first replacement for Corsair iCUE.
It is not a port of the proprietary iCUE application. Instead, it provides a
realistic starting point for an open-source implementation that can grow device
support over time.

## What works today

- Starts on Linux and other platforms with Python 3.11+
- Detects Corsair USB/HID devices through `hidapi` when available
- Falls back to `/sys/bus/usb/devices` discovery on Linux
- Classifies matching devices into current target families like K95 RGB Platinum, M65 Pro RGB, Virtuoso SE, and the Virtuoso wireless receiver
- Supports offline development via mock probe fixtures for known target devices
- Creates and stores JSON profiles
- Creates a K95-specific zoned lighting profile with prepared packet planning
- Builds hardware-near K95 report frames through a mock HID transport
- Creates an M65-specific DPI/RGB profile with prepared mouse report frames
- Creates a Virtuoso-specific EQ/RGB/control profile with prepared headset report frames
- Ships with a desktop GUI for profile browsing, preview, and live-write entry points
- Simulates profile application so the CLI can already be exercised end to end

## Why this is only an MVP

The original iCUE includes proprietary protocol knowledge, firmware-specific
effects, telemetry, cooling control, macro handling, and a graphical frontend.
Those features require reverse engineering and per-device implementations.

This repository sets up the parts we can build cleanly right away:

- device discovery
- profile persistence
- service layer boundaries
- CLI workflow for testing on Linux

## Quick start

```bash
bash scripts/install-cachyos-dev.sh
~/.local/bin/linuxcue doctor
~/.local/bin/linuxcue gui
~/.local/bin/linuxcue devices
~/.local/bin/linuxcue map-devices
~/.local/bin/linuxcue analyze-map linuxcue-hid-map.json
~/.local/bin/linuxcue capture-descriptors
~/.local/bin/linuxcue analyze-descriptors linuxcue-hid-descriptors.json
~/.local/bin/linuxcue capabilities
~/.local/bin/linuxcue capture-plan --target virtuoso-se --capability eq-presets
~/.local/bin/linuxcue diff-captures before.json after.json
~/.local/bin/linuxcue import-icue-profile "Standard Profil.cueprofile"
~/.local/bin/linuxcue import-icue-profile "Standard Profil.cueprofile" --save
~/.local/bin/linuxcue targets
~/.local/bin/linuxcue probe-template
~/.local/bin/linuxcue mock-probe k95
~/.local/bin/linuxcue mock-probe m65
~/.local/bin/linuxcue mock-probe virtuoso-se
~/.local/bin/linuxcue mock-probe virtuoso-rgb-wireless-receiver
~/.local/bin/linuxcue probes
~/.local/bin/linuxcue init-profile default
~/.local/bin/linuxcue init-k95-profile k95-default
~/.local/bin/linuxcue init-m65-profile m65-default
~/.local/bin/linuxcue init-virtuoso-profile virtuoso-default
~/.local/bin/linuxcue preview-k95 k95-default
~/.local/bin/linuxcue preview-m65 m65-default
~/.local/bin/linuxcue preview-virtuoso virtuoso-default
~/.local/bin/linuxcue write-k95-live k95-default
~/.local/bin/linuxcue k95-hardware-mode
~/.local/bin/linuxcue write-m65-live m65-default
~/.local/bin/linuxcue write-virtuoso-live virtuoso-default
~/.local/bin/linuxcue profiles
~/.local/bin/linuxcue delete-profile old-profile-name
~/.local/bin/linuxcue apply k95-default
```

Optional HID support:

```bash
pip install -e .[hid]
```

## Protocol mapping workflow

The HID descriptor tells linuxcue which report IDs and payload sizes are safe to
use. The remaining work is mapping Corsair's command bytes from before/after
iCUE captures:

```bash
~/.local/bin/linuxcue capture-plan
~/.local/bin/linuxcue capture-plan --target virtuoso-se --capability eq-presets
~/.local/bin/linuxcue diff-captures virtuoso-eq-flat.json virtuoso-eq-1k-plus6.json
```

For each capture pair, change exactly one iCUE setting. Good first captures are:

- Virtuoso EQ: flat 10-band EQ to one band at +6 dB
- Virtuoso controls: sidetone 0 to 50
- Virtuoso RGB: accent off to pure blue
- K95 RGB: all off to one zone pure red
- M65 DPI: 800 DPI to 1200 DPI

### Virtuoso EQ on Linux

The Virtuoso USB HID endpoint can accept linuxcue test frames, but current EQ
frames are not observed to change the headset state. Treat Virtuoso HID EQ as
experimental. For a reliable Linux EQ path, linuxcue can drive EasyEffects as a
hidden PipeWire backend:

```bash
sudo pacman -S --needed easyeffects lsp-plugins-lv2
linuxcue repair-virtuoso-presets "PUBG-virtuoso"
linuxcue apply-virtuoso-eq "PUBG-virtuoso"
```

This writes EasyEffects output presets under `~/.config/easyeffects/output/`
and loads the active linuxcue EQ preset through EasyEffects/PipeWire without
requiring you to operate a second GUI.

If EasyEffects shows `Equalizer cannot be used because Linux Studio Plugins is
not installed`, install `lsp-plugins-lv2`. If an old `Bassverstarker` effect
complains about Calf Studio Gear, either remove that effect or install `calf`.

## CachyOS / Arch package

CachyOS is Arch-based, so the preferred VM test path is the included `PKGBUILD`.
The detailed VM checklist is in [INSTALL-CACHYOS.md](INSTALL-CACHYOS.md).

Recommended CachyOS install path:

```bash
bash scripts/install-cachyos-package.sh
```

This installs the required runtime pieces for the QML dashboard, HID access, and
Virtuoso EQ through EasyEffects/PipeWire:

- `pyside6` and `qt6-declarative` for the Qt Quick/QML GUI
- `python-hidapi` and `python-pyusb` for Corsair HID/USB access
- `easyeffects` and `lsp-plugins-lv2` for Virtuoso Linux EQ profiles
- `git` for GitHub-based update checks and self-updates
- `base-devel`, `python-build`, `python-installer`, `python-setuptools`, and `python-wheel` for local package builds

Manual build and install:

```bash
sudo pacman -S --needed base-devel git python python-build python-installer python-setuptools python-wheel python-hidapi python-pyusb pyside6 qt6-declarative easyeffects lsp-plugins-lv2
bash scripts/build-cachyos-package.sh
sudo pacman -U packaging/arch/linuxcue-0.1.0-1-any.pkg.tar.zst
sudo udevadm control --reload-rules
sudo udevadm trigger
linuxcue qml-gui
```

For a quick editable development install instead:

```bash
bash scripts/install-cachyos-dev.sh
bash scripts/install-udev-rules.sh
~/.local/bin/linuxcue gui
```

The development installer keeps the virtual environment in
`~/.local/share/linuxcue/venv` so it also works when the repository is on a USB
or shared VM mount that does not allow symlinks.
It creates a direct launcher at `~/.local/bin/linuxcue`. In fish you can also
activate the venv with `source ~/.local/share/linuxcue/venv/bin/activate.fish`.

## Roadmap

1. Add a write backend for specific Corsair devices.
2. Implement RGB zones and hardware effect translation.
3. Add fan and pump telemetry/control where Linux kernel interfaces exist.
4. Build a GTK or Qt desktop UI.
5. Add udev rules, packaging, and background daemon support.

## Current target devices

- Corsair K95 RGB Platinum
- Corsair M65 Pro RGB
- Corsair Virtuoso SE
- Corsair Virtuoso RGB Wireless USB Receiver

## Next Linux capture step

Run `linuxcue probe-template` to get the exact command checklist we need on your Linux machine.
Once you share the outputs for your three devices, I can turn the current scaffolding into model-specific backends.

## Offline workflow

You do not need a running Linux machine to continue building the software.

1. Create mock fixtures with `linuxcue mock-probe k95`, `linuxcue mock-probe m65`, `linuxcue mock-probe virtuoso-se`, and `linuxcue mock-probe virtuoso-rgb-wireless-receiver`.
2. Create a keyboard-focused profile with `linuxcue init-k95-profile k95-default`.
3. Run `linuxcue apply k95-default` to see the per-device action plan and the prepared K95 packet layout.

The generated fixture files live in `fixtures/` and can later be replaced or extended with real probe data from Linux.

## GUI

Start the Qt Quick/QML dashboard with:

```bash
linuxcue gui
linuxcue qml-gui
```

The QML dashboard is the only supported design path for an iCUE-like layout with compact
device cards, profile sidebar, keyboard preview, lighting layers, effect cards,
quick zones, color controls, and the existing Python/HID backend underneath.

## Updates

The QML dashboard checks GitHub on startup and can also be checked manually with
the `Update pruefen` button in the sidebar. The check compares both the newest
GitHub release tag and the latest commit on the repository default branch, so it
also detects code changes when no new release was published yet.

Manual CLI check:

```bash
linuxcue check-update
```

Install the newest GitHub source and rebuild the CachyOS package:

```bash
linuxcue install-update --yes
```

The updater downloads the repository to `~/.cache/linuxcue/source`, runs the
included CachyOS package installer, reloads udev rules, and leaves the installed
files managed through `pacman`. From an existing checkout you can still update
manually with:

```bash
git pull
bash scripts/install-cachyos-package.sh
```

## K95 backend progress

The K95 path now has a dedicated backend module in [src/linuxcue/k95_backend.py](src/linuxcue/k95_backend.py).
It currently provides:

- a zoned K95 layout model
- a default color profile for major keyboard areas
- prepared lighting packet objects shaped from the captured K95 RGB Platinum HID descriptor
- unnumbered 64-byte output-report frames for every K95 lighting zone
- OpenRGB-derived Corsair Peripheral command candidates for software lighting and keyboard color submit (`07 05 02`, then `07 28 ...`)
- a Linux-only hidapi write path for sending those frames to real hardware

## Live K95 writing

The command `linuxcue write-k95-live <profile>` is the real hardware path.
It requires:

- Linux
- `pip install -e .[hid]`
- permission to access the Corsair HID device, often via udev rules or root

Without a Linux machine I could not verify the hardware write itself, but the frame generation and CLI flow are implemented and tested in mock mode.

## M65 backend progress

The M65 path now has its own backend in [src/linuxcue/m65_backend.py](src/linuxcue/m65_backend.py).
It currently provides:

- a default DPI ladder including sniper mode
- RGB packets for logo and DPI indicator lighting
- a default button-map packet
- a Linux-only hidapi write path for live hardware sending

## Virtuoso backend progress

The Virtuoso path now has its own backend in [src/linuxcue/virtuoso_backend.py](src/linuxcue/virtuoso_backend.py).
It currently provides:

- three default EQ presets for the Virtuoso SE headset
- a 10-band EQ model per preset, while keeping bass/mids/treble compatibility fields
- RGB accent-ring packets
- headset control packets for sidetone, mic level, sleep timer, and voice prompts
- a battery-poll packet
- receiver-side wireless link packets for the Virtuoso USB dongle
- 63-byte output payloads on report ID `0x02`, matching the captured Virtuoso/receiver HID descriptors
- a Linux-only hidapi write path for live hardware sending
