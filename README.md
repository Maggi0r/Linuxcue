# linuxcue

## Deutsch

`linuxcue` ist ein Linux-Control-Center fuer Corsair/iCUE-Hardware. Ziel ist
eine einfache Desktop-App fuer Linux, die sich fuer normale Nutzer so
unkompliziert anfuehlt wie iCUE unter Windows: installieren, starten, Geraet
auswaehlen, Profil anpassen.

Das Projekt waechst geraeteweise. Aktuell gibt es bereits eine Qt Quick/QML
Oberflaeche, Profilverwaltung, Live-Lighting, PipeWire-Equalizer fuer Headsets,
Update-Pruefung und einen sicheren Bericht-Workflow fuer noch nicht unterstuetzte
Corsair-Geraete.

### Einfache Installation

Auf CachyOS oder anderen Arch-basierten Systemen:

```bash
curl -fsSL https://raw.githubusercontent.com/Maggi0r/Linuxcue/main/install.sh | bash
```

Wenn du das Repository bereits heruntergeladen hast:

```bash
bash install.sh
```

Der Installer laedt oder aktualisiert linuxcue unter
`~/.cache/linuxcue/source`, installiert die benoetigten Arch/CachyOS-Pakete,
baut ein lokales Paket mit `makepkg`, installiert es mit `pacman`, laedt die
udev-Regeln neu und legt den Desktop-Starter an.

Start nach der Installation:

```bash
linuxcue qml-gui
```

Oder starte `linuxcue Control Center` aus dem Anwendungsmenue.

### Aktueller Stand

- Qt Quick/QML Dashboard mit Geraetekacheln, Profil-Seitenleiste, Live Write,
  Update-Pruefung und iCUE-aehnlichen Geraeteseiten.
- K95 RGB Platinum mit deutschem/ISO-Tastaturlayout, Beleuchtungsschichten,
  Einzeltastenfarben, Schnellzonen, Rahmenauswahl und Live-Write-Pfad.
- M65 Pro RGB mit DPI/RGB-Profilmodell und Live-Write-Pfad.
- Virtuoso SE mit RGB/Akzentsteuerung, 15-Band PipeWire-EQ, Presets,
  Ausgabelautstaerke, Mikrofonlevel und Nebenton.
- VOID Elite Wireless Dongle/Headset-Erkennung mit sicherem PipeWire-EQ,
  Headset-Audioreglern und Akkuanzeige, wenn Linux den Akku meldet.
- NVIDIA-Broadcast-Seite fuer die optionale Installation des externen Projekts
  `nvidia-broadcast-linux`.
- Unbekannte Corsair/iCUE-Geraete werden sichtbar angezeigt statt ignoriert.
  Nutzer koennen einen vollstaendigen Geraetebericht speichern und an GitHub
  anhaengen.
- GitHub-basierte Update-Pruefung und Paket-Neubau direkt aus GUI oder CLI.

### Unterstuetzte und geplante Geraete

Aktuell gemappte Geraete:

- Corsair K95 RGB Platinum
- Corsair M65 Pro RGB
- Corsair Virtuoso SE
- Corsair Virtuoso RGB Wireless Receiver
- Corsair VOID Elite Wireless Dongle/Headset Audio-Profil

Unbekannte Corsair-Geraete erscheinen als `Treiber geplant`. linuxcue sendet an
diese Geraete keine Schreibbefehle, bis Report-IDs, Endpunkte und Befehle sauber
gemappt sind.

### Geraeteberichte fuer neue Hardware

Wenn linuxcue ein noch nicht unterstuetztes iCUE-Geraet findet, waehle die
Geraetekachel aus und klicke auf `Vollstaendigen Bericht speichern`. Die App
fragt nach dem Speicherort fuer die JSON-Datei. Haenge diese Datei anschliessend
an ein GitHub-Issue mit dem Template `Device support request` an.

Der Bericht enthaelt Geraeteidentitaet, HID-Descriptoren und lesbare
Feature-Reports. Er ist dafuer gedacht, neue Geraete hinzuzufuegen, ohne dass
normale Nutzer Terminalbefehle ausfuehren muessen.

Fuer Entwickler kann ein Bericht lokal in eine Startvorlage umgewandelt werden:

```bash
linuxcue prepare-device-support /pfad/zum/linuxcue-device-report.json
```

### Updates

Die GUI prueft GitHub und hebt den Update-Button hervor, wenn ein neuer Release
oder ein neuerer `main`-Commit verfuegbar ist.

Manuelle Befehle:

```bash
linuxcue check-update
linuxcue install-update --yes
```

Der Updater laedt die aktuelle Quelle nach `~/.cache/linuxcue/source`, baut das
lokale Arch-Paket neu, installiert es mit `pacman`, laedt udev-Regeln neu und
versucht anschliessend, die GUI neu zu starten.

Wenn `pacman` eine Datenbank-Sperre meldet, schliesse zuerst andere
Paketmanager. Der Installer wartet auf aktive Sperren und entfernt nur veraltete
Locks ohne laufenden Besitzer.

### Audio und Equalizer

linuxcue nutzt fuer Headset-EQ einen nativen PipeWire-Pfad statt manueller
EasyEffects-Fernsteuerung. Virtuoso- und VOID-Seiten bieten Live-EQ-Slider,
Presets, Ausgabelautstaerke, Mikrofonlevel und Nebenton, soweit der Linux-
Audiostack das erlaubt.

