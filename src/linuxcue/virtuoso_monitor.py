from __future__ import annotations

import time
from dataclasses import dataclass

from .models import Device


@dataclass(frozen=True, slots=True)
class VirtuosoBatteryStatus:
    percent: float
    raw_value: int
    packet_count: int
    link_state: int | None = None

    @property
    def critical(self) -> bool:
        return self.percent <= 15.0


class VirtuosoBatteryMonitor:
    """Non-blocking reader for Virtuoso wireless battery/status input reports."""

    BATTERY_PREFIX = b"\x03\x01\x01\x0f\x00"
    LINK_PREFIX = b"\x03\x01\x01\x10\x00"

    def __init__(self) -> None:
        self._devices: dict[str, object] = {}
        self._opened_paths: list[str] = []
        self._failed_paths: list[str] = []

    def ensure_open_many(self, devices: list[Device]) -> bool:
        targets = [device for device in devices if device.transport == "hidapi" and device.path]
        target_paths = {str(device.path) for device in targets}
        for stale_path in [path for path in self._devices if path not in target_paths]:
            self._close_path(stale_path)
        if target_paths and target_paths.issubset(set(self._devices)):
            return True
        try:
            import hid  # type: ignore
        except ImportError:
            return False
        for device in targets:
            path = str(device.path)
            if path in self._devices:
                continue
            try:
                handle = hid.device()
                handle.open_path(device.path.encode() if isinstance(device.path, str) else device.path)
                handle.set_nonblocking(True)
            except OSError:
                self._failed_paths.append(path)
                continue
            self._devices[path] = handle
            self._opened_paths.append(path)
        return bool(self._devices)

    def read_status(self, seconds: float = 1.5) -> VirtuosoBatteryStatus | None:
        deadline = time.monotonic() + max(seconds, 0.1)
        battery_raw: int | None = None
        link_state: int | None = None
        packet_count = 0
        while time.monotonic() < deadline:
            reports = self.read_reports(limit_per_device=8)
            if not reports:
                time.sleep(0.03)
                continue
            for report in reports:
                packet_count += 1
                parsed_raw = parse_virtuoso_battery_raw(report)
                if parsed_raw is not None:
                    battery_raw = parsed_raw
                parsed_link = parse_virtuoso_link_state(report)
                if parsed_link is not None:
                    link_state = parsed_link
        if battery_raw is None:
            return None
        return VirtuosoBatteryStatus(
            percent=max(0.0, min(100.0, round(battery_raw / 10, 1))),
            raw_value=battery_raw,
            packet_count=packet_count,
            link_state=link_state,
        )

    def send_battery_poll(self, mode: str = "capture") -> list[dict[str, object]]:
        payloads = _battery_poll_payloads(mode)
        results: list[dict[str, object]] = []
        for path, device in list(self._devices.items()):
            for label, payload in payloads:
                try:
                    written = device.write(payload)
                except OSError as exc:
                    results.append({"path": path, "mode": mode, "label": label, "ok": False, "error": str(exc)})
                    continue
                results.append(
                    {
                        "path": path,
                        "mode": mode,
                        "label": label,
                        "ok": written > 0,
                        "written": written,
                        "payload_prefix": payload[:16].hex(" "),
                    }
                )
        return results

    def read_reports(self, limit_per_device: int = 8) -> list[bytes]:
        reports: list[bytes] = []
        for path, device in list(self._devices.items()):
            for _ in range(limit_per_device):
                try:
                    report = bytes(device.read(64))
                except OSError:
                    self._close_path(path)
                    break
                if not report:
                    break
                reports.append(_strip_zero_report_id(report))
        return reports

    def close(self) -> None:
        for path in list(self._devices):
            self._close_path(path)

    @property
    def open_count(self) -> int:
        return len(self._devices)

    @property
    def opened_paths(self) -> list[str]:
        return list(self._opened_paths)

    @property
    def failed_paths(self) -> list[str]:
        return list(self._failed_paths)

    def _close_path(self, path: str) -> None:
        device = self._devices.pop(path, None)
        if device is not None:
            try:
                device.close()
            except Exception:
                pass


def parse_virtuoso_battery_raw(report: bytes) -> int | None:
    payload = _strip_zero_report_id(report)
    if len(payload) >= 7 and payload.startswith(VirtuosoBatteryMonitor.BATTERY_PREFIX):
        return int.from_bytes(payload[5:7], "little")
    return None


def parse_virtuoso_link_state(report: bytes) -> int | None:
    payload = _strip_zero_report_id(report)
    if len(payload) >= 6 and payload.startswith(VirtuosoBatteryMonitor.LINK_PREFIX):
        return payload[5]
    return None


def classify_virtuoso_status_report(report: bytes) -> str:
    payload = _strip_zero_report_id(report)
    if parse_virtuoso_battery_raw(payload) is not None:
        return "battery"
    if parse_virtuoso_link_state(payload) is not None:
        return "link"
    if len(payload) >= 4 and payload.startswith(b"\x01\x01\x06"):
        return "ack"
    return "unknown"


