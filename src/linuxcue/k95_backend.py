from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .models import Device, LightingZone, Profile
from .transport import HidTransport, MockHidTransport

K95_OUTPUT_REPORT_ID = 0x00
K95_OUTPUT_PAYLOAD_SIZE = 64
K95_COMMAND_WRITE = 0x07
K95_PROPERTY_SPECIAL_FUNCTION = 0x04
K95_PROPERTY_LIGHTING_CONTROL = 0x05
K95_PROPERTY_SUBMIT_KEYBOARD_COLOR_24 = 0x28
K95_LIGHTING_CONTROL_SOFTWARE = 0x02
K95_LIGHTING_CONTROL_HARDWARE = 0x01
K95_SPECIAL_FUNCTION_SOFTWARE = 0x02
K95_COMMAND_STREAM = 0x7F
K95_COLOR_CHANNEL_RED = 0x01
K95_COLOR_CHANNEL_GREEN = 0x02
K95_COLOR_CHANNEL_BLUE = 0x03
K95_COLOR_BUFFER_SIZE = 168

K95_PLAT_OPENRGB_KEYS: list[int] = [
    0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0C, 0x0D, 0x0E, 0x0F, 0x11, 0x12,
    0x14, 0x15, 0x18, 0x19, 0x1A, 0x1B, 0x1C, 0x1D, 0x1E, 0x1F, 0x20, 0x21, 0x24, 0x25, 0x26,
    0x27, 0x28, 0x2A, 0x2B, 0x2C, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39,
    0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x42, 0x43, 0x44, 0x45, 0x48, 73, 74, 75, 76, 78,
    79, 80, 81, 84, 85, 86, 87, 88, 89, 90, 91, 92, 93, 96, 97,
    98, 99, 100, 101, 102, 103, 104, 105, 108, 109, 110, 111, 112, 113, 115,
    116, 117, 120, 121, 122, 123, 124, 126, 127, 128, 129, 132, 133, 134, 135,
    136, 137, 139, 140, 141, 0x10, 114, 0x0A, 0x16, 0x22, 0x2E, 0x3A, 0x46, 125,
    144, 145, 146, 158, 160, 147, 148, 149, 150, 151, 152, 153, 154, 155, 159, 162, 161, 156, 157,
]

