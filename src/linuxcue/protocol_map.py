from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class CapabilityMap:
    capability: str
    endpoint_role: str
    report_id: int
    payload_size: int
    direction: str
    state: str
    notes: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["report_id"] = f"0x{self.report_id:02x}"
        return payload


DEVICE_CAPABILITY_MAP: dict[str, tuple[CapabilityMap, ...]] = {
    "k95": (
        CapabilityMap(
            capability="rgb-zone-lighting",
            endpoint_role="keyboard-control-feature",
            report_id=0x00,
            payload_size=64,
            direction="output",
            state="descriptor-mapped",
            notes="K95 RGB Platinum interface 1 exposes unnumbered 64-byte output reports.",
        ),
        CapabilityMap(
            capability="macro-keys",
            endpoint_role="keyboard-control-feature",
            report_id=0x00,
            payload_size=64,
            direction="output",
            state="planned",
            notes="Macro storage needs command-byte capture before live writes are enabled.",
        ),
    ),
    "m65": (
        CapabilityMap(
            capability="dpi-stages",
            endpoint_role="mouse-hid",
            report_id=0x05,
            payload_size=64,
            direction="output",
            state="capture-derived-active-stage",
            notes="Live active-stage uses 07 13 02 00 <stage>; iCUE also sends 07 13 02 01 <stage> to persist the selected stage. The first onboard-save capture additionally shows 07 40, 07 13 d2, and 07 13 05 candidates, but exact DPI value bytes still need a before/after save diff.",
        ),
        CapabilityMap(
            capability="rgb-logo",
            endpoint_role="mouse-hid",
            report_id=0x00,
            payload_size=64,
            direction="output",
            state="capture-derived-first-pass",
            notes="The first iCUE M65 RGB capture shows one unnumbered 64-byte output report beginning 07 22 03 01. Observed zone order: 1 front, 2 logo, 3 DPI indicator.",
        ),
        CapabilityMap(
            capability="button-map",
            endpoint_role="mouse-hid",
            report_id=0x07,
            payload_size=0,
            direction="none",
            state="capture-not-observed",
            notes="The first iCUE button-assignment capture produced only DPI-slot and RGB reports, no button-map HID output. GUI values are profile-only until a hardware or Linux input-remap path is implemented.",
        ),
    ),
    "virtuoso-se": (
        CapabilityMap(
            capability="eq-presets",
            endpoint_role="pipewire-output",
            report_id=0x00,
            payload_size=0,
            direction="software",
            state="software-eq-export",
            notes="Virtuoso EQ is exported as EasyEffects/PipeWire presets. HID EQ writes are technically accepted but not observed to affect this headset.",
        ),
        CapabilityMap(
            capability="sidetone-mic-sleep-prompts",
            endpoint_role="headset-hid",
            report_id=0x02,
            payload_size=63,
            direction="output",
            state="descriptor-mapped",
            notes="Headset controls share the same output report shape as EQ and RGB.",
        ),
        CapabilityMap(
            capability="rgb-accent-ring",
            endpoint_role="headset-hid",
            report_id=0x02,
            payload_size=63,
            direction="output",
            state="experimental-unverified",
            notes="OpenLinkHub lists Virtuoso SE RGB support, but linuxcue still needs a verified iCUE capture for the exact RGB command bytes.",
        ),
        CapabilityMap(
            capability="battery-status",
            endpoint_role="headset-hid",
            report_id=0x0C,
            payload_size=63,
            direction="feature",
            state="read-candidate",
            notes="Feature report 0x0c appears in the descriptor; exact battery fields still need capture.",
        ),
    ),
    "virtuoso-rgb-wireless-receiver": (
        CapabilityMap(
            capability="wireless-link",
            endpoint_role="wireless-receiver-control",
            report_id=0x02,
            payload_size=63,
            direction="output",
            state="descriptor-mapped",
            notes="Receiver descriptor exposes report ID 0x02 as the output path.",
        ),
        CapabilityMap(
            capability="receiver-status",
            endpoint_role="wireless-receiver-control",
            report_id=0x0C,
            payload_size=63,
            direction="feature",
            state="read-candidate",
            notes="Your map showed readable feature report 0x0c on the wireless receiver.",
        ),
        CapabilityMap(
            capability="receiver-pairing",
            endpoint_role="wireless-receiver-control",
            report_id=0x02,
            payload_size=63,
            direction="output",
            state="capture-needed",
            notes="iCUE pairing assistant must be captured from start through USB unplug and completion before linuxcue can safely replay pairing commands.",
        ),
    ),
}


