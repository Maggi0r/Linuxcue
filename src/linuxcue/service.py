from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from .device_manager import DeviceManager
from .easyeffects_export import export_virtuoso_easyeffects_preset, export_virtuoso_easyeffects_presets, preset_export_name
from .icue_importer import import_icue_profile, profiles_from_icue
from .k95_backend import (
    build_k95_default_profile,
    build_k95_lighting_control_packet,
    build_k95_special_function_packets,
    plan_k95_apply,
    preview_k95_frames,
    send_k95_profile,
    write_k95_packets,
)
from .m65_backend import build_m65_default_profile, plan_m65_apply, preview_m65_frames, send_m65_profile
from .virtuoso_backend import (
    build_virtuoso_rgb_sweep_packets,
    build_virtuoso_default_profile,
    plan_virtuoso_apply,
    preview_virtuoso_frames,
    send_virtuoso_profile,
    write_virtuoso_packets,
)
from .known_devices import TARGET_DEVICES, known_device_by_slug, mock_probe_for_slug, support_for_product
from .models import Device, ProbeData, Profile
from .pipewire_eq import restart_pipewire_user_services, write_virtuoso_pipewire_eq
from .profile_store import ProfileStore
from .probe_store import ProbeStore
from .protocol_map import all_capability_maps, capability_map_for_slug
from .simulator import plan_apply
from .transport import LiveHidTransport
from .virtuoso_monitor import VirtuosoBatteryMonitor, VirtuosoUsbBatteryMonitor

VIRTUOSO_BASS_BOOST_BANDS = [4, 6, 4, 0, -3, -3, -2, 1, 2, 2]
SYSTEM_PROFILE_SET_NAME = "Standard Profil"
SYSTEM_PROFILE_FLAG = "linuxcue_system_profile"
SYSTEM_PROFILE_VERSION = 1
SYSTEM_PROFILE_CHILDREN = {
    "keyboard": ("k95", "keyboard", "Standard Profil-k95"),
    "mouse": ("m65", "mouse", "Standard Profil-m65"),
    "headset": ("virtuoso-se", "headset", "Standard Profil-virtuoso"),
}


@dataclass(slots=True)
class ApplyResult:
    profile_name: str
    device_count: int
    simulated: bool
    message: str
    actions: list[dict[str, object]]


@dataclass(slots=True)
class LiveWriteResult:
    profile_name: str
    device: str
    packet_count: int
    transport: str
    live: bool
    message: str


