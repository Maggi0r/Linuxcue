# linuxcue

`linuxcue` is a Linux-first control center for Corsair/iCUE hardware. The goal
is to become an easy desktop application for people who want iCUE-like device
control on Linux without manually juggling scripts, JSON files, or command-line
tools.

The project is still growing device by device, but it already provides a Qt
Quick/QML desktop UI, profile management, live lighting work, PipeWire based
headset EQ, update checks, and a safe workflow for collecting reports from
unknown Corsair devices.

## Easy Install

On CachyOS or Arch-based systems, use the bootstrap installer:

```bash
curl -fsSL https://raw.githubusercontent.com/Maggi0r/Linuxcue/main/install.sh | bash
```

If you already downloaded the repository, run:

```bash
bash install.sh
```

The installer downloads or updates the source in `~/.cache/linuxcue/source`,
installs the needed Arch/CachyOS packages, builds a local package with
`makepkg`, installs it with `pacman`, reloads udev rules, and adds the desktop
launcher.

Start linuxcue after installation:

```bash
linuxcue qml-gui
```

You can also launch `linuxcue Control Center` from the desktop menu.

## What Works Today

- Qt Quick/QML dashboard with device cards, profile sidebar, live write flow,
  update checks, and iCUE-like device pages.
- K95 RGB Platinum keyboard lighting with German/ISO layout support, lighting
  layers, per-key coloring, quick zones, selection frames, and live write path.
- M65 Pro RGB mouse profile support with DPI/RGB data model and live write path.
- Virtuoso SE headset support with RGB/accent handling, 15-band PipeWire EQ,
  EQ presets, output volume, mic level, and sidetone controls.
- VOID Elite Wireless dongle/headset recognition with safe PipeWire EQ,
  headset audio controls, and system battery display where Linux exposes it.
- NVIDIA Broadcast integration page for optionally installing the external
  `nvidia-broadcast-linux` project.
- Unknown Corsair/iCUE devices are shown safely instead of being ignored. Users
  can save a full device report and attach it to a GitHub support request.
- GitHub based update check and package rebuild from inside the GUI or CLI.

## Supported And Planned Devices

Current mapped devices:

- Corsair K95 RGB Platinum
- Corsair M65 Pro RGB
- Corsair Virtuoso SE
- Corsair Virtuoso RGB Wireless receiver
- Corsair VOID Elite Wireless dongle/headset audio profile

Unknown Corsair devices can be detected as `Treiber geplant`. linuxcue does not
send write commands to those devices until their report IDs, endpoints, and
commands are mapped.

## Unknown Device Reports

When linuxcue finds an unsupported iCUE device, select its card and click
`Vollstaendigen Bericht speichern`. The app asks where to save the JSON report.
Attach that report to a GitHub issue using the `Device support request`
template.

The report contains device identity, HID descriptors, and readable feature
reports. It is designed to help developers add new devices without asking normal
users to run terminal commands.

For local developer preparation, the same report can be converted into a starter
implementation plan:

```bash
linuxcue prepare-device-support /path/to/linuxcue-device-report.json
```

## Updates

The GUI checks GitHub and highlights the update button when a newer release or
newer `main` commit is available.

Manual commands:

```bash
linuxcue check-update
linuxcue install-update --yes
```

The updater downloads the latest source into `~/.cache/linuxcue/source`, rebuilds
the local Arch package, installs it with `pacman`, reloads udev rules, and then
tries to restart the GUI.

If `pacman` reports a database lock, close other package managers first. The
installer waits for active locks and removes only stale locks that have no
running owner.

## Audio And EQ

linuxcue uses a native PipeWire audio path for headset EQ instead of relying on
manual EasyEffects control. The Virtuoso and VOID pages expose live EQ sliders,
presets, output volume, mic level, and sidetone where the Linux audio stack
allows it.

EasyEffects remains a compatibility fallback for setups that prefer it, but the
normal UI path is the linuxcue-managed PipeWire EQ.

## Development Install

For development without installing a package:

```bash
bash scripts/install-cachyos-dev.sh
bash scripts/install-udev-rules.sh
~/.local/bin/linuxcue qml-gui
```

The development installer keeps its virtual environment under
`~/.local/share/linuxcue/venv` so it also works from USB, NTFS, exFAT, and VM
shared folders where symlinks can be unreliable.

## Manual Package Build

```bash
sudo pacman -S --needed base-devel git python python-build python-installer python-setuptools python-wheel python-hidapi python-numpy python-pyusb libpulse pipewire pipewire-pulse wireplumber pyside6 qt6-declarative easyeffects lsp-plugins-lv2
bash scripts/build-cachyos-package.sh
sudo pacman -U packaging/arch/linuxcue-0.1.0-1-any.pkg.tar.zst
sudo udevadm control --reload-rules
sudo udevadm trigger
linuxcue qml-gui
```

## Useful Developer Commands

```bash
linuxcue doctor
linuxcue devices
linuxcue capabilities
linuxcue capture-descriptors
linuxcue map-devices
linuxcue prepare-device-support /path/to/report.json
linuxcue qml-gui
```

## Project Direction

linuxcue is intended to mature into a real Linux alternative to iCUE:

- simple installation and self-updates
- safe defaults for normal users
- device reports for unsupported hardware
- per-device backends added from real captures
- live RGB, EQ, battery, and device controls in one desktop UI

Device support is intentionally added cautiously. linuxcue shows unsupported
hardware, but it will not write to a device until the command mapping is known
well enough to avoid unsafe behavior.