K95_LAYOUT: dict[str, list[str]] = {
    "function": ["esc", "f1", "f2", "f3", "f4", "f5", "f6", "f7", "f8", "f9", "f10", "f11", "f12"],
    "numbers": ["grave", "1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "minus", "equals", "backspace"],
    "tab_row": ["tab", "q", "w", "e", "r", "t", "y", "u", "i", "o", "p", "lbracket", "rbracket", "backslash"],
    "caps_row": ["caps", "a", "s", "d", "f", "g", "h", "j", "k", "l", "semicolon", "quote", "enter"],
    "shift_row": ["lshift", "z", "x", "c", "v", "b", "n", "m", "comma", "period", "slash", "rshift"],
    "bottom_row": ["lctrl", "lwin", "lalt", "space", "ralt", "fn", "menu", "rctrl"],
    "arrows": ["insert", "home", "pageup", "delete", "end", "pagedown", "up", "left", "down", "right"],
    "numpad": ["numlock", "kp_slash", "kp_star", "kp_minus", "kp7", "kp8", "kp9", "kp_plus", "kp4", "kp5", "kp6", "kp1", "kp2", "kp3", "kp_enter", "kp0", "kp_dot"],
    "macro": ["g1", "g2", "g3", "g4", "g5", "g6"],
    "media": ["brightness", "mute", "stop", "prev", "play", "next", "vol_wheel"],
}

K95_OPENRGB_ZONE_ORDER: list[str] = [
    "esc", "grave", "tab", "caps", "lshift", "lctrl", "f12", "equals", "lock", "kp7",
    "f1", "1", "q", "a", "lwin", "printscreen", "mute", "kp8",
    "f2", "2", "w", "s", "z", "lalt", "scrolllock", "backspace", "stop", "kp9",
    "f3", "3", "e", "d", "x", "pause", "delete", "prev",
    "f4", "4", "r", "f", "c", "space", "insert", "end", "play", "kp4",
    "f5", "5", "t", "g", "v", "home", "pagedown", "next", "kp5",
    "f6", "6", "y", "h", "b", "pageup", "rshift", "numlock", "kp6",
    "f7", "7", "u", "j", "n", "ralt", "rbracket", "rctrl", "kp_slash", "kp1",
    "f8", "8", "i", "k", "m", "rwin", "backslash", "up", "kp_star", "kp2",
    "f9", "9", "o", "l", "comma", "menu", "left", "kp_minus", "kp3",
    "f10", "0", "p", "semicolon", "period", "enter", "down", "kp_plus", "kp0",
    "f11", "minus", "lbracket", "quote", "slash", "brightness", "right", "kp_enter", "kp_dot",
    "iso_slash", "iso_backslash", "g1", "g2", "g3", "g4", "g5", "g6", "preset",
]
K95_EXTRA_ZONE_ORDER: list[str] = [
    *[f"led_topzone{index}" for index in range(1, 20)],
]
K95_OPENRGB_ZONE_ORDER.extend(K95_EXTRA_ZONE_ORDER)
K95_PLAT_ISO_SKIPPED_IDENTIFIERS = {0x3F, 0x41, 0x42, 0x50, 0x53, 0x55, 0x6F, 0x78, 0x7E, 0x7F, 0x80, 0x81}


@dataclass(frozen=True, slots=True)
class K95Packet:
    packet_type: str
    zone_name: str
    rgb: tuple[int, int, int]
    keys: list[str]
    report_id: int = K95_OUTPUT_REPORT_ID
    command_id: int = K95_COMMAND_WRITE
    property_id: int = K95_PROPERTY_SUBMIT_KEYBOARD_COLOR_24
    raw_payload: bytes | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "packet_type": self.packet_type,
            "zone_name": self.zone_name,
            "report_id": self.report_id,
            "command_id": self.command_id,
            "property_id": self.property_id,
            "descriptor_shape": "unnumbered 64-byte output report",
            "rgb": list(self.rgb),
            "key_count": len(self.keys),
            "keys": self.keys,
            "raw_payload": self.raw_payload.hex(" ") if self.raw_payload else "",
            "frame_hex": self.to_frame().hex(" "),
            "byte_count": len(self.to_frame()),
        }

    def to_frame(self) -> bytes:
        if self.raw_payload is not None:
            return self.raw_payload[:K95_OUTPUT_PAYLOAD_SIZE].ljust(K95_OUTPUT_PAYLOAD_SIZE, b"\x00")
        key_slots = [_key_code_for_name(key) for key in self.keys[:56]]
        r, g, b = self.rgb
        frame = bytes(
            [
                self.command_id,
                self.property_id,
                len(self.keys) & 0xFF,
                r,
                g,
                b,
                _mode_code_for_type(self.packet_type),
                0x00,
                0x00,
                *key_slots,
            ]
        )
        return frame[:K95_OUTPUT_PAYLOAD_SIZE].ljust(K95_OUTPUT_PAYLOAD_SIZE, b"\x00")


def build_k95_default_profile(name: str) -> Profile:
    zone_colors = {
        "function": "#ff6b00",
        "numbers": "#ffd166",
        "tab_row": "#06d6a0",
        "caps_row": "#118ab2",
        "shift_row": "#8338ec",
        "bottom_row": "#ef476f",
        "arrows": "#ffffff",
        "numpad": "#73d2de",
        "macro": "#ff006e",
        "media": "#fb5607",
    }
    lighting = [
        LightingZone(name=zone_name, color=color, mode="static", keys=list(keys))
        for zone_name, keys in K95_LAYOUT.items()
        for color in [zone_colors[zone_name]]
    ]
    return Profile(
        name=name,
        target_device="k95",
        target_family="keyboard",
        description="K95 zoned lighting profile",
        lighting=lighting,
    )


