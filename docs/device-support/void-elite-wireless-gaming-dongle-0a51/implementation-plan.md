# CORSAIR VOID ELITE Wireless Gaming Dongle

Generated from a linuxcue device report.

## Identity
- Slug: `void-elite-wireless-gaming-dongle-0a51`
- Vendor ID: `0x1b1c`
- Product ID: `0x0a51`
- Transport: `hidapi`
- HID endpoints in report: `3`
- HID descriptors in report: `1`
- Current capabilities: `device-detection`

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
