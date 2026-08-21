from __future__ import annotations

from .models import Device, Profile


def plan_apply(profile: Profile, device: Device) -> list[str]:
    family = device.support.family
    if family == "keyboard":
        return [
            f"Map profile '{profile.name}' to keyboard zones",
            "Prepare per-key or grouped RGB effect payloads",
            "Reserve macro-key layer for future HID write support",
        ]
    if family == "mouse":
        return [
            f"Map profile '{profile.name}' to DPI stages",
            "Prepare logo RGB state packet",
            "Reserve button remapping for future HID write support",
        ]
    if family == "headset":
        return [
            f"Map profile '{profile.name}' to headset RGB accent",
            "Keep USB audio path untouched",
            "Reserve battery polling and sidetone control for future HID write support",
        ]
    return [
        f"Map profile '{profile.name}' to generic Corsair device",
        "Wait for dedicated backend implementation",
    ]