EasyEffects bleibt als Kompatibilitaets-Fallback moeglich, der normale UI-Pfad
ist aber der von linuxcue verwaltete PipeWire-EQ.

### Entwicklerinstallation

Fuer Entwicklung ohne Paketinstallation:

```bash
bash scripts/install-cachyos-dev.sh
bash scripts/install-udev-rules.sh
~/.local/bin/linuxcue qml-gui
```

Die Entwicklungsinstallation legt die virtuelle Umgebung unter
`~/.local/share/linuxcue/venv` ab. Das funktioniert auch auf USB, NTFS, exFAT
und VM-Shared-Folders, wo Symlinks manchmal unzuverlaessig sind.

### Manueller Paketbau

```bash
sudo pacman -S --needed base-devel git python python-build python-installer python-setuptools python-wheel python-hidapi python-numpy python-pyusb libpulse pipewire pipewire-pulse wireplumber pyside6 qt6-declarative easyeffects lsp-plugins-lv2
bash scripts/build-cachyos-package.sh
sudo pacman -U packaging/arch/linuxcue-0.1.1-1-any.pkg.tar.zst
sudo udevadm control --reload-rules
sudo udevadm trigger
linuxcue qml-gui
```

### Nuetzliche Entwicklerbefehle

```bash
linuxcue doctor
linuxcue devices
linuxcue capabilities
linuxcue capture-descriptors
linuxcue map-devices
linuxcue prepare-device-support /pfad/zum/report.json
linuxcue qml-gui
```

### Projektziel

linuxcue soll zu einer echten Linux-Alternative zu iCUE reifen:

- einfache Installation und Self-Updates
- sichere Standardwerte fuer normale Nutzer
- Geraeteberichte fuer noch nicht unterstuetzte Hardware
- geraetespezifische Backends aus echten Captures
- Live-RGB, EQ, Akku- und Geraetesteuerung in einer Desktop-App

Geraeteunterstuetzung wird absichtlich vorsichtig erweitert. linuxcue zeigt
unbekannte Hardware an, schreibt aber erst auf ein Geraet, wenn das Mapping
sicher genug ist.

---

## English

`linuxcue` is a Linux-first control center for Corsair/iCUE hardware. The goal
is to become an easy desktop application for people who want iCUE-like device
control on Linux without manually juggling scripts, JSON files, or command-line
tools.

The project is growing device by device. It already provides a Qt Quick/QML
desktop UI, profile management, live lighting work, PipeWire based headset EQ,
update checks, and a safe workflow for collecting reports from unsupported
Corsair devices.

### Easy Install

On CachyOS or Arch-based systems:

```bash
curl -fsSL https://raw.githubusercontent.com/Maggi0r/Linuxcue/main/install.sh | bash
```

If you already downloaded the repository:

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

### Current Status

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

### Supported And Planned Devices

Current mapped devices:

- Corsair K95 RGB Platinum
- Corsair M65 Pro RGB
- Corsair Virtuoso SE
- Corsair Virtuoso RGB Wireless receiver
- Corsair VOID Elite Wireless dongle/headset audio profile

Unknown Corsair devices can be detected as `Treiber geplant`. linuxcue does not
send write commands to those devices until their report IDs, endpoints, and
commands are mapped.

### Unknown Device Reports

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

### Updates

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

### Audio And EQ

linuxcue uses a native PipeWire audio path for headset EQ instead of relying on
manual EasyEffects control. The Virtuoso and VOID pages expose live EQ sliders,
presets, output volume, mic level, and sidetone where the Linux audio stack
allows it.

EasyEffects remains a compatibility fallback for setups that prefer it, but the
normal UI path is the linuxcue-managed PipeWire EQ.

### Development Install

For development without installing a package:

```bash
bash scripts/install-cachyos-dev.sh
bash scripts/install-udev-rules.sh
~/.local/bin/linuxcue qml-gui
```

The development installer keeps its virtual environment under
`~/.local/share/linuxcue/venv` so it also works from USB, NTFS, exFAT, and VM
shared folders where symlinks can be unreliable.

### Manual Package Build

```bash
sudo pacman -S --needed base-devel git python python-build python-installer python-setuptools python-wheel python-hidapi python-numpy python-pyusb libpulse pipewire pipewire-pulse wireplumber pyside6 qt6-declarative easyeffects lsp-plugins-lv2
bash scripts/build-cachyos-package.sh
sudo pacman -U packaging/arch/linuxcue-0.1.1-1-any.pkg.tar.zst
sudo udevadm control --reload-rules
sudo udevadm trigger
linuxcue qml-gui
```

### Useful Developer Commands

```bash
linuxcue doctor
linuxcue devices
linuxcue capabilities
linuxcue capture-descriptors
linuxcue map-devices
linuxcue prepare-device-support /path/to/report.json
linuxcue qml-gui
```

### Project Direction

linuxcue is intended to mature into a real Linux alternative to iCUE:

- simple installation and self-updates
- safe defaults for normal users
- device reports for unsupported hardware
- per-device backends added from real captures
- live RGB, EQ, battery, and device controls in one desktop UI

Device support is intentionally added cautiously. linuxcue shows unsupported
hardware, but it will not write to a device until the command mapping is known
well enough to avoid unsafe behavior.
