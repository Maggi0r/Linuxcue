from __future__ import annotations

import argparse
import json
import platform
import sys
import time
from pathlib import Path

from .capture_analysis import analyze_virtuoso_battery_capture, analyze_virtuoso_rgb_capture, capture_plan, diff_capture_files
from .m65_backend import M65_PACKET_KINDS
from .virtuoso_backend import VIRTUOSO_PACKET_KINDS
from .m65_monitor import M65DpiInputMonitor
from .protocol_map import summarize_descriptor_capture
from .service import LinuxCueService


def qt_status() -> dict[str, object]:
    try:
        import PySide6  # noqa: F401
    except Exception as exc:
        return {
            "available": False,
            "error": str(exc),
            "cachyos_fix": "sudo pacman -S --needed pyside6 qt6-declarative",
        }
    return {"available": True}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="linuxcue",
        description="Early Linux-first replacement for Corsair iCUE.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("doctor", help="Show runtime compatibility details.")
    subparsers.add_parser("vm-usb-doctor", help="Diagnose VirtualBox USB/HID passthrough for Corsair devices.")
    subparsers.add_parser("gui", help="Launch the QML dashboard GUI.")
    subparsers.add_parser("qml-gui", help="Launch the Qt Quick/QML dashboard GUI.")
    check_update = subparsers.add_parser("check-update", help="Check GitHub releases and source commits for updates.")
    check_update.add_argument("--repo", default="Maggi0r/Linuxcue", help="GitHub repository in owner/name form.")
    install_update = subparsers.add_parser("install-update", help="Download the latest GitHub source and install the CachyOS package.")
    install_update.add_argument("--repo", default="Maggi0r/Linuxcue", help="GitHub repository in owner/name form.")
    install_update.add_argument("--yes", action="store_true", help="Run without an interactive confirmation prompt.")
    install_update.add_argument("--cache-dir", help="Override the updater source cache directory.")
    subparsers.add_parser("devices", help="List detected Corsair devices.")
    subparsers.add_parser("capture-descriptors", help="Safely capture Linux sysfs HID report descriptors.")
    map_devices = subparsers.add_parser("map-devices", help="Safely map HID endpoints and readable feature reports.")
    map_devices.add_argument("--max-report-id", type=int, default=16, help="Highest feature report id to read.")
    map_devices.add_argument("--report-length", type=int, default=64, help="Feature report read length.")
    analyze_map = subparsers.add_parser("analyze-map", help="Summarize a linuxcue HID map JSON file.")
    analyze_map.add_argument("path", help="Path to linuxcue-hid-map.json")
    analyze_descriptors = subparsers.add_parser("analyze-descriptors", help="Summarize captured HID report descriptors.")
    analyze_descriptors.add_argument("path", help="Path to linuxcue-hid-descriptors.json")
    capture_plan_parser = subparsers.add_parser("capture-plan", help="Show before/after capture scenarios for protocol mapping.")
    capture_plan_parser.add_argument("--target", help="Optional target slug, for example k95, m65, or virtuoso-se.")
    capture_plan_parser.add_argument("--capability", help="Optional capability, for example eq-presets or rgb-zone-lighting.")
    diff_captures = subparsers.add_parser("diff-captures", help="Compare two HID capture exports and show changed bytes.")
    diff_captures.add_argument("before", help="Before capture JSON/text file.")
    diff_captures.add_argument("after", help="After capture JSON/text file.")
    virtuoso_battery_capture = subparsers.add_parser(
        "analyze-virtuoso-battery-capture",
        help="Summarize Virtuoso USBPcap status reports that may contain battery/link state.",
    )
    virtuoso_battery_capture.add_argument("path", help="Virtuoso battery/status pcapng capture.")
    virtuoso_rgb_capture = subparsers.add_parser(
        "analyze-virtuoso-rgb-capture",
        help="Group Virtuoso USBPcap RGB/control output reports by endpoint and payload shape.",
    )
    virtuoso_rgb_capture.add_argument("path", help="Virtuoso RGB/control pcapng capture.")
    subparsers.add_parser("capabilities", help="Show mapped linuxcue capabilities and report shapes.")
    subparsers.add_parser("easyeffects-doctor", help="Diagnose EasyEffects preset paths and CLI support.")
    subparsers.add_parser("m65-doctor", help="Diagnose M65 HID endpoints and live-write readiness.")
    virtuoso_battery_doctor = subparsers.add_parser("virtuoso-battery-doctor", help="Diagnose Virtuoso battery input-report monitoring.")
    virtuoso_battery_doctor.add_argument("--seconds", type=float, default=3.0, help="How long to listen for battery input reports.")
    virtuoso_battery_doctor.add_argument("--no-poll", action="store_true", help="Do not send the small battery poll output report before listening.")
    virtuoso_battery_doctor.add_argument("--poll-mode", choices=("basic", "capture", "both"), default="capture", help="Which battery poll candidate to send before listening.")
    virtuoso_hotplug_doctor = subparsers.add_parser(
        "virtuoso-battery-hotplug-doctor",
        help="Wait for a freshly attached Virtuoso USB device and immediately listen for startup battery reports.",
    )
    virtuoso_hotplug_doctor.add_argument("--wait-seconds", type=float, default=45.0, help="How long to wait for the USB device to appear.")
    virtuoso_hotplug_doctor.add_argument("--listen-seconds", type=float, default=8.0, help="How long to listen immediately after the USB device appears.")
    virtuoso_hotplug_doctor.add_argument("--poll", action="store_true", help="Also send battery poll candidates after the hotplug passive window starts.")
    virtuoso_hotplug_doctor.add_argument("--poll-mode", choices=("basic", "capture", "both"), default="capture", help="Which battery poll candidate to send if --poll is used.")
    virtuoso_hotplug_doctor.add_argument("--require-reconnect", action="store_true", help="Ignore already-attached devices and wait until the Virtuoso disappears and appears again.")
    m65_input_monitor = subparsers.add_parser("m65-input-monitor", help="Read M65 HID input reports for DPI button debugging.")
    m65_input_monitor.add_argument("--seconds", type=float, default=10.0, help="How long to listen for input reports.")
    subparsers.add_parser("targets", help="Show the current support plan for known target devices.")
    subparsers.add_parser("probe-template", help="Show the Linux commands needed for the next device capture step.")
    subparsers.add_parser("probes", help="List saved offline probe fixtures.")

    mock_probe = subparsers.add_parser("mock-probe", help="Create an offline mock probe for a known target device.")
    mock_probe.add_argument("slug", help="Known device slug, for example k95, m65, or virtuoso-rgb")

    import_icue = subparsers.add_parser("import-icue-profile", help="Import EQ/DPI/RGB data from an exported iCUE .cueprofile.")
    import_icue.add_argument("path", help="Path to the .cueprofile file.")
    import_icue.add_argument("--save", action="store_true", help="Save imported linuxcue profiles to the profile store.")

    init_profile = subparsers.add_parser("init-profile", help="Create a default profile.")
    init_profile.add_argument("name", help="Profile name")

    init_k95_profile = subparsers.add_parser("init-k95-profile", help="Create a K95-oriented lighting profile.")
    init_k95_profile.add_argument("name", help="Profile name")

    init_m65_profile = subparsers.add_parser("init-m65-profile", help="Create an M65-oriented DPI/RGB profile.")
    init_m65_profile.add_argument("name", help="Profile name")

    init_virtuoso_profile = subparsers.add_parser("init-virtuoso-profile", help="Create a Virtuoso RGB headset profile.")
    init_virtuoso_profile.add_argument("name", help="Profile name")

    repair_virtuoso = subparsers.add_parser("repair-virtuoso-presets", help="Repair known Virtuoso preset defaults such as Bass Boost.")
    repair_virtuoso.add_argument("name", help="Virtuoso profile name")

    export_virtuoso_eq = subparsers.add_parser("export-virtuoso-eq", help="Export Virtuoso EQ presets for EasyEffects/PipeWire.")
    export_virtuoso_eq.add_argument("name", help="Virtuoso profile name")
    export_virtuoso_eq.add_argument("--output-dir", help="Override EasyEffects output preset directory.")

    apply_virtuoso_eq = subparsers.add_parser("apply-virtuoso-eq", help="Apply Virtuoso EQ through EasyEffects/PipeWire without opening a second GUI.")
    apply_virtuoso_eq.add_argument("name", help="Virtuoso profile name")
    apply_virtuoso_eq.add_argument("--preset", help="Optional EQ preset name. Defaults to the active preset.")

    apply_virtuoso_pipewire_eq = subparsers.add_parser("apply-virtuoso-pipewire-eq", help="Apply Virtuoso EQ through a native PipeWire filter-chain.")
    apply_virtuoso_pipewire_eq.add_argument("name", help="Virtuoso profile name")
    apply_virtuoso_pipewire_eq.add_argument("--preset", help="Optional EQ preset name. Defaults to the active preset.")
    apply_virtuoso_pipewire_eq.add_argument("--no-restart", action="store_true", help="Only write the PipeWire config; do not restart user PipeWire services.")

    preview_k95 = subparsers.add_parser("preview-k95", help="Preview the K95 HID frames for a saved profile.")
    preview_k95.add_argument("name", help="Profile name")

    preview_m65 = subparsers.add_parser("preview-m65", help="Preview the M65 HID frames for a saved profile.")
    preview_m65.add_argument("name", help="Profile name")
    preview_m65.add_argument(
        "--packet-kind",
        choices=sorted(M65_PACKET_KINDS),
        default="all",
        help="Preview only one M65 command group.",
    )

    preview_virtuoso = subparsers.add_parser("preview-virtuoso", help="Preview the Virtuoso HID frames for a saved profile.")
    preview_virtuoso.add_argument("name", help="Profile name")

    write_k95 = subparsers.add_parser("write-k95-live", help="Send the saved K95 profile to real hardware on Linux.")
    write_k95.add_argument("name", help="Profile name")
    write_k95.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")

    k95_hardware = subparsers.add_parser("k95-hardware-mode", help="Switch K95 back to hardware lighting mode.")
    k95_hardware.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")

    k95_options = subparsers.add_parser("k95-options-sync", help="Send known K95 special-function and ISO option frames.")
    k95_options.add_argument("name", help="Saved K95 profile name")
    k95_options.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")

    write_m65 = subparsers.add_parser("write-m65-live", help="Send the saved M65 profile to real hardware on Linux.")
    write_m65.add_argument("name", help="Profile name")
    write_m65.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")
    write_m65.add_argument(
        "--packet-kind",
        choices=sorted(M65_PACKET_KINDS),
        default="all",
        help="Send only one M65 command group so RGB, DPI, and buttons can be mapped independently.",
    )
    write_m65.add_argument(
        "--feature-report",
        action="store_true",
        help="Diagnostic only. M65 Pro RGB usually rejects feature reports; output reports are preferred.",
    )

    write_virtuoso = subparsers.add_parser("write-virtuoso-live", help="Send the saved Virtuoso profile to real hardware on Linux.")
    write_virtuoso.add_argument("name", help="Profile name")
    write_virtuoso.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")
    write_virtuoso.add_argument("--feature-report", action="store_true", help="Send Virtuoso frames with hidapi send_feature_report instead of output write.")
    write_virtuoso.add_argument("--receiver", action="store_true", help="Prefer the Virtuoso wireless receiver endpoint instead of the USB headset HID endpoint.")
    write_virtuoso.add_argument(
        "--packet-kind",
        choices=sorted(VIRTUOSO_PACKET_KINDS),
        default="all",
        help="Send only one Virtuoso command group so RGB/control/EQ can be tested independently.",
    )
    virtuoso_rgb_sweep = subparsers.add_parser("virtuoso-rgb-sweep", help="Send a capture-derived Virtuoso RGB value sweep for protocol testing.")
    virtuoso_rgb_sweep.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override")
    virtuoso_rgb_sweep.add_argument("--receiver", action="store_true", help="Prefer the Virtuoso wireless receiver endpoint instead of the USB headset HID endpoint.")
    virtuoso_rgb_sweep.add_argument("--delay", type=float, default=0.35, help="Delay in seconds between RGB sweep frames.")

    read_virtuoso_status = subparsers.add_parser("read-virtuoso-status", help="Read raw Virtuoso battery/link status candidate feature report 0x0c.")
    read_virtuoso_status.add_argument("--receiver", action="store_true", help="Read from the wireless receiver instead of the USB headset HID endpoint.")
    read_virtuoso_status.add_argument("--device-path", dest="device_path", help="Optional hidapi device path override.")
    read_virtuoso_battery = subparsers.add_parser("read-virtuoso-battery", help="Listen for Virtuoso battery/link input reports and decode battery percent.")
    read_virtuoso_battery.add_argument("--seconds", type=float, default=3.0, help="How long to listen for battery input reports.")
    read_virtuoso_battery.add_argument("--no-poll", action="store_true", help="Do not send the small battery poll output report before listening.")
    read_virtuoso_battery.add_argument("--poll-mode", choices=("basic", "capture", "both"), default="capture", help="Which battery poll candidate to send before listening.")

    write_set = subparsers.add_parser("write-profile-set-live", help="Send every device profile in a saved profile set to real hardware on Linux.")
    write_set.add_argument("name", help="Profile set name")

    subparsers.add_parser("profiles", help="List saved profiles.")

    delete_profile = subparsers.add_parser("delete-profile", help="Delete a saved profile.")
    delete_profile.add_argument("name", help="Profile name")

    apply_profile = subparsers.add_parser("apply", help="Apply a profile in simulated mode.")
    apply_profile.add_argument("name", help="Profile name")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    service = LinuxCueService()

    if args.command in {"gui", "qml-gui"}:
        from .qml_gui import main as qml_gui_main

        return qml_gui_main()

    if args.command == "check-update":
        from .updater import check_github_update

        try:
            print(json.dumps(check_github_update(args.repo), indent=2))
            return 0
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1

    if args.command == "install-update":
        from .updater import install_update_from_github

        try:
            print(json.dumps(install_update_from_github(args.repo, yes=args.yes, cache_dir=args.cache_dir), indent=2))
            return 0
        except Exception as exc:
            print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
            return 1

    if args.command == "doctor":
        payload = {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "linux": sys.platform.startswith("linux"),
            "qt": qt_status(),
            "device_count": len(service.discover_devices()),
            "connected_devices": service.connected_device_summaries(),
            "virtualbox_usb": service.virtualbox_usb_diagnostics(),
            "probe_count": len(service.list_probes()),
            "profile_dir": service.profile_root(),
        }
        print(json.dumps(payload, indent=2))
        return 0

    if args.command == "vm-usb-doctor":
        print(json.dumps(service.virtualbox_usb_diagnostics(), indent=2))
        return 0

    if args.command == "devices":
        print(json.dumps(service.connected_device_summaries(), indent=2))
        return 0

    if args.command == "capture-descriptors":
        print(json.dumps(service.capture_hid_descriptors(), indent=2))
        return 0

    if args.command == "map-devices":
        print(json.dumps(service.map_hid_endpoints(args.max_report_id, args.report_length), indent=2))
        return 0

    if args.command == "analyze-map":
        payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
        print(json.dumps(analyze_hid_map(payload), indent=2))
        return 0

    if args.command == "analyze-descriptors":
        payload = json.loads(Path(args.path).read_text(encoding="utf-8"))
        print(json.dumps(summarize_descriptor_capture(payload), indent=2))
        return 0

    if args.command == "capture-plan":
        print(json.dumps(capture_plan(args.target, args.capability), indent=2))
        return 0

    if args.command == "diff-captures":
        print(json.dumps(diff_capture_files(args.before, args.after), indent=2))
        return 0

    if args.command == "analyze-virtuoso-battery-capture":
        print(json.dumps(analyze_virtuoso_battery_capture(args.path), indent=2))
        return 0

    if args.command == "analyze-virtuoso-rgb-capture":
        print(json.dumps(analyze_virtuoso_rgb_capture(args.path), indent=2))
        return 0

    if args.command == "capabilities":
        print(json.dumps(service.capability_matrix(), indent=2))
        return 0

    if args.command == "easyeffects-doctor":
        print(json.dumps(service.easyeffects_doctor(), indent=2))
        return 0

    if args.command == "m65-doctor":
        status = service.live_status(service.create_m65_profile("m65-doctor"))
        print(json.dumps(
            {
                "connected_count": status["connected_count"],
                "writable_count": status["writable_count"],
                "matching_count": status["matching_count"],
                "m65_devices": [
                    item for item in status["devices"]
                    if "m65" in str(item.get("target", "")).casefold()
                    or item.get("product_id") in {"0x1b12", "0x1b2e"}
                    or item.get("family") == "mouse"
                ],
                "note": "M65 Pro RGB should usually appear as VID 0x1b1c PID 0x1b2e. Older M65 RGB can be PID 0x1b12.",
                "transport_result_from_vm": "Your M65 accepted output_report writes on the mouse HID endpoint; feature_report returned no bytes and should not be used for normal M65 writes.",
                "next_tests": [
                    'linuxcue write-m65-live "Standard Profil-m65" --packet-kind rgb',
                    'linuxcue write-m65-live "Standard Profil-m65" --packet-kind dpi',
                    'linuxcue write-m65-live "Standard Profil-m65" --packet-kind buttons',
                ],
                "capture_needed_if_no_visible_change": [
                    "linuxcue capture-plan --target m65 --capability rgb-logo",
                    "linuxcue capture-plan --target m65 --capability rgb-dpi-indicator",
                    "linuxcue capture-plan --target m65 --capability dpi-stages",
                    "linuxcue capture-plan --target m65 --capability button-map",
                ],
            },
            indent=2,
        ))
        return 0

    if args.command == "virtuoso-battery-doctor":
        print(json.dumps(service.virtuoso_battery_doctor(seconds=args.seconds, poll=not args.no_poll, poll_mode=args.poll_mode), indent=2))
        return 0

    if args.command == "virtuoso-battery-hotplug-doctor":
        print(json.dumps(
            service.virtuoso_battery_hotplug_doctor(
                wait_seconds=args.wait_seconds,
                listen_seconds=args.listen_seconds,
                poll=args.poll,
                poll_mode=args.poll_mode,
                require_reconnect=args.require_reconnect,
            ),
            indent=2,
        ))
        return 0

    if args.command == "targets":
        print(json.dumps(service.target_matrix(), indent=2))
        return 0

    if args.command == "probe-template":
        template = {
            "run_on_linux": [
                "lsusb | grep -i corsair",
                "python - <<'PY'\nimport hid\nfor d in hid.enumerate(0x1b1c, 0):\n    print(hex(d.get('vendor_id', 0)), hex(d.get('product_id', 0)), d.get('product_string'), d.get('interface_number'), d.get('path'))\nPY",
                "sudo usbhid-dump -d 1b1c:XXXX",
                "sudo evtest",
                "sudo libinput list-devices",
            ],
            "notes": [
                "Replace XXXX with the device product id from lsusb.",
                "For K95, capture key presses, media keys, and RGB changes.",
                "For M65, capture DPI button presses and RGB logo changes.",
                "For Virtuoso, capture USB descriptors plus battery/RGB behavior if exposed over HID.",
            ],
        }
        print(json.dumps(template, indent=2))
        return 0

    if args.command == "probes":
        print(json.dumps(service.list_probes(), indent=2))
        return 0

    if args.command == "mock-probe":
        path = service.create_mock_probe(args.slug)
        if path is None:
            parser.error(f"Unknown device slug: {args.slug}")
        print(path)
        return 0

    if args.command == "import-icue-profile":
        if args.save:
            print(json.dumps(service.import_icue_profiles(args.path), indent=2))
        else:
            print(json.dumps(service.preview_icue_import(args.path), indent=2))
        return 0

    if args.command == "init-profile":
        profile = service.create_default_profile(args.name)
        path = service.save_profile(profile)
        print(path)
        return 0

    if args.command == "init-k95-profile":
        profile = service.create_k95_profile(args.name)
        path = service.save_profile(profile)
        print(path)
        return 0

    if args.command == "init-m65-profile":
        profile = service.create_m65_profile(args.name)
        path = service.save_profile(profile)
        print(path)
        return 0

    if args.command == "init-virtuoso-profile":
        profile = service.create_virtuoso_profile(args.name)
        path = service.save_profile(profile)
        print(path)
        return 0

    if args.command == "repair-virtuoso-presets":
        try:
            print(json.dumps(service.repair_virtuoso_presets(args.name), indent=2))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "export-virtuoso-eq":
        try:
            print(json.dumps(service.export_virtuoso_easyeffects(args.name, output_dir=args.output_dir), indent=2))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "apply-virtuoso-eq":
        try:
            print(json.dumps(service.apply_virtuoso_easyeffects(args.name, preset_name=args.preset), indent=2))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "apply-virtuoso-pipewire-eq":
        try:
            print(json.dumps(service.apply_virtuoso_pipewire_eq(args.name, preset_name=args.preset, restart=not args.no_restart), indent=2))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "preview-k95":
        preview = service.preview_k95_profile(args.name)
        if preview is None:
            parser.error(f"Profile not found or K95 preview unavailable: {args.name}")
        print(json.dumps(preview, indent=2))
        return 0

    if args.command == "preview-m65":
        preview = service.preview_m65_profile(args.name, packet_kind=args.packet_kind)
        if preview is None:
            parser.error(f"Profile not found or M65 preview unavailable: {args.name}")
        print(json.dumps(preview, indent=2))
        return 0

    if args.command == "preview-virtuoso":
        preview = service.preview_virtuoso_profile(args.name)
        if preview is None:
            parser.error(f"Profile not found or Virtuoso preview unavailable: {args.name}")
        print(json.dumps(preview, indent=2))
        return 0

    if args.command == "m65-input-monitor":
        devices = [
            device
            for device in service.discover_devices()
            if device.support.family == "mouse" and "m65" in device.support.model_hint.casefold()
        ]
        monitor = M65DpiInputMonitor()
        opened = monitor.ensure_open_many(devices)
        print(json.dumps({
            "opened": opened,
            "open_count": monitor.open_count,
            "device_paths": [device.path for device in devices],
            "hint": "Press M65 DPI up/down now. Reports 03 20/03 40 or 03 00 01 0f/10 should be recognized.",
        }, indent=2))
        deadline = time.monotonic() + max(0.5, args.seconds)
        try:
            while time.monotonic() < deadline:
                for report in monitor.read_reports(limit_per_device=16):
                    delta = monitor.parse_report_delta(report)
                    print(json.dumps({
                        "payload_hex": report.hex(" "),
                        "dpi_delta": delta,
                        "direction": "up" if delta > 0 else "down" if delta < 0 else "",
                    }))
                time.sleep(0.05)
        finally:
            monitor.close()
        return 0

    if args.command == "write-k95-live":
        try:
            result = service.write_k95_profile_live(args.name, device_path=args.device_path)
        except RuntimeError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "profile": result.profile_name,
                    "device": result.device,
                    "packet_count": result.packet_count,
                    "transport": result.transport,
                    "live": result.live,
                    "message": result.message,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "k95-hardware-mode":
        try:
            result = service.write_k95_hardware_mode_live(device_path=args.device_path)
        except RuntimeError as exc:
            parser.error(str(exc))
        print(json.dumps(
            {
                "profile": result.profile_name,
                "device": result.device,
                "packet_count": result.packet_count,
                "transport": result.transport,
                "live": result.live,
                "message": result.message,
            },
            indent=2,
        ))
        return 0

    if args.command == "k95-options-sync":
        try:
            result = service.write_k95_options_sync_live(args.name, device_path=args.device_path)
        except RuntimeError as exc:
            parser.error(str(exc))
        print(json.dumps(
            {
                "profile": result.profile_name,
                "device": result.device,
                "packet_count": result.packet_count,
                "transport": result.transport,
                "live": result.live,
                "message": result.message,
                "note": "This sends known K95 special-function/ISO setup frames. Win-lock behavior bits still need a capture diff.",
            },
            indent=2,
        ))
        return 0

    if args.command == "write-m65-live":
        try:
            result = service.write_m65_profile_live(
                args.name,
                device_path=args.device_path,
                use_feature_report=args.feature_report,
                packet_kind=args.packet_kind,
            )
        except RuntimeError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "profile": result.profile_name,
                    "device": result.device,
                    "packet_count": result.packet_count,
                    "transport": result.transport,
                    "live": result.live,
                    "message": result.message,
                    "write_mode": "feature_report" if args.feature_report else "output_report",
                    "packet_kind": args.packet_kind,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "write-virtuoso-live":
        try:
            result = service.write_virtuoso_profile_live(
                args.name,
                device_path=args.device_path,
                use_feature_report=args.feature_report,
                prefer_receiver=args.receiver,
                packet_kind=args.packet_kind,
            )
        except RuntimeError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "profile": result.profile_name,
                    "device": result.device,
                    "packet_count": result.packet_count,
                    "transport": result.transport,
                    "live": result.live,
                    "message": result.message,
                    "write_mode": "feature_report" if args.feature_report else "output_report",
                    "receiver": args.receiver,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "virtuoso-rgb-sweep":
        try:
            result = service.sweep_virtuoso_rgb_live(
                device_path=args.device_path,
                prefer_receiver=args.receiver,
                delay_seconds=args.delay,
            )
        except RuntimeError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                {
                    "profile": result.profile_name,
                    "device": result.device,
                    "packet_count": result.packet_count,
                    "transport": result.transport,
                    "live": result.live,
                    "message": result.message,
                    "receiver": args.receiver,
                },
                indent=2,
            )
        )
        return 0

    if args.command == "write-profile-set-live":
        try:
            results = service.write_profile_set_live(args.name)
        except RuntimeError as exc:
            parser.error(str(exc))
        print(
            json.dumps(
                [
                    {
                        "profile": result.profile_name,
                        "device": result.device,
                        "packet_count": result.packet_count,
                        "transport": result.transport,
                        "live": result.live,
                        "message": result.message,
                    }
                    for result in results
                ],
                indent=2,
            )
        )
        return 0

    if args.command == "read-virtuoso-status":
        try:
            print(json.dumps(
                service.read_virtuoso_status_live(prefer_receiver=args.receiver, device_path=args.device_path),
                indent=2,
            ))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "read-virtuoso-battery":
        try:
            print(json.dumps(service.read_virtuoso_battery_live(seconds=args.seconds, poll=not args.no_poll, poll_mode=args.poll_mode), indent=2))
        except RuntimeError as exc:
            parser.error(str(exc))
        return 0

    if args.command == "profiles":
        print(json.dumps(service.list_profiles(), indent=2))
        return 0

    if args.command == "delete-profile":
        if not service.delete_profile(args.name):
            parser.error(f"Profile could not be deleted: {args.name}. Profile directory: {service.profile_root()}")
        print(json.dumps({"deleted": args.name, "profile_dir": service.profile_root()}, indent=2))
        return 0

    if args.command == "apply":
        result = service.apply_profile(args.name)
        print(
            json.dumps(
                {
                    "profile": result.profile_name,
                    "devices": result.device_count,
                    "simulated": result.simulated,
                    "message": result.message,
                    "actions": result.actions,
                },
                indent=2,
            )
        )
        return 0

    parser.error("Unknown command")
    return 2


