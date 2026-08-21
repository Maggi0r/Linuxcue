from __future__ import annotations

import json
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CaptureScenario:
    target: str
    capability: str
    before: str
    action: str
    after: str
    expected_report_hint: str

    def to_dict(self) -> dict[str, str]:
        return {
            "target": self.target,
            "capability": self.capability,
            "before": self.before,
            "action": self.action,
            "after": self.after,
            "expected_report_hint": self.expected_report_hint,
        }


CAPTURE_SCENARIOS: tuple[CaptureScenario, ...] = (
    CaptureScenario(
        target="k95",
        capability="rgb-zone-lighting",
        before="Set the whole keyboard to static black/off in iCUE, then capture one write.",
        action="Change exactly one zone, for example function row, to pure red #ff0000 and apply.",
        after="Capture the HID write immediately after applying the change.",
        expected_report_hint="K95 control endpoint, unnumbered 64-byte output report.",
    ),
    CaptureScenario(
        target="k95",
        capability="win-lock-options",
        before="In iCUE K95 options, set Win Lock to default/off for Alt+Tab, Alt+F4, Shift+Tab, and Windows key, then capture one write.",
        action="Change exactly one Win Lock option, for example disable Windows key, and apply/save only that setting.",
        after="Capture the HID write immediately after applying the option change.",
        expected_report_hint="K95 special-function/control endpoint, likely unnumbered 64-byte output report; compare against known 07 04 02 setup frames.",
    ),
    CaptureScenario(
        target="k95",
        capability="indicator-colors",
        before="Set K95 option indicator colors to black/off for lock, brightness, and profile indicators, then capture.",
        action="Change exactly one indicator color, for example profile color to pure red #ff0000, and apply.",
        after="Capture the HID write immediately after applying the color change.",
        expected_report_hint="K95 RGB color buffer reports; current linuxcue maps lock, brightness, and preset as live zones.",
    ),
    CaptureScenario(
        target="m65",
        capability="dpi-stages",
        before="Set M65 stage 1 to 800/800 with color red #ff0000 in iCUE, then capture the HID write.",
        action="Change only stage 1 to 1200/1200 and color green #00ff00, then apply.",
        after="Capture the HID write immediately after applying the DPI change.",
        expected_report_hint="M65 active DPI stage is mapped from iCUE reports 07 13 02 00 <stage> and 07 13 02 01 <stage>. Exact DPI value storage still needs a hardware-memory/save-to-device capture.",
    ),
    CaptureScenario(
        target="m65",
        capability="rgb-logo",
        before="Set M65 logo, DPI indicator, and front light to black/off, then capture the HID write.",
        action="Change only the logo to pure green #00ff00 and apply.",
        after="Capture the HID write immediately after applying the RGB change.",
        expected_report_hint="M65 RGB command bytes are still unverified. The current linuxcue test writes unnumbered 64-byte output reports beginning 07 22; capture should confirm or replace that shape.",
    ),
    CaptureScenario(
        target="m65",
        capability="rgb-dpi-indicator",
        before="Set only the M65 DPI indicator light to black/off in iCUE, then capture the HID write.",
        action="Change only the DPI indicator light to pure blue #0000ff and apply.",
        after="Capture the HID write immediately after applying the RGB change.",
        expected_report_hint="This separates logo RGB from DPI indicator RGB so linuxcue can map the zone index/order correctly.",
    ),
    CaptureScenario(
        target="m65",
        capability="button-map",
        before="Set M65 button assignments to hardware/default in iCUE, then capture the HID write.",
        action="Change exactly one button, for example Sniper -> Disabled or Sniper -> Forward, then apply.",
        after="Capture the HID write immediately after applying the button assignment.",
        expected_report_hint="The first button capture showed no button-map HID output, only DPI/RGB reports. Try a hardware-assignment/onboard-save workflow if iCUE offers one; otherwise this may need a Linux-side evdev/uinput remapper.",
    ),
    CaptureScenario(
        target="virtuoso-se",
        capability="eq-presets",
        before="Set active EQ preset to flat: all ten bands at 0 dB, then capture.",
        action="Change only one EQ band, for example 1 kHz, from 0 dB to +6 dB and apply.",
        after="Capture the HID write immediately after applying the EQ change.",
        expected_report_hint="Virtuoso control endpoint, report ID 0x02 with 63-byte output payload.",
    ),
    CaptureScenario(
        target="virtuoso-se",
        capability="sidetone-mic-sleep-prompts",
        before="Set sidetone to 0, mic level to 50, sleep timer to 20, voice prompts on, then capture.",
        action="Change only sidetone from 0 to 50 and apply.",
        after="Capture the HID write immediately after applying the control change.",
        expected_report_hint="Virtuoso control endpoint, report ID 0x02 with 63-byte output payload.",
    ),
    CaptureScenario(
        target="virtuoso-se",
        capability="rgb-accent-ring",
        before="Set accent lighting to black/off, then capture.",
        action="Change only accent lighting to pure blue #0000ff and apply.",
        after="Capture the HID write immediately after applying the RGB change.",
        expected_report_hint="Virtuoso USB headset HID control endpoint, report ID 0x02 with 63-byte output payload; linuxcue RGB command is still experimental until this capture is verified.",
    ),
    CaptureScenario(
        target="virtuoso-rgb-wireless-receiver",
        capability="receiver-status",
        before="Capture receiver status while the headset is connected and idle.",
        action="Switch the headset off or disconnect wireless link.",
        after="Capture receiver status again after the link state changes.",
        expected_report_hint="Receiver feature report 0x0c is the current readable status candidate.",
    ),
    CaptureScenario(
        target="virtuoso-rgb-wireless-receiver",
        capability="wireless-eq-tunnel",
        before="Put Virtuoso in wireless/dongle mode, set EQ flat in iCUE, then capture the receiver HID write.",
        action="Change exactly one EQ band, for example 1 kHz from 0 dB to +6 dB, and apply only that change.",
        after="Capture the receiver HID write immediately after applying the EQ change.",
        expected_report_hint="Receiver may tunnel headset EQ/control over report ID 0x02, but this path is not verified yet.",
    ),
    CaptureScenario(
        target="virtuoso-rgb-wireless-receiver",
        capability="receiver-pairing",
        before="Receiver visible in iCUE, headset connected by USB cable, pairing assistant not started yet. Start capture before clicking 'Koppeln'.",
        action="Click 'Koppeln', then follow iCUE's prompt and unplug the headset USB cable when it asks. Keep capturing until iCUE says pairing is done or failed.",
        after="Stop capture only after the pairing assistant reaches a final state. Save one complete capture plus screenshots of each assistant state.",
        expected_report_hint="Look for receiver output reports around report ID 0x02 and feature/status report 0x0c changes. Do not replay pairing writes until exact start/finish/abort bytes are known.",
    ),
    CaptureScenario(
        target="virtuoso-se",
        capability="battery-status",
        before="Capture/read status while the headset battery is known high, ideally >80%. Also run linuxcue read-virtuoso-status and save the JSON.",
        action="Repeat the same capture/read at medium battery and again near low battery, ideally below 20%.",
        after="Compare feature report 0x0c and receiver status bytes between high/medium/low charge.",
        expected_report_hint="Feature report 0x0c is the current read candidate. We need multiple charge levels to identify the true battery byte and critical threshold.",
    ),
)


