from __future__ import annotations

import sys
import json
import base64
import copy
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse
import xml.etree.ElementTree as ET

QT_QML_IMPORT_ERROR: Exception | None = None
try:
    from PySide6.QtCore import Property, QObject, QTimer, QUrl, Signal, Slot
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
except Exception as exc:  # pragma: no cover - depends on optional GUI runtime
    QT_QML_IMPORT_ERROR = exc
    QObject = object  # type: ignore[assignment, misc]
    Signal = lambda *args, **kwargs: None  # type: ignore[assignment]
    Slot = lambda *args, **kwargs: (lambda fn: fn)  # type: ignore[assignment]
    Property = lambda *args, **kwargs: None  # type: ignore[assignment]

from .service import LinuxCueService, SYSTEM_PROFILE_FLAG
from .k95_backend import K95_OPENRGB_ZONE_ORDER
from .m65_backend import M65_RGB_ZONES
from .m65_monitor import M65DpiInputMonitor
from .models import AudioPreset, CoolingChannel, DpiStage, HeadsetSetting, LightingZone, Profile
from .easyeffects_export import ICUE_EQ_FREQUENCIES, expand_eq_bands

M65_DPI_ORDER = ("stage1", "stage2", "stage3", "stage4", "stage5", "sniper")
M65_DPI_DEFAULTS: dict[str, tuple[int, str]] = {
    "stage1": (800, "#ff001f"),
    "stage2": (1500, "#ffffff"),
    "stage3": (3000, "#04ff00"),
    "stage4": (6000, "#ffe600"),
    "stage5": (9000, "#12c8ff"),
    "sniper": (400, "#1ecfdf"),
}
M65_DPI_DEFAULT_ACTIVE = "stage2"
VIRTUOSO_EQ_MIN = -48
VIRTUOSO_EQ_MAX = 48
VIRTUOSO_EQ_LABELS = ["31", "45", "63", "90", "125", "180", "250", "355", "500", "710", "1k", "2k", "4k", "8k", "16k"]
VIRTUOSO_LOUDNESS_BANDS = [7, 6, 5, 4, 3, 1, 0, -1, -1, 0, 1, 3, 5, 6, 5]
VIRTUOSO_FLAT_BANDS = [0] * len(ICUE_EQ_FREQUENCIES)
VIRTUOSO_SYSTEM_PRESETS = {
    "flat": VIRTUOSO_FLAT_BANDS,
    "loudness": VIRTUOSO_LOUDNESS_BANDS,
    "bass boost": [4, 5, 6, 5, 4, 2, 0, -1, -3, -3, -3, -2, 1, 2, 2],
}
VIRTUOSO_PROTECTED_PRESETS = set(VIRTUOSO_SYSTEM_PRESETS) | {
    "clear chat",
    "fps",
    "fps competition",
    "movie theater",
    "music",
    "pure direct",
    "voice",
}


def _device_slug(target: str, family: str) -> str:
    text = f"{target} {family}".casefold()
    if "void elite" in text:
        return "void-elite"
    if "receiver" in text:
        return "receiver"
    if "virtuoso" in text or "headset" in text:
        return "virtuoso-se"
    if "m65" in text or "mouse" in text:
        return "m65"
    if "k95" in text or "keyboard" in text:
        return "k95"
    return "unknown"


def _device_title(slug: str) -> str:
    if slug.startswith("unknown-"):
        return "Unbekanntes Corsair-Geraet"
    return {
        "k95": "K95 RGB Platinum",
        "m65": "M65 Pro RGB",
        "virtuoso-se": "Virtuoso SE",
        "void-elite": "VOID Elite Wireless Dongle",
        "receiver": "Wireless Receiver",
    }.get(slug, "Corsair Device")


def _device_meta(slug: str) -> tuple[str, str]:
    if slug.startswith("unknown-"):
        return ("Erkannt, noch nicht unterstuetzt", "Geraetebericht")
    return {
        "k95": ("Layout: ISO-DE", "RGB keyboard"),
        "m65": ("DPI Profile: Default", "Mouse control"),
        "virtuoso-se": ("Audio Profile: EasyEffects", "Headset EQ"),
        "void-elite": ("Erkannt, Treiber geplant", "Wireless Dongle"),
        "receiver": ("Link + battery status", "USB receiver"),
    }.get(slug, ("Detected", "Corsair HID"))


