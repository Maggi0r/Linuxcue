from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .models import AudioPreset, Device, HeadsetSetting, LightingZone, Profile
from .transport import HidTransport, MockHidTransport

VIRTUOSO_OUTPUT_REPORT_ID = 0x02
VIRTUOSO_OUTPUT_PAYLOAD_SIZE = 63
VIRTUOSO_PACKET_KINDS = {"all", "eq", "rgb", "control", "battery"}


@dataclass(frozen=True, slots=True)
class VirtuosoPacket:
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
            "descriptor_shape": "report-id 0x02 with 63-byte output payload",
            "payload_hex": self.payload.hex(" "),
            "byte_count": len(self.payload),
        }


def build_virtuoso_default_profile(name: str) -> Profile:
    lighting = [LightingZone(name="accent_ring", color="#5dd39e", mode="static")]
    audio = [
        AudioPreset(name="fps", bass=-2, mids=3, treble=5, active=True, bands=[-4, -3, -2, 0, 2, 3, 4, 5, 5, 4]),
        AudioPreset(name="music", bass=4, mids=1, treble=2, active=False, bands=[4, 4, 3, 2, 1, 1, 2, 2, 3, 3]),
        AudioPreset(name="voice", bass=-1, mids=4, treble=1, active=False, bands=[-3, -2, -1, 1, 3, 4, 4, 3, 2, 1]),
    ]
    headset = HeadsetSetting(sidetone=35, mic_level=72, sleep_timer_minutes=20, voice_prompt_enabled=True)
    return Profile(
        name=name,
        target_device="virtuoso-se",
        target_family="headset",
        description="Virtuoso SE EQ, lighting, and control profile",
        lighting=lighting,
        audio=audio,
        headset=headset,
    )


def build_virtuoso_packets(profile: Profile, device: Device) -> list[VirtuosoPacket]:
    if "receiver" in device.support.model_hint.casefold():
        return build_virtuoso_receiver_packets(profile, device)

    packets: list[VirtuosoPacket] = []
    packets.extend(_build_eq_packets(profile.audio))
    packets.append(_build_lighting_packet(profile.lighting))
    packets.append(_build_headset_packet(profile.headset))
    packets.append(_build_battery_poll_packet())
    return packets


def build_virtuoso_receiver_packets(profile: Profile, device: Device) -> list[VirtuosoPacket]:
    return [
        _build_receiver_lighting_packet(profile.lighting),
        _build_receiver_sidetone_packet(profile.headset),
    ]


def plan_virtuoso_apply(profile: Profile, device: Device) -> dict[str, object]:
    packets = build_virtuoso_packets(profile, device)
    transport = MockHidTransport()
    write_virtuoso_packets(packets, transport)
    active_eq = next((preset.name for preset in profile.audio if preset.active), "none")
    return {
        "device": device.support.model_hint,
        "family": device.support.family,
        "backend": "virtuoso-rgb",
        "transport": device.transport,
        "steps": [
            *(
                [
                    f"Map profile '{profile.name}' to {len(profile.audio[:8])} EQ presets",
                    f"Prepare headset control state with sidetone {profile.headset.sidetone} and mic level {profile.headset.mic_level}",
                    f"Prepare {len(packets)} descriptor-shaped HID reports for EQ, RGB, control, and battery polling",
                    "Use Virtuoso HID descriptor output shape: report ID 0x02 with 63-byte payloads",
                    f"Keep USB audio streaming on the standard audio path while active EQ preset is '{active_eq}'",
                ]
                if device.support.family == "headset"
                else [
                    f"Prepare wireless link profile '{profile.name}' for the Virtuoso receiver",
                    f"Prepare {len(packets)} capture-derived HID reports for receiver RGB/control candidates",
                    "Use receiver HID descriptor output shape: report ID 0x02 with 63-byte payloads",
                    "Keep EQ on the Linux EasyEffects/PipeWire path; receiver EQ HID writes were not visible in the capture",
                ]
            ),
        ],
        "packets": [packet.to_dict() for packet in packets],
        "transport_writes": transport.dump(),
    }


def preview_virtuoso_frames(profile: Profile, device: Device) -> dict[str, object]:
    packets = build_virtuoso_packets(profile, device)
    transport = MockHidTransport()
    write_virtuoso_packets(packets, transport)
    return {
        "device": device.support.model_hint,
        "packet_count": len(packets),
        "frames": transport.dump(),
    }


def send_virtuoso_profile(
    profile: Profile,
    device: Device,
    transport: HidTransport,
    *,
    use_feature_report: bool = False,
    packet_kind: str = "all",
) -> dict[str, object]:
    packets = build_virtuoso_packets(profile, device)
    packets = _filter_packets(packets, packet_kind)
    write_virtuoso_packets(packets, transport, use_feature_report=use_feature_report)
    return {
        "device": device.support.model_hint,
        "packet_count": len(packets),
        "write_mode": "feature_report" if use_feature_report else "output_report",
        "packet_kind": packet_kind,
        "packets": [packet.to_dict() for packet in packets],
    }


def _filter_packets(packets: list[VirtuosoPacket], packet_kind: str) -> list[VirtuosoPacket]:
    if packet_kind == "all":
        return packets
    if packet_kind == "rgb":
        return [packet for packet in packets if "lighting" in packet.packet_type]
    if packet_kind == "control":
        return [packet for packet in packets if "control" in packet.packet_type]
    return [packet for packet in packets if packet.packet_type == packet_kind]