def capture_plan(target: str | None = None, capability: str | None = None) -> dict[str, object]:
    selected = [
        scenario
        for scenario in CAPTURE_SCENARIOS
        if (target is None or scenario.target == target)
        and (capability is None or scenario.capability == capability)
    ]
    return {
        "scenario_count": len(selected),
        "scenarios": [scenario.to_dict() for scenario in selected],
        "capture_notes": [
            "Change exactly one setting between before and after captures.",
            "Prefer pure values first: RGB red/green/blue, EQ 0 dB to +6 dB, DPI 800 to 1200.",
            "Save each pair with clear names, for example virtuoso-eq-flat.json and virtuoso-eq-1k-plus6.json.",
            "If using Wireshark/usbmon, export packet bytes as JSON or text with hex bytes; linuxcue can diff both.",
        ],
    }


def diff_capture_files(before_path: str, after_path: str) -> dict[str, object]:
    before = _load_capture(Path(before_path))
    after = _load_capture(Path(after_path))
    before_records = _extract_hex_records(before)
    after_records = _extract_hex_records(after)
    pairs = _pair_records(before_records, after_records)
    diffs = [_diff_pair(left, right) for left, right in pairs]
    changed = [item for item in diffs if item["changed_byte_count"]]
    result = {
        "before": before_path,
        "after": after_path,
        "before_record_count": len(before_records),
        "after_record_count": len(after_records),
        "compared_record_count": len(pairs),
        "changed_record_count": len(changed),
        "changed_records": changed,
    }
    pcapng_summary = _pcapng_output_summary(before, after)
    if pcapng_summary is not None:
        result["pcapng_output_summary"] = pcapng_summary
    return result


