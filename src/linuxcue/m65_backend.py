from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .models import Device, DpiStage, LightingZone, Profile
from .transport import HidTransport, MockHidTransport

M65_COMMAND_WRITE = 0x07
M65_PROPERTY_SUBMIT_MOUSE_COLOR = 0x22
M65_PAYLOAD_SIZE = 64
M65_PACKET_KINDS = {"all", "dpi", "rgb", "buttons"}
M65_BUTTON_HID_MAPPING_VERIFIED = False

M65_BUTTONS: list[str] = [
    "left",
    "right",
    "middle",
    "dpi_up",
    "dpi_down",
    "sniper",
    "forward",
    "back",
]

# iCUE sends M65 RGB as zone records 1..3. Hardware observation:
# 1 = front light, 2 = logo, 3 = DPI indicator.
M65_RGB_ZONES: list[str] = ["front", "logo", "dpi_indicator"]


@dataclass(frozen=True, slots=True)
class M65Packet:
    packet_type: str
    label: str
    payload: bytes
    report_id: int
    command_id: int

    def to_dict(self) -> dict[str, object]:
        return {
            "packet_type": self.packet_type,
            "label": self.label,
            "report_id": self.report_id,
            "command_id": self.command_id,
            "descriptor_shape": "64-byte Corsair mouse HID output payload",
            "payload_hex": self.payload.hex(" "),
            "byte_count": len(self.payload),
        }


def build_m65_default_profile(name: str) -> Profile:
    lighting = [
        LightingZone(name="logo", color="#ff3b30", mode="static"),
        LightingZone(name="dpi_indicator", color="#00c2ff", mode="static"),
        LightingZone(name="front", color="#d7ff37", mode="static"),
    ]
    dpi = [
        DpiStage(name="stage1", x=800, y=800, color="#ff001f", active=True),
        DpiStage(name="stage2", x=1500, y=1500, color="#ffffff", active=False),
        DpiStage(name="stage3", x=3000, y=3000, color="#04ff00", active=False),
        DpiStage(name="stage4", x=6000, y=6000, color="#ffe600", active=False),
        DpiStage(name="stage5", x=9000, y=9000, color="#12c8ff", active=False),
        DpiStage(name="sniper", x=400, y=400, color="#1ecfdf", active=False),
    ]
    return Profile(
        name=name,
        target_device="m65",
        target_family="mouse",
        description="M65 DPI and lighting profile",
        lighting=lighting,
        dpi=dpi,
    )


def build_m65_packets(profile: Profile, device: Device, packet_kind: str = "all") -> list[M65Packet]:
    if packet_kind not in M65_PACKET_KINDS:
        raise ValueError(f"Unsupported M65 packet kind: {packet_kind}")
    packets: list[M65Packet] = []
    if packet_kind in {"all", "dpi"}:
        packets.extend(_build_dpi_packets(profile))
    if packet_kind in {"all", "rgb"}:
        packets.extend(_build_lighting_packets(profile))
    if packet_kind in {"all", "buttons"} and M65_BUTTON_HID_MAPPING_VERIFIED:
        packets.append(_build_button_map_packet(profile))
    return packets


def plan_m65_apply(profile: Profile, device: Device) -> dict[str, object]:
    packets = build_m65_packets(profile, device)
    transport = MockHidTransport()
    write_m65_packets(packets, transport)
    lighting_count = len([zone for zone in profile.lighting if zone.name in set(M65_RGB_ZONES)])
    dpi_count = len(profile.dpi[:5])
    return {
        "device": device.support.model_hint,
        "family": "mouse",
        "backend": "m65",
        "transport": device.transport,
        "steps": [
            f"Map profile '{profile.name}' to {dpi_count} DPI stages",
            f"Prepare {lighting_count} RGB zones for the M65 shell",
            f"Prepare {len(packets)} verified HID reports for DPI slot and lighting",
            "Button mapping is represented in the profile, but no M65 button HID write was present in the iCUE capture yet.",
        ],
        "packets": [packet.to_dict() for packet in packets],
        "transport_writes": transport.dump(),
    }


def preview_m65_frames(profile: Profile, device: Device, packet_kind: str = "all") -> dict[str, object]:
    packets = build_m65_packets(profile, device, packet_kind=packet_kind)
    transport = MockHidTransport()
    write_m65_packets(packets, transport)
    return {
        "device": device.support.model_hint,
        "packet_kind": packet_kind,
        "packet_count": len(packets),
        "frames": transport.dump(),
    }


def send_m65_profile(
    profile: Profile,
    device: Device,
    transport: HidTransport,
    *,
    use_feature_report: bool = False,
    packet_kind: str = "all",
) -> dict[str, object]:
    packets = build_m65_packets(profile, device, packet_kind=packet_kind)
    write_m65_packets(packets, transport, use_feature_report=use_feature_report)
    return {
        "device": device.support.model_hint,
        "packet_kind": packet_kind,
        "packet_count": len(packets),
        "write_mode": "feature_report" if use_feature_report else "output_report",
        "button_hid_mapping_verified": M65_BUTTON_HID_MAPPING_VERIFIED,
        "packets": [packet.to_dict() for packet in packets],
    }


