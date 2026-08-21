from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class HidTransport(Protocol):
    def write(self, report_id: int, payload: bytes) -> None: ...
    def write_feature(self, report_id: int, payload: bytes) -> None: ...


@dataclass(slots=True)
class TransportWrite:
    report_id: int
    payload_hex: str
    byte_count: int


class MockHidTransport:
    """Collects HID reports so backend logic can be tested without hardware."""

    def __init__(self) -> None:
        self.writes: list[TransportWrite] = []

    def write(self, report_id: int, payload: bytes) -> None:
        self.writes.append(
            TransportWrite(
                report_id=report_id,
                payload_hex=payload.hex(" "),
                byte_count=len(payload),
            )
        )

    def write_feature(self, report_id: int, payload: bytes) -> None:
        self.write(report_id, payload)

    def dump(self) -> list[dict[str, object]]:
        return [
            {
                "report_id": write.report_id,
                "payload_hex": write.payload_hex,
                "byte_count": write.byte_count,
            }
            for write in self.writes
        ]


class LiveHidTransport:
    """Thin hidapi wrapper for writing prepared reports to real hardware."""

    def __init__(self, vendor_id: int, product_id: int, path: str | None = None) -> None:
        try:
            import hid  # type: ignore
        except ImportError as exc:
            raise RuntimeError("hidapi support is not installed. Use `pip install -e .[hid]`.") from exc

        self._hid = hid
        self._device = hid.device()
        self._open_device(vendor_id=vendor_id, product_id=product_id, path=path)

    def _open_device(self, vendor_id: int, product_id: int, path: str | None) -> None:
        if path:
            try:
                self._device.open_path(path.encode() if isinstance(path, str) else path)
            except OSError as exc:
                raise RuntimeError(self._open_error_message(vendor_id, product_id, path)) from exc
            return

        matches = self._hid.enumerate(vendor_id, product_id)
        if not matches:
            raise RuntimeError(
                f"No matching HID device found for vendor 0x{vendor_id:04x} product 0x{product_id:04x}."
            )

        selected = matches[0]
        selected_path = selected.get("path")
        if not selected_path:
            raise RuntimeError("Matching HID device does not expose a writable path.")
        try:
            self._device.open_path(selected_path)
        except OSError as exc:
            raise RuntimeError(self._open_error_message(vendor_id, product_id, str(selected_path))) from exc

    def write(self, report_id: int, payload: bytes) -> None:
        report = bytes([report_id, *payload])
        try:
            written = self._device.write(report)
        except OSError as exc:
            raise RuntimeError("hidapi could not write to the device. Reconnect the device and check USB permissions.") from exc
        if written <= 0:
            raise RuntimeError("hidapi write returned no bytes.")

    def write_feature(self, report_id: int, payload: bytes) -> None:
        report = bytes([report_id, *payload])
        try:
            written = self._device.send_feature_report(report)
        except OSError as exc:
            raise RuntimeError("hidapi could not send a feature report to the device. Reconnect the device and check USB permissions.") from exc
        if written <= 0:
            raise RuntimeError("hidapi send_feature_report returned no bytes.")

    def read_feature_report(self, report_id: int, length: int = 64) -> bytes:
        try:
            return bytes(self._device.get_feature_report(report_id, length))
        except OSError as exc:
            raise RuntimeError(f"hidapi could not read feature report 0x{report_id:02x}.") from exc

    def close(self) -> None:
        try:
            self._device.close()
        except Exception:
            pass

    @staticmethod
    def _open_error_message(vendor_id: int, product_id: int, path: str | None) -> str:
        location = f" Path: {path}." if path else ""
        return (
            f"hidapi found the device 0x{vendor_id:04x}:0x{product_id:04x}, but could not open it."
            f"{location} This is usually a permission, udev, or VirtualBox USB passthrough issue. "
            "Install/reload the linuxcue udev rules, reconnect the device, and make sure the USB device is attached to the VM."
        )