def analyze_virtuoso_battery_capture(path: str) -> dict[str, Any]:
    capture_path = Path(path)
    records = _extract_usbpcap_records(capture_path)
    product_hits = []
    report_groups: dict[str, list[tuple[int, bytes]]] = {}
    receiver_outputs = []

    for record in records:
        payload_hex = record.get("payload_hex")
        if not isinstance(payload_hex, str) or not payload_hex:
            continue
        payload = bytes.fromhex(payload_hex)
        text = _decode_usb_string_descriptor(payload)
        if text and "virtuoso" in text.casefold():
            product_hits.append(
                {
                    "packet_index": record.get("packet_index"),
                    "direction": record.get("direction"),
                    "endpoint": record.get("endpoint"),
                    "text": text,
                }
            )
        if record.get("direction") == "in" and record.get("endpoint") == "0x82" and len(payload) == 64:
            key = payload[:5].hex(" ")
            report_groups.setdefault(key, []).append((int(record.get("packet_index", -1)), payload))
        if (
            record.get("direction") == "out"
            and record.get("endpoint") == "0x02"
            and len(payload) == 64
            and payload.startswith(bytes.fromhex("02 09 06 00 09"))
        ):
            receiver_outputs.append(
                {
                    "packet_index": record.get("packet_index"),
                    "payload_prefix": payload[:18].hex(" "),
                }
            )

    grouped_reports = []
    for key, items in sorted(report_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        le_values = [int.from_bytes(payload[5:7], "little") for _index, payload in items if len(payload) >= 7]
        grouped_reports.append(
            {
                "prefix": key,
                "count": len(items),
                "samples": [
                    {
                        "packet_index": packet_index,
                        "payload_prefix": payload[:16].hex(" "),
                        "byte5": payload[5] if len(payload) > 5 else None,
                        "byte6": payload[6] if len(payload) > 6 else None,
                        "little_endian_byte5_6": int.from_bytes(payload[5:7], "little") if len(payload) >= 7 else None,
                    }
                    for packet_index, payload in items[:8]
                ],
                "little_endian_byte5_6_unique": sorted(set(le_values))[:32],
                "little_endian_byte5_6_range": [min(le_values), max(le_values)] if le_values else [],
            }
        )

    status_0f = report_groups.get("03 01 01 0f 00", [])
    status_10 = report_groups.get("03 01 01 10 00", [])
    countdown_values = [int.from_bytes(payload[5:7], "little") for _index, payload in status_0f if len(payload) >= 7]
    link_values = [payload[5] for _index, payload in status_10 if len(payload) > 5]
    battery_percent_values = [round(value / 10, 1) for value in countdown_values]

    return {
        "path": str(capture_path),
        "record_count": len(records),
        "virtuoso_product_strings": product_hits[:12],
        "report_groups": grouped_reports,
        "receiver_output_candidates": receiver_outputs[:24],
        "inference": {
            "has_virtuoso": bool(product_hits),
            "status_stream_report": "03 01 01 0f 00" if status_0f else "",
            "status_stream_count": len(status_0f),
            "status_stream_byte5_6": {
                "range": [min(countdown_values), max(countdown_values)] if countdown_values else [],
                "note": "Observed across 80/50/20/charging captures as tenths-of-percent battery candidate.",
            },
            "battery_percent_estimate": {
                "first": battery_percent_values[0] if battery_percent_values else None,
                "last": battery_percent_values[-1] if battery_percent_values else None,
                "min": min(battery_percent_values) if battery_percent_values else None,
                "max": max(battery_percent_values) if battery_percent_values else None,
            },
            "link_state_report": "03 01 01 10 00" if status_10 else "",
            "link_state_values": sorted(set(link_values)),
            "battery_percent": battery_percent_values[-1] if battery_percent_values else None,
            "battery_note": (
                "Battery is decoded from report 03 01 01 0f 00 bytes 5-6 as little-endian tenths of percent. "
                "This is capture-derived and should be treated as approximate until confirmed live on Linux."
            ),
        },
    }


def analyze_virtuoso_rgb_capture(path: str) -> dict[str, Any]:
    capture_path = Path(path)
    records = _extract_usbpcap_records(capture_path)
    output_groups: dict[str, list[tuple[int, bytes, str]]] = {}
    all_output_samples = []
    mass_storage_like_count = 0
    for record in records:
        payload_hex = record.get("payload_hex")
        if not isinstance(payload_hex, str) or not payload_hex:
            continue
        payload = bytes.fromhex(payload_hex)
        if record.get("direction") != "out":
            continue
        if len(all_output_samples) < 16:
            all_output_samples.append(
                {
                    "packet_index": record.get("packet_index"),
                    "endpoint": record.get("endpoint"),
                    "transfer": record.get("transfer"),
                    "payload_length": len(payload),
                    "payload_prefix": payload[:32].hex(" "),
                    "note": _virtuoso_rgb_group_note(payload),
                }
            )
        if payload.startswith(b"USBC") or payload.startswith(b"USBS"):
            mass_storage_like_count += 1
        if len(payload) != 64:
            continue
        endpoint = str(record.get("endpoint", ""))
        prefix = payload[:12].hex(" ")
        output_groups.setdefault(f"{endpoint} {prefix}", []).append((int(record.get("packet_index", -1)), payload, endpoint))

    groups = []
    for key, items in sorted(output_groups.items(), key=lambda item: (-len(item[1]), item[0])):
        packets = [payload for _index, payload, _endpoint in items]
        variable_offsets = []
        for offset in range(64):
            values = sorted({payload[offset] for payload in packets})
            if len(values) > 1:
                variable_offsets.append(
                    {
                        "offset": offset,
                        "unique_count": len(values),
                        "values": [f"0x{value:02x}" for value in values[:48]],
                    }
                )
        groups.append(
            {
                "group": key,
                "endpoint": items[0][2],
                "count": len(items),
                "first_packet_indices": [index for index, _payload, _endpoint in items[:12]],
                "sample_payload_prefix": packets[0][:24].hex(" "),
                "variable_offsets": variable_offsets[:16],
                "note": _virtuoso_rgb_group_note(packets[0]),
            }
        )

    return {
        "path": str(capture_path),
        "record_count": len(records),
        "all_output_sample_count": len(all_output_samples),
        "all_output_samples": all_output_samples,
        "mass_storage_like_output_count": mass_storage_like_count,
        "output_group_count": len(groups),
        "output_groups": groups[:32],
        "diagnosis": _virtuoso_rgb_capture_diagnosis(groups, mass_storage_like_count, all_output_samples),
        "capture_request_if_unresolved": [
            "Capture 1: set Virtuoso lighting off/black and save as virtuoso-rgb-off.pcapng.",
            "Capture 2: change only Virtuoso accent ring to pure red #ff0000 and save as virtuoso-rgb-red.pcapng.",
            "Capture 3: change only Virtuoso accent ring to pure blue #0000ff and save as virtuoso-rgb-blue.pcapng.",
            "Avoid changing EQ, sidetone, brightness, or profiles between captures.",
        ],
    }


def _virtuoso_rgb_group_note(payload: bytes) -> str:
    if payload.startswith(b"USBC") or payload.startswith(b"USBS"):
        return "Mass-storage/SCSI style transfer, not a Virtuoso HID RGB report."
    if payload.startswith(bytes.fromhex("02 09 06 00 09 00 00 00 98 00 ff f8")):
        return "Known receiver RGB/intensity ramp candidate. User VM sweep wrote this shape but no visible USB-headset change occurred."
    if payload.startswith(bytes.fromhex("02 09 06 00 09")):
        return "Virtuoso vendor report candidate; compare before/after color-only captures."
    return ""


def _virtuoso_rgb_capture_diagnosis(groups: list[dict[str, Any]], mass_storage_like_count: int, output_samples: list[dict[str, Any]]) -> str:
    if not groups and mass_storage_like_count:
        return (
            "No 64-byte Virtuoso HID RGB output reports were captured. The visible OUT packets look like "
            "USB mass-storage/SCSI transfers (USBC/USBS), so Wireshark likely captured the wrong USB function/interface."
        )
    if not groups and output_samples:
        return "No 64-byte Virtuoso HID RGB output reports were captured; capture may be on the wrong interface or the RGB write was not applied during recording."
    if not groups:
        return "No output packets were captured."
    return "Virtuoso-sized output report candidates were found; compare variable offsets across off/red/blue captures."


def _load_capture(path: Path) -> Any:
    if path.suffix.casefold() == ".pcapng":
        return {"pcapng_usbpcap": _extract_usbpcap_records(path)}
    text = path.read_text(encoding="utf-8", errors="replace")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"text": text}