def _strip_zero_report_id(report: bytes) -> bytes:
    if len(report) >= 2 and report[0] == 0x00:
        return report[1:]
    return report


def _battery_poll_payloads(mode: str) -> list[tuple[str, bytes]]:
    basic = ("basic-70", bytes([0x02, 0x70, 0x01, 0x00, 0x00, *([0x00] * 59)]))
    # Captured directly before 03 01 01 0f 00 battery/status input reports in Windows iCUE.
    capture_zero = (
        "capture-status-00",
        bytes([0x02, 0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0xFB, 0x00, 0x00, 0x29, 0x00, 0xFF, 0x59, *([0x00] * 49)]),
    )
    capture_mid = (
        "capture-status-80",
        bytes([0x02, 0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0xFB, 0x00, 0x00, 0x29, 0x80, 0xFF, 0x59, *([0x00] * 49)]),
    )
    capture_ff_zero = (
        "capture-status-ff-00",
        bytes([0x02, 0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0xFB, 0xFF, 0x00, 0x29, 0x00, 0xFF, 0x59, *([0x00] * 49)]),
    )
    capture_ff_be = (
        "capture-status-ff-be",
        bytes([0x02, 0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0xFB, 0xFF, 0x00, 0x29, 0xBE, 0xFF, 0x59, *([0x00] * 49)]),
    )
    if mode == "basic":
        return [basic]
    if mode == "both":
        return [basic, capture_zero, capture_mid, capture_ff_zero, capture_ff_be]
    return [capture_zero, capture_mid, capture_ff_zero, capture_ff_be]