class LinuxCueService:
    def __init__(
        self,
        manager: DeviceManager | None = None,
        store: ProfileStore | None = None,
        probe_store: ProbeStore | None = None,
    ) -> None:
        self.manager = manager or DeviceManager()
        self.store = store or ProfileStore()
        self.probe_store = probe_store or ProbeStore()
        self.ensure_default_profiles()

    def discover_devices(self) -> list[Device]:
        return self.manager.discover()

    def discover_usb_devices(self) -> list[Device]:
        return self.manager.discover_usb_devices()

    def profile_root(self) -> str:
        return str(self.store.root)

    def connected_device_summaries(self) -> list[dict[str, object]]:
        summaries: list[dict[str, object]] = []
        for device in self.discover_devices():
            access = self.hid_open_status(device)
            summaries.append(
                {
                    "product": device.product_name,
                    "vendor_id": f"0x{device.vendor_id:04x}",
                    "product_id": f"0x{device.product_id:04x}",
                    "transport": device.transport,
                    "path": device.path,
                    "interface_number": device.interface_number,
                    "endpoint_role": self.endpoint_role(device),
                    "target": device.support.model_hint,
                    "family": device.support.family,
                    "live_writable": access["open_ok"],
                    "open_ok": access["open_ok"],
                    "open_error": access["error"],
                }
            )
        return summaries

    def usb_device_summaries(self) -> list[dict[str, object]]:
        return [
            {
                "product": device.product_name,
                "vendor_id": f"0x{device.vendor_id:04x}",
                "product_id": f"0x{device.product_id:04x}",
                "transport": device.transport,
                "path": device.path,
                "target": device.support.model_hint,
                "family": device.support.family,
            }
            for device in self.discover_usb_devices()
        ]

    def virtualbox_usb_diagnostics(self) -> dict[str, object]:
        usb_devices = self.usb_device_summaries()
        hid_devices = self.connected_device_summaries()
        hid_keys = {(item["product_id"], str(item["target"])) for item in hid_devices}
        usb_without_hid = [
            item
            for item in usb_devices
            if (item["product_id"], str(item["target"])) not in hid_keys
        ]
        recommendations: list[str] = []
        for item in usb_without_hid:
            if item["target"] == "Corsair Virtuoso SE":
                recommendations.append(
                    "Virtuoso SE is visible on USB/sysfs but not as hidapi endpoint. In VirtualBox this usually means the audio device passed through, but the vendor HID interface did not."
                )
            if item["target"] == "Corsair Virtuoso RGB Wireless USB Receiver":
                recommendations.append(
                    "Virtuoso receiver is visible on USB/sysfs but not as hidapi endpoint. Remove/recreate the VirtualBox USB filter and pass the whole receiver, not only an audio function."
                )
        if not any(item["target"] == "Corsair Virtuoso RGB Wireless USB Receiver" for item in usb_devices + hid_devices):
            recommendations.append(
                "Virtuoso wireless receiver is not visible inside the guest. It must be detached from the Windows host and captured by a VirtualBox USB filter before Linux can control it."
            )
        if not any(item["target"] == "Corsair Virtuoso SE" for item in usb_devices + hid_devices):
            recommendations.append(
                "Virtuoso headset is not visible inside the guest. If the headset is attached by USB, add a VirtualBox USB 2.0/3.0 filter for VID 1b1c PID 0a3d and reconnect it after the VM has focus."
            )
        for item in usb_devices + hid_devices:
            if item["product_id"] == "0x0a46" and item["target"] == "Corsair Virtuoso RGB Wireless USB Receiver":
                recommendations.append(
                    "Virtuoso receiver is available as HID control endpoint. A headset product string on PID 0x0a46 is normal/confusing Corsair naming; linuxcue treats it as the wireless receiver."
                )
        return {
            "usb_device_count": len(usb_devices),
            "hid_endpoint_count": len(hid_devices),
            "usb_devices": usb_devices,
            "hid_endpoints": hid_devices,
            "usb_without_hidapi": usb_without_hid,
            "recommendations": sorted(set(recommendations)),
        }

    def live_status(self, profile: Profile | None = None) -> dict[str, object]:
        devices = self.discover_devices()
        access_by_path = {device.path or f"{device.vendor_id}:{device.product_id}:{index}": self.hid_open_status(device) for index, device in enumerate(devices)}
        writable = [
            device
            for index, device in enumerate(devices)
            if access_by_path[device.path or f"{device.vendor_id}:{device.product_id}:{index}"]["open_ok"]
        ]
        matching = [device for device in writable if profile is None or self._profile_matches_live_device(profile, device)]
        return {
            "connected_count": len(devices),
            "writable_count": len(writable),
            "matching_count": len(matching),
            "devices": [
                {
                    **access_by_path[device.path or f"{device.vendor_id}:{device.product_id}:{index}"],
                    "product": device.product_name,
                    "vendor_id": f"0x{device.vendor_id:04x}",
                    "product_id": f"0x{device.product_id:04x}",
                    "target": device.support.model_hint,
                    "family": device.support.family,
                    "transport": device.transport,
                    "path": device.path,
                    "interface_number": device.interface_number,
                    "endpoint_role": self.endpoint_role(device),
                }
                for index, device in enumerate(devices)
            ],
        }

    def map_hid_endpoints(self, max_report_id: int = 16, report_length: int = 64) -> dict[str, object]:
        devices = self.discover_devices()
        mapped: list[dict[str, object]] = []
        for device in devices:
            endpoint: dict[str, object] = {
                "product": device.product_name,
                "vendor_id": f"0x{device.vendor_id:04x}",
                "product_id": f"0x{device.product_id:04x}",
                "target": device.support.model_hint,
                "family": device.support.family,
                "path": device.path,
                "interface_number": device.interface_number,
                "endpoint_role": self.endpoint_role(device),
                "transport": device.transport,
                "open_ok": False,
                "feature_reports": [],
            }
            if device.transport != "hidapi":
                endpoint["open_error"] = "not a hidapi endpoint"
                mapped.append(endpoint)
                continue

            transport = None
            try:
                transport = LiveHidTransport(device.vendor_id, device.product_id, path=device.path)
                endpoint["open_ok"] = True
                reports: list[dict[str, object]] = []
                for report_id in range(0, max_report_id + 1):
                    try:
                        payload = transport.read_feature_report(report_id, report_length)
                    except RuntimeError as exc:
                        reports.append(
                            {
                                "report_id": f"0x{report_id:02x}",
                                "ok": False,
                                "error": str(exc),
                            }
                        )
                        continue
                    reports.append(
                        {
                            "report_id": f"0x{report_id:02x}",
                            "ok": True,
                            "byte_count": len(payload),
                            "payload_hex": payload.hex(" "),
                        }
                    )
                endpoint["feature_reports"] = reports
            except RuntimeError as exc:
                endpoint["open_error"] = str(exc)
            finally:
                if transport is not None:
                    transport.close()
            mapped.append(endpoint)

        return {
            "safe": True,
            "write_performed": False,
            "note": "This mapping pass opens HID endpoints and reads feature reports only; it does not write to hardware.",
            "device_count": len(devices),
            "endpoints": mapped,
        }

    def capture_hid_descriptors(self) -> dict[str, object]:
        if os.name != "posix":
            return {
                "safe": True,
                "write_performed": False,
                "descriptor_count": 0,
                "descriptors": [],
                "note": "HID report descriptors are available through /sys on Linux only.",
            }

        base = Path("/sys/bus/hid/devices")
        descriptors: list[dict[str, object]] = []
        if not base.exists():
            return {
                "safe": True,
                "write_performed": False,
                "descriptor_count": 0,
                "descriptors": [],
                "note": "/sys/bus/hid/devices does not exist.",
            }

        for device_dir in sorted(base.iterdir()):
            name = device_dir.name.casefold()
            uevent = self._safe_read_text(device_dir / "uevent") or ""
            if "1b1c" not in name and "00001b1c" not in uevent.casefold():
                continue
            descriptor_path = device_dir / "report_descriptor"
            try:
                descriptor = descriptor_path.read_bytes()
            except OSError as exc:
                descriptors.append(
                    {
                        "sysfs_name": device_dir.name,
                        "uevent": uevent,
                        "ok": False,
                        "error": str(exc),
                    }
                )
                continue
            descriptors.append(
                {
                    "sysfs_name": device_dir.name,
                    "uevent": uevent,
                    "ok": True,
                    "byte_count": len(descriptor),
                    "descriptor_hex": descriptor.hex(" "),
                }
            )

        return {
            "safe": True,
            "write_performed": False,
            "descriptor_count": len(descriptors),
            "descriptors": descriptors,
            "note": "This reads Linux sysfs HID report descriptors only; it does not write to hardware.",
        }

    def hid_open_status(self, device: Device) -> dict[str, object]:
        if device.transport != "hidapi":
            return {"open_ok": False, "error": "not a hidapi endpoint"}
        transport = None
        try:
            transport = LiveHidTransport(device.vendor_id, device.product_id, path=device.path)
        except RuntimeError as exc:
            return {"open_ok": False, "error": str(exc)}
        finally:
            if transport is not None:
                transport.close()
        return {"open_ok": True, "error": ""}

    @staticmethod
    def _safe_read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None

    def target_matrix(self) -> list[dict[str, object]]:
        return [
            {
                "slug": item.slug,
                "family": item.family,
                "model_hint": item.model_hint,
                "protocol": item.protocol,
                "support_level": item.support_level,
                "next_step": item.next_step,
                "companion_slug": item.companion_slug,
                "companion_role": item.companion_role,
                "capabilities": list(item.capabilities),
                "capability_map": capability_map_for_slug(item.slug),
            }
            for item in TARGET_DEVICES
        ]

    def capability_matrix(self) -> dict[str, object]:
        devices = self.discover_devices()
        connected_slugs = sorted(
            {
                slug
                for device in devices
                for slug in self._device_slug_candidates(device)
            }
        )
        return {
            "connected_slugs": connected_slugs,
            "capability_map": all_capability_maps(),
            "connected_devices": [
                {
                    "product": device.product_name,
                    "product_id": f"0x{device.product_id:04x}",
                    "path": device.path,
                    "interface_number": device.interface_number,
                    "endpoint_role": self.endpoint_role(device),
                    "target": device.support.model_hint,
                    "slugs": sorted(self._device_slug_candidates(device)),
                }
                for device in devices
            ],
        }

    def create_default_profile(self, name: str) -> Profile:
        return Profile(name=name, description="Generic fallback profile")

    def create_k95_profile(self, name: str) -> Profile:
        return build_k95_default_profile(name)

    def create_m65_profile(self, name: str) -> Profile:
        return build_m65_default_profile(name)

    def create_virtuoso_profile(self, name: str) -> Profile:
        return build_virtuoso_default_profile(name)

    def create_profile_for_target(self, target: str, name: str) -> Profile:
        if target == "k95":
            return self.create_k95_profile(name)
        if target == "m65":
            return self.create_m65_profile(name)
        if target in {"virtuoso-rgb", "virtuoso-se"}:
            return self.create_virtuoso_profile(name)
        return self.create_default_profile(name)

    def ensure_default_profiles(self) -> list[str]:
        saved: list[str] = []
        group = self.load_profile(SYSTEM_PROFILE_SET_NAME)
        if group is None:
            group = Profile(
                name=SYSTEM_PROFILE_SET_NAME,
                target_device="profile-set",
                target_family="bundle",
                profile_group=SYSTEM_PROFILE_SET_NAME,
                group_role="set",
                description="Geschuetztes Standardprofil fuer linuxcue.",
                lighting=[],
                cooling=[],
            )
            self._mark_system_profile(group, "set")
            self.store.save(group)
            saved.append(group.name)
        else:
            if self._repair_system_profile_metadata(group, "profile-set", "bundle", "set"):
                self.store.save(group)
                saved.append(group.name)

        for role, (target, family, name) in SYSTEM_PROFILE_CHILDREN.items():
            profile = self.load_profile(name)
            if profile is None:
                profile = self.create_profile_for_target(target, name)
                profile.profile_group = SYSTEM_PROFILE_SET_NAME
                profile.group_role = role
                self._mark_system_profile(profile, role)
                self.store.save(profile)
                saved.append(profile.name)
                continue
            if self._repair_system_profile_metadata(profile, target, family, role):
                self.store.save(profile)
                saved.append(profile.name)
        return saved

    def is_protected_profile(self, name: str) -> bool:
        profile = self.load_profile(name)
        return bool(profile and self._is_system_profile(profile))

    def _mark_system_profile(self, profile: Profile, role: str) -> None:
        profile.profile_group = SYSTEM_PROFILE_SET_NAME
        profile.group_role = role
        profile.options[SYSTEM_PROFILE_FLAG] = True
        profile.options["protected"] = True
        profile.options["system_profile_version"] = SYSTEM_PROFILE_VERSION

    def _repair_system_profile_metadata(self, profile: Profile, target_device: str, target_family: str, role: str) -> bool:
        changed = False
        expected = {
            "target_device": target_device,
            "target_family": target_family,
            "profile_group": SYSTEM_PROFILE_SET_NAME,
            "group_role": role,
        }
        for field_name, value in expected.items():
            if getattr(profile, field_name) != value:
                setattr(profile, field_name, value)
                changed = True
        before = dict(profile.options)
        self._mark_system_profile(profile, role)
        return changed or profile.options != before

    def _is_system_profile(self, profile: Profile) -> bool:
        return bool(profile.options.get(SYSTEM_PROFILE_FLAG) or profile.options.get("protected"))

    def preview_k95_profile(self, profile_name: str) -> dict[str, object] | None:
        profile = self.load_profile(profile_name)
        if profile is None:
            return None
        device = self.resolve_k95_device(prefer_real=False)
        if device is None:
            return None
        return preview_k95_frames(profile, device)

    def preview_m65_profile(self, profile_name: str, packet_kind: str = "all") -> dict[str, object] | None:
        profile = self.load_profile(profile_name)
        if profile is None:
            return None
        device = self.resolve_m65_device(prefer_real=False)
        if device is None:
            return None
        return preview_m65_frames(profile, device, packet_kind=packet_kind)

    def preview_virtuoso_profile(self, profile_name: str) -> dict[str, object] | None:
        profile = self.load_profile(profile_name)
        if profile is None:
            return None
        device = self.resolve_virtuoso_device(prefer_real=False)
        if device is None:
            return None
        return preview_virtuoso_frames(profile, device)

    def preview_profile(self, profile_name: str) -> dict[str, object] | None:
        profile = self.load_profile(profile_name)
        if profile is None:
            return None
        if profile.target_device == "k95":
            return self.preview_k95_profile(profile_name)
        if profile.target_device == "m65":
            return self.preview_m65_profile(profile_name)
        if profile.target_device == "virtuoso-se":
            return self.preview_virtuoso_profile(profile_name)
        return None

    def resolve_k95_device(self, prefer_real: bool = True) -> Device | None:
        devices = self.load_probe_devices()
        if prefer_real:
            devices = self.discover_devices() or devices
        for device in devices:
            if device.support.family == "keyboard" and "k95" in device.support.model_hint.casefold():
                return device
        fallback_probe = mock_probe_for_slug("k95")
        fallback_device = self.device_from_probe(fallback_probe) if fallback_probe else None
        if fallback_device is None:
            return None
        return fallback_device

    def resolve_m65_device(self, prefer_real: bool = True) -> Device | None:
        devices = self.load_probe_devices()
        if prefer_real:
            devices = self.discover_devices() or devices
        for device in devices:
            if device.support.family == "mouse" and "m65" in device.support.model_hint.casefold():
                return device
        fallback_probe = mock_probe_for_slug("m65")
        fallback_device = self.device_from_probe(fallback_probe) if fallback_probe else None
        if fallback_device is None:
            return None
        return fallback_device

    def resolve_virtuoso_device(self, prefer_real: bool = True) -> Device | None:
        devices = self.load_probe_devices()
        if prefer_real:
            devices = self.discover_devices() or devices
        for device in devices:
            if device.support.family == "headset" and "virtuoso" in device.support.model_hint.casefold():
                return device
        fallback_probe = mock_probe_for_slug("virtuoso-se")
        fallback_device = self.device_from_probe(fallback_probe) if fallback_probe else None
        if fallback_device is None:
            return None
        return fallback_device

    def resolve_virtuoso_receiver(self, prefer_real: bool = True) -> Device | None:
        devices = self.load_probe_devices()
        if prefer_real:
            devices = self.discover_devices() or devices
        for device in devices:
            if device.support.family == "receiver" and "virtuoso" in device.support.model_hint.casefold():
                return device
        fallback_probe = mock_probe_for_slug("virtuoso-rgb-wireless-receiver")
        return self.device_from_probe(fallback_probe) if fallback_probe else None

    def resolve_live_device_for_profile(self, profile: Profile) -> Device | None:
        devices = self.resolve_live_devices_for_profile(profile)
        return devices[0] if devices else None

    def resolve_live_devices_for_profile(self, profile: Profile) -> list[Device]:
        devices = [
            device
            for device in self.discover_devices()
            if device.transport == "hidapi" and self._profile_matches_live_device(profile, device)
        ]
        return sorted(devices, key=lambda device: self._live_device_priority(profile, device))

    def save_profile(self, profile: Profile) -> str:
        return str(self.store.save(profile))

    def rename_profile(self, old_name: str, new_name: str) -> bool:
        profile = self.load_profile(old_name)
        if profile is None or self._is_system_profile(profile):
            return False
        renamed = self.store.rename(old_name, new_name)
        if renamed is None:
            return False
        profile.name = new_name
        self.store.save(profile)
        return True

    def duplicate_profile(self, source_name: str, target_name: str) -> bool:
        profile = self.load_profile(source_name)
        if profile is None or self.store.load(target_name) is not None:
            return False
        profile.name = target_name
        profile.profile_group = ""
        profile.group_role = ""
        profile.options.pop(SYSTEM_PROFILE_FLAG, None)
        profile.options.pop("protected", None)
        profile.options.pop("system_profile_version", None)
        self.store.save(profile)
        return True

    def delete_profile(self, name: str) -> bool:
        if self.is_protected_profile(name):
            return False
        return self.store.delete(name)

    def load_profile(self, name: str) -> Profile | None:
        profile = self.store.load(name)
        if profile is None:
            return None
        self._repair_virtuoso_presets(profile)
        return self._normalize_profile_scope(profile)

    def repair_virtuoso_presets(self, name: str) -> dict[str, object]:
        profile = self.store.load(name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {name}")
        changed = self._repair_virtuoso_presets(profile)
        if changed:
            self.store.save(profile)
        return {
            "profile": name,
            "changed": changed,
            "bass_boost_bands": next(
                (preset.bands for preset in profile.audio if preset.name.casefold() == "bass boost"),
                [],
            ),
        }

    def export_virtuoso_easyeffects(self, name: str, output_dir: str | None = None) -> dict[str, object]:
        profile = self.load_profile(name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {name}")
        if profile.target_device != "virtuoso-se":
            raise RuntimeError(f"Profile is not a Virtuoso profile: {name}")
        target = Path(output_dir) if output_dir else None
        paths = export_virtuoso_easyeffects_presets(profile, target)
        return {
            "profile": name,
            "preset_count": len(paths),
            "paths": [str(path) for path in paths],
            "note": "linuxcue can load these presets through EasyEffects/PipeWire so you do not have to operate a second GUI.",
        }

    def apply_virtuoso_easyeffects(self, name: str, preset_name: str | None = None) -> dict[str, object]:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("EasyEffects apply is only supported on Linux/PipeWire.")
        binary = shutil.which("easyeffects")
        if binary is None:
            raise RuntimeError("EasyEffects is not installed. On CachyOS use: sudo pacman -S --needed easyeffects")
        profile = self.load_profile(name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {name}")
        if profile.target_device != "virtuoso-se":
            raise RuntimeError(f"Profile is not a Virtuoso profile: {name}")
        selected = self._selected_audio_preset(profile, preset_name)
        path = export_virtuoso_easyeffects_preset(profile, selected)
        exported_name = preset_export_name(profile, selected)
        load = subprocess.run([binary, "--load-preset", exported_name], check=False, capture_output=True, text=True, timeout=8)
        hide_stderr = ""
        if load.returncode != 0:
            hide = subprocess.run([binary, "--hide-window"], check=False, capture_output=True, text=True, timeout=8)
            hide_stderr = hide.stderr
            load = subprocess.run([binary, "--load-preset", exported_name], check=False, capture_output=True, text=True, timeout=8)
        if load.returncode != 0:
            raise RuntimeError(
                "EasyEffects could not load the exported preset. "
                f"Preset: {exported_name}. stderr: {(load.stderr or hide_stderr).strip()}"
            )
        return {
            "profile": name,
            "preset": selected.name,
            "easyeffects_preset": exported_name,
            "exported_count": 1,
            "paths": [str(path)],
            "backend": "EasyEffects/PipeWire",
            "visible_second_gui_required": False,
        }

    def apply_virtuoso_pipewire_eq(self, name: str, preset_name: str | None = None, restart: bool = True) -> dict[str, object]:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Native PipeWire EQ is only supported on Linux/PipeWire.")
        if shutil.which("pipewire") is None:
            raise RuntimeError("PipeWire was not found.")
        profile = self.load_profile(name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {name}")
        if profile.target_device != "virtuoso-se":
            raise RuntimeError(f"Profile is not a Virtuoso profile: {name}")
        selected = self._selected_audio_preset(profile, preset_name)
        path = write_virtuoso_pipewire_eq(profile, selected)
        reload_result: dict[str, object] | None = None
        if restart:
            if shutil.which("systemctl") is None:
                raise RuntimeError("systemctl was not found. PipeWire config was written, but PipeWire must be restarted manually.")
            reload_result = restart_pipewire_user_services()
            if not reload_result.get("ok"):
                raise RuntimeError(
                    "PipeWire config was written, but the virtual EQ sink could not be activated yet. "
                    f"{reload_result.get('stderr', '')}"
                )
        return {
            "profile": name,
            "preset": selected.name,
            "backend": "PipeWire filter-chain",
            "config": str(path),
            "restart": restart,
            "reload": reload_result,
            "note": "Select the virtual sink 'linuxcue Virtuoso EQ' as output if WirePlumber does not route it automatically.",
        }

    def easyeffects_doctor(self) -> dict[str, object]:
        binary = shutil.which("easyeffects")
        output_dir = Path.home() / ".config" / "easyeffects" / "output"
        legacy_output_dir = Path.home() / ".var" / "app" / "com.github.wwmm.easyeffects" / "config" / "easyeffects" / "output"
        lsp_paths = [
            Path("/usr/lib/lv2/lsp-plugins.lv2"),
            Path("/usr/lib/lv2/lsp-plugins-lv2.lv2"),
            Path("/usr/local/lib/lv2/lsp-plugins.lv2"),
            Path.home() / ".lv2" / "lsp-plugins.lv2",
        ]
        lsp_installed = any(path.exists() for path in lsp_paths)
        calf_paths = [
            Path("/usr/lib/lv2/calf.lv2"),
            Path("/usr/local/lib/lv2/calf.lv2"),
            Path.home() / ".lv2" / "calf.lv2",
        ]
        calf_installed = any(path.exists() for path in calf_paths)
        presets = sorted(path.name for path in output_dir.glob("linuxcue-*.json")) if output_dir.exists() else []
        legacy_presets = sorted(path.name for path in legacy_output_dir.glob("linuxcue-*.json")) if legacy_output_dir.exists() else []
        version = None
        help_text = ""
        if binary:
            try:
                version_run = subprocess.run([binary, "--version"], check=False, capture_output=True, text=True, timeout=4)
                version = (version_run.stdout or version_run.stderr).strip()
            except Exception as exc:
                version = f"version check failed: {exc}"
            try:
                help_run = subprocess.run([binary, "--help"], check=False, capture_output=True, text=True, timeout=4)
                help_text = (help_run.stdout or help_run.stderr)
            except Exception:
                help_text = ""
        return {
            "easyeffects_binary": binary,
            "version": version,
            "supports_load_preset_cli": "--load-preset" in help_text,
            "lsp_plugins_lv2_installed": lsp_installed,
            "lsp_checked_paths": [str(path) for path in lsp_paths],
            "calf_installed": calf_installed,
            "calf_checked_paths": [str(path) for path in calf_paths],
            "output_preset_dir": str(output_dir),
            "output_preset_dir_exists": output_dir.exists(),
            "linuxcue_presets": presets,
            "flatpak_output_preset_dir": str(legacy_output_dir),
            "flatpak_output_preset_dir_exists": legacy_output_dir.exists(),
            "flatpak_linuxcue_presets": legacy_presets,
            "cachyos_fix": "sudo pacman -S --needed easyeffects lsp-plugins-lv2",
            "optional_bass_enhancer_fix": "sudo pacman -S --needed calf",
            "note": "In the EasyEffects GUI, linuxcue presets are Voreinstellungen/Presets, not items under Effekt hinzufuegen. The Equalizer effect requires Linux Studio Plugins (lsp-plugins-lv2).",
        }

    @staticmethod
    def _selected_audio_preset(profile: Profile, preset_name: str | None = None):
        if preset_name:
            match = next((preset for preset in profile.audio if preset.name.casefold() == preset_name.casefold()), None)
            if match is None:
                raise RuntimeError(f"EQ preset not found in profile '{profile.name}': {preset_name}")
            return match
        active = next((preset for preset in profile.audio if preset.active), None)
        if active is not None:
            return active
        if profile.audio:
            return profile.audio[0]
        raise RuntimeError(f"Virtuoso profile has no EQ presets: {profile.name}")

    def list_profiles(self) -> list[str]:
        return self.store.list_profiles()

    def list_profile_summaries(self) -> list[dict[str, object]]:
        summaries: list[dict[str, object]] = []
        for name in self.list_profiles():
            profile = self.load_profile(name)
            if profile is None:
                continue
            summaries.append(
                {
                    "name": profile.name,
                    "target_device": profile.target_device,
                    "target_family": profile.target_family,
                    "description": profile.description,
                    "profile_group": profile.profile_group,
                    "group_role": profile.group_role,
                    "companion": self.profile_companion_label(profile),
                    "protected": self._is_system_profile(profile),
                }
            )
        return summaries

    def profiles_in_group(self, group_name: str) -> list[Profile]:
        profiles = []
        for name in self.list_profiles():
            profile = self.load_profile(name)
            if profile is None:
                continue
            if profile.profile_group == group_name and profile.group_role != "set":
                profiles.append(profile)
        order = {"keyboard": 0, "mouse": 1, "headset": 2, "receiver": 3}
        return sorted(profiles, key=lambda profile: order.get(profile.group_role, 99))

    def create_mock_probe(self, slug: str) -> str | None:
        probe = mock_probe_for_slug(slug)
        if probe is None:
            return None
        return str(self.probe_store.save(probe))

    def preview_icue_import(self, path: str) -> dict[str, object]:
        return import_icue_profile(path)

    def import_icue_profiles(self, path: str) -> dict[str, object]:
        profiles = profiles_from_icue(path)
        saved = [self.save_profile(profile) for profile in profiles]
        return {
            "source": path,
            "saved_count": len(saved),
            "saved_profiles": saved,
            "profile_names": [profile.name for profile in profiles],
        }

    def write_profile_set_live(self, profile_name: str) -> list[LiveWriteResult]:
        profile = self.load_profile(profile_name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {profile_name}")
        group_name = profile.profile_group or profile.name
        targets = self.profiles_in_group(group_name) if profile.target_device == "profile-set" else [profile]
        if not targets:
            raise RuntimeError(f"No device profiles found in profile set: {profile_name}")

        results: list[LiveWriteResult] = []
        errors: list[str] = []
        for target in targets:
            try:
                if target.target_device == "k95":
                    results.append(self.write_k95_profile_live(target.name))
                elif target.target_device == "m65":
                    results.append(self.write_m65_profile_live(target.name))
                elif target.target_device == "virtuoso-se":
                    results.append(self.write_virtuoso_profile_live(target.name))
            except RuntimeError as exc:
                errors.append(f"{target.name}: {exc}")
        if errors and not results:
            raise RuntimeError("No device in the profile set accepted live writes. " + " | ".join(errors))
        if errors:
            results.append(
                LiveWriteResult(
                    profile_name=profile_name,
                    device="partial-profile-set",
                    packet_count=0,
                    transport="hidapi",
                    live=True,
                    message="Partial profile set write. Errors: " + " | ".join(errors),
                )
            )
        return results

    def list_probes(self) -> list[str]:
        return self.probe_store.list_probes()

    def load_probe_devices(self) -> list[Device]:
        devices: list[Device] = []
        for slug in self.probe_store.list_probes():
            probe = self.probe_store.load(slug)
            if probe is None:
                continue
            devices.append(self.device_from_probe(probe))
        return devices

    def device_from_probe(self, probe: ProbeData) -> Device:
        known = known_device_by_slug(probe.slug)
        support = known.to_support() if known is not None else support_for_product(probe.product_name)
        return probe.to_device(support)

    def apply_profile(self, profile_name: str) -> ApplyResult:
        profile = self.load_profile(profile_name) or self.create_default_profile(profile_name)
        devices = self.resolve_profile_devices(profile)
        simulated = True
        actions: list[dict[str, object]] = []
        for device in devices:
            if device.support.family == "keyboard" and "k95" in device.support.model_hint.casefold():
                actions.append(plan_k95_apply(profile, device))
            elif device.support.family == "mouse" and "m65" in device.support.model_hint.casefold():
                actions.append(plan_m65_apply(profile, device))
            elif device.support.family == "headset" and "virtuoso" in device.support.model_hint.casefold():
                actions.append(plan_virtuoso_apply(profile, device))
            else:
                actions.append(
                    {
                        "device": device.support.model_hint,
                        "family": device.support.family,
                        "steps": plan_apply(profile, device),
                    }
                )
        if devices:
            matched = [device.support.model_hint for device in devices]
            message = (
                "Profile prepared for detected Corsair devices: "
                + ", ".join(matched)
                + ". Low-level write support is the next implementation layer."
            )
        else:
            message = "No compatible Corsair devices detected; apply was simulated."
        return ApplyResult(
            profile_name=profile_name,
            device_count=len(devices),
            simulated=simulated,
            message=message,
            actions=actions,
        )

    def resolve_profile_devices(self, profile: Profile) -> list[Device]:
        devices = self.load_probe_devices() or self.discover_devices()
        matched = [device for device in devices if self._profile_matches_device(profile, device)]
        if matched:
            return matched

        fallback = self._fallback_device_for_profile(profile)
        if fallback is not None:
            return [fallback]

        return devices if profile.target_device == "generic" else []

    def write_k95_profile_live(self, profile_name: str, device_path: str | None = None) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")

        profile = self.load_profile(profile_name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {profile_name}")

        devices = self.resolve_live_devices_for_profile(profile)
        if not devices:
            raise RuntimeError(self._live_device_error(profile))
        if profile.target_device == "virtuoso-se":
            headset_devices = [device for device in devices if self.endpoint_role(device) == "headset-hid"]
            receiver_devices = [device for device in devices if self.endpoint_role(device) == "wireless-receiver-control"]
            if headset_devices:
                devices = headset_devices
            elif receiver_devices:
                devices = receiver_devices

        last_error: RuntimeError | None = None
        for device in devices:
            transport = None
            try:
                transport = LiveHidTransport(
                    vendor_id=device.vendor_id,
                    product_id=device.product_id,
                    path=device_path or device.path,
                )
                sent = send_k95_profile(profile, device, transport)
                return LiveWriteResult(
                    profile_name=profile_name,
                    device=device.support.model_hint,
                    packet_count=int(sent["packet_count"]),
                    transport="hidapi",
                    live=True,
                    message=f"K95 profile frames were sent through hidapi path {device.path}.",
                )
            except RuntimeError as exc:
                last_error = exc
            finally:
                if transport is not None:
                    transport.close()

        raise RuntimeError(f"No K95 HID endpoint accepted the write. Last error: {last_error}")

    def write_k95_hardware_mode_live(self, device_path: str | None = None) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")
        profile = self.create_k95_profile("k95-hardware-mode")
        devices = self.resolve_live_devices_for_profile(profile)
        if not devices:
            raise RuntimeError(self._live_device_error(profile))
        packet = build_k95_lighting_control_packet(0x01)
        last_error: RuntimeError | None = None
        for device in devices:
            transport = None
            try:
                transport = LiveHidTransport(device.vendor_id, device.product_id, path=device_path or device.path)
                write_k95_packets([packet], transport)
                return LiveWriteResult(
                    profile_name="k95-hardware-mode",
                    device=device.support.model_hint,
                    packet_count=1,
                    transport="hidapi",
                    live=True,
                    message=f"K95 hardware lighting mode was sent through hidapi path {device.path}.",
                )
            except RuntimeError as exc:
                last_error = exc
            finally:
                if transport is not None:
                    transport.close()
        raise RuntimeError(f"No K95 HID endpoint accepted hardware-mode write. Last error: {last_error}")

    def write_k95_options_sync_live(self, profile_name: str, device_path: str | None = None) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")
        profile = self.load_profile(profile_name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {profile_name}")
        if profile.target_device != "k95":
            raise RuntimeError("K95 options can only be synced for K95 profiles.")
        devices = self.resolve_live_devices_for_profile(profile)
        if not devices:
            raise RuntimeError(self._live_device_error(profile))
        packets = build_k95_special_function_packets()
        last_error: RuntimeError | None = None
        for device in devices:
            transport = None
            try:
                transport = LiveHidTransport(device.vendor_id, device.product_id, path=device_path or device.path)
                write_k95_packets(packets, transport)
                return LiveWriteResult(
                    profile_name=profile_name,
                    device=device.support.model_hint,
                    packet_count=len(packets),
                    transport="hidapi",
                    live=True,
                    message=f"K95 special-function/ISO option frames were sent through hidapi path {device.path}.",
                )
            except RuntimeError as exc:
                last_error = exc
            finally:
                if transport is not None:
                    transport.close()
        raise RuntimeError(f"No K95 HID endpoint accepted options sync. Last error: {last_error}")

    def write_m65_profile_live(
        self,
        profile_name: str,
        device_path: str | None = None,
        *,
        use_feature_report: bool = False,
        packet_kind: str = "all",
    ) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")

        profile = self.load_profile(profile_name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {profile_name}")

        devices = self.resolve_live_devices_for_profile(profile)
        if not devices:
            raise RuntimeError(self._live_device_error(profile))

        last_error: RuntimeError | None = None
        for device in devices:
            transport = None
            try:
                transport = LiveHidTransport(
                    vendor_id=device.vendor_id,
                    product_id=device.product_id,
                    path=device_path or device.path,
                )
                sent = send_m65_profile(
                    profile,
                    device,
                    transport,
                    use_feature_report=use_feature_report,
                    packet_kind=packet_kind,
                )
                if packet_kind == "buttons" and int(sent["packet_count"]) == 0:
                    message = (
                        "M65 button mapping is stored in the linuxcue profile, but no verified M65 button HID write "
                        "was present in the iCUE capture. No hardware packets were sent."
                    )
                else:
                    message = (
                        f"M65 {sent.get('packet_kind', packet_kind)} frames were sent through hidapi path {device.path} "
                        f"using {sent.get('write_mode', 'output_report')} mode."
                    )
                return LiveWriteResult(
                    profile_name=profile_name,
                    device=device.support.model_hint,
                    packet_count=int(sent["packet_count"]),
                    transport="hidapi",
                    live=True,
                    message=message,
                )
            except RuntimeError as exc:
                last_error = exc
            finally:
                if transport is not None:
                    transport.close()

        raise RuntimeError(f"No M65 HID endpoint accepted the write. Last error: {last_error}")

    def write_virtuoso_profile_live(
        self,
        profile_name: str,
        device_path: str | None = None,
        *,
        use_feature_report: bool = False,
        prefer_receiver: bool = False,
        packet_kind: str = "all",
    ) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")

        profile = self.load_profile(profile_name)
        if profile is None:
            raise RuntimeError(f"Profile not found: {profile_name}")

        if prefer_receiver:
            receiver = self.resolve_virtuoso_receiver(prefer_real=True)
            if receiver is None or receiver.transport != "hidapi":
                raise RuntimeError("Virtuoso receiver was requested, but no wireless receiver HID endpoint is available.")
            devices = [receiver]
        else:
            devices = self.resolve_live_devices_for_profile(profile)
            if not devices:
                raise RuntimeError(self._live_device_error(profile))

        last_error: RuntimeError | None = None
        for device in devices:
            transport = None
            try:
                transport = LiveHidTransport(
                    vendor_id=device.vendor_id,
                    product_id=device.product_id,
                    path=device_path or device.path,
                )
                sent = send_virtuoso_profile(
                    profile,
                    device,
                    transport,
                    use_feature_report=use_feature_report,
                    packet_kind=packet_kind,
                )
                return LiveWriteResult(
                    profile_name=profile_name,
                    device=device.support.model_hint,
                    packet_count=int(sent["packet_count"]),
                    transport="hidapi",
                    live=True,
                    message=(
                        f"Virtuoso profile frames were sent through hidapi path {device.path} "
                        f"using {sent.get('write_mode', 'output_report')} mode."
                    ),
                )
            except RuntimeError as exc:
                last_error = exc
            finally:
                if transport is not None:
                    transport.close()

        raise RuntimeError(f"No Virtuoso HID endpoint accepted the write. Last error: {last_error}")

    def sweep_virtuoso_rgb_live(
        self,
        *,
        device_path: str | None = None,
        prefer_receiver: bool = False,
        delay_seconds: float = 0.35,
    ) -> LiveWriteResult:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID writing is only supported on Linux.")
        device = self.resolve_virtuoso_receiver(prefer_real=True) if prefer_receiver else self.resolve_virtuoso_device(prefer_real=True)
        if device is None or device.transport != "hidapi":
            raise RuntimeError("No Virtuoso HID endpoint is available for RGB sweep.")
        packets = build_virtuoso_rgb_sweep_packets()
        transport = None
        try:
            transport = LiveHidTransport(device.vendor_id, device.product_id, path=device_path or device.path)
            for packet in packets:
                write_virtuoso_packets([packet], transport)
                time.sleep(max(0.05, delay_seconds))
        finally:
            if transport is not None:
                transport.close()
        return LiveWriteResult(
            profile_name="virtuoso-rgb-sweep",
            device=device.support.model_hint,
            packet_count=len(packets),
            transport="hidapi",
            live=True,
            message=f"Virtuoso RGB sweep frames were sent through hidapi path {device.path}.",
        )

    def read_virtuoso_status_live(self, *, prefer_receiver: bool = False, device_path: str | None = None) -> dict[str, object]:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live HID reading is only supported on Linux.")
        if prefer_receiver:
            device = self.resolve_virtuoso_receiver(prefer_real=True)
            if device is None or device.transport != "hidapi":
                raise RuntimeError("Virtuoso receiver status was requested, but no receiver HID endpoint is available.")
        else:
            device = self.resolve_virtuoso_device(prefer_real=True) or self.resolve_virtuoso_receiver(prefer_real=True)
            if device is None or device.transport != "hidapi":
                raise RuntimeError("No Virtuoso headset or receiver HID endpoint is available.")

        transport = None
        try:
            transport = LiveHidTransport(device.vendor_id, device.product_id, path=device_path or device.path)
            report = transport.read_feature_report(0x0C, 64)
        finally:
            if transport is not None:
                transport.close()
        candidates = [
            {"offset": index, "value": value}
            for index, value in enumerate(report)
            if 0 <= value <= 100
        ]
        return {
            "device": device.support.model_hint,
            "path": device.path,
            "endpoint_role": self.endpoint_role(device),
            "report_id": "0x0c",
            "raw_hex": report.hex(" "),
            "candidate_percent_values": candidates[:24],
            "battery_warning": "Battery byte mapping is not verified yet; use captures at high/medium/low charge to identify the correct offset.",
        }

    def read_virtuoso_battery_live(self, *, seconds: float = 1.5, poll: bool = True, poll_mode: str = "capture") -> dict[str, object]:
        if not sys.platform.startswith("linux"):
            raise RuntimeError("Live Virtuoso battery reading is only supported on Linux.")
        devices = [
            device
            for device in self.discover_devices()
            if device.transport == "hidapi"
            and (
                device.support.family in {"headset", "receiver"}
                or "virtuoso" in device.support.model_hint.casefold()
            )
        ]
        if not devices:
            usb_status = self._read_virtuoso_usb_battery(seconds=seconds, poll_mode=poll_mode, poll=poll)
            if usb_status.get("battery_percent") is not None:
                usb_status["source"] = "pyusb"
                return usb_status
            raise RuntimeError(
                "No Virtuoso HID endpoint is available for battery monitoring. "
                f"USB fallback: {usb_status}"
            )
        endpoint_summary = [
            {
                "product": device.product_name,
                "target": device.support.model_hint,
                "family": device.support.family,
                "path": device.path,
                "interface_number": device.interface_number,
                "endpoint_role": self.endpoint_role(device),
            }
            for device in devices
        ]
        monitor = VirtuosoBatteryMonitor()
        try:
            if not monitor.ensure_open_many(devices):
                raise RuntimeError(f"Virtuoso HID endpoints were found, but none could be opened for input monitoring. Endpoints: {endpoint_summary}")
            open_count = monitor.open_count
            opened_paths = monitor.opened_paths
            failed_paths = monitor.failed_paths
            poll_results = monitor.send_battery_poll(mode=poll_mode) if poll else []
            status = monitor.read_status(seconds=seconds)
        finally:
            monitor.close()
        if status is None:
            usb_status = self._read_virtuoso_usb_battery(seconds=seconds, poll_mode=poll_mode, poll=poll)
            if usb_status.get("battery_percent") is None:
                raise RuntimeError(
                    "No Virtuoso battery input report was received. "
                    f"Listened for {seconds:.1f}s on {opened_paths}. "
                    f"Poll results: {poll_results}. "
                    f"USB fallback: {usb_status}. "
                    "This usually means the VM exposes the HID control endpoint but no interrupt-input status stream, "
                    "or the headset/receiver is not currently emitting status reports. "
                    f"Detected endpoints: {endpoint_summary}"
                )
            usb_status["hidapi_poll_results"] = poll_results
            usb_status["hidapi_opened_paths"] = opened_paths
            usb_status["source"] = "pyusb"
            return usb_status
        return {
            "device_count": len(devices),
            "open_count": open_count,
            "opened_paths": opened_paths,
            "failed_paths": failed_paths,
            "poll_results": poll_results,
            "endpoints": endpoint_summary,
            "battery_percent": status.percent,
            "battery_raw_tenths": status.raw_value,
            "critical": status.critical,
            "link_state": status.link_state,
            "packet_count": status.packet_count,
            "mapping": "report 03 01 01 0f 00 bytes 5-6 little-endian, divided by 10",
        }

    def virtuoso_battery_doctor(self, *, seconds: float = 3.0, poll: bool = True, poll_mode: str = "capture") -> dict[str, object]:
        devices = [
            device
            for device in self.discover_devices()
            if device.transport == "hidapi"
            and (
                device.support.family in {"headset", "receiver"}
                or "virtuoso" in device.support.model_hint.casefold()
            )
        ]
        result: dict[str, object] = {
            "device_count": len(devices),
            "poll_enabled": poll,
            "poll_mode": poll_mode,
            "endpoints": [
                {
                    "product": device.product_name,
                    "target": device.support.model_hint,
                    "family": device.support.family,
                    "path": device.path,
                    "interface_number": device.interface_number,
                    "endpoint_role": self.endpoint_role(device),
                }
                for device in devices
            ],
        }
        if not sys.platform.startswith("linux"):
            result["live_supported"] = False
            result["error"] = "Live monitoring is only supported on Linux."
            return result
        if not devices:
            result["live_supported"] = True
            result["error"] = "No Virtuoso HID endpoint was detected."
            result["usb_fallback"] = self._read_virtuoso_usb_battery(seconds=seconds, poll_mode=poll_mode, poll=poll)
            return result
        monitor = VirtuosoBatteryMonitor()
        status = None
        opened = False
        try:
            opened = monitor.ensure_open_many(devices)
            result["opened"] = opened
            result["opened_paths"] = monitor.opened_paths
            result["failed_paths"] = monitor.failed_paths
            if opened:
                result["poll_results"] = monitor.send_battery_poll(mode=poll_mode) if poll else []
                status = monitor.read_status(seconds=seconds)
                result["packet_listen_seconds"] = seconds
                if status is not None:
                    result["battery_percent"] = status.percent
                    result["battery_raw_tenths"] = status.raw_value
                    result["critical"] = status.critical
                    result["link_state"] = status.link_state
                    result["packet_count"] = status.packet_count
                else:
                    result["battery_percent"] = None
                    result["packet_count"] = 0
                    result["hint"] = "No 03 01 01 0f 00 input report arrived while listening. Try USB mode, receiver mode, and keeping the Virtuoso page open."
        finally:
            monitor.close()
        if opened and status is None:
            result["usb_fallback"] = self._read_virtuoso_usb_battery(seconds=seconds, poll_mode=poll_mode, poll=poll)
        return result

    def virtuoso_battery_hotplug_doctor(
        self,
        *,
        wait_seconds: float = 45.0,
        listen_seconds: float = 8.0,
        poll: bool = False,
        poll_mode: str = "capture",
        require_reconnect: bool = False,
    ) -> dict[str, object]:
        if not sys.platform.startswith("linux"):
            return {
                "live_supported": False,
                "error": "Hotplug monitoring is only supported on Linux.",
            }
        deadline = time.monotonic() + max(wait_seconds, 1.0)
        attempts = 0
        last_open: dict[str, object] | None = None
        saw_missing = not require_reconnect
        while time.monotonic() < deadline:
            attempts += 1
            monitor = VirtuosoUsbBatteryMonitor()
            open_result = monitor.open(product_id=0x0A3E)
            last_open = open_result
            if require_reconnect and open_result.get("ok") and not saw_missing:
                monitor.close()
                time.sleep(0.25)
                continue
            if not open_result.get("ok"):
                saw_missing = True
                monitor.close()
                time.sleep(0.2)
                continue
            if open_result.get("ok"):
                try:
                    status, meta = monitor.read_status(seconds=listen_seconds, poll_mode=poll_mode, poll=poll)
                    result: dict[str, object] = {
                        "mode": "hotplug",
                        "attempts": attempts,
                        "wait_seconds": wait_seconds,
                        "listen_seconds": listen_seconds,
                        "poll_enabled": poll,
                        "poll_mode": poll_mode,
                        "require_reconnect": require_reconnect,
                        "saw_missing_before_open": saw_missing,
                        "open": open_result,
                        "read": meta,
                    }
                    if status is not None:
                        result.update(
                            {
                                "battery_percent": status.percent,
                                "battery_raw_tenths": status.raw_value,
                                "critical": status.critical,
                                "link_state": status.link_state,
                                "packet_count": status.packet_count,
                                "mapping": "pyusb hotplug interface 4 endpoint 0x82, report 03 01 01 0f 00 bytes 5-6 / 10",
                            }
                        )
                    else:
                        result["battery_percent"] = None
                        result["hint"] = (
                            "Device appeared, but no battery input report arrived during the first listen window. "
                            "Try starting this command before attaching the Virtuoso to the VM, then attach it immediately."
                        )
                    return result
                finally:
                    monitor.close()
            monitor.close()
            time.sleep(0.2)
        return {
            "mode": "hotplug",
            "attempts": attempts,
            "wait_seconds": wait_seconds,
            "listen_seconds": listen_seconds,
            "poll_enabled": poll,
            "poll_mode": poll_mode,
            "require_reconnect": require_reconnect,
            "saw_missing_before_open": saw_missing,
            "battery_percent": None,
            "last_open": last_open,
            "hint": "No fresh Virtuoso USB attach was observed before the timeout. Detach VID 1b1c PID 0a3e from the VM, wait until linuxcue sees it missing, then attach it again.",
        }

    def _read_virtuoso_usb_battery(self, *, seconds: float = 3.0, poll_mode: str = "capture", poll: bool = True) -> dict[str, object]:
        monitor = VirtuosoUsbBatteryMonitor()
        open_result = monitor.open(product_id=0x0A3E)
        result: dict[str, object] = {
            "poll_enabled": poll,
            "poll_mode": poll_mode,
            "open": open_result,
        }
        if not open_result.get("ok"):
            return result
        try:
            status, meta = monitor.read_status(seconds=seconds, poll_mode=poll_mode, poll=poll)
            result["read"] = meta
            if status is not None:
                result.update(
                    {
                        "battery_percent": status.percent,
                        "battery_raw_tenths": status.raw_value,
                        "critical": status.critical,
                        "link_state": status.link_state,
                        "packet_count": status.packet_count,
                        "mapping": "pyusb interface 4 endpoint 0x82, report 03 01 01 0f 00 bytes 5-6 / 10",
                    }
                )
            else:
                result["battery_percent"] = None
        finally:
            monitor.close()
        return result

    def _profile_matches_device(self, profile: Profile, device: Device) -> bool:
        if profile.target_device not in {"", "generic"}:
            return profile.target_device in self._device_slug_candidates(device)
        if profile.target_family not in {"", "generic"}:
            return profile.target_family == device.support.family
        return True

    def _profile_matches_live_device(self, profile: Profile, device: Device) -> bool:
        if self._profile_matches_device(profile, device):
            return True
        if profile.target_device == "virtuoso-se":
            return "virtuoso-rgb-wireless-receiver" in self._device_slug_candidates(device)
        return False

    @staticmethod
    def endpoint_role(device: Device) -> str:
        name = device.support.model_hint.casefold()
        if "k95" in name and device.interface_number == 1:
            return "keyboard-control-feature"
        if "k95" in name and device.interface_number == 0:
            return "keyboard-input"
        if "virtuoso" in name and "receiver" in name:
            return "wireless-receiver-control"
        if "virtuoso" in name and device.interface_number in {3, 4}:
            return "headset-hid"
        if device.support.family != "unknown":
            return f"{device.support.family}-hid"
        return "unknown-hid"

    @staticmethod
    def _live_device_priority(profile: Profile, device: Device) -> int:
        role = LinuxCueService.endpoint_role(device)
        if profile.target_device == "k95":
            return {
                "keyboard-control-feature": 0,
                "keyboard-input": 50,
            }.get(role, 100)
        if profile.target_device == "virtuoso-se":
            return {
                "headset-hid": 0,
                "wireless-receiver-control": 50,
            }.get(role, 100)
        if profile.target_device == "m65":
            return 0 if device.support.family == "mouse" else 100
        return 100

    def _fallback_device_for_profile(self, profile: Profile) -> Device | None:
        if profile.target_device == "k95":
            return self.resolve_k95_device(prefer_real=False)
        if profile.target_device == "m65":
            return self.resolve_m65_device(prefer_real=False)
        if profile.target_device == "virtuoso-se":
            return self.resolve_virtuoso_device(prefer_real=False)
        return None

    @staticmethod
    def _device_slug_candidates(device: Device) -> set[str]:
        name = device.support.model_hint.casefold()
        candidates: set[str] = set()
        if "k95" in name:
            candidates.add("k95")
        if "m65" in name:
            candidates.add("m65")
        if "virtuoso" in name and "receiver" not in name:
            candidates.add("virtuoso-se")
        if "virtuoso" in name and "receiver" in name:
            candidates.add("virtuoso-rgb-wireless-receiver")
        return candidates

    def profile_companion_label(self, profile: Profile) -> str:
        if profile.target_device == "profile-set":
            members = self.profiles_in_group(profile.profile_group or profile.name)
            roles = [member.group_role or member.target_device for member in members]
            return "Profile set: " + ", ".join(roles)
        if profile.profile_group and profile.group_role:
            return f"{profile.profile_group} / {profile.group_role}"
        if profile.target_device == "virtuoso-se":
            receiver = self.resolve_virtuoso_receiver(prefer_real=False)
            return receiver.support.model_hint if receiver is not None else "Virtuoso wireless receiver"
        return ""

    def _live_device_error(self, profile: Profile) -> str:
        status = self.live_status(profile)
        if status["connected_count"] == 0:
            return (
                f"No connected Corsair HID device was detected for profile target '{profile.target_device}'. "
                "In VirtualBox, pass the USB device through to the VM first."
            )
        if status["writable_count"] == 0:
            return (
                "Corsair devices were detected through sysfs, but no writable hidapi endpoint is available. "
                "Install python-hidapi and check udev permissions, then reconnect the USB device."
            )
        seen = ", ".join(
            f"{item['product']} ({item['product_id']}, {item['transport']})"
            for item in status["devices"]
        )
        return (
            f"No writable HID endpoint matched profile target '{profile.target_device}'. "
            f"Detected Corsair devices: {seen or 'none'}. "
            "If this is VirtualBox, make sure the specific keyboard/mouse/headset USB device is passed through to the VM."
        )

    @staticmethod
    def _normalize_profile_scope(profile: Profile) -> Profile:
        if profile.target_device not in {"", "generic"} or profile.target_family not in {"", "generic"}:
            return profile

        name = profile.name.casefold()
        if "k95" in name or any(zone.name in {"function", "numbers", "macro", "media"} for zone in profile.lighting):
            profile.target_device = "k95"
            profile.target_family = "keyboard"
            profile.description = profile.description or "K95 zoned lighting profile"
            return profile

        if "m65" in name or profile.dpi:
            profile.target_device = "m65"
            profile.target_family = "mouse"
            profile.description = profile.description or "M65 DPI and lighting profile"
            return profile

        if "virtuoso" in name or profile.audio:
            profile.target_device = "virtuoso-se"
            profile.target_family = "headset"
            profile.description = profile.description or "Virtuoso SE EQ, lighting, and control profile"
            return profile

        return profile

    @staticmethod
    def _repair_virtuoso_presets(profile: Profile) -> bool:
        if profile.target_device != "virtuoso-se" and "virtuoso" not in profile.name.casefold() and not profile.audio:
            return False
        changed = False
        for preset in profile.audio:
            if preset.name.casefold() != "bass boost":
                continue
            if preset.bands and any(value != 0 for value in preset.bands):
                continue
            preset.bands = list(VIRTUOSO_BASS_BOOST_BANDS)
            preset.bass = round(sum(preset.bands[:3]) / 3)
            preset.mids = round(sum(preset.bands[3:7]) / 4)
            preset.treble = round(sum(preset.bands[7:]) / 3)
            changed = True
        return changed
