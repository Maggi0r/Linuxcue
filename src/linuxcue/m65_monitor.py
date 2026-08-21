from __future__ import annotations

import time

from .models import Device


class M65DpiInputMonitor:
    """Non-blocking reader for M65 physical DPI button reports."""

    DPI_DOWN_REPORT = 0x0F
    DPI_UP_REPORT = 0x10
    DPI_DOWN_BUTTON_MASK = 0x20
    DPI_UP_BUTTON_MASK = 0x40
    SNIPER_BUTTON_MASK = 0x80
    SNIPER_REPORT = 0x12

    def __init__(self) -> None:
        self._devices: dict[str, object] = {}
        self._last_event: tuple[int, float] | None = None

    def ensure_open(self, device: Device | None) -> bool:
        return self.ensure_open_many([device] if device is not None else [])

    def ensure_open_many(self, devices: list[Device]) -> bool:
        targets = [device for device in devices if device.transport == "hidapi" and device.path]
        target_paths = {str(device.path) for device in targets}
        for stale_path in [path for path in self._devices if path not in target_paths]:
            self._close_path(stale_path)
        if target_paths and target_paths.issubset(set(self._devices)):
            return True
        try:
            import hid  # type: ignore
        except ImportError:
            return False
        for device in targets:
            path = str(device.path)
            if path in self._devices:
                continue
            try:
                handle = hid.device()
                handle.open_path(device.path.encode() if isinstance(device.path, str) else device.path)
                handle.set_nonblocking(True)
            except OSError:
                continue
            self._devices[path] = handle
        return bool(self._devices)

    def read_dpi_delta(self) -> int:
        event = self.read_dpi_event()
        return event if isinstance(event, int) else 0

    def read_dpi_event(self) -> int | str:
        if not self._devices:
            return 0
        event: int | str = 0
        for report in self.read_reports(limit_per_device=8):
            parsed = self._parse_report(report)
            if parsed:
                event = parsed
        return event

    def read_reports(self, limit_per_device: int = 8) -> list[bytes]:
        reports: list[bytes] = []
        if not self._devices:
            return reports
        for path, device in list(self._devices.items()):
            for _ in range(limit_per_device):
                try:
                    report = bytes(device.read(64))
                except OSError:
                    self._close_path(path)
                    break
                if not report:
                    break
                reports.append(report)
        return reports

    def parse_report_delta(self, report: bytes) -> int:
        parsed = self._parse_report(report)
        return parsed if isinstance(parsed, int) else 0

    def parse_report_event(self, report: bytes) -> int | str:
        return self._parse_report(report)

    def close(self) -> None:
        for path in list(self._devices):
            self._close_path(path)
        self._last_event = None

    @property
    def open_count(self) -> int:
        return len(self._devices)

    def _close_path(self, path: str) -> None:
        device = self._devices.pop(path, None)
        if device is not None:
            try:
                device.close()
            except Exception:
                pass

    def _parse_report(self, report: bytes) -> int | str:
        payload = report
        if len(payload) >= 6 and payload[0] == 0x00 and payload[1:4] == b"\x03\x00\x01":
            payload = payload[1:]
        if len(payload) >= 2 and payload[0] == 0x03 and payload[1] in {self.DPI_DOWN_BUTTON_MASK, self.DPI_UP_BUTTON_MASK, self.SNIPER_BUTTON_MASK}:
            return self._dedupe_button_report(payload[1])
        if len(payload) >= 2 and payload[0] == 0x03 and payload[1] == 0x00:
            if self._last_event and self._last_event[0] == self.SNIPER_BUTTON_MASK:
                self._last_event = None
                return "sniper_release"
        if len(payload) < 5 or payload[0:3] != b"\x03\x00\x01":
            return 0
        code = payload[3]
        if code == self.SNIPER_REPORT:
            return self._dedupe_button_report(self.SNIPER_BUTTON_MASK)
        if code not in {self.DPI_DOWN_REPORT, self.DPI_UP_REPORT}:
            return 0
        now = time.monotonic()
        if self._last_event and self._last_event[0] == code and now - self._last_event[1] < 0.18:
            return 0
        self._last_event = (code, now)
        return 1 if code == self.DPI_UP_REPORT else -1

    def _dedupe_button_report(self, code: int) -> int | str:
        now = time.monotonic()
        if self._last_event and self._last_event[0] == code and now - self._last_event[1] < 0.18:
            return 0
        self._last_event = (code, now)
        if code == self.SNIPER_BUTTON_MASK:
            return "sniper"
        return -1 if code == self.DPI_UP_BUTTON_MASK else 1