def _decode_usb_string_descriptor(payload: bytes) -> str:
    if len(payload) < 4 or payload[1] != 0x03:
        return ""
    try:
        return payload[2:].decode("utf-16-le", errors="ignore").strip("\x00")
    except UnicodeError:
        return ""


def _extract_usbpcap_records(path: Path) -> list[dict[str, Any]]:
    data = path.read_bytes()
    records: list[dict[str, Any]] = []
    offset = 0
    packet_index = 0
    linktype = None
    while offset + 12 <= len(data):
        block_type, block_length = struct.unpack_from("<II", data, offset)
        if block_length < 12 or offset + block_length > len(data):
            break
        body = data[offset + 8: offset + block_length - 4]
        if block_type == 0x00000001 and len(body) >= 8:
            linktype = struct.unpack_from("<H", body, 0)[0]
        elif block_type == 0x00000006 and len(body) >= 20:
            _interface_id, timestamp_high, timestamp_low, captured_length, _original_length = struct.unpack_from("<IIIII", body, 0)
            packet = body[20: 20 + captured_length]
            record = _parse_usbpcap_packet(packet)
            record.update(
                {
                    "packet_index": packet_index,
                    "timestamp": (timestamp_high << 32) | timestamp_low,
                    "linktype": linktype,
                    "raw_hex": packet.hex(" "),
                }
            )
            records.append(record)
            packet_index += 1
        offset += block_length
    return records