def analyze_hid_map(payload: dict[str, object]) -> dict[str, object]:
    endpoints = payload.get("endpoints", [])
    summaries: list[dict[str, object]] = []
    for endpoint in endpoints if isinstance(endpoints, list) else []:
        if not isinstance(endpoint, dict):
            continue
        reports = endpoint.get("feature_reports", [])
        readable_reports = [
            report.get("report_id")
            for report in reports
            if isinstance(report, dict) and report.get("ok") is True
        ]
        nonzero_reports = []
        for report in reports if isinstance(reports, list) else []:
            if not isinstance(report, dict) or report.get("ok") is not True:
                continue
            payload_hex = report.get("payload_hex")
            if not isinstance(payload_hex, str):
                continue
            values = []
            for byte in payload_hex.split():
                try:
                    values.append(int(byte, 16))
                except ValueError:
                    values.append(0)
            nonzero_positions = [
                {"offset": offset, "value": f"0x{value:02x}"}
                for offset, value in enumerate(values)
                if value
            ]
            if nonzero_positions:
                nonzero_reports.append(
                    {
                        "report_id": report.get("report_id"),
                        "byte_count": report.get("byte_count"),
                        "nonzero_positions": nonzero_positions[:16],
                    }
                )
        summaries.append(
            {
                "product": endpoint.get("product"),
                "product_id": endpoint.get("product_id"),
                "target": endpoint.get("target"),
                "family": endpoint.get("family"),
                "path": endpoint.get("path"),
                "interface_number": endpoint.get("interface_number"),
                "endpoint_role": endpoint.get("endpoint_role") or infer_endpoint_role(endpoint),
                "open_ok": endpoint.get("open_ok"),
                "readable_report_ids": readable_reports,
                "readable_report_count": len(readable_reports),
                "nonzero_report_count": len(nonzero_reports),
                "nonzero_reports": nonzero_reports,
            }
        )

    recommendations = []
    for summary in summaries:
        if summary["target"] == "Corsair K95 RGB Platinum" and summary["interface_number"] == 1:
            recommendations.append("Use K95 interface 1 as the preferred control endpoint.")
            if summary["readable_report_count"] and summary["nonzero_report_count"] == 0:
                recommendations.append("K95 feature reads are all zero-filled; capture HID descriptors and compare before/after device state changes.")
            recommendations.append("K95 descriptor input 1 exposes unnumbered 64-byte output reports; live writes should use report ID 0x00.")
        if summary["target"] == "Corsair Virtuoso RGB Wireless USB Receiver" and "0x0c" in summary["readable_report_ids"]:
            recommendations.append("Use Virtuoso receiver report 0x0c as a readable feature/status candidate.")
            recommendations.append("Virtuoso receiver descriptor exposes output report ID 0x02 with 63-byte payloads for live writes.")
        if summary["target"] == "Corsair Virtuoso SE" and summary["open_ok"]:
            recommendations.append("Virtuoso headset descriptor exposes output report ID 0x02 with 63-byte payloads on the HID control interface.")

    return {
        "device_count": payload.get("device_count"),
        "endpoint_count": len(summaries),
        "summaries": summaries,
        "recommendations": sorted(set(recommendations)),
    }


def infer_endpoint_role(endpoint: dict[str, object]) -> str:
    target = str(endpoint.get("target", "")).casefold()
    interface_number = endpoint.get("interface_number")
    if "k95" in target and interface_number == 1:
        return "keyboard-control-feature"
    if "k95" in target and interface_number == 0:
        return "keyboard-input"
    if "virtuoso" in target and "receiver" in target:
        return "wireless-receiver-control"
    if "virtuoso" in target:
        return "headset-hid"
    return "unknown-hid"


if __name__ == "__main__":
    raise SystemExit(main())
