from __future__ import annotations

import os
from pathlib import Path

from .known_devices import support_for_usb_product
from .models import Device

CORSAIR_VENDOR_ID = 0x1B1C


class DeviceManager:
    """Discovers Corsair devices on Linux and falls back gracefully elsewhere."""

    def discover(self) -> list[Device]:
        devices = self._discover_hid_devices()
        if devices:
            return devices
        return self._discover_sysfs_devices()

    def discover_usb_devices(self) -> list[Device]:
        return self._discover_sysfs_devices()

    def _discover_hid_devices(self) -> list[Device]:
        try:
            import hid  # type: ignore
        except ImportError:
            return []

        discovered: list[Device] = []
        for entry in hid.enumerate(CORSAIR_VENDOR_ID, 0):
            discovered.append(
                Device(
                    vendor_id=entry.get("vendor_id", CORSAIR_VENDOR_ID),
                    product_id=entry.get("product_id", 0),
                    product_name=entry.get("product_string") or "Corsair device",
                    serial_number=entry.get("serial_number"),
                    path=self._decode_path(entry.get("path")),
                    interface_number=entry.get("interface_number"),
                    transport="hidapi",
                    support=support_for_usb_product(
                        int(entry.get("product_id", 0) or 0),
                        entry.get("product_string") or "Corsair device",
                    ),
                )
            )
        return discovered

    def _discover_sysfs_devices(self) -> list[Device]:
        if os.name != "posix":
            return []

        base = Path("/sys/bus/usb/devices")
        if not base.exists():
            return []

        discovered: list[Device] = []
        for device_dir in base.iterdir():
            vendor_file = device_dir / "idVendor"
            product_file = device_dir / "idProduct"
            if not vendor_file.exists() or not product_file.exists():
                continue

            try:
                vendor_id = int(vendor_file.read_text(encoding="utf-8").strip(), 16)
                product_id = int(product_file.read_text(encoding="utf-8").strip(), 16)
            except ValueError:
                continue

            if vendor_id != CORSAIR_VENDOR_ID:
                continue

            product_name = self._safe_read_text(device_dir / "product") or "Corsair USB device"
            serial_number = self._safe_read_text(device_dir / "serial")
            discovered.append(
                Device(
                    vendor_id=vendor_id,
                    product_id=product_id,
                    product_name=product_name,
                    serial_number=serial_number,
                    path=str(device_dir),
                    transport="sysfs",
                    support=support_for_usb_product(product_id, product_name),
                )
            )
        return discovered

    @staticmethod
    def _safe_read_text(path: Path) -> str | None:
        try:
            return path.read_text(encoding="utf-8").strip() or None
        except OSError:
            return None

    @staticmethod
    def _decode_path(value: object) -> str | None:
        if isinstance(value, bytes):
            return value.decode(errors="ignore")
        if isinstance(value, str):
            return value
        return None