def _parse_usbpcap_packet(packet: bytes) -> dict[str, Any]:
    if len(packet) < 27:
        return {"payload_hex": "", "payload_length": 0}
    header_length = int.from_bytes(packet[:2], "little")
    if header_length < 27 or header_length > len(packet):
        header_length = 27
    payload = packet[header_length:]
    endpoint = packet[21] if len(packet) > 21 else 0
    direction = "in" if endpoint & 0x80 else "out"
    return {
        "header_length": header_length,
        "endpoint": f"0x{endpoint:02x}",
        "direction": direction,
        "transfer": packet[22] if len(packet) > 22 else None,
        "declared_data_length": int.from_bytes(packet[23:27], "little") if len(packet) >= 27 else len(payload),
        "payload_length": len(payload),
        "payload_hex": payload.hex(" "),
    }


def _extract_hex_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    def walk(node: Any, path: str) -> None:
        if isinstance(node, dict):
            for key, child in node.items():
                if key == "raw_hex":
                    continue
                if isinstance(child, str) and _looks_like_hex_stream(child):
                    records.append(
                        {
                            "path": f"{path}.{key}" if path else key,
                            "context": _record_context(node),
                            "bytes": _hex_to_bytes(child),
                        }
                    )
                else:
                    walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
        elif isinstance(node, str):
            for index, line in enumerate(node.splitlines()):
                if _looks_like_hex_stream(line):
                    records.append(
                        {
                            "path": f"{path}.line[{index}]",
                            "context": {},
                            "bytes": _hex_to_bytes(line),
                        }
                    )

    walk(value, "")
    return records


def _pcapng_output_summary(before: Any, after: Any) -> dict[str, Any] | None:
    before_records = before.get("pcapng_usbpcap") if isinstance(before, dict) else None
    after_records = after.get("pcapng_usbpcap") if isinstance(after, dict) else None
    if not isinstance(before_records, list) or not isinstance(after_records, list):
        return None

    before_payloads = {
        item.get("payload_hex")
        for item in before_records
        if isinstance(item, dict)
        and item.get("direction") == "out"
        and isinstance(item.get("payload_hex"), str)
        and item.get("payload_hex")
    }
    after_outputs = [
        item
        for item in after_records
        if isinstance(item, dict)
        and item.get("direction") == "out"
        and isinstance(item.get("payload_hex"), str)
        and item.get("payload_hex")
    ]
    new_outputs = []
    seen: set[str] = set()
    for item in after_outputs:
        payload = str(item["payload_hex"])
        if payload in before_payloads or payload in seen:
            continue
        seen.add(payload)
        new_outputs.append(
            {
                "packet_index": item.get("packet_index"),
                "endpoint": item.get("endpoint"),
                "payload_length": item.get("payload_length"),
                "declared_data_length": item.get("declared_data_length"),
                "payload_hex": payload,
                "linuxcue_hint": _payload_hint(payload),
            }
        )
    interesting = [
        item
        for item in new_outputs
        if str(item["payload_hex"]).startswith(("07 22", "07 13", "07 05", "10 ", "30 "))
    ]
    return {
        "before_output_count": len(before_payloads),
        "after_output_count": len(after_outputs),
        "new_output_count": len(new_outputs),
        "interesting_new_outputs": interesting[:32],
    }