def write_m65_packets(packets: list[M65Packet], transport: HidTransport, *, use_feature_report: bool = False) -> None:
    for packet in packets:
        if use_feature_report:
            transport.write_feature(packet.report_id, packet.payload)
        else:
            transport.write(packet.report_id, packet.payload)


def _build_dpi_packets(profile: Profile) -> list[M65Packet]:
    active_stage = next((stage for stage in profile.dpi if stage.active), None)
    active_index = _dpi_hardware_slot(active_stage)
    return [
        M65Packet(
            packet_type="dpi",
            label=f"active-stage-live-{active_index}",
            payload=_dpi_active_stage_payload(active_index, persist=False),
            report_id=0x00,
            command_id=0x13,
        ),
        M65Packet(
            packet_type="dpi",
            label=f"active-stage-persist-{active_index}",
            payload=_dpi_active_stage_payload(active_index, persist=True),
            report_id=0x00,
            command_id=0x13,
        )
    ]


def _build_lighting_packets(profile: Profile) -> list[M65Packet]:
    zones_by_name = {zone.name: zone for zone in profile.lighting if zone.name in set(M65_RGB_ZONES)}
    if not zones_by_name:
        return []
    return [
        M65Packet(
            packet_type="lighting",
            label="rgb-zones",
            payload=_lighting_payload(zones_by_name),
            report_id=0x00,
            command_id=M65_COMMAND_WRITE,
        )
    ]


def _build_button_map_packet(profile: Profile) -> M65Packet:
    configured = profile.options.get("m65_buttons", {}) if isinstance(profile.options, dict) else {}
    slots = [_button_code(str(configured.get(name, name))) for name in M65_BUTTONS]
    payload = bytes([0x30, len(slots), *slots, *([0x00] * (16 - len(slots)))]).ljust(M65_PAYLOAD_SIZE, b"\x00")
    return M65Packet(
        packet_type="buttons",
        label="default-map",
        payload=payload,
        report_id=0x07,
        command_id=0x30,
    )


def _dpi_payload(index: int, stage: DpiStage) -> bytes:
    r, g, b = _parse_hex_color(stage.color)
    flags = 0x01 if stage.active else 0x00
    return bytes(
        [
            0x10,
            index & 0xFF,
            flags,
            stage.x & 0xFF,
            (stage.x >> 8) & 0xFF,
            stage.y & 0xFF,
            (stage.y >> 8) & 0xFF,
            r,
            g,
            b,
            0x00,
            0x00,
        ]
    ).ljust(M65_PAYLOAD_SIZE, b"\x00")


def _dpi_hardware_slot(stage: DpiStage | None) -> int:
    if stage is None:
        return 0x02
    name = stage.name.casefold()
    if "sniper" in name:
        return 0x00
    if name.startswith("stage"):
        suffix = name.removeprefix("stage")
        try:
            return max(0x01, min(0x06, int(suffix) + 1))
        except ValueError:
            return 0x02
    return 0x02


def _dpi_active_stage_payload(active_index: int, *, persist: bool) -> bytes:
    return bytes(
        [
            M65_COMMAND_WRITE,
            0x13,
            0x02,
            0x01 if persist else 0x00,
            active_index & 0xFF,
        ]
    ).ljust(M65_PAYLOAD_SIZE, b"\x00")


def _lighting_payload(zones_by_name: dict[str, LightingZone]) -> bytes:
    payload = bytearray([M65_COMMAND_WRITE, M65_PROPERTY_SUBMIT_MOUSE_COLOR, len(M65_RGB_ZONES), 0x01])
    for index, zone_name in enumerate(M65_RGB_ZONES, start=1):
        zone = zones_by_name.get(zone_name)
        r, g, b = _parse_hex_color(zone.color if zone is not None else "#000000")
        payload.extend([index & 0xFF, r, g, b])
    return bytes(payload).ljust(M65_PAYLOAD_SIZE, b"\x00")


def _button_code(name: str) -> int:
    mapping = {
        "disabled": 0x00,
        "left": 0x01,
        "right": 0x02,
        "middle": 0x03,
        "dpi_up": 0x10,
        "dpi_down": 0x11,
        "sniper": 0x12,
        "forward": 0x13,
        "back": 0x14,
    }
    return mapping.get(name, 0x00)


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        return (255, 255, 255)
    try:
        return cast(tuple[int, int, int], tuple(int(value[index:index + 2], 16) for index in range(0, 6, 2)))
    except ValueError:
        return (255, 255, 255)