if QT_QML_IMPORT_ERROR is None:

    class LinuxCueQmlBridge(QObject):
        dataChanged = Signal()
        updateStatusReady = Signal(str)
        statusReady = Signal(str)

        def __init__(self) -> None:
            super().__init__()
            self.service = LinuxCueService()
            self._profiles: list[dict[str, Any]] = []
            self._devices: list[dict[str, Any]] = []
            self._current_profile = ""
            self._current_device = ""
            self._current_device_details: dict[str, Any] = {}
            self._status = "Ready"
            self._lighting_layers: list[dict[str, Any]] = []
            self._k95_key_colors: dict[str, str] = {}
            self._virtuoso_presets: list[dict[str, Any]] = []
            self._virtuoso_eq_bands: list[int] = [0] * len(ICUE_EQ_FREQUENCIES)
            self._virtuoso_accent_color = "#1ecfdf"
            self._virtuoso_sidetone = 35
            self._virtuoso_mic_level = 72
            self._virtuoso_volume = 100
            self._virtuoso_sleep_timer = 20
            self._virtuoso_voice_prompts = True
            self._virtuoso_eq_backend = "pipewire"
            self._m65_lighting_zones: list[dict[str, Any]] = []
            self._m65_dpi_presets: list[dict[str, Any]] = []
            self._m65_dpi_stages: list[dict[str, Any]] = []
            self._m65_previous_dpi_name = "stage1"
            self._virtuoso_eq_apply_running = False
            self._virtuoso_eq_apply_pending: str | None = None
            self._virtuoso_eq_apply_lock = threading.Lock()
            self._m65_dpi_monitor = M65DpiInputMonitor()
            self._m65_input_timer = QTimer(self)
            self._m65_input_timer.setInterval(80)
            self._m65_input_timer.timeout.connect(self._poll_m65_dpi_input)
            self._copied_profile: dict[str, Any] | None = None
            self._update_available = False
            self.updateStatusReady.connect(self._apply_update_status)
            self.statusReady.connect(self._apply_status)
            self.refresh()
            QTimer.singleShot(4500, self.checkForUpdates)

        @Property("QVariantList", notify=dataChanged)
        def profiles(self) -> list[dict[str, Any]]:
            return self._profiles

        @Property("QVariantList", notify=dataChanged)
        def devices(self) -> list[dict[str, Any]]:
            return self._devices

        @Property("QVariantList", notify=dataChanged)
        def lightingLayers(self) -> list[dict[str, Any]]:
            return self._lighting_layers

        @Property("QVariantMap", notify=dataChanged)
        def k95KeyColors(self) -> dict[str, str]:
            return self._k95_key_colors

        @Property("QVariantList", notify=dataChanged)
        def virtuosoPresets(self) -> list[dict[str, Any]]:
            return self._virtuoso_presets

        @Property("QVariantList", notify=dataChanged)
        def virtuosoEqBands(self) -> list[int]:
            return self._virtuoso_eq_bands

        @Property("QVariantList", notify=dataChanged)
        def virtuosoEqBandLabels(self) -> list[str]:
            return VIRTUOSO_EQ_LABELS

        @Property(str, notify=dataChanged)
        def virtuosoAccentColor(self) -> str:
            return self._virtuoso_accent_color

        @Property(int, notify=dataChanged)
        def virtuosoSidetone(self) -> int:
            return self._virtuoso_sidetone

        @Property(int, notify=dataChanged)
        def virtuosoMicLevel(self) -> int:
            return self._virtuoso_mic_level

        @Property(int, notify=dataChanged)
        def virtuosoVolume(self) -> int:
            return self._virtuoso_volume

        @Property(int, notify=dataChanged)
        def virtuosoSleepTimer(self) -> int:
            return self._virtuoso_sleep_timer

        @Property(bool, notify=dataChanged)
        def virtuosoVoicePrompts(self) -> bool:
            return self._virtuoso_voice_prompts

        @Property("QVariantList", notify=dataChanged)
        def m65LightingZones(self) -> list[dict[str, Any]]:
            return self._m65_lighting_zones

        @Property("QVariantList", notify=dataChanged)
        def m65DpiPresets(self) -> list[dict[str, Any]]:
            return self._m65_dpi_presets

        @Property("QVariantList", notify=dataChanged)
        def m65DpiStages(self) -> list[dict[str, Any]]:
            return self._m65_dpi_stages

        @Property(str, notify=dataChanged)
        def currentProfile(self) -> str:
            return self._current_profile

        @Property(str, notify=dataChanged)
        def currentDevice(self) -> str:
            return self._current_device

        @Property("QVariantMap", notify=dataChanged)
        def currentDeviceDetails(self) -> dict[str, Any]:
            return self._current_device_details

        @Property(str, notify=dataChanged)
        def status(self) -> str:
            return self._status

        @Property(bool, notify=dataChanged)
        def updateAvailable(self) -> bool:
            return self._update_available

        @Slot(str)
        def setStatusMessage(self, message: str) -> None:
            self._status = message
            self.dataChanged.emit()

        @Slot()
        def refresh(self) -> None:
            summaries = self.service.list_profile_summaries()
            self._profiles = self._main_profile_summaries(summaries)
            if not self._current_profile and self._profiles:
                self._current_profile = str(self._profiles[0]["name"])
                self._profiles[0]["selected"] = True
            if self._profiles and not any(item["name"] == self._current_profile for item in self._profiles):
                self._current_profile = str(self._profiles[0]["name"])
                for item in self._profiles:
                    item["selected"] = item["name"] == self._current_profile
            self._devices = self._device_cards()
            if self._devices and not any(item["slug"] == self._current_device for item in self._devices):
                self._current_device = str(self._devices[0]["slug"])
            if not self._devices:
                self._current_device = ""
            self._sync_current_device_details()
            self._refresh_lighting_layers()
            self._refresh_virtuoso_state()
            self._refresh_m65_state()
            self._sync_m65_dpi_monitor()
            self._status = f"Devices: {len(self._devices)} connected"
            self.dataChanged.emit()

        @Slot(str)
        def selectProfile(self, name: str) -> None:
            self._current_profile = name
            for item in self._profiles:
                item["selected"] = item["name"] == name
            self._devices = self._device_cards()
            if self._devices and not any(item["slug"] == self._current_device for item in self._devices):
                self._current_device = str(self._devices[0]["slug"])
            if not self._devices:
                self._current_device = ""
            self._sync_current_device_details()
            self._refresh_lighting_layers()
            self._refresh_virtuoso_state()
            self._refresh_m65_state()
            self._sync_m65_dpi_monitor()
            self._status = f"Profil aktiv: {name}"
            self.dataChanged.emit()

        @Slot(str)
        def selectDevice(self, slug: str) -> None:
            self._current_device = slug
            for item in self._devices:
                item["selected"] = item["slug"] == slug
            if slug == "virtuoso-se":
                self._refresh_virtuoso_state()
            if slug == "m65":
                self._refresh_m65_state()
            self._sync_current_device_details()
            self._sync_m65_dpi_monitor()
            self._status = f"Geraet aktiv: {self._current_device_details.get('title', _device_title(slug))}"
            self.dataChanged.emit()

        @Slot(str)
        def exportDeviceReport(self, url: str = "") -> None:
            if not self._current_device:
                self._status = "Kein Geraet fuer Bericht ausgewaehlt."
                self.dataChanged.emit()
                return
            path = self._path_from_url(url) if url else None
            if path is None:
                path = self._default_device_report_path(self._current_device)
            if path.suffix.casefold() != ".json":
                path = path.with_suffix(".json")
            try:
                saved = self._write_device_report(self._current_device, path)
            except Exception as exc:
                self._status = f"Geraetebericht fehlgeschlagen: {exc}"
            else:
                self._status = f"Geraetebericht gespeichert: {saved}. Bitte als GitHub-Issue 'Device support request' anhaengen."
            self.dataChanged.emit()

        @Slot(str, str)
        def createProfile(self, target: str, name: str) -> None:
            clean = self._unique_profile_name(name.strip() or f"{target}-profile")
            profile = self.service.create_profile_for_target(target, clean)
            self.service.save_profile(profile)
            self._current_profile = profile.name
            self.refresh()
            self._status = f"Profil erstellt: {profile.name}"
            self.dataChanged.emit()

        @Slot(str)
        def createProfileSet(self, name: str) -> None:
            group_name = self._unique_profile_name(name.strip() or "Neues Profil")
            group = Profile(
                name=group_name,
                target_device="profile-set",
                target_family="bundle",
                profile_group=group_name,
                group_role="set",
                description=f"linuxcue profile set '{group_name}'.",
                lighting=[],
                cooling=[],
            )
            profiles = [
                group,
                self.service.create_profile_for_target("k95", self._unique_profile_name(f"{group_name}-k95")),
                self.service.create_profile_for_target("m65", self._unique_profile_name(f"{group_name}-m65")),
                self.service.create_profile_for_target("virtuoso-se", self._unique_profile_name(f"{group_name}-virtuoso")),
            ]
            roles = ["set", "keyboard", "mouse", "headset"]
            for profile, role in zip(profiles, roles):
                profile.profile_group = group_name
                profile.group_role = role
                self.service.save_profile(profile)
            self._current_profile = group_name
            self.refresh()
            self._status = f"Profil erstellt: {group_name}"
            self.dataChanged.emit()

        @Slot(str)
        def deleteProfile(self, name: str) -> None:
            if not name:
                return
            deleted = self._delete_profile_bundle(name)
            if deleted and self._current_profile == name:
                self._current_profile = ""
            self.refresh()
            self._status = f"Profil geloescht: {name}" if deleted else f"Profil konnte nicht geloescht werden: {name}"
            self.dataChanged.emit()

        @Slot(str)
        def duplicateProfile(self, name: str) -> None:
            profiles = self._profile_bundle(name)
            if not profiles:
                self._status = f"Profil nicht gefunden: {name}"
                self.dataChanged.emit()
                return
            copied_names = self._save_bundle_copy(profiles, f"{name} Kopie")
            self._current_profile = copied_names[0]
            self.refresh()
            self._status = f"Kopie erstellt: {self._current_profile}"
            self.dataChanged.emit()

        @Slot(str)
        def copyProfile(self, name: str) -> None:
            profiles = self._profile_bundle(name)
            if not profiles:
                self._status = f"Profil nicht gefunden: {name}"
                self.dataChanged.emit()
                return
            self._copied_profile = {"profiles": [profile.to_dict() for profile in profiles]}
            self._status = f"Profil kopiert: {name}"
            self.dataChanged.emit()

        @Slot()
        def pasteProfile(self) -> None:
            if not self._copied_profile:
                self._status = "Keine Profilkopie im Zwischenspeicher."
                self.dataChanged.emit()
                return
            payload = copy.deepcopy(self._copied_profile)
            profiles = [self._profile_from_payload(item) for item in payload.get("profiles", [])]
            if not profiles and "name" in payload:
                profiles = [self._profile_from_payload(payload)]
            if not profiles:
                self._status = "Kopiertes Profil ist leer."
                self.dataChanged.emit()
                return
            copied_names = self._save_bundle_copy(profiles, f"{profiles[0].name} Kopie")
            self._current_profile = copied_names[0]
            self.refresh()
            self._status = f"Profil eingefuegt: {self._current_profile}"
            self.dataChanged.emit()

        @Slot(str)
        def importProfile(self, url: str) -> None:
            path = self._path_from_url(url)
            if path is None or not path.exists():
                self._status = f"Importdatei nicht gefunden: {url}"
                self.dataChanged.emit()
                return
            try:
                if path.suffix.casefold() == ".cueprofile":
                    names = self._import_cueprofile(path)
                    if names:
                        self._current_profile = names[0]
                    self.refresh()
                    self._status = f"iCUE Import OK: {len(names)} Profile"
                    self.dataChanged.emit()
                    return
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and "profiles" in payload:
                    profiles = [self._profile_from_payload(item) for item in payload.get("profiles", [])]
                    names = self._save_bundle_copy(profiles, str(payload.get("name") or path.stem))
                    self._current_profile = names[0] if names else ""
                else:
                    profile = self._profile_from_payload(payload)
                    profile.name = self._unique_profile_name(profile.name)
                    self._clear_system_profile_flags(profile)
                    self.service.save_profile(profile)
                    self._current_profile = profile.name
                self.refresh()
                self._status = f"Profil importiert: {self._current_profile}"
            except Exception as exc:
                self._status = f"Profilimport fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(str, str)
        def exportProfile(self, name: str, url: str) -> None:
            profiles = self._profile_bundle(name)
            path = self._path_from_url(url)
            if not profiles:
                self._status = "Kein Profil fuer Export ausgewaehlt."
                self.dataChanged.emit()
                return
            if path is None:
                self._status = f"Exportpfad ist ungueltig: {url}"
                self.dataChanged.emit()
                return
            suffix = path.suffix.casefold()
            if suffix not in {".json", ".cueprofile"}:
                path = path.with_suffix(".json")
            try:
                path.parent.mkdir(parents=True, exist_ok=True)
                if path.suffix.casefold() == ".cueprofile":
                    path.write_text(self._export_cueprofile_xml(profiles), encoding="utf-8")
                else:
                    payload: dict[str, Any]
                    if len(profiles) == 1:
                        payload = profiles[0].to_dict()
                    else:
                        payload = {"format": "linuxcue-profile-set", "profiles": [profile.to_dict() for profile in profiles]}
                    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
                self._status = f"Profil exportiert: {path}"
            except Exception as exc:
                self._status = f"Profilexport fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot()
        def checkForUpdates(self) -> None:
            self._status = "Pruefe GitHub auf Updates..."
            self.dataChanged.emit()
            thread = threading.Thread(target=self._check_for_updates_worker, daemon=True)
            thread.start()

        def _check_for_updates_worker(self) -> None:
            try:
                from .updater import check_github_update

                info = check_github_update()
                self.updateStatusReady.emit(self._format_update_status(info))
            except Exception as exc:
                self.updateStatusReady.emit(f"Update-Pruefung fehlgeschlagen: {exc}")

        def _format_update_status(self, info: dict[str, Any]) -> str:
            if not info.get("update_available"):
                return str(info.get("recommendation") or "linuxcue ist aktuell.")
            parts: list[str] = []
            release = info.get("latest_release")
            if info.get("release_update_available") and isinstance(release, dict):
                parts.append(f"Release {release.get('tag')}")
            latest_commit = info.get("latest_commit")
            if info.get("source_update_available") and isinstance(latest_commit, dict):
                parts.append(f"GitHub-Code {latest_commit.get('short_sha')}")
            detail = " / ".join(part for part in parts if part) or "Update"
            return f"Update verfuegbar: {detail}. Nutze 'Update installieren'."

        @Slot(str)
        def _apply_update_status(self, message: str) -> None:
            self._status = message
            self._update_available = message.startswith("Update verfuegbar:")
            self.dataChanged.emit()

        @Slot(str)
        def _apply_status(self, message: str) -> None:
            self._status = message
            self.dataChanged.emit()

        @Slot()
        def installUpdate(self) -> None:
            if not sys.platform.startswith("linux"):
                self._status = "Update-Installation ist nur auf Linux/CachyOS aktiv."
                self.dataChanged.emit()
                return
            if not shutil.which("bash"):
                self._status = "Update nicht moeglich: bash wurde nicht gefunden."
                self.dataChanged.emit()
                return
            script_path = Path("/tmp/linuxcue-update-and-restart.sh")
            script_path.write_text(
                """#!/usr/bin/env bash
set +e
restart_log=/tmp/linuxcue-restart.log
gui_log=/tmp/linuxcue-gui-restart.log
: > "$restart_log"
: > "$gui_log"
log() {
  echo "$@" | tee -a "$restart_log"
}
log "Update terminal started $(date)"
linuxcue install-update --yes 2>&1 | tee -a "$restart_log"
status=${PIPESTATUS[0]}
echo | tee -a "$restart_log"
if [ $status -ne 0 ]; then
  log "linuxcue Update fehlgeschlagen."
  read -r -p "Enter zum Schliessen..."
  exit $status
fi
log "linuxcue Update abgeschlossen. Starte linuxcue neu..."
launcher="$(command -v linuxcue || true)"
if [ -z "$launcher" ]; then
  launcher=/usr/bin/linuxcue
fi
log "Restart launcher: $launcher"
restart_helper=/tmp/linuxcue-gui-restart.sh
cat >"$restart_helper" <<'EOS'
#!/usr/bin/env bash
log=/tmp/linuxcue-gui-restart.log
exec >>"$log" 2>&1
echo "GUI restart helper started $(date)"
sleep 3
launcher="$(command -v linuxcue || true)"
if [ -z "$launcher" ]; then
  launcher=/usr/bin/linuxcue
fi
echo "Using launcher: $launcher"
echo "DISPLAY=${DISPLAY:-}"
echo "WAYLAND_DISPLAY=${WAYLAND_DISPLAY:-}"
echo "XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-}"
"$launcher" qml-gui
status=$?
echo "GUI exited with status $status at $(date)"
exit $status
EOS
chmod +x "$restart_helper"
echo "GUI dispatch $(date)" >>"$gui_log"
if command -v systemd-run >/dev/null 2>&1; then
  systemd-run --user --collect --unit=linuxcue-gui-restart "$restart_helper" >>"$gui_log" 2>&1
  dispatch_status=$?
  echo "systemd-run dispatch status: $dispatch_status" >>"$gui_log"
fi
if [ "${dispatch_status:-1}" -ne 0 ]; then
  setsid "$restart_helper" >/dev/null 2>&1 < /dev/null &
  echo "setsid fallback dispatched with pid $!" >>"$gui_log"
fi
log "Restart command dispatched. Log: $gui_log"
exit 0
""",
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            terminals = [
                ["konsole", "-e", "bash", str(script_path)],
                ["gnome-terminal", "--", "bash", str(script_path)],
                ["xfce4-terminal", "-e", f"bash {script_path}"],
                ["xterm", "-e", "bash", str(script_path)],
            ]
            for args in terminals:
                if shutil.which(args[0]):
                    subprocess.Popen(args, start_new_session=True)
                    self._status = "Update-Installation im Terminal gestartet."
                    self.dataChanged.emit()
                    QTimer.singleShot(5000, QGuiApplication.instance().quit)
                    return
            self._status = "Kein Terminal gefunden. Bitte ausfuehren: linuxcue install-update --yes"
            self.dataChanged.emit()

        @Slot()
        def installNvidiaBroadcast(self) -> None:
            if not sys.platform.startswith("linux"):
                self._status = "NVBroadcast-Installation ist nur auf Linux aktiv."
                self.dataChanged.emit()
                return
            if not shutil.which("bash"):
                self._status = "NVBroadcast-Installation nicht moeglich: bash wurde nicht gefunden."
                self.dataChanged.emit()
                return
            script_path = Path("/tmp/linuxcue-install-nvbroadcast.sh")
            script_path.write_text(
                """#!/usr/bin/env bash
set -e
log=/tmp/linuxcue-nvbroadcast-install.log
exec > >(tee "$log") 2>&1
trap 'status=$?; echo; echo "NVBroadcast Installation fehlgeschlagen ($status). Log: $log"; read -r -p "Enter zum Schliessen..."; exit $status' ERR
echo "NVBroadcast installation started $(date)"
if ! command -v git >/dev/null 2>&1; then
  echo "git fehlt. Bitte zuerst git installieren."
  false
fi
work_dir="$HOME/.cache/linuxcue"
repo_dir="$work_dir/nvidia-broadcast-linux"
mkdir -p "$work_dir"
cd "$work_dir"
if [ -d "nvidia-broadcast-linux/.git" ]; then
  echo "Aktualisiere vorhandenes Repo..."
  cd nvidia-broadcast-linux
  git pull --ff-only
else
  echo "Klone NVBroadcast..."
  git clone https://github.com/Hkshoonya/nvidia-broadcast-linux.git
  cd nvidia-broadcast-linux
fi
echo "Starte offiziellen Installer..."
./install.sh
echo
echo "NVBroadcast Installation abgeschlossen."
echo "Log: $log"
read -r -p "Enter zum Schliessen..."
""",
                encoding="utf-8",
            )
            script_path.chmod(0o755)
            terminals = [
                ["konsole", "-e", "bash", str(script_path)],
                ["gnome-terminal", "--", "bash", str(script_path)],
                ["xfce4-terminal", "-e", f"bash {script_path}"],
                ["xterm", "-e", "bash", str(script_path)],
            ]
            for args in terminals:
                if shutil.which(args[0]):
                    subprocess.Popen(args, start_new_session=True)
                    self._status = "NVBroadcast-Installation im Terminal gestartet."
                    self.dataChanged.emit()
                    return
            self._status = "Kein Terminal gefunden. Bitte ausfuehren: git clone https://github.com/Hkshoonya/nvidia-broadcast-linux.git && cd nvidia-broadcast-linux && ./install.sh"
            self.dataChanged.emit()

        @Slot()
        def writeLive(self) -> None:
            profile = self.service.load_profile(self._current_profile)
            if profile is None:
                self._status = "Kein Profil geladen."
                self.dataChanged.emit()
                return
            try:
                if profile.target_device == "k95":
                    result = self.service.write_k95_profile_live(profile.name)
                elif profile.target_device == "m65":
                    result = self.service.write_m65_profile_live(profile.name)
                elif profile.target_device == "virtuoso-se":
                    result = self.service.write_virtuoso_profile_live(profile.name)
                elif profile.target_device == "profile-set":
                    results = self.service.write_profile_set_live(profile.name)
                    packets = sum(item.packet_count for item in results)
                    self._status = f"Live Write OK: {packets} packets"
                    self.dataChanged.emit()
                    return
                else:
                    self._status = f"Live Write fuer {profile.target_device} ist noch nicht verdrahtet."
                    self.dataChanged.emit()
                    return
            except Exception as exc:
                self._status = f"Live Write fehlgeschlagen: {exc}"
                self.dataChanged.emit()
                return
            self._status = f"Live Write OK: {result.packet_count} packets"
            self.dataChanged.emit()

        @Slot(str, bool)
        def applyK95Color(self, color: str, live: bool = True) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_k95_key_zones(profile)
            for zone in profile.lighting:
                if zone.name in K95_OPENRGB_ZONE_ORDER or zone.keys:
                    zone.color = color
                    zone.mode = "static"
            self.service.save_profile(profile)
            self._status = f"K95 Farbe gespeichert: {color}"
            self._update_selected_lighting_layer(profile, color, "all")
            if live:
                try:
                    result = self.service.write_k95_profile_live(profile.name)
                    self._status = f"K95 Live Write OK: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"K95 Farbe gespeichert, Live Write fehlgeschlagen: {exc}"
            self.refresh()

        @Slot(str, str, bool)
        def applyK95ColorToZone(self, zone: str, color: str, live: bool = True) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            keys = self._k95_quick_zone_keys(zone)
            self._ensure_k95_key_zones(profile)
            key_set = set(keys)
            for lighting_zone in profile.lighting:
                if zone == "all" and (lighting_zone.name in K95_OPENRGB_ZONE_ORDER or lighting_zone.keys):
                    lighting_zone.color = color
                    lighting_zone.mode = "static"
                elif lighting_zone.name in key_set or key_set.intersection(lighting_zone.keys):
                    lighting_zone.color = color
                    lighting_zone.mode = "static"
            self.service.save_profile(profile)
            self._update_selected_lighting_layer(profile, color, zone)
            self._status = f"K95 Zone {zone} gespeichert: {color}"
            if live:
                try:
                    result = self.service.write_k95_profile_live(profile.name)
                    self._status = f"K95 Zone {zone} Live Write OK: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"K95 Zone gespeichert, Live Write fehlgeschlagen: {exc}"
            self.refresh()

        @Slot(str)
        def addLightingLayer(self, title: str = "Statische Farbe") -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            layer_title = title.strip() or "Statische Farbe"
            for layer in layers:
                layer["selected"] = False
            layers.append(
                {
                    "id": self._unique_lighting_layer_id(layers, "layer"),
                    "title": self._unique_lighting_layer_title(layers, layer_title),
                    "color": "#04ff00",
                    "zone": "keys:",
                    "keys": [],
                    "selected": True,
                    "profile": profile.name,
                }
            )
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers
            self._status = "Beleuchtungsschicht erstellt."
            self.dataChanged.emit()

        @Slot(str)
        def copyLightingLayer(self, layer_id: str) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            source = next((layer for layer in layers if layer.get("id") == layer_id), None)
            if source is None:
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            new_layer = dict(source)
            new_layer["id"] = self._unique_lighting_layer_id(layers, str(source.get("id") or "layer"))
            new_layer["title"] = self._unique_lighting_layer_title(layers, f"{source.get('title', 'Schicht')} Kopie")
            new_layer["profile"] = profile.name
            for layer in layers:
                layer["selected"] = False
            new_layer["selected"] = True
            layers.append(new_layer)
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers
            self._status = f"Beleuchtungsschicht kopiert: {new_layer['title']}"
            self.dataChanged.emit()

        @Slot(str)
        def selectLightingLayer(self, layer_id: str) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            found = False
            for layer in layers:
                selected = layer.get("id") == layer_id
                layer["selected"] = selected
                found = found or selected
            if not found:
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers
            self._status = "Beleuchtungsschicht aktiv."
            self.dataChanged.emit()

        @Slot(str, str)
        def renameLightingLayer(self, layer_id: str, new_title: str) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            layer = next((item for item in layers if item.get("id") == layer_id), None)
            if layer is None:
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            clean = new_title.strip()
            if not clean:
                self._status = "Name darf nicht leer sein."
                self.dataChanged.emit()
                return
            layer["title"] = clean
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers
            self._status = f"Beleuchtungsschicht umbenannt: {clean}"
            self.dataChanged.emit()

        @Slot(str)
        def deleteLightingLayer(self, layer_id: str) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            if len(layers) <= 1:
                self._status = "Mindestens eine Beleuchtungsschicht bleibt erhalten."
                self.dataChanged.emit()
                return
            next_layers = [layer for layer in layers if layer.get("id") != layer_id]
            if len(next_layers) == len(layers):
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            deleted = next((layer for layer in layers if layer.get("id") == layer_id), None)
            if deleted is not None:
                self._reset_deleted_lighting_layer(profile, deleted, next_layers)
            if next_layers and not any(layer.get("selected") for layer in next_layers):
                next_layers[0]["selected"] = True
            profile.options["lighting_layers"] = next_layers
            self._apply_lighting_layers_to_profile(profile, next_layers)
            self.service.save_profile(profile)
            self._refresh_lighting_layers()
            try:
                result = self.service.write_k95_profile_live(profile.name)
                self._status = f"Beleuchtungsschicht geloescht, K95 Live Write OK: {result.packet_count} packets"
            except Exception as exc:
                self._status = f"Beleuchtungsschicht geloescht, Live Write fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(str, bool)
        def addK95SelectionToLayer(self, zone: str, live: bool = True) -> None:
            self._modify_k95_layer_keys(zone, add=True, live=live)

        @Slot(str, bool)
        def removeK95SelectionFromLayer(self, zone: str, live: bool = True) -> None:
            self._modify_k95_layer_keys(zone, add=False, live=live)

        @Slot(str, str, bool)
        def setK95LightingLayerKeys(self, layer_id: str, zone: str, live: bool = True) -> None:
            self._set_k95_layer_keys(layer_id, zone, live=live)

        @Slot(str, str, bool)
        def setK95LightingLayerColor(self, layer_id: str, color: str, live: bool = True) -> None:
            self._set_k95_layer_color(layer_id, color, live=live)

        @Slot()
        def k95HardwareMode(self) -> None:
            try:
                result = self.service.write_k95_hardware_mode_live()
                self._status = f"K95 Hardware Mode OK: {result.packet_count} packets"
            except Exception as exc:
                self._status = f"K95 Hardware Mode fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot()
        def k95OptionsSync(self) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            try:
                result = self.service.write_k95_options_sync_live(profile.name)
                self._status = f"K95 Optionen OK: {result.packet_count} packets"
            except Exception as exc:
                self._status = f"K95 Optionen fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(str, bool, bool)
        def setK95Option(self, key: str, enabled: bool, live: bool = False) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            allowed = {
                "disable_alt_tab",
                "disable_alt_f4",
                "disable_shift_tab",
                "disable_windows_key",
            }
            if key not in allowed:
                self._status = f"Unbekannte K95 Option: {key}"
                self.dataChanged.emit()
                return
            profile.options[key] = bool(enabled)
            self.service.save_profile(profile)
            self._status = f"K95 Option gespeichert: {key}={enabled}"
            if live:
                try:
                    result = self.service.write_k95_options_sync_live(profile.name)
                    self._status = f"K95 Option gespeichert und gesendet: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"K95 Option gespeichert, Live Sync fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(str, str, bool)
        def applyM65ColorToZone(self, zone: str, color: str, live: bool = True) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_m65_defaults(profile)
            targets = list(M65_RGB_ZONES) if zone == "all" else [zone]
            for target in targets:
                lighting = next((item for item in profile.lighting if item.name == target), None)
                if lighting is None:
                    lighting = LightingZone(name=target, color="#04ff00", mode="static")
                    profile.lighting.append(lighting)
                lighting.color = color
                lighting.mode = "static"
            self.service.save_profile(profile)
            self._refresh_m65_state()
            self._status = f"M65 RGB gespeichert: {zone} {color}"
            if live:
                self._write_m65_kind(profile.name, "rgb")
            self.dataChanged.emit()

        @Slot(int, bool)
        def setM65ActiveDpiStage(self, index: int, live: bool = True) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_m65_defaults(profile)
            if 0 <= index < len(profile.dpi):
                for stage_index, stage in enumerate(profile.dpi):
                    stage.active = stage_index == index
                self._store_active_m65_dpi_preset(profile)
                self.service.save_profile(profile)
                self._refresh_m65_state()
                self._status = f"M65 DPI-Stufe aktiv: {profile.dpi[index].name}"
                if live:
                    self._write_m65_kind(profile.name, "dpi")
            self.dataChanged.emit()

        @Slot()
        def createM65DpiPreset(self) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            presets = self._ensure_m65_dpi_presets(profile)
            existing_ids = {str(item.get("id")) for item in presets}
            index = 2
            while f"preset-{index}" in existing_ids:
                index += 1
            preset = {"id": f"preset-{index}", "name": f"DPI Gruppe {index}", "default": False}
            presets.append(preset)
            stage_store = profile.options.get("m65_dpi_preset_stages")
            if not isinstance(stage_store, dict):
                stage_store = {}
            stage_store[preset["id"]] = self._m65_dpi_stage_payloads(self._default_m65_dpi_stages())
            profile.options["m65_dpi_preset_stages"] = stage_store
            profile.options["m65_active_dpi_preset"] = preset["id"]
            profile.dpi = self._default_m65_dpi_stages()
            self.service.save_profile(profile)
            self._refresh_m65_state()
            self._status = f"M65 DPI-Gruppe erstellt: {preset['name']}"
            self.dataChanged.emit()

        @Slot(str)
        def selectM65DpiPreset(self, preset_id: str) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            presets = self._ensure_m65_dpi_presets(profile)
            clean_id = str(preset_id or "default")
            if clean_id not in {str(item.get("id")) for item in presets}:
                clean_id = "default"
            profile.options["m65_active_dpi_preset"] = clean_id
            stage_store = profile.options.get("m65_dpi_preset_stages")
            if isinstance(stage_store, dict):
                profile.dpi = self._m65_dpi_stages_from_payloads(stage_store.get(clean_id))
            self.service.save_profile(profile)
            self._refresh_m65_state()
            active = next((item for item in presets if str(item.get("id")) == clean_id), presets[0])
            self._status = f"M65 DPI-Gruppe aktiv: {active.get('name', 'Default')}"
            self.dataChanged.emit()

        @Slot(str)
        def deleteM65DpiPreset(self, preset_id: str) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            presets = self._ensure_m65_dpi_presets(profile)
            clean_id = str(preset_id or "")
            target = next((item for item in presets if str(item.get("id")) == clean_id), None)
            if target is None:
                self._status = "M65 DPI-Gruppe nicht gefunden."
            elif bool(target.get("default")) or clean_id == "default":
                self._status = "Default-DPI-Gruppe kann nicht geloescht werden."
            else:
                profile.options["m65_dpi_presets"] = [
                    item for item in presets if str(item.get("id")) != clean_id
                ]
                stage_store = profile.options.get("m65_dpi_preset_stages")
                if isinstance(stage_store, dict):
                    stage_store.pop(clean_id, None)
                    profile.options["m65_dpi_preset_stages"] = stage_store
                if profile.options.get("m65_active_dpi_preset") == clean_id:
                    profile.options["m65_active_dpi_preset"] = "default"
                    profile.dpi = self._m65_dpi_stages_from_payloads(
                        profile.options.get("m65_dpi_preset_stages", {}).get("default")
                    )
                self.service.save_profile(profile)
                self._refresh_m65_state()
                self._status = f"M65 DPI-Gruppe geloescht: {target.get('name', clean_id)}"
            self.dataChanged.emit()

        @Slot()
        def resetM65DpiPreset(self) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_m65_defaults(profile)
            profile.dpi = self._default_m65_dpi_stages()
            self._store_active_m65_dpi_preset(profile)
            self.service.save_profile(profile)
            self._refresh_m65_state()
            self._status = "M65 DPI-Werte auf iCUE-Default zurueckgesetzt."
            self.dataChanged.emit()

        @Slot(int, int, int, bool)
        def setM65DpiStage(self, index: int, x: int, y: int, live: bool = False) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._status = "Kein M65-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_m65_defaults(profile)
            if 0 <= index < len(profile.dpi):
                stage = profile.dpi[index]
                stage.x = max(100, min(18000, int(x)))
                stage.y = max(100, min(18000, int(y)))
                self._store_active_m65_dpi_preset(profile)
                self.service.save_profile(profile)
                self._refresh_m65_state()
                self._status = f"M65 DPI gespeichert: {stage.name} {stage.x}/{stage.y}"
                if live:
                    self._write_m65_kind(profile.name, "dpi")
            self.dataChanged.emit()

        @Slot(str, bool)
        def applyVirtuosoColor(self, color: str, live: bool = True) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            zone = self._virtuoso_accent_zone(profile)
            zone.color = color
            zone.mode = "static"
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = f"Virtuoso Accent-Ring gespeichert: {color}"
            if live:
                try:
                    result = self.service.write_virtuoso_profile_live(profile.name, packet_kind="rgb")
                    self._status = f"Virtuoso RGB Live Write OK: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"Virtuoso RGB gespeichert, Live Write fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(str, bool)
        def selectVirtuosoPreset(self, name: str, live: bool = True) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            found = False
            for preset in profile.audio:
                preset.active = preset.name == name
                found = found or preset.active
            if not found and profile.audio:
                profile.audio[0].active = True
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = f"Virtuoso EQ Preset aktiv: {name}"
            if live:
                self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot(int, int, bool)
        def setVirtuosoBand(self, index: int, value: int, live: bool = False) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            preset = self._active_virtuoso_preset(profile)
            bands = self._virtuoso_bands(preset)
            if 0 <= index < len(bands):
                bands[index] = max(VIRTUOSO_EQ_MIN, min(VIRTUOSO_EQ_MAX, int(value)))
                preset.bands = bands
                self.service.save_profile(profile)
                self._refresh_virtuoso_state()
                self._status = f"Virtuoso EQ Band {index + 1} gespeichert."
                if live:
                    self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot(int, int, int, bool, bool)
        def setVirtuosoControls(self, sidetone: int, mic_level: int, sleep_timer: int, voice_prompts: bool, live: bool = True) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            profile.headset.sidetone = max(0, min(100, int(sidetone)))
            profile.headset.mic_level = max(0, min(100, int(mic_level)))
            profile.headset.sleep_timer_minutes = max(0, min(120, int(sleep_timer)))
            profile.headset.voice_prompt_enabled = bool(voice_prompts)
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = "Virtuoso Headset-Regler gespeichert."
            if live:
                try:
                    result = self.service.write_virtuoso_profile_live(profile.name, packet_kind="control")
                    self._status = f"Virtuoso Control Live Write OK: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"Virtuoso Control gespeichert, Live Write fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot(int, bool)
        def setVirtuosoVolume(self, volume: int, live: bool = True) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            clamped = max(0, min(150, int(volume)))
            profile.options["virtuoso_volume"] = clamped
            self.service.save_profile(profile)
            self._virtuoso_volume = clamped
            self._status = f"Virtuoso Lautstaerke gespeichert: {clamped}%"
            if live:
                try:
                    result = self.service.set_virtuoso_eq_volume(clamped)
                    if result.get("ok"):
                        self._status = f"Virtuoso Lautstaerke aktiv: {clamped}%"
                    else:
                        self._status = f"Virtuoso Lautstaerke gespeichert, PipeWire abgelehnt: {result.get('stderr', '')}"
                except Exception as exc:
                    self._status = f"Virtuoso Lautstaerke gespeichert, Live-Set fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot()
        def applyVirtuosoFlatEq(self) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            flat = next((preset for preset in profile.audio if preset.name.casefold() == "flat"), None)
            if flat is None:
                flat = AudioPreset(name="Flat", active=False, bands=[0] * len(ICUE_EQ_FREQUENCIES))
                profile.audio.append(flat)
            flat.bands = [0] * len(ICUE_EQ_FREQUENCIES)
            for preset in profile.audio:
                preset.active = preset is flat
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = "Virtuoso Flat EQ gespeichert."
            self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot()
        def applyVirtuosoLoudnessEq(self) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            loudness = next((preset for preset in profile.audio if preset.name.casefold() == "loudness"), None)
            if loudness is None:
                loudness = AudioPreset(name="Loudness", active=False, bands=list(VIRTUOSO_LOUDNESS_BANDS))
                profile.audio.append(loudness)
            loudness.bands = list(VIRTUOSO_LOUDNESS_BANDS)
            for preset in profile.audio:
                preset.active = preset is loudness
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = "Virtuoso Loudness EQ gespeichert."
            self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot(str)
        def createVirtuosoPreset(self, name: str = "") -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            preset_name = self._unique_virtuoso_preset_name(profile, name.strip() or "Eigenes Preset")
            preset = AudioPreset(name=preset_name, active=True, bands=list(VIRTUOSO_FLAT_BANDS))
            for item in profile.audio:
                item.active = False
            profile.audio.append(preset)
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = f"Virtuoso Preset erstellt: {preset_name}"
            self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot(str, str)
        def copyVirtuosoPreset(self, source_name: str = "", new_name: str = "") -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            source = next((preset for preset in profile.audio if preset.name == source_name), self._active_virtuoso_preset(profile))
            preset_name = self._unique_virtuoso_preset_name(profile, new_name.strip() or f"{source.name} Kopie")
            clone = AudioPreset(name=preset_name, active=True, bands=self._virtuoso_bands(source))
            for item in profile.audio:
                item.active = False
            profile.audio.append(clone)
            self.service.save_profile(profile)
            self._refresh_virtuoso_state()
            self._status = f"Virtuoso Preset kopiert: {preset_name}"
            self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot(str)
        def deleteVirtuosoPreset(self, name: str) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._ensure_virtuoso_defaults(profile)
            target = next((preset for preset in profile.audio if preset.name == name), None)
            if target is None:
                self._status = "Virtuoso Preset nicht gefunden."
            elif self._virtuoso_preset_protected(profile, target):
                self._status = f"Virtuoso Preset ist geschuetzt: {target.name}"
            elif len(profile.audio) <= 1:
                self._status = "Das letzte Virtuoso Preset kann nicht geloescht werden."
            else:
                was_active = target.active
                profile.audio = [preset for preset in profile.audio if preset is not target]
                if was_active and profile.audio:
                    profile.audio[0].active = True
                self.service.save_profile(profile)
                self._refresh_virtuoso_state()
                self._status = f"Virtuoso Preset geloescht: {name}"
                self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot()
        def applyVirtuosoLinuxEq(self) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._apply_virtuoso_eq(profile.name)
            self.dataChanged.emit()

        @Slot()
        def applyVirtuosoPipeWireEq(self) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._status = "Kein Virtuoso-Profil aktiv."
                self.dataChanged.emit()
                return
            self._virtuoso_eq_backend = "pipewire"
            profile.options["virtuoso_eq_backend"] = "pipewire"
            self.service.save_profile(profile)
            try:
                result = self.service.apply_virtuoso_pipewire_eq(profile.name)
                self.service.set_virtuoso_eq_volume(int(profile.options.get("virtuoso_volume") or 100))
                self._status = f"Native PipeWire EQ aktiviert: {result.get('preset', 'Preset')}"
            except Exception as exc:
                self._status = f"Native PipeWire EQ Aktivierung fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        @Slot()
        def stopVirtuosoLiveEq(self) -> None:
            try:
                result = self.service.stop_virtuoso_live_eq()
                profile = self._active_profile_for_target("virtuoso-se")
                if profile is not None:
                    profile.options["virtuoso_eq_backend"] = "profile"
                    self.service.save_profile(profile)
                self._virtuoso_eq_backend = "profile"
                target = result.get("target_sink") or "direkter Ausgang"
                self._status = f"Virtuoso Live EQ gestoppt. Ausgabe: {target}"
            except Exception as exc:
                self._status = f"Virtuoso Live EQ Stop fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        def _profile_subtitle(self, item: dict[str, object]) -> str:
            target = str(item.get("target_device", ""))
            group_role = str(item.get("group_role") or item.get("target_family") or "")
            if target == "profile-set":
                return "main profile"
            return f"{target} / {group_role}"

        def _device_cards(self) -> list[dict[str, Any]]:
            status = self.service.live_status(None)
            connected_slugs = self._connected_slugs(status)
            profile_slugs = self._current_profile_device_slugs()
            cards: list[dict[str, Any]] = []
            virtuoso_wireless = self._virtuoso_wireless_connected(status)
            if virtuoso_wireless:
                connected_slugs.add("virtuoso-se")
            detected_details = self._detected_device_details(status)
            for slug in ["k95", "m65", "virtuoso-se", "void-elite", "receiver"]:
                if slug not in connected_slugs:
                    continue
                device_details = detected_details.get(slug, {})
                support_level = str(device_details.get("support_level") or "")
                if slug not in profile_slugs and support_level not in {"detected", "planned"}:
                    continue
                meta, kind = _device_meta(slug)
                image_source = ""
                if slug == "m65":
                    image_source = "../assets/devices/m65-card.png"
                if slug == "virtuoso-se":
                    image_source = "../assets/devices/virtuoso-wireless-card.png" if virtuoso_wireless else "../assets/devices/virtuoso-usb-card.png"
                    meta = "Wireless Link: 2.4 GHz" if virtuoso_wireless else "USB Link: kabelgebunden"
                cards.append(
                    {
                        "slug": slug,
                        "title": _device_title(slug),
                        "kind": kind,
                        "meta": meta,
                        "state": "online",
                        "selected": slug == self._current_device,
                        "imageSource": image_source,
                        "wireless": virtuoso_wireless if slug == "virtuoso-se" else False,
                        "supportLevel": support_level or "supported",
                        "vendorId": self._normalized_hex_id(device_details.get("vendor_id")),
                        "productId": self._normalized_hex_id(device_details.get("product_id")),
                        "transport": str(device_details.get("transport") or ""),
                        "endpointCount": int(device_details.get("endpoint_count") or 1),
                        "path": str(device_details.get("path") or ""),
                        "reportIncludes": "Basisdaten, USB-Infos, HID-Descriptoren, Feature-Report-Map",
                        "nextStep": str(device_details.get("next_step") or "Vollstaendigen Geraetebericht speichern und als GitHub Device support request anhaengen."),
                    }
                )
            cards.extend(self._unknown_device_cards(status))
            return cards

        def _detected_device_details(self, status: dict[str, Any]) -> dict[str, dict[str, Any]]:
            details: dict[str, dict[str, Any]] = {}
            for device in status.get("devices", []):
                if not isinstance(device, dict):
                    continue
                slug = _device_slug(str(device.get("target", "")), str(device.get("family", "")))
                if slug == "unknown":
                    continue
                entry = details.setdefault(
                    slug,
                    {
                        "support_level": str(device.get("support_level") or ""),
                        "vendor_id": device.get("vendor_id"),
                        "product_id": device.get("product_id"),
                        "transport": device.get("transport"),
                        "path": device.get("path"),
                        "next_step": device.get("next_step"),
                        "endpoint_count": 0,
                    },
                )
                entry["endpoint_count"] = int(entry.get("endpoint_count") or 0) + 1
            return details

        def _unknown_device_cards(self, status: dict[str, Any]) -> list[dict[str, Any]]:
            grouped: dict[str, dict[str, Any]] = {}
            for device in status.get("devices", []):
                if not isinstance(device, dict):
                    continue
                slug = _device_slug(str(device.get("target", "")), str(device.get("family", "")))
                if slug != "unknown":
                    continue
                product_id = self._normalized_hex_id(device.get("product_id"))
                vendor_id = self._normalized_hex_id(device.get("vendor_id"))
                key = f"{vendor_id}-{product_id}"
                entry = grouped.setdefault(
                    key,
                    {
                        "slug": f"unknown-{vendor_id.replace('0x', '')}-{product_id.replace('0x', '')}",
                        "title": str(device.get("product") or "Unbekanntes Corsair-Geraet"),
                        "kind": "Noch nicht unterstuetzt",
                        "meta": f"{vendor_id.upper()} / {product_id.upper()}",
                        "state": "detected",
                        "selected": False,
                        "imageSource": "",
                        "wireless": False,
                        "supportLevel": str(device.get("support_level") or "planned"),
                        "family": str(device.get("family") or "unknown"),
                        "vendorId": vendor_id,
                        "productId": product_id,
                        "transport": str(device.get("transport") or "unknown"),
                        "endpointCount": 0,
                        "liveWritable": False,
                        "openError": "",
                        "path": str(device.get("path") or ""),
                        "reportIncludes": "Basisdaten, USB-Infos, HID-Descriptoren, Feature-Report-Map",
                        "nextStep": str(device.get("next_step") or "Vollstaendigen Geraetebericht speichern und als GitHub Device support request anhaengen."),
                    },
                )
                entry["endpointCount"] = int(entry["endpointCount"]) + 1
                entry["liveWritable"] = bool(entry["liveWritable"]) or bool(device.get("live_writable") or device.get("open_ok"))
                if device.get("open_error") and not entry["openError"]:
                    entry["openError"] = str(device.get("open_error"))
            for entry in grouped.values():
                endpoints = int(entry["endpointCount"])
                entry["kind"] = f"{endpoints} Endpunkt{'e' if endpoints != 1 else ''} erkannt"
                entry["selected"] = entry["slug"] == self._current_device
            return list(grouped.values())

        def _sync_current_device_details(self) -> None:
            self._current_device_details = {}
            for item in self._devices:
                if item.get("slug") == self._current_device:
                    self._current_device_details = dict(item)
                    return

        def _default_device_report_path(self, slug: str) -> Path:
            safe_slug = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in slug)
            return Path.home() / f"linuxcue-device-report-{safe_slug}.json"

        def _write_device_report(self, slug: str, path: Path | None = None) -> str:
            self._sync_current_device_details()
            path = path or self._default_device_report_path(slug)
            product_id = self._current_device_details.get("productId")
            live_status = self.service.live_status(None)
            matching_devices = [
                device
                for device in live_status.get("devices", [])
                if not product_id or self._normalized_hex_id(device.get("product_id")) == product_id
            ]
            try:
                hid_endpoint_map: dict[str, Any] = self.service.map_hid_endpoints(max_report_id=32, report_length=128)
            except Exception as exc:
                hid_endpoint_map = {
                    "safe": True,
                    "write_performed": False,
                    "ok": False,
                    "error": str(exc),
                    "note": "HID endpoint mapping failed while creating the GUI device report.",
                }
            report = {
                "linuxcue_report": "corsair-device-support-request",
                "selected_device": self._current_device_details,
                "matching_devices": matching_devices,
                "all_connected_devices": live_status.get("devices", []),
                "usb_devices": self.service.usb_device_summaries(),
                "hid_descriptors": self.service.capture_hid_descriptors(),
                "hid_endpoint_map": hid_endpoint_map,
                "developer_command": f"linuxcue prepare-device-support {path}",
                "github_upload_hint": "Open a Device support request issue at https://github.com/Maggi0r/Linuxcue/issues/new/choose and attach this JSON file.",
                "next_step": "Attach this JSON to a linuxcue issue or share it with the developer to add a dedicated driver module.",
            }
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
            return str(path)

        def _main_profile_summaries(self, summaries: list[dict[str, object]]) -> list[dict[str, Any]]:
            child_groups = {str(item.get("profile_group", "")) for item in summaries if str(item.get("group_role", "")) != "set"}
            rows: list[dict[str, Any]] = []
            for item in summaries:
                name = str(item.get("name", ""))
                target = str(item.get("target_device", ""))
                group_role = str(item.get("group_role", ""))
                if target != "profile-set" and (group_role or str(item.get("profile_group", ""))):
                    continue
                if target != "profile-set" and name in child_groups:
                    continue
                rows.append(
                    {
                        "name": name,
                        "subtitle": self._profile_subtitle(item),
                        "target": target,
                        "selected": name == self._current_profile,
                        "protected": bool(item.get("protected", False)),
                    }
                )
            return rows

        def _connected_slugs(self, status: dict[str, Any]) -> set[str]:
            slugs: set[str] = set()
            for device in status.get("devices", []):
                slug = _device_slug(str(device.get("target", "")), str(device.get("family", "")))
                if slug != "unknown":
                    slugs.add(slug)
                if self._is_virtuoso_wireless_device(device):
                    slugs.add("virtuoso-se")
            return slugs

        def _virtuoso_wireless_connected(self, status: dict[str, Any]) -> bool:
            if any(self._is_virtuoso_wireless_device(device) for device in status.get("devices", [])):
                return True
            try:
                usb_devices = self.service.discover_usb_devices()
            except Exception:
                return False
            return any(
                self._is_virtuoso_wireless_device(
                    {
                        "product": device.product_name,
                        "product_id": f"0x{device.product_id:04x}",
                        "target": device.support.model_hint,
                        "family": device.support.family,
                        "transport": device.transport,
                        "endpoint_role": self.service.endpoint_role(device),
                        "path": device.path,
                    }
                )
                for device in usb_devices
            )

        @staticmethod
        def _is_virtuoso_wireless_device(device: dict[str, Any]) -> bool:
            text = " ".join(
                str(device.get(key, ""))
                for key in ("target", "product", "family", "transport", "endpoint_role", "path")
            ).casefold()
            product_id = LinuxCueQmlBridge._normalized_hex_id(device.get("product_id"))
            return (
                product_id == "0x0a46"
                or "wireless-receiver" in text
                or "wireless receiver" in text
                or ("receiver" in text and "virtuoso" in text)
            )

        @staticmethod
        def _normalized_hex_id(value: Any) -> str:
            if isinstance(value, int):
                return f"0x{value:04x}"
            text = str(value or "").strip().casefold()
            try:
                if text.startswith("0x"):
                    return f"0x{int(text, 16):04x}"
                if text.isdigit():
                    return f"0x{int(text, 10):04x}"
            except ValueError:
                return text
            return text

        def _current_profile_device_slugs(self) -> set[str]:
            profile = self.service.load_profile(self._current_profile)
            if profile is None:
                return set()
            profiles = self._profile_bundle(profile.name)
            slugs = {_device_slug(item.target_device, item.target_family) for item in profiles}
            return {slug for slug in slugs if slug != "unknown"}

        def _active_profile_for_target(self, target: str) -> Profile | None:
            profile = self.service.load_profile(self._current_profile)
            if profile is None:
                return None
            if profile.target_device == target:
                return profile
            if profile.target_device != "profile-set":
                return None
            group_name = profile.profile_group or profile.name
            for child in self.service.profiles_in_group(group_name):
                if child.target_device == target:
                    return child
            return None

        def _refresh_virtuoso_state(self) -> None:
            profile = self._active_profile_for_target("virtuoso-se")
            if profile is None:
                self._virtuoso_presets = []
                self._virtuoso_eq_bands = [0] * len(ICUE_EQ_FREQUENCIES)
                self._virtuoso_accent_color = "#1ecfdf"
                self._virtuoso_sidetone = 35
                self._virtuoso_mic_level = 72
                self._virtuoso_volume = 100
                self._virtuoso_sleep_timer = 20
                self._virtuoso_voice_prompts = True
                return
            self._ensure_virtuoso_defaults(profile)
            active = self._active_virtuoso_preset(profile)
            self._virtuoso_presets = [
                {"name": preset.name, "selected": preset is active, "protected": self._virtuoso_preset_protected(profile, preset), "bands": self._virtuoso_bands(preset)}
                for preset in profile.audio
            ]
            self._virtuoso_eq_bands = self._virtuoso_bands(active)
            self._virtuoso_accent_color = self._virtuoso_accent_zone(profile).color
            self._virtuoso_sidetone = profile.headset.sidetone
            self._virtuoso_mic_level = profile.headset.mic_level
            self._virtuoso_volume = int(profile.options.get("virtuoso_volume") or 100)
            self._virtuoso_sleep_timer = profile.headset.sleep_timer_minutes
            self._virtuoso_voice_prompts = profile.headset.voice_prompt_enabled

        def _ensure_virtuoso_defaults(self, profile: Profile) -> None:
            if not profile.audio:
                profile.audio = [AudioPreset(name="Custom", active=True, bands=[0] * len(ICUE_EQ_FREQUENCIES))]
            for preset_name, bands in VIRTUOSO_SYSTEM_PRESETS.items():
                if not any(preset.name.casefold() == preset_name for preset in profile.audio):
                    display_name = "Bass Boost" if preset_name == "bass boost" else preset_name.title()
                    profile.audio.append(AudioPreset(name=display_name, active=False, bands=list(bands)))
            protected = profile.options.get("virtuoso_system_presets")
            if not isinstance(protected, list):
                protected = []
            protected_names = {str(item).casefold() for item in protected}
            protected_names.update(VIRTUOSO_PROTECTED_PRESETS)
            profile.options["virtuoso_system_presets"] = sorted(protected_names)
            for preset in profile.audio:
                preset.bands = self._virtuoso_bands(preset)
            if not any(preset.active for preset in profile.audio):
                profile.audio[0].active = True
            if profile.headset is None:
                profile.headset = HeadsetSetting()
            profile.options.setdefault("virtuoso_eq_backend", "pipewire")
            profile.options.setdefault("virtuoso_volume", 100)
            self._virtuoso_accent_zone(profile)

        def _active_virtuoso_preset(self, profile: Profile) -> AudioPreset:
            return next((preset for preset in profile.audio if preset.active), profile.audio[0])

        def _virtuoso_bands(self, preset: AudioPreset) -> list[int]:
            if preset.bands:
                values = expand_eq_bands([int(value) for value in preset.bands])
            else:
                values = [
                    preset.bass,
                    preset.bass,
                    round((preset.bass + preset.mids) / 2),
                    preset.mids,
                    preset.mids,
                    preset.mids,
                    round((preset.mids + preset.treble) / 2),
                    preset.treble,
                    preset.treble,
                    preset.treble,
                ]
            values.extend([0] * (len(ICUE_EQ_FREQUENCIES) - len(values)))
            return [max(VIRTUOSO_EQ_MIN, min(VIRTUOSO_EQ_MAX, int(value))) for value in values[: len(ICUE_EQ_FREQUENCIES)]]

        def _virtuoso_preset_protected(self, profile: Profile, preset: AudioPreset) -> bool:
            protected = profile.options.get("virtuoso_system_presets")
            protected_names = {str(item).casefold() for item in protected} if isinstance(protected, list) else set()
            return preset.name.casefold() in protected_names or preset.name.casefold() in VIRTUOSO_PROTECTED_PRESETS

        def _unique_virtuoso_preset_name(self, profile: Profile, desired: str) -> str:
            base = desired.strip() or "Eigenes Preset"
            existing = {preset.name.casefold() for preset in profile.audio}
            if base.casefold() not in existing:
                return base
            index = 2
            while f"{base} {index}".casefold() in existing:
                index += 1
            return f"{base} {index}"

        def _virtuoso_accent_zone(self, profile: Profile) -> LightingZone:
            zone = next((item for item in profile.lighting if item.name == "accent_ring"), None)
            if zone is None:
                zone = LightingZone(name="accent_ring", color="#1ecfdf", mode="static")
                profile.lighting.append(zone)
            return zone

        def _apply_virtuoso_eq(self, profile_name: str) -> None:
            with self._virtuoso_eq_apply_lock:
                if self._virtuoso_eq_apply_running:
                    self._virtuoso_eq_apply_pending = profile_name
                    return
                self._virtuoso_eq_apply_running = True
            thread = threading.Thread(target=self._apply_virtuoso_eq_worker, args=(profile_name,), daemon=True)
            thread.start()

        def _apply_virtuoso_eq_worker(self, profile_name: str) -> None:
            try:
                backend = self._virtuoso_eq_backend_for_profile(profile_name)
                if backend == "pipewire":
                    result = self.service.apply_virtuoso_native_pipewire_eq(profile_name)
                    if result.get("ok"):
                        self.statusReady.emit(f"Native PipeWire EQ live aktualisiert: {result.get('node', {}).get('node_name', 'EQ')}")
                    elif result.get("needs_activation"):
                        activation = self.service.apply_virtuoso_pipewire_eq(profile_name)
                        profile = self.service.load_profile(profile_name)
                        volume = int(profile.options.get("virtuoso_volume") or 100) if profile is not None else 100
                        self.service.set_virtuoso_eq_volume(volume)
                        self.statusReady.emit(f"Native PipeWire EQ automatisch aktiviert: {activation.get('preset', 'Preset')}")
                    else:
                        attempts = result.get("attempts") or []
                        last = attempts[-1] if attempts else {}
                        self.statusReady.emit(f"Native PipeWire Live-Update abgelehnt: {last.get('label', 'set-param')}. Doctor ausfuehren.")
                elif backend == "easyeffects":
                    result = self.service.apply_virtuoso_easyeffects(profile_name)
                    self.statusReady.emit(f"Virtuoso Linux EQ aktiv: {result.get('preset', 'Preset')}")
                else:
                    self.statusReady.emit("Virtuoso EQ gespeichert. Audio bleibt auf direktem Ausgang.")
            except Exception as exc:
                backend_label = "Native PipeWire EQ" if self._virtuoso_eq_backend_for_profile(profile_name) == "pipewire" else "Virtuoso Linux EQ"
                self.statusReady.emit(f"{backend_label} fehlgeschlagen: {exc}")
            next_profile: str | None = None
            with self._virtuoso_eq_apply_lock:
                if self._virtuoso_eq_apply_pending:
                    next_profile = self._virtuoso_eq_apply_pending
                    self._virtuoso_eq_apply_pending = None
                else:
                    self._virtuoso_eq_apply_running = False
            if next_profile is not None:
                self._apply_virtuoso_eq_worker(next_profile)

        def _virtuoso_eq_backend_for_profile(self, profile_name: str) -> str:
            profile = self.service.load_profile(profile_name)
            if profile is None:
                return self._virtuoso_eq_backend
            backend = str(profile.options.get("virtuoso_eq_backend") or self._virtuoso_eq_backend).casefold()
            if backend == "easyeffects":
                return "easyeffects"
            if backend == "pipewire":
                return "pipewire"
            return "pipewire"

        def _refresh_m65_state(self) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                self._m65_lighting_zones = []
                self._m65_dpi_presets = []
                self._m65_dpi_stages = []
                return
            self._ensure_m65_defaults(profile)
            dpi_presets = self._ensure_m65_dpi_presets(profile)
            active_preset_id = str(profile.options.get("m65_active_dpi_preset") or "default")
            lighting_by_name = {zone.name: zone for zone in profile.lighting}
            labels = {
                "front": "Vorderseite",
                "logo": "Logo",
                "dpi_indicator": "DPI Indicator",
            }
            self._m65_lighting_zones = [
                {
                    "name": name,
                    "title": labels.get(name, name),
                    "color": lighting_by_name[name].color,
                    "mode": lighting_by_name[name].mode,
                }
                for name in M65_RGB_ZONES
                if name in lighting_by_name
            ]
            self._m65_dpi_presets = [
                {
                    "id": str(item.get("id") or "default"),
                    "name": str(item.get("name") or "Default"),
                    "isDefault": bool(item.get("default")),
                    "active": str(item.get("id") or "default") == active_preset_id,
                }
                for item in dpi_presets
            ]
            self._m65_dpi_stages = [
                {
                    "index": index,
                    "name": stage.name,
                    "title": self._m65_dpi_title(stage.name),
                    "x": stage.x,
                    "y": stage.y,
                    "color": stage.color,
                    "active": stage.active,
                }
                for index, stage in enumerate(profile.dpi)
            ]

        def _ensure_m65_defaults(self, profile: Profile) -> None:
            if not profile.lighting:
                profile.lighting = []
            colors = {
                "front": "#d7ff37",
                "logo": "#ff3b30",
                "dpi_indicator": "#00c2ff",
            }
            for zone_name in M65_RGB_ZONES:
                if not any(zone.name == zone_name for zone in profile.lighting):
                    profile.lighting.append(LightingZone(name=zone_name, color=colors[zone_name], mode="static"))
            profile.dpi = self._normalise_m65_dpi_stages(profile.dpi)
            self._ensure_m65_dpi_presets(profile)
            self._load_active_m65_dpi_preset(profile)

        def _default_m65_dpi_stages(self) -> list[DpiStage]:
            return [
                DpiStage(name=name, x=dpi, y=dpi, color=color, active=name == M65_DPI_DEFAULT_ACTIVE)
                for name, (dpi, color) in M65_DPI_DEFAULTS.items()
            ]

        def _normalise_m65_dpi_stages(self, stages: list[DpiStage]) -> list[DpiStage]:
            by_name = {stage.name.casefold(): stage for stage in stages}
            ordered: list[DpiStage] = []
            for name in M65_DPI_ORDER:
                stage = by_name.pop(name, None)
                dpi, color = M65_DPI_DEFAULTS[name]
                if stage is None:
                    stage = DpiStage(name=name, x=dpi, y=dpi, color=color, active=name == M65_DPI_DEFAULT_ACTIVE)
                else:
                    stage.name = name
                    if int(stage.x) <= 0:
                        stage.x = dpi
                    if int(stage.y) <= 0:
                        stage.y = dpi
                    if not stage.color:
                        stage.color = color
                ordered.append(stage)
            ordered.extend(by_name.values())
            if not any(stage.active for stage in ordered) and ordered:
                fallback = next((stage for stage in ordered if stage.name == M65_DPI_DEFAULT_ACTIVE), ordered[0])
                fallback.active = True
            return ordered

        def _ensure_m65_dpi_presets(self, profile: Profile) -> list[dict[str, Any]]:
            if not isinstance(profile.options, dict):
                profile.options = {}
            raw_presets = profile.options.get("m65_dpi_presets")
            if not isinstance(raw_presets, list):
                raw_presets = []

            normalised: list[dict[str, Any]] = []
            seen: set[str] = set()
            for index, item in enumerate(raw_presets):
                if not isinstance(item, dict):
                    continue
                preset_id = str(item.get("id") or "").strip() or f"preset-{index + 1}"
                if preset_id in seen:
                    continue
                seen.add(preset_id)
                normalised.append(
                    {
                        "id": preset_id,
                        "name": str(item.get("name") or "DPI Gruppe"),
                        "default": bool(item.get("default") or preset_id == "default"),
                    }
                )

            default = next((item for item in normalised if item["id"] == "default"), None)
            if default is None:
                default = {"id": "default", "name": "Default", "default": True}
                normalised.insert(0, default)
            else:
                default["name"] = "Default"
                default["default"] = True
                normalised = [default] + [item for item in normalised if item is not default]

            active_id = str(profile.options.get("m65_active_dpi_preset") or "default")
            if active_id not in {item["id"] for item in normalised}:
                active_id = "default"
            raw_stage_store = profile.options.get("m65_dpi_preset_stages")
            stage_store = raw_stage_store if isinstance(raw_stage_store, dict) else {}
            default_payload = self._m65_dpi_stage_payloads(self._default_m65_dpi_stages())
            current_payload = self._m65_dpi_stage_payloads(profile.dpi)
            for item in normalised:
                preset_id = str(item["id"])
                if preset_id not in stage_store:
                    source_payload = current_payload if preset_id == active_id else default_payload
                    stage_store[preset_id] = [dict(stage) for stage in source_payload]
            if not profile.options.get("m65_dpi_defaults_migrated_v2"):
                stage_store["default"] = [dict(stage) for stage in default_payload]
                profile.options["m65_dpi_defaults_migrated_v2"] = True
            profile.options["m65_dpi_presets"] = normalised
            profile.options["m65_active_dpi_preset"] = active_id
            profile.options["m65_dpi_preset_stages"] = stage_store
            return normalised

        def _load_active_m65_dpi_preset(self, profile: Profile) -> None:
            stage_store = profile.options.get("m65_dpi_preset_stages")
            if not isinstance(stage_store, dict):
                return
            active_id = str(profile.options.get("m65_active_dpi_preset") or "default")
            if active_id in stage_store:
                profile.dpi = self._m65_dpi_stages_from_payloads(stage_store.get(active_id))

        def _m65_dpi_stage_payloads(self, stages: list[DpiStage]) -> list[dict[str, Any]]:
            return [
                {
                    "name": stage.name,
                    "x": int(stage.x),
                    "y": int(stage.y),
                    "color": stage.color,
                    "active": bool(stage.active),
                }
                for stage in self._normalise_m65_dpi_stages(stages)
            ]

        def _m65_dpi_stages_from_payloads(self, payloads: object) -> list[DpiStage]:
            if not isinstance(payloads, list):
                return self._default_m65_dpi_stages()
            stages: list[DpiStage] = []
            for item in payloads:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "")
                dpi, color = M65_DPI_DEFAULTS.get(name, (800, "#ffffff"))
                stages.append(
                    DpiStage(
                        name=name,
                        x=int(item.get("x") or dpi),
                        y=int(item.get("y") or dpi),
                        color=str(item.get("color") or color),
                        active=bool(item.get("active")),
                    )
                )
            return self._normalise_m65_dpi_stages(stages)

        def _store_active_m65_dpi_preset(self, profile: Profile) -> None:
            self._ensure_m65_dpi_presets(profile)
            active_id = str(profile.options.get("m65_active_dpi_preset") or "default")
            stage_store = profile.options.get("m65_dpi_preset_stages")
            if not isinstance(stage_store, dict):
                stage_store = {}
            stage_store[active_id] = self._m65_dpi_stage_payloads(profile.dpi)
            profile.options["m65_dpi_preset_stages"] = stage_store

        def _m65_dpi_title(self, name: str) -> str:
            folded = name.casefold()
            if "sniper" in folded:
                return "Sniper"
            if folded.startswith("stage"):
                suffix = folded.removeprefix("stage")
                return f"Stufe {suffix}" if suffix else "Stufe"
            return name

        def _write_m65_kind(self, profile_name: str, packet_kind: str) -> None:
            monitor_was_active = self._m65_input_timer.isActive()
            self._stop_m65_dpi_monitor()
            try:
                result = self.service.write_m65_profile_live(profile_name, packet_kind=packet_kind)
                self._status = f"M65 {packet_kind.upper()} Live Write OK: {result.packet_count} packets"
            except Exception as exc:
                self._status = (
                    f"M65 {packet_kind.upper()} lokal gespeichert. Live Write nicht moeglich: {exc}"
                )
            finally:
                if monitor_was_active:
                    self._sync_m65_dpi_monitor()

        def _sync_m65_dpi_monitor(self) -> None:
            if self._current_device != "m65" or self._active_profile_for_target("m65") is None:
                self._stop_m65_dpi_monitor()
                return
            devices = [
                device
                for device in self.service.discover_devices()
                if device.support.family == "mouse" and "m65" in device.support.model_hint.casefold()
            ]
            if self._m65_dpi_monitor.ensure_open_many(devices):
                if not self._m65_input_timer.isActive():
                    self._m65_input_timer.start()
            else:
                self._stop_m65_dpi_monitor()

        def _stop_m65_dpi_monitor(self) -> None:
            if self._m65_input_timer.isActive():
                self._m65_input_timer.stop()
            self._m65_dpi_monitor.close()

        def _poll_m65_dpi_input(self) -> None:
            if self._current_device != "m65":
                self._stop_m65_dpi_monitor()
                return
            event = self._m65_dpi_monitor.read_dpi_event()
            if isinstance(event, int) and event:
                self._apply_m65_dpi_delta(event)
            elif event == "sniper":
                self._apply_m65_sniper(True)
            elif event == "sniper_release":
                self._apply_m65_sniper(False)

        def _apply_m65_dpi_delta(self, delta: int) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                return
            self._ensure_m65_defaults(profile)
            if not profile.dpi:
                return
            active_index = next((index for index, stage in enumerate(profile.dpi) if stage.active), 0)
            next_index = max(0, min(len(profile.dpi) - 1, active_index + delta))
            if next_index == active_index:
                return
            for index, stage in enumerate(profile.dpi):
                stage.active = index == next_index
            self._store_active_m65_dpi_preset(profile)
            self.service.save_profile(profile)
            self._refresh_m65_state()
            direction = "hoch" if delta > 0 else "runter"
            active = profile.dpi[next_index]
            if active.name.casefold() != "sniper":
                self._m65_previous_dpi_name = active.name
            self._status = f"M65 DPI-Taste erkannt: {direction}, aktive Stufe {next_index + 1} ({active.x}/{active.y})."
            self.dataChanged.emit()

        def _apply_m65_sniper(self, pressed: bool) -> None:
            profile = self._active_profile_for_target("m65")
            if profile is None:
                return
            self._ensure_m65_defaults(profile)
            if not profile.dpi:
                return
            active = next((stage for stage in profile.dpi if stage.active), None)
            if pressed:
                if active is not None and active.name.casefold() != "sniper":
                    self._m65_previous_dpi_name = active.name
                target_name = "sniper"
                status = "M65 Sniper-Taste erkannt: Sniper-DPI aktiv."
            else:
                target_name = self._m65_previous_dpi_name or "stage1"
                status = "M65 Sniper-Taste losgelassen: vorherige DPI-Stufe aktiv."
            changed = False
            for stage in profile.dpi:
                active_stage = stage.name.casefold() == target_name.casefold()
                changed = changed or stage.active != active_stage
                stage.active = active_stage
            if not changed:
                return
            self._store_active_m65_dpi_preset(profile)
            self.service.save_profile(profile)
            self._refresh_m65_state()
            self._status = status
            self.dataChanged.emit()

        def _ensure_k95_key_zones(self, profile: Profile) -> None:
            existing = {zone.name: zone for zone in profile.lighting}
            for key in K95_OPENRGB_ZONE_ORDER:
                if key not in existing:
                    zone = LightingZone(name=key, color="#04ff00", mode="static", keys=[key])
                    profile.lighting.append(zone)

        def _k95_quick_zone_keys(self, zone: str) -> list[str]:
            if zone.startswith("key:"):
                key_name = zone.split(":", 1)[1].casefold()
                if key_name == "preset":
                    return ["preset", "led_topzone9", "led_topzone10"]
                return [key_name] if key_name in K95_OPENRGB_ZONE_ORDER else []
            if zone.startswith("keys:"):
                key_names = [item.strip().casefold() for item in zone.split(":", 1)[1].split(",")]
                return [key for key in key_names if key in K95_OPENRGB_ZONE_ORDER]
            groups = {
                "all": list(K95_OPENRGB_ZONE_ORDER),
                "wasd": ["w", "a", "s", "d"],
                "qwerdf": ["q", "w", "e", "r", "d", "f"],
                "gkeys": ["g1", "g2", "g3", "g4", "g5", "g6"],
                "numpad": [
                    "numlock",
                    "kp_slash",
                    "kp_star",
                    "kp_minus",
                    "kp7",
                    "kp8",
                    "kp9",
                    "kp_plus",
                    "kp4",
                    "kp5",
                    "kp6",
                    "kp1",
                    "kp2",
                    "kp3",
                    "kp_enter",
                    "kp0",
                    "kp_dot",
                ],
                "arrows": ["up", "left", "down", "right"],
                "numbers": ["1", "2", "3", "4", "5", "6"],
            }
            return groups.get(zone, groups["all"])

        def _refresh_lighting_layers(self) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._lighting_layers = []
                self._k95_key_colors = {}
                return
            self._lighting_layers = self._lighting_layer_store(profile)
            self._k95_key_colors = self._k95_key_color_map(profile)

        def _k95_key_color_map(self, profile: Profile) -> dict[str, str]:
            colors: dict[str, str] = {}
            for zone in profile.lighting:
                keys = zone.keys or ([zone.name] if zone.name in K95_OPENRGB_ZONE_ORDER else [])
                for key in keys:
                    colors[str(key).casefold()] = zone.color
            return colors

        def _lighting_layer_store(self, profile: Profile) -> list[dict[str, Any]]:
            raw_layers = profile.options.get("lighting_layers")
            if isinstance(raw_layers, list) and raw_layers:
                layers = [
                    self._normalise_lighting_layer(item, index, profile.name)
                    for index, item in enumerate(copy.deepcopy(raw_layers))
                    if isinstance(item, dict) and self._lighting_layer_belongs_to_profile(item, profile.name)
                ]
                if layers:
                    if not any(layer.get("selected") for layer in layers):
                        layers[0]["selected"] = True
                    changed = layers != raw_layers
                    profile.options["lighting_layers"] = layers
                    if changed:
                        self.service.save_profile(profile)
                    return layers
            color = self._first_k95_color(profile)
            layers = [
                {
                    "id": "static-color",
                    "title": "Statische Farbe",
                    "color": color,
                    "zone": "all",
                    "keys": self._k95_quick_zone_keys("all"),
                    "selected": True,
                    "profile": profile.name,
                },
                {
                    "id": "color-shift",
                    "title": "Farbwechsel",
                    "color": "#1ecfdf",
                    "zone": "all",
                    "keys": self._k95_quick_zone_keys("all"),
                    "selected": False,
                    "profile": profile.name,
                },
            ]
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            return layers

        def _lighting_layer_belongs_to_profile(self, item: dict[str, Any], profile_name: str) -> bool:
            owner = str(item.get("profile") or "")
            return not owner or owner == profile_name

        def _normalise_lighting_layer(self, item: dict[str, Any], index: int, profile_name: str) -> dict[str, Any]:
            zone = str(item.get("zone") or "all")
            return {
                "id": str(item.get("id") or f"layer-{index + 1}"),
                "title": str(item.get("title") or "Beleuchtungsschicht"),
                "color": str(item.get("color") or "#04ff00"),
                "zone": zone,
                "keys": self._k95_quick_zone_keys(zone),
                "selected": bool(item.get("selected", index == 0)),
                "profile": profile_name,
            }

        def _first_k95_color(self, profile: Profile) -> str:
            for zone in profile.lighting:
                if zone.color:
                    return zone.color
            return "#04ff00"

        def _update_selected_lighting_layer(self, profile: Profile, color: str, zone: str) -> None:
            layers = self._lighting_layer_store(profile)
            clean_zone = zone or "all"
            selected = next((layer for layer in layers if layer.get("selected")), None)
            target = None
            if selected is not None and str(selected.get("zone") or "all") == clean_zone:
                target = selected
            if target is None and selected is not None and not self._k95_quick_zone_keys(str(selected.get("zone") or "")):
                target = selected
            if target is None:
                target = next((layer for layer in layers if str(layer.get("zone") or "all") == clean_zone), None)
            if target is None:
                target = {
                    "id": self._unique_lighting_layer_id(layers, self._lighting_layer_id_for_zone(clean_zone)),
                    "title": self._lighting_layer_title_for_zone(clean_zone),
                    "color": color,
                    "zone": clean_zone,
                    "keys": self._k95_quick_zone_keys(clean_zone),
                    "selected": True,
                    "profile": profile.name,
                }
                layers.append(target)
            for layer in layers:
                layer["selected"] = layer is target
            target["color"] = color
            target["zone"] = clean_zone
            target["keys"] = self._k95_quick_zone_keys(clean_zone)
            target["title"] = self._lighting_layer_title_for_zone(clean_zone)
            target["profile"] = profile.name
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers

        def _modify_k95_layer_keys(self, zone: str, *, add: bool, live: bool) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            keys = self._k95_quick_zone_keys(zone)
            if not keys:
                self._status = "Keine Tasten fuer die Gruppenbearbeitung ausgewaehlt."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            layer = next((item for item in layers if item.get("selected")), None)
            if layer is None:
                self._status = "Keine aktive Beleuchtungsschicht ausgewaehlt."
                self.dataChanged.emit()
                return
            layer_zone = str(layer.get("zone") or "all")
            current_keys = [] if add and layer_zone == "all" else self._k95_quick_zone_keys(layer_zone)
            if layer_zone == "all" and not add:
                current_keys = list(K95_OPENRGB_ZONE_ORDER)
            merged = list(dict.fromkeys([*current_keys, *keys])) if add else [key for key in current_keys if key not in set(keys)]
            layer["zone"] = self._zone_for_keys(merged)
            layer["keys"] = self._k95_quick_zone_keys(str(layer["zone"]))
            layer["title"] = self._lighting_layer_title_for_zone(str(layer["zone"]))
            layer["profile"] = profile.name
            for item in layers:
                item["selected"] = item is layer
            action = "hinzugefuegt" if add else "entfernt"
            self._store_k95_layers(profile, layers, live=live, status_prefix=f"{len(keys)} Tasten zur aktiven Schicht {action}.")

        def _set_k95_layer_keys(self, layer_id: str, zone: str, *, live: bool) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            layer = self._lighting_layer_by_id(layers, layer_id)
            if layer is None:
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            keys = self._k95_quick_zone_keys(zone)
            layer["zone"] = self._zone_for_keys(keys)
            layer["keys"] = keys
            layer["title"] = self._lighting_layer_title_for_zone(str(layer["zone"]))
            layer["profile"] = profile.name
            for item in layers:
                item["selected"] = item is layer
            self._store_k95_layers(profile, layers, live=live, status_prefix=f"Schicht aktualisiert: {len(keys)} Tasten.")

        def _set_k95_layer_color(self, layer_id: str, color: str, *, live: bool) -> None:
            profile = self._active_profile_for_target("k95")
            if profile is None:
                self._status = "Kein K95-Profil aktiv."
                self.dataChanged.emit()
                return
            layers = self._lighting_layer_store(profile)
            layer = self._lighting_layer_by_id(layers, layer_id)
            if layer is None:
                self._status = "Beleuchtungsschicht nicht gefunden."
                self.dataChanged.emit()
                return
            layer["color"] = color
            layer["profile"] = profile.name
            for item in layers:
                item["selected"] = item is layer
            self._store_k95_layers(profile, layers, live=live, status_prefix=f"Schichtfarbe gespeichert: {color}.")

        def _lighting_layer_by_id(self, layers: list[dict[str, Any]], layer_id: str) -> dict[str, Any] | None:
            return next((layer for layer in layers if str(layer.get("id")) == layer_id), None)

        def _store_k95_layers(self, profile: Profile, layers: list[dict[str, Any]], *, live: bool, status_prefix: str) -> None:
            self._apply_lighting_layers_to_profile(profile, layers)
            profile.options["lighting_layers"] = layers
            self.service.save_profile(profile)
            self._lighting_layers = layers
            self._k95_key_colors = self._k95_key_color_map(profile)
            self._status = status_prefix
            if live:
                try:
                    result = self.service.write_k95_profile_live(profile.name)
                    self._status = f"{self._status} K95 Live Write OK: {result.packet_count} packets"
                except Exception as exc:
                    self._status = f"{self._status} Live Write fehlgeschlagen: {exc}"
            self.dataChanged.emit()

        def _zone_for_keys(self, keys: list[str]) -> str:
            clean = [key for key in dict.fromkeys(keys) if key in K95_OPENRGB_ZONE_ORDER]
            if not clean:
                return "keys:"
            if len(clean) == len(K95_OPENRGB_ZONE_ORDER):
                return "all"
            if len(clean) == 1:
                return f"key:{clean[0]}"
            return "keys:" + ",".join(clean)

        def _apply_lighting_layers_to_profile(self, profile: Profile, layers: list[dict[str, Any]]) -> None:
            self._ensure_k95_key_zones(profile)
            color_by_key = {key: "#04ff00" for key in K95_OPENRGB_ZONE_ORDER}
            for layer in layers:
                color = str(layer.get("color") or "#04ff00")
                for key in self._k95_quick_zone_keys(str(layer.get("zone") or "all")):
                    color_by_key[key] = color
            for zone in profile.lighting:
                keys = zone.keys or ([zone.name] if zone.name in K95_OPENRGB_ZONE_ORDER else [])
                if keys:
                    zone.color = color_by_key.get(str(keys[0]).casefold(), zone.color)
                    zone.mode = "static"

        def _reset_deleted_lighting_layer(self, profile: Profile, deleted: dict[str, Any], remaining_layers: list[dict[str, Any]]) -> None:
            keys = self._k95_quick_zone_keys(str(deleted.get("zone") or "all"))
            if not keys:
                return
            key_set = set(keys)
            for lighting_zone in profile.lighting:
                zone_keys = set(lighting_zone.keys or ([lighting_zone.name] if lighting_zone.name in K95_OPENRGB_ZONE_ORDER else []))
                affected = key_set.intersection(zone_keys)
                if not affected:
                    continue
                lighting_zone.color = "#04ff00"
                lighting_zone.mode = "static"

        def _layer_key_fallbacks(self, layers: list[dict[str, Any]]) -> dict[str, str]:
            colors: dict[str, str] = {}
            for layer in layers:
                color = str(layer.get("color") or "#04ff00")
                for key in self._k95_quick_zone_keys(str(layer.get("zone") or "all")):
                    colors[key] = color
            return colors

        def _lighting_layer_title_for_zone(self, zone: str) -> str:
            if zone == "all":
                return "Statische Farbe"
            if zone.startswith("key:"):
                key_name = zone.split(":", 1)[1].casefold()
                titles = {
                    "mute": "Taste: Profil",
                    "brightness": "Taste: Helligkeit",
                    "lock": "Taste: Win-Lock",
                    "preset": "Logo",
                    "stop": "Taste: Stop",
                    "prev": "Taste: Zurueck",
                    "play": "Taste: Play/Pause",
                    "next": "Taste: Vorwaerts",
                }
                return titles.get(key_name, f"Taste: {key_name.upper()}")
            if zone.startswith("keys:"):
                count = len(self._k95_quick_zone_keys(zone))
                return f"Tasten: {count}"
            titles = {
                "wasd": "Zone: WASD",
                "qwerdf": "Zone: QWERDF",
                "gkeys": "Zone: G-Tasten",
                "numpad": "Zone: Ziffernblock",
                "arrows": "Zone: Pfeiltasten",
                "numbers": "Zone: 1-6",
            }
            return titles.get(zone, f"Zone: {zone}")

        def _lighting_layer_id_for_zone(self, zone: str) -> str:
            if zone == "all":
                return "static-color"
            if zone.startswith("key:"):
                return f"key-{zone.split(':', 1)[1]}"
            if zone.startswith("keys:"):
                return "selection"
            return f"zone-{zone}"

        def _unique_lighting_layer_id(self, layers: list[dict[str, Any]], base_id: str) -> str:
            safe_base = "".join(ch.lower() if ch.isalnum() else "-" for ch in base_id).strip("-") or "layer"
            existing = {str(layer.get("id", "")) for layer in layers}
            candidate = safe_base
            index = 2
            while candidate in existing:
                candidate = f"{safe_base}-{index}"
                index += 1
            return candidate

        def _unique_lighting_layer_title(self, layers: list[dict[str, Any]], base_title: str) -> str:
            existing = {str(layer.get("title", "")) for layer in layers}
            if base_title not in existing:
                return base_title
            index = 2
            while f"{base_title} {index}" in existing:
                index += 1
            return f"{base_title} {index}"

        def _unique_profile_name(self, base_name: str) -> str:
            existing = set(self.service.list_profiles())
            if base_name not in existing:
                return base_name
            index = 2
            while f"{base_name} {index}" in existing:
                index += 1
            return f"{base_name} {index}"

        def _profile_bundle(self, name: str) -> list[Profile]:
            profile = self.service.load_profile(name)
            if profile is None:
                return []
            if profile.target_device == "profile-set":
                return [profile, *self.service.profiles_in_group(profile.profile_group or profile.name)]
            return [profile]

        def _delete_profile_bundle(self, name: str) -> bool:
            profiles = self._profile_bundle(name)
            if any(self.service.is_protected_profile(profile.name) for profile in profiles):
                return False
            deleted = False
            for profile in profiles:
                deleted = self.service.delete_profile(profile.name) or deleted
            return deleted

        def _save_bundle_copy(self, profiles: list[Profile], base_name: str) -> list[str]:
            profiles = copy.deepcopy(profiles)
            if len(profiles) == 1 and profiles[0].target_device != "profile-set":
                profile = profiles[0]
                profile.name = self._unique_profile_name(base_name)
                profile.profile_group = ""
                profile.group_role = ""
                self._clear_system_profile_flags(profile)
                self.service.save_profile(profile)
                return [profile.name]

            main = next((item for item in profiles if item.target_device == "profile-set"), profiles[0])
            new_group = self._unique_profile_name(base_name)
            saved_names: list[str] = []
            for profile in profiles:
                if profile is main or profile.target_device == "profile-set":
                    profile.name = new_group
                    profile.target_device = "profile-set"
                    profile.target_family = "set"
                    profile.profile_group = new_group
                    profile.group_role = "set"
                else:
                    role = profile.group_role or profile.target_family or profile.target_device
                    suffix = profile.target_device if profile.target_device != "virtuoso-se" else "virtuoso"
                    profile.name = self._unique_profile_name(f"{new_group}-{suffix}")
                    profile.profile_group = new_group
                    profile.group_role = role
                self._clear_system_profile_flags(profile)
                self.service.save_profile(profile)
                saved_names.append(profile.name)
            return saved_names

        def _clear_system_profile_flags(self, profile: Profile) -> None:
            profile.options.pop(SYSTEM_PROFILE_FLAG, None)
            profile.options.pop("protected", None)
            profile.options.pop("system_profile_version", None)

        def _path_from_url(self, url: str) -> Path | None:
            if not url:
                return None
            parsed = urlparse(url)
            if parsed.scheme == "file":
                return Path(unquote(parsed.path))
            return Path(url)

        def _import_cueprofile(self, path: Path) -> list[str]:
            text = path.read_text(encoding="utf-8")
            if "<linuxcueProfileBundle" in text:
                root = ET.fromstring(text)
                data = root.findtext(".//payload")
                if not data:
                    return []
                payload = json.loads(base64.b64decode(data.encode("ascii")).decode("utf-8"))
                profiles = [self._profile_from_payload(item) for item in payload.get("profiles", [])]
                return self._save_bundle_copy(profiles, str(payload.get("name") or path.stem))
            result = self.service.import_icue_profiles(str(path))
            return [str(name) for name in result.get("profile_names", [])]

        def _export_cueprofile_xml(self, profiles: list[Profile]) -> str:
            name = profiles[0].profile_group or profiles[0].name
            payload = {
                "format": "linuxcue-profile-set",
                "name": name,
                "profiles": [profile.to_dict() for profile in profiles],
            }
            encoded = base64.b64encode(json.dumps(payload, indent=2).encode("utf-8")).decode("ascii")
            root = ET.Element("linuxcueProfileBundle", {"version": "1"})
            ET.SubElement(root, "name").text = name
            ET.SubElement(root, "payload", {"encoding": "base64-json"}).text = encoded
            return "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n" + ET.tostring(root, encoding="unicode")

        def _profile_from_payload(self, payload: dict[str, Any]) -> Profile:
            return Profile(
                name=str(payload.get("name") or "Imported Profile"),
                target_device=str(payload.get("target_device", "generic")),
                target_family=str(payload.get("target_family", "generic")),
                profile_group=str(payload.get("profile_group", "")),
                group_role=str(payload.get("group_role", "")),
                description=str(payload.get("description", "")),
                lighting=[LightingZone(**zone) for zone in payload.get("lighting", [])],
                dpi=[DpiStage(**stage) for stage in payload.get("dpi", [])],
                audio=[AudioPreset(**preset) for preset in payload.get("audio", [])],
                headset=HeadsetSetting(**payload.get("headset", {})),
                cooling=[CoolingChannel(**channel) for channel in payload.get("cooling", [])],
                options=dict(payload.get("options", {})),
            )


def launch_qml_gui() -> None:
    if QT_QML_IMPORT_ERROR is not None:
        raise RuntimeError(
            "PySide6 Qt/QML is missing. On CachyOS install it with: sudo pacman -S --needed pyside6\n"
            "Then reinstall linuxcue with: bash scripts/install-cachyos-dev.sh"
        ) from QT_QML_IMPORT_ERROR
    app = QGuiApplication(sys.argv)
    icon_path = Path(__file__).resolve().parent / "assets" / "icons" / "linuxcue.svg"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    engine = QQmlApplicationEngine()
    bridge = LinuxCueQmlBridge()
    engine.rootContext().setContextProperty("linuxcue", bridge)
    qml_path = Path(__file__).resolve().parent / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_path)))
    if not engine.rootObjects():
        raise RuntimeError(f"QML GUI could not be loaded from {qml_path}")
    app.exec()


def main() -> int:
    try:
        launch_qml_gui()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