def capability_map_for_slug(slug: str) -> list[dict[str, Any]]:
    return [entry.to_dict() for entry in DEVICE_CAPABILITY_MAP.get(slug, ())]


def all_capability_maps() -> dict[str, list[dict[str, Any]]]:
    return {slug: capability_map_for_slug(slug) for slug in DEVICE_CAPABILITY_MAP}


def summarize_descriptor_capture(payload: dict[str, Any]) -> dict[str, Any]:
    descriptors = payload.get("descriptors", [])
    summaries: list[dict[str, Any]] = []
    for descriptor in descriptors if isinstance(descriptors, list) else []:
        if not isinstance(descriptor, dict):
            continue
        descriptor_hex = descriptor.get("descriptor_hex")
        report_items = parse_hid_report_descriptor(descriptor_hex if isinstance(descriptor_hex, str) else "")
        summaries.append(
            {
                "sysfs_name": descriptor.get("sysfs_name"),
                "ok": descriptor.get("ok"),
                "byte_count": descriptor.get("byte_count"),
                "uevent": descriptor.get("uevent"),
                "reports": report_items,
                "linuxcue_hint": _descriptor_hint(str(descriptor.get("sysfs_name", "")), report_items),
            }
        )
    return {
        "descriptor_count": payload.get("descriptor_count"),
        "summary_count": len(summaries),
        "summaries": summaries,
        "capability_map": all_capability_maps(),
    }


def parse_hid_report_descriptor(descriptor_hex: str) -> list[dict[str, Any]]:
    data = _hex_to_bytes(descriptor_hex)
    reports: list[dict[str, Any]] = []
    report_id = 0x00
    report_size = 0
    report_count = 0
    usage_page = 0
    offset = 0
    while offset < len(data):
        prefix = data[offset]
        offset += 1
        if prefix == 0xFE:
            if offset + 1 >= len(data):
                break
            data_size = data[offset]
            offset += 2 + data_size
            continue

        size_code = prefix & 0x03
        data_size = 4 if size_code == 3 else size_code
        item_type = (prefix >> 2) & 0x03
        tag = (prefix >> 4) & 0x0F
        raw = data[offset: offset + data_size]
        offset += data_size
        value = int.from_bytes(raw, "little", signed=False) if raw else 0

        if item_type == 1 and tag == 0x0:
            usage_page = value
        elif item_type == 1 and tag == 0x7:
            report_size = value
        elif item_type == 1 and tag == 0x8:
            report_id = value
        elif item_type == 1 and tag == 0x9:
            report_count = value
        elif item_type == 0 and tag in {0x8, 0x9, 0xB}:
            direction = {0x8: "input", 0x9: "output", 0xB: "feature"}[tag]
            payload_bits = report_size * report_count
            reports.append(
                {
                    "report_id": f"0x{report_id:02x}",
                    "direction": direction,
                    "usage_page": f"0x{usage_page:04x}",
                    "report_size_bits": report_size,
                    "report_count": report_count,
                    "payload_bits": payload_bits,
                    "payload_bytes": (payload_bits + 7) // 8,
                }
            )
    return reports


def _hex_to_bytes(value: str) -> bytes:
    try:
        return bytes(int(part, 16) for part in value.split())
    except ValueError:
        return b""


def _descriptor_hint(sysfs_name: str, reports: list[dict[str, Any]]) -> str:
    name = sysfs_name.casefold()
    if "1b2d" in name and any(
        item["direction"] == "output" and item["payload_bytes"] == 64 and item["report_id"] == "0x00"
        for item in reports
    ):
        return "K95 control endpoint: use unnumbered 64-byte output reports."
    if "0a3d" in name or "0a46" in name:
        if any(item["direction"] == "output" and item["report_id"] == "0x02" for item in reports):
            return "Virtuoso control endpoint: use report ID 0x02 with 63-byte output payloads."
    return "No device-specific linuxcue mapping hint yet."