def write_virtuoso_packets(packets: list[VirtuosoPacket], transport: HidTransport, *, use_feature_report: bool = False) -> None:
    for packet in packets:
        if use_feature_report:
            transport.write_feature(packet.report_id, packet.payload)
        else:
            transport.write(packet.report_id, packet.payload)


def build_virtuoso_rgb_sweep_packets(values: list[int] | None = None) -> list[VirtuosoPacket]:
    steps = values or [0x00, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70, 0x80]
    return [
        VirtuosoPacket(
            packet_type="lighting",
            label=f"capture-rgb-sweep-0x{value:02x}",
            payload=_output_payload([0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0x98, 0x00, 0xFF, 0xF8, value, 0x00, 0xFB]),
            report_id=VIRTUOSO_OUTPUT_REPORT_ID,
            command_id=0x09,
        )
        for value in steps
    ]


def _build_eq_packets(audio: list[AudioPreset]) -> list[VirtuosoPacket]:
    packets: list[VirtuosoPacket] = []
    for index, preset in enumerate(audio[:8], start=1):
        packets.append(
            VirtuosoPacket(
                packet_type="eq",
                label=preset.name,
                payload=_eq_payload(index, preset),
                report_id=VIRTUOSO_OUTPUT_REPORT_ID,
                command_id=0x40,
            )
        )
    if not packets:
        packets.append(
            VirtuosoPacket(
                packet_type="eq",
                label="flat",
                payload=_eq_payload(1, AudioPreset(name="flat", active=True)),
                report_id=VIRTUOSO_OUTPUT_REPORT_ID,
                command_id=0x40,
            )
        )
    return packets


def _build_lighting_packet(lighting: list[LightingZone]) -> VirtuosoPacket:
    return _build_capture_lighting_packet(lighting, packet_type="lighting", label="accent-ring-candidate")


def _build_capture_lighting_packet(lighting: list[LightingZone], *, packet_type: str, label: str) -> VirtuosoPacket:
    zone = next((entry for entry in lighting if entry.name == "accent_ring"), LightingZone(name="accent_ring"))
    r, g, b = _parse_hex_color(zone.color)
    # Captured Virtuoso RGB writes use the same 02 09 06... vendor report shape on the
    # headset/receiver HID interface. Byte 12 moved through 00..80 while iCUE changed RGB.
    intensity = max(r, g, b) * 0x80 // 0xFF
    return VirtuosoPacket(
        packet_type=packet_type,
        label=label,
        payload=_output_payload([0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0x98, 0x00, 0xFF, 0xF8, intensity, 0x00, 0xFB]),
        report_id=VIRTUOSO_OUTPUT_REPORT_ID,
        command_id=0x09,
    )


def _build_headset_packet(setting: HeadsetSetting) -> VirtuosoPacket:
    return VirtuosoPacket(
        packet_type="control",
        label="headset-state",
        payload=_output_payload(
            [
                0x60,
                max(0, min(setting.sidetone, 100)),
                max(0, min(setting.mic_level, 100)),
                max(0, min(setting.sleep_timer_minutes, 120)),
                0x01 if setting.voice_prompt_enabled else 0x00,
                0x00,
                0x00,
                0x00,
            ]
        ),
        report_id=VIRTUOSO_OUTPUT_REPORT_ID,
        command_id=0x60,
    )


def _build_receiver_lighting_packet(lighting: list[LightingZone]) -> VirtuosoPacket:
    return _build_capture_lighting_packet(lighting, packet_type="receiver-lighting", label="receiver-accent-candidate")


def _build_receiver_sidetone_packet(setting: HeadsetSetting) -> VirtuosoPacket:
    sidetone = max(0, min(setting.sidetone, 100)) * 0x80 // 100
    return VirtuosoPacket(
        packet_type="receiver-control",
        label="receiver-sidetone-candidate",
        payload=_output_payload([0x09, 0x06, 0x00, 0x09, 0x00, 0x00, 0x00, 0xFB, 0x00, 0xFF, 0x29, sidetone, 0x00, 0x59]),
        report_id=VIRTUOSO_OUTPUT_REPORT_ID,
        command_id=0x09,
    )


def _build_battery_poll_packet() -> VirtuosoPacket:
    return VirtuosoPacket(
        packet_type="battery",
        label="battery-poll",
        payload=_output_payload([0x70, 0x01, 0x00, 0x00]),
        report_id=VIRTUOSO_OUTPUT_REPORT_ID,
        command_id=0x70,
    )


def _eq_payload(index: int, preset: AudioPreset) -> bytes:
    flags = 0x01 if preset.active else 0x00
    bands = _eq_bands(preset)
    return _output_payload(
        [
            0x40,
            index & 0xFF,
            flags,
            len(bands) & 0xFF,
            *(_signed_byte(value) for value in bands),
        ]
    )


def _eq_bands(preset: AudioPreset) -> list[int]:
    if preset.bands:
        values = list(preset.bands[:10])
        values.extend([0] * (10 - len(values)))
        return values
    return [
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


def _output_payload(values: list[int]) -> bytes:
    payload = bytes(value & 0xFF for value in values)
    return payload[:VIRTUOSO_OUTPUT_PAYLOAD_SIZE].ljust(VIRTUOSO_OUTPUT_PAYLOAD_SIZE, b"\x00")


def _signed_byte(value: int) -> int:
    clamped = max(-12, min(value, 12))
    return clamped & 0xFF


def _parse_hex_color(color: str) -> tuple[int, int, int]:
    value = color.lstrip("#")
    if len(value) != 6:
        return (255, 255, 255)
    try:
        return cast(tuple[int, int, int], tuple(int(value[index:index + 2], 16) for index in range(0, 6, 2)))
    except ValueError:
        return (255, 255, 255)