def build_k95_packets(profile: Profile, device: Device) -> list[K95Packet]:
    packets: list[K95Packet] = [
        _build_special_function_packet(),
        _build_software_lighting_packet(),
        *_build_iso_key_mapping_packets(),
    ]
    color_by_key = _profile_key_colors(profile)
    if color_by_key:
        packets.extend(_build_full_color_packets(color_by_key))
        return packets

    matched_zones = [zone for zone in profile.lighting if zone.name in K95_LAYOUT or zone.keys]
    per_key_static: dict[str, list[str]] = {}
    other_zones: list[LightingZone] = []
    for zone in matched_zones:
        if zone.keys and zone.mode == "static":
            per_key_static.setdefault(zone.color.lower(), []).extend(zone.keys)
            continue
        other_zones.append(zone)

    for color, keys in per_key_static.items():
        unique_keys = list(dict.fromkeys(keys))
        for chunk_index, key_chunk in enumerate(_chunks(unique_keys, 56), start=1):
            packets.append(
                K95Packet(
                    packet_type="static",
                    zone_name=f"keys_{color.lstrip('#')}_{chunk_index}",
                    rgb=_parse_hex_color(color),
                    keys=key_chunk,
                    report_id=K95_OUTPUT_REPORT_ID,
                    command_id=K95_COMMAND_WRITE,
                )
            )

    for zone in other_zones:
        keys = zone.keys or K95_LAYOUT.get(zone.name, [])
        if not keys:
            continue
        packets.append(
            K95Packet(
                packet_type=_packet_type_for_mode(zone.mode),
                zone_name=zone.name,
                rgb=_parse_hex_color(zone.color),
                keys=list(keys),
                report_id=K95_OUTPUT_REPORT_ID,
                command_id=K95_COMMAND_WRITE,
            )
        )
    if not packets:
        packets.append(
            K95Packet(
                packet_type="static",
                zone_name="default",
                rgb=(255, 255, 255),
                keys=K95_LAYOUT["function"],
            )
        )
    return packets


def _build_software_lighting_packet() -> K95Packet:
    return build_k95_lighting_control_packet(K95_LIGHTING_CONTROL_SOFTWARE)


def build_k95_special_function_packets() -> list[K95Packet]:
    return [_build_special_function_packet(), *_build_iso_key_mapping_packets()]


def build_k95_lighting_control_packet(mode: int) -> K95Packet:
    return K95Packet(
        packet_type="control",
        zone_name="software-lighting" if mode == K95_LIGHTING_CONTROL_SOFTWARE else "hardware-lighting",
        rgb=(0, 0, 0),
        keys=[],
        report_id=K95_OUTPUT_REPORT_ID,
        command_id=K95_COMMAND_WRITE,
        property_id=K95_PROPERTY_LIGHTING_CONTROL,
        raw_payload=bytes([K95_COMMAND_WRITE, K95_PROPERTY_LIGHTING_CONTROL, mode, 0x00, 0x03]),
    )


def _build_special_function_packet() -> K95Packet:
    return _raw_packet(
        packet_type="control",
        zone_name="special-function-software",
        payload=bytes([K95_COMMAND_WRITE, K95_PROPERTY_SPECIAL_FUNCTION, K95_SPECIAL_FUNCTION_SOFTWARE]),
    )


def _build_iso_key_mapping_packets() -> list[K95Packet]:
    packets = [
        _raw_packet(
            packet_type="control",
            zone_name="iso-keymap-start",
            payload=bytes([K95_COMMAND_WRITE, K95_PROPERTY_LIGHTING_CONTROL, 0x08, 0x00, 0x01]),
        )
    ]
    identifier = 0
    for packet_index in range(4):
        values: list[int] = []
        for _ in range(30):
            while identifier in K95_PLAT_ISO_SKIPPED_IDENTIFIERS:
                identifier += 1
            values.extend([identifier & 0xFF, 0xC0])
            identifier += 1
        packets.append(
            _raw_packet(
                packet_type="control",
                zone_name=f"iso-keymap-{packet_index + 1}",
                payload=bytes([K95_COMMAND_WRITE, 0x40, 0x1E, 0x00, 0x00, *values]),
            )
        )
    return packets