def _payload_hint(payload_hex: str) -> str:
    if payload_hex.startswith("07 22 03 01"):
        return "M65 RGB: captured iCUE-style 3-zone lighting report."
    if payload_hex.startswith("07 22"):
        return "Corsair RGB/control candidate."
    if payload_hex.startswith("07 13 02 00"):
        return "M65 active DPI stage candidate."
    if payload_hex.startswith("07 13 d2"):
        return "M65 onboard-save/DPI-memory candidate. Needs before/after captures with changed DPI values."
    if payload_hex.startswith("07 13 05"):
        return "M65 onboard-save commit/finalize candidate."
    if payload_hex.startswith("07 13 02 01"):
        return "M65 onboard profile/DPI-slot persistence candidate."
    if payload_hex.startswith("07 40"):
        return "M65 onboard-memory preparation candidate."
    if payload_hex.startswith("10 "):
        return "M65 DPI candidate."
    if payload_hex.startswith("30 "):
        return "M65 button-map candidate."
    return ""


def _record_context(node: dict[str, Any]) -> dict[str, Any]:
    context_keys = ("product", "product_id", "target", "path", "interface_number", "report_id", "direction", "endpoint_role")
    return {key: node[key] for key in context_keys if key in node}


def _pair_records(before: list[dict[str, Any]], after: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
    used_after: set[int] = set()
    for left in before:
        best_index = None
        for index, right in enumerate(after):
            if index in used_after:
                continue
            if _pair_key(left) == _pair_key(right):
                best_index = index
                break
        if best_index is None:
            best_index = next((index for index in range(len(after)) if index not in used_after), None)
        if best_index is None:
            continue
        used_after.add(best_index)
        pairs.append((left, after[best_index]))
    return pairs


def _pair_key(record: dict[str, Any]) -> tuple[Any, ...]:
    context = record.get("context", {})
    return (
        context.get("product_id"),
        context.get("path"),
        context.get("interface_number"),
        context.get("report_id"),
        record.get("path"),
    )


def _diff_pair(left: dict[str, Any], right: dict[str, Any]) -> dict[str, Any]:
    left_bytes = left["bytes"]
    right_bytes = right["bytes"]
    max_len = max(len(left_bytes), len(right_bytes))
    changes = []
    for offset in range(max_len):
        left_value = left_bytes[offset] if offset < len(left_bytes) else None
        right_value = right_bytes[offset] if offset < len(right_bytes) else None
        if left_value != right_value:
            changes.append(
                {
                    "offset": offset,
                    "before": None if left_value is None else f"0x{left_value:02x}",
                    "after": None if right_value is None else f"0x{right_value:02x}",
                }
            )
    return {
        "before_path": left["path"],
        "after_path": right["path"],
        "context": right.get("context") or left.get("context") or {},
        "before_byte_count": len(left_bytes),
        "after_byte_count": len(right_bytes),
        "changed_byte_count": len(changes),
        "changes": changes[:128],
    }


def _looks_like_hex_stream(value: str) -> bool:
    parts = value.replace(",", " ").replace(":", " ").split()
    if len(parts) < 4:
        return False
    hex_parts = 0
    for part in parts:
        normalized = part.removeprefix("0x").removeprefix("0X")
        if len(normalized) <= 2 and all(char in "0123456789abcdefABCDEF" for char in normalized):
            hex_parts += 1
    return hex_parts >= 4 and hex_parts / len(parts) > 0.75


def _hex_to_bytes(value: str) -> bytes:
    values = []
    for part in value.replace(",", " ").replace(":", " ").split():
        normalized = part.removeprefix("0x").removeprefix("0X")
        try:
            if len(normalized) <= 2:
                values.append(int(normalized, 16))
        except ValueError:
            continue
    return bytes(values)
