from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


def prepare_device_support_from_report(
    report_path: str | Path,
    *,
    output_dir: str | Path = "docs/device-support",
    slug: str | None = None,
) -> dict[str, Any]:
    source = Path(report_path).expanduser()
    report = json.loads(source.read_text(encoding="utf-8"))
    device = _primary_device(report)
    generated_slug = slug or _device_slug(device)
    root = Path(output_dir).expanduser() / generated_slug
    root.mkdir(parents=True, exist_ok=True)

    report_target = root / "device-report.json"
    plan_target = root / "implementation-plan.md"
    snippet_target = root / "known-device-snippet.py"

    report_target.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    plan_target.write_text(_implementation_plan(generated_slug, device, report), encoding="utf-8")
    snippet_target.write_text(_known_device_snippet(generated_slug, device), encoding="utf-8")

    return {
        "ok": True,
        "slug": generated_slug,
        "title": device.get("title") or device.get("product") or "Unknown Corsair Device",
        "vendor_id": _hex_id(device.get("vendorId") or device.get("vendor_id"), 0x1B1C),
        "product_id": _hex_id(device.get("productId") or device.get("product_id"), 0),
        "output_dir": str(root),
        "files": {
            "report": str(report_target),
            "plan": str(plan_target),
            "known_device_snippet": str(snippet_target),
        },
        "next_steps": [
            "Read implementation-plan.md.",
            "Copy the KnownDevice snippet into src/linuxcue/known_devices.py and adjust family/capabilities.",
            "Add or extend a backend only after safe HID captures confirm write packets.",
            "Connect the new slug to qml_gui.py and Main.qml once the feature set is known.",
        ],
    }


def _primary_device(report: dict[str, Any]) -> dict[str, Any]:
    selected = report.get("selected_device")
    if isinstance(selected, dict) and selected:
        return selected
    matching = report.get("matching_devices")
    if isinstance(matching, list):
        for item in matching:
            if isinstance(item, dict):
                return item
    connected = report.get("all_connected_devices")
    if isinstance(connected, list):
        for item in connected:
            if isinstance(item, dict):
                return item
    return {}


def _device_slug(device: dict[str, Any]) -> str:
    name = str(device.get("title") or device.get("product") or device.get("target") or "corsair-device")
    product_id = _hex_id(device.get("productId") or device.get("product_id"), 0).replace("0x", "")
    base = re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
    base = base.replace("corsair-", "")
    if not base:
        base = "corsair-device"
    if product_id and product_id != "0000" and product_id not in base:
        base = f"{base}-{product_id}"
    return base[:64].strip("-") or "corsair-device"


def _hex_id(value: object, fallback: int) -> str:
    if isinstance(value, int):
        return f"0x{value:04x}"
    text = str(value or "").strip().casefold()
    try:
        if text.startswith("0x"):
            return f"0x{int(text, 16):04x}"
        if text:
            return f"0x{int(text, 10):04x}"
    except ValueError:
        return f"0x{fallback:04x}"
    return f"0x{fallback:04x}"


def _product_id_literal(device: dict[str, Any]) -> str:
    product_id = _hex_id(device.get("productId") or device.get("product_id"), 0)
    return "0x" + product_id.replace("0x", "").upper()


def _implementation_plan(slug: str, device: dict[str, Any], report: dict[str, Any]) -> str:
    title = str(device.get("title") or device.get("product") or "Unknown Corsair Device")
    vendor_id = _hex_id(device.get("vendorId") or device.get("vendor_id"), 0x1B1C)
    product_id = _hex_id(device.get("productId") or device.get("product_id"), 0)
    transport = str(device.get("transport") or "unknown")
    endpoint_count = device.get("endpointCount") or len(report.get("matching_devices", []) or [])
    capabilities = device.get("capabilities") or ["device-detection"]
    descriptors = report.get("hid_descriptors", {})
    descriptor_count = descriptors.get("descriptor_count") if isinstance(descriptors, dict) else "unknown"
    if descriptor_count is None:
        descriptor_count = "unknown"

    return f"""# {title}

Generated from a linuxcue device report.

## Identity
- Slug: `{slug}`
- Vendor ID: `{vendor_id}`
- Product ID: `{product_id}`
- Transport: `{transport}`
- HID endpoints in report: `{endpoint_count}`
- HID descriptors in report: `{descriptor_count}`
- Current capabilities: `{", ".join(str(item) for item in capabilities)}`

## Developer Flow
1. Add the generated `KnownDevice` snippet to `src/linuxcue/known_devices.py`.
2. Choose the first safe support level: `detected`, `scaffolding`, `descriptor-mapped`, or `live-write`.
3. Keep writes disabled until Windows/iCUE captures confirm the packet format.
4. Add a small backend only for confirmed capabilities.
5. Add GUI routing when the feature set is clear.
6. Test `linuxcue devices`, `linuxcue doctor`, and the QML device card.

## Capture Checklist
- Capture Linux `linuxcue devices` output with the device connected.
- Capture `linuxcue capture-descriptors`.
- Capture `linuxcue map-devices --max-report-id 32 --report-length 128`.
- For write features, capture before/after changes from Windows iCUE.
- Compare captures with `linuxcue diff-captures before.json after.json`.

## Safety Notes
- Do not reuse RGB, DPI, EQ, or macro packets from another model without confirming the report shape.
- Start with read-only detection and user-facing status.
- Add live writes one feature at a time.
"""


def _known_device_snippet(slug: str, device: dict[str, Any]) -> str:
    title = str(device.get("title") or device.get("product") or "Unknown Corsair Device")
    product_id = _product_id_literal(device)
    token = re.sub(r"[^a-z0-9 ]+", " ", title.casefold()).strip() or slug.replace("-", " ")
    return f"""KnownDevice(
    slug="{slug}",
    family="unknown",
    model_hint="{title}",
    match_tokens=("{token}",),
    protocol="hid",
    support_level="detected",
    next_step="Classify this device family and capture safe HID descriptors before enabling writes.",
    companion_slug=None,
    companion_role=None,
    capabilities=("device-detection",),
    default_product_id={product_id},
    default_transport="hid",
    mock_transport="hid",
    mock_serial_number="MOCK-{slug.upper().replace('-', '-')}-001",
    mock_notes=("Generated from a linuxcue device report.",),
),
"""