def _build_full_color_packets(color_by_key: dict[str, tuple[int, int, int]]) -> list[K95Packet]:
    red = [0] * K95_COLOR_BUFFER_SIZE
    green = [0] * K95_COLOR_BUFFER_SIZE
    blue = [0] * K95_COLOR_BUFFER_SIZE
    for zone_index, key in enumerate(K95_OPENRGB_ZONE_ORDER):
        if zone_index >= len(K95_PLAT_OPENRGB_KEYS):
            break
        hardware_index = K95_PLAT_OPENRGB_KEYS[zone_index]
        if hardware_index >= K95_COLOR_BUFFER_SIZE:
            continue
        r, g, b = color_by_key.get(key, (0, 0, 0))
        red[hardware_index] = r
        green[hardware_index] = g
        blue[hardware_index] = b

    packets: list[K95Packet] = []
    packets.extend(_channel_packets("red", K95_COLOR_CHANNEL_RED, red, finish=0x01))
    packets.extend(_channel_packets("green", K95_COLOR_CHANNEL_GREEN, green, finish=0x01))
    packets.extend(_channel_packets("blue", K95_COLOR_CHANNEL_BLUE, blue, finish=0x02))
    return packets


def _channel_packets(name: str, channel: int, values: list[int], finish: int) -> list[K95Packet]:
    chunks = [values[:60], values[60:120], values[120:168]]
    packets = [
        _raw_packet(
            packet_type="stream",
            zone_name=f"{name}-stream-{index}",
            payload=bytes([K95_COMMAND_STREAM, index, len(chunk), 0x00, *chunk]),
        )
        for index, chunk in enumerate(chunks, start=1)
    ]
    packets.append(
        _raw_packet(
            packet_type="submit",
            zone_name=f"{name}-submit",
            payload=bytes([K95_COMMAND_WRITE, K95_PROPERTY_SUBMIT_KEYBOARD_COLOR_24, channel, len(chunks), finish]),
        )
    )
    return packets


def _raw_packet(packet_type: str, zone_name: str, payload: bytes) -> K95Packet:
    return K95Packet(
        packet_type=packet_type,
        zone_name=zone_name,
        rgb=(0, 0, 0),
        keys=[],
        report_id=K95_OUTPUT_REPORT_ID,
        command_id=payload[0] if payload else K95_COMMAND_WRITE,
        property_id=payload[1] if len(payload) > 1 else 0x00,
        raw_payload=payload,
    )


def _profile_key_colors(profile: Profile) -> dict[str, tuple[int, int, int]]:
    color_by_key: dict[str, tuple[int, int, int]] = {}
    for zone in profile.lighting:
        keys = zone.keys or K95_LAYOUT.get(zone.name, [])
        if not keys:
            continue
        rgb = _parse_hex_color(zone.color)
        for key in keys:
            if key != "fn":
                color_by_key[key] = rgb
    return color_by_key


def plan_k95_apply(profile: Profile, device: Device) -> dict[str, object]:
    packets = build_k95_packets(profile, device)
    transport = MockHidTransport()
    write_k95_packets(packets, transport)
    return {
        "device": device.support.model_hint,
        "family": "keyboard",
        "backend": "k95",
        "transport": device.transport,
        "steps": [
            f"Map profile '{profile.name}' to {len(packets)} keyboard zones",
            f"Prepare {len(packets)} descriptor-shaped HID lighting packets for K95 interface 1",
            "Use the K95 RGB Platinum control descriptor: unnumbered 64-byte output reports",
            "Reserve macro-key layer and hardware playback bindings",
        ],
        "packets": [packet.to_dict() for packet in packets],
        "transport_writes": transport.dump(),
    }


def preview_k95_frames(profile: Profile, device: Device) -> dict[str, object]:
    packets = build_k95_packets(profile, device)
    transport = MockHidTransport()
    write_k95_packets(packets, transport)
    return {
        "device": device.support.model_hint,
        "packet_count": len(packets),
        "frames": transport.dump(),
    }


def send_k95_profile(profile: Profile, device: Device, transport: HidTransport) -> dict[str, object]:
    packets = build_k95_packets(profile, device)
    write_k95_packets(packets, transport)
    return {
        "device": device.support.model_hint,
        "packet_count": len(packets),
        "packets": [packet.to_dict() for packet in packets],
    }


def write_k95_packets(packets: list[K95Packet], transport: HidTransport) -> None:
    for packet in packets:
        transport.write(packet.report_id, packet.to_frame())


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        return (255, 255, 255)
    try:
        return cast(tuple[int, int, int], tuple(int(value[index:index + 2], 16) for index in range(0, 6, 2)))
    except ValueError:
        return (255, 255, 255)