class VirtuosoUsbBatteryMonitor:
    """pyusb/libusb fallback for Virtuoso interface 4 endpoint 0x82 battery reports."""

    VENDOR_ID = 0x1B1C
    PRODUCT_IDS = (0x0A3E, 0x0A3D, 0x0A46)
    INTERFACE = 4
    ENDPOINT_IN = 0x82
    ENDPOINT_OUT = 0x02

    def __init__(self) -> None:
        self._usb = None
        self._device = None
        self._detached = False

    def open(self, product_id: int | None = None) -> dict[str, object]:
        try:
            import usb.core  # type: ignore
            import usb.util  # type: ignore
        except ImportError as exc:
            return {
                "ok": False,
                "backend": "pyusb",
                "error": "pyusb is not installed. Install python-pyusb or `pip install pyusb` in the linuxcue venv.",
                "exception": str(exc),
            }

        self._usb = usb
        product_ids = [product_id] if product_id is not None else list(self.PRODUCT_IDS)
        for candidate in product_ids:
            device = usb.core.find(idVendor=self.VENDOR_ID, idProduct=candidate)
            if device is None:
                continue
            self._device = device
            try:
                if device.is_kernel_driver_active(self.INTERFACE):
                    device.detach_kernel_driver(self.INTERFACE)
                    self._detached = True
                usb.util.claim_interface(device, self.INTERFACE)
            except Exception as exc:
                return {
                    "ok": False,
                    "backend": "pyusb",
                    "product_id": f"0x{candidate:04x}",
                    "interface": self.INTERFACE,
                    "error": str(exc),
                    "hint": "Try udev permissions or run once with sudo. Claiming interface 4 may temporarily detach usbhid for the Virtuoso status HID.",
                }
            return {
                "ok": True,
                "backend": "pyusb",
                "product_id": f"0x{candidate:04x}",
                "interface": self.INTERFACE,
                "endpoint_in": f"0x{self.ENDPOINT_IN:02x}",
                "endpoint_out": f"0x{self.ENDPOINT_OUT:02x}",
                "detached_kernel_driver": self._detached,
            }
        return {
            "ok": False,
            "backend": "pyusb",
            "error": "No Virtuoso USB device found through libusb.",
            "product_ids": [f"0x{item:04x}" for item in product_ids],
        }

    def read_status(self, seconds: float = 3.0, poll_mode: str = "capture", poll: bool = True) -> tuple[VirtuosoBatteryStatus | None, dict[str, object]]:
        if self._device is None:
            return None, {"ok": False, "error": "USB device is not open."}
        if not poll:
            status, meta = self._read_status_window(seconds=seconds, phase="passive")
            meta["poll_results"] = []
            return status, meta
        pre_status, pre_meta = self._read_status_window(seconds=min(1.0, max(seconds / 3, 0.2)), phase="pre-poll")
        if pre_status is not None:
            pre_meta["poll_results"] = []
            return pre_status, pre_meta
        post_status, post_meta = self._poll_and_read_status(seconds=seconds, poll_mode=poll_mode)
        post_meta["pre_samples"] = pre_meta.get("samples", [])
        return post_status, post_meta

    def _poll_and_read_status(self, seconds: float, poll_mode: str) -> tuple[VirtuosoBatteryStatus | None, dict[str, object]]:
        if self._device is None:
            return None, {"ok": False, "error": "USB device is not open."}
        deadline = time.monotonic() + max(seconds, 0.5)
        poll_results: list[dict[str, object]] = []
        samples: list[dict[str, object]] = []
        packet_count = 0
        battery_raw: int | None = None
        link_state: int | None = None
        last_read_error = ""
        while time.monotonic() < deadline:
            for label, payload in _battery_poll_payloads(poll_mode):
                if time.monotonic() >= deadline:
                    break
                try:
                    written = self._device.write(self.ENDPOINT_OUT, payload, timeout=500)
                except Exception as exc:
                    poll_results.append({"mode": poll_mode, "label": label, "ok": False, "error": str(exc)})
                    continue
                poll_results.append(
                    {
                        "mode": poll_mode,
                        "label": label,
                        "ok": written > 0,
                        "written": int(written),
                        "payload_prefix": payload[:16].hex(" "),
                    }
                )
                status, meta = self._read_status_window(seconds=0.45, phase=f"after-{label}")
                packet_count += int(meta.get("packet_count", 0))
                last_read_error = str(meta.get("last_read_error", "")) or last_read_error
                samples.extend(list(meta.get("samples", []))[: max(0, 16 - len(samples))])
                if status is not None:
                    return status, {
                        "packet_count": packet_count,
                        "samples": samples,
                        "last_read_error": last_read_error,
                        "poll_results": poll_results,
                    }
        if battery_raw is None:
            return None, {
                "packet_count": packet_count,
                "samples": samples,
                "last_read_error": last_read_error,
                "poll_results": poll_results,
            }
        return (
            VirtuosoBatteryStatus(
                percent=max(0.0, min(100.0, round(battery_raw / 10, 1))),
                raw_value=battery_raw,
                packet_count=packet_count,
                link_state=link_state,
            ),
            {
                "packet_count": packet_count,
                "samples": samples,
                "last_read_error": last_read_error,
                "poll_results": poll_results,
            },
        )

    def _read_status_window(self, seconds: float, phase: str) -> tuple[VirtuosoBatteryStatus | None, dict[str, object]]:
        if self._device is None:
            return None, {"ok": False, "error": "USB device is not open."}
        deadline = time.monotonic() + max(seconds, 0.1)
        packet_count = 0
        battery_raw: int | None = None
        link_state: int | None = None
        last_error = ""
        samples: list[dict[str, object]] = []
        while time.monotonic() < deadline:
            try:
                data = bytes(self._device.read(self.ENDPOINT_IN, 64, timeout=250))
            except Exception as exc:
                last_error = str(exc)
                continue
            packet_count += 1
            if len(samples) < 12:
                samples.append(
                    {
                        "index": packet_count,
                        "phase": phase,
                        "length": len(data),
                        "payload_hex": data.hex(" "),
                        "kind": classify_virtuoso_status_report(data),
                        "parsed_battery_raw": parse_virtuoso_battery_raw(data),
                        "parsed_link_state": parse_virtuoso_link_state(data),
                    }
                )
            parsed_raw = parse_virtuoso_battery_raw(data)
            if parsed_raw is not None:
                battery_raw = parsed_raw
            parsed_link = parse_virtuoso_link_state(data)
            if parsed_link is not None:
                link_state = parsed_link
        meta = {
            "packet_count": packet_count,
            "samples": samples,
            "last_read_error": last_error,
        }
        if battery_raw is None:
            return None, meta
        return (
            VirtuosoBatteryStatus(
                percent=max(0.0, min(100.0, round(battery_raw / 10, 1))),
                raw_value=battery_raw,
                packet_count=packet_count,
                link_state=link_state,
            ),
            meta,
        )

    def send_battery_poll(self, mode: str = "capture") -> list[dict[str, object]]:
        if self._device is None:
            return [{"ok": False, "error": "USB device is not open."}]
        results: list[dict[str, object]] = []
        for label, payload in _battery_poll_payloads(mode):
            try:
                written = self._device.write(self.ENDPOINT_OUT, payload, timeout=500)
            except Exception as exc:
                results.append({"mode": mode, "label": label, "ok": False, "error": str(exc)})
                continue
            results.append(
                {
                    "mode": mode,
                    "label": label,
                    "ok": written > 0,
                    "written": int(written),
                    "payload_prefix": payload[:16].hex(" "),
                }
            )
        return results

    def close(self) -> None:
        if self._device is None or self._usb is None:
            return
        try:
            self._usb.util.release_interface(self._device, self.INTERFACE)
        except Exception:
            pass
        if self._detached:
            try:
                self._device.attach_kernel_driver(self.INTERFACE)
            except Exception:
                pass
        self._device = None
        self._detached = False