def _chunks(values: list[str], size: int) -> list[list[str]]:
    return [values[index:index + size] for index in range(0, len(values), size)]


def _packet_type_for_mode(mode: str) -> str:
    return {
        "static": "static",
        "wave": "animated-wave",
        "rain": "animated-rain",
    }.get(mode, "static")


def _command_for_mode(mode: str) -> int:
    return {
        "static": K95_COMMAND_WRITE,
        "wave": K95_COMMAND_WRITE,
        "rain": K95_COMMAND_WRITE,
    }.get(mode, K95_COMMAND_WRITE)


def _mode_code_for_type(packet_type: str) -> int:
    return {
        "static": 0x10,
        "animated-wave": 0x20,
        "animated-rain": 0x30,
    }.get(packet_type, 0x10)


def _key_code_for_name(name: str) -> int:
    mapping = {
        "esc": 0x29,
        "f1": 0x3A,
        "f2": 0x3B,
        "f3": 0x3C,
        "f4": 0x3D,
        "f5": 0x3E,
        "f6": 0x3F,
        "f7": 0x40,
        "f8": 0x41,
        "f9": 0x42,
        "f10": 0x43,
        "f11": 0x44,
        "f12": 0x45,
        "grave": 0x35,
        "1": 0x1E,
        "2": 0x1F,
        "3": 0x20,
        "4": 0x21,
        "5": 0x22,
        "6": 0x23,
        "7": 0x24,
        "8": 0x25,
        "9": 0x26,
        "0": 0x27,
        "minus": 0x2D,
        "equals": 0x2E,
        "backspace": 0x2A,
        "tab": 0x2B,
        "q": 0x14,
        "w": 0x1A,
        "e": 0x08,
        "r": 0x15,
        "t": 0x17,
        "y": 0x1C,
        "u": 0x18,
        "i": 0x0C,
        "o": 0x12,
        "p": 0x13,
        "lbracket": 0x2F,
        "rbracket": 0x30,
        "backslash": 0x31,
        "iso_backslash": 0x64,
        "caps": 0x39,
        "a": 0x04,
        "s": 0x16,
        "d": 0x07,
        "f": 0x09,
        "g": 0x0A,
        "h": 0x0B,
        "j": 0x0D,
        "k": 0x0E,
        "l": 0x0F,
        "semicolon": 0x33,
        "quote": 0x34,
        "enter": 0x28,
        "lshift": 0xE1,
        "z": 0x1D,
        "x": 0x1B,
        "c": 0x06,
        "v": 0x19,
        "b": 0x05,
        "n": 0x11,
        "m": 0x10,
        "comma": 0x36,
        "period": 0x37,
        "slash": 0x38,
        "rshift": 0xE5,
        "lctrl": 0xE0,
        "lwin": 0xE3,
        "lalt": 0xE2,
        "space": 0x2C,
        "ralt": 0xE6,
        "fn": 0x00,
        "menu": 0x65,
        "rctrl": 0xE4,
        "insert": 0x49,
        "home": 0x4A,
        "pageup": 0x4B,
        "delete": 0x4C,
        "end": 0x4D,
        "pagedown": 0x4E,
        "up": 0x52,
        "left": 0x50,
        "down": 0x51,
        "right": 0x4F,
        "numlock": 0x53,
        "kp_slash": 0x54,
        "kp_star": 0x55,
        "kp_minus": 0x56,
        "kp7": 0x5F,
        "kp8": 0x60,
        "kp9": 0x61,
        "kp_plus": 0x57,
        "kp4": 0x5C,
        "kp5": 0x5D,
        "kp6": 0x5E,
        "kp1": 0x59,
        "kp2": 0x5A,
        "kp3": 0x5B,
        "kp_enter": 0x58,
        "kp0": 0x62,
        "kp_dot": 0x63,
        "g1": 0x90,
        "g2": 0x91,
        "g3": 0x92,
        "g4": 0x93,
        "g5": 0x94,
        "g6": 0x95,
        "brightness": 0x80,
        "mute": 0x7F,
        "stop": 0xB7,
        "prev": 0xB6,
        "play": 0xCD,
        "next": 0xB5,
        "vol_wheel": 0x81,
    }
    return mapping.get(name, 0x00)
