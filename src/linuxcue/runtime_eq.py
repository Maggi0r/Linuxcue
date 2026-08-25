from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from .easyeffects_export import ICUE_EQ_FREQUENCIES
from .models import AudioPreset, Profile

RUNTIME_EQ_ROOT = Path.home() / ".config" / "linuxcue"
RUNTIME_EQ_STATE = RUNTIME_EQ_ROOT / "virtuoso-live-eq.json"
RUNTIME_EQ_PID = RUNTIME_EQ_ROOT / "virtuoso-live-eq.pid"
RUNTIME_EQ_LOG = Path("/tmp/linuxcue-virtuoso-live-eq.log")
RUNTIME_EQ_SINK = "linuxcue_virtuoso_eq"
RUNTIME_EQ_MONITOR = f"{RUNTIME_EQ_SINK}.monitor"
RUNTIME_EQ_DESCRIPTION = "linuxcue Virtuoso EQ"


def write_virtuoso_runtime_eq_state(profile: Profile, preset: AudioPreset, target_sink: str | None = None) -> Path:
    RUNTIME_EQ_ROOT.mkdir(parents=True, exist_ok=True)
    payload = {
        "profile": profile.name,
        "preset": preset.name,
        "bands": _bands(preset),
        "frequencies": ICUE_EQ_FREQUENCIES,
        "target_sink": target_sink or _current_target_sink(),
        "sample_rate": 48000,
        "q": 1.41,
    }
    RUNTIME_EQ_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return RUNTIME_EQ_STATE


def virtuoso_runtime_eq_running() -> bool:
    return _helper_running()


def start_virtuoso_runtime_eq(profile: Profile, preset: AudioPreset) -> dict[str, object]:
    _ensure_virtual_sink()
    target_sink = _current_target_sink()
    state_path = write_virtuoso_runtime_eq_state(profile, preset, target_sink)
    if _helper_running():
        route = _set_default_sink(RUNTIME_EQ_SINK)
        return {
            "started": False,
            "running": True,
            "state": str(state_path),
            "target_sink": target_sink,
            "route": route,
            "pid": _read_pid(),
        }

    route = _set_default_sink(RUNTIME_EQ_SINK)
    moved_inputs = _move_current_sink_inputs()
    command = [
        sys.executable,
        "-m",
        "linuxcue.runtime_eq_helper",
        "--state",
        str(state_path),
        "--source",
        RUNTIME_EQ_MONITOR,
        "--target",
        target_sink,
    ]
    log = RUNTIME_EQ_LOG.open("ab")
    process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
    RUNTIME_EQ_PID.write_text(str(process.pid), encoding="utf-8")
    return {
        "started": True,
        "running": True,
        "state": str(state_path),
        "target_sink": target_sink,
        "route": route,
        "moved_inputs": moved_inputs,
        "pid": process.pid,
        "log": str(RUNTIME_EQ_LOG),
    }


def _helper_running() -> bool:
    pid = _read_pid()
    if pid is None:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _read_pid() -> int | None:
    try:
        return int(RUNTIME_EQ_PID.read_text(encoding="utf-8").strip())
    except (OSError, ValueError):
        return None


def _ensure_virtual_sink() -> None:
    sinks = _pactl(["list", "short", "sinks"]).stdout
    if RUNTIME_EQ_SINK in sinks:
        return
    _pactl(
        [
            "load-module",
            "module-null-sink",
            f"sink_name={RUNTIME_EQ_SINK}",
            "sink_properties=device.description=linuxcue Virtuoso EQ",
        ]
    )


def _current_target_sink() -> str:
    previous = _read_previous_target()
    default = _pactl(["get-default-sink"]).stdout.strip()
    if default and default != RUNTIME_EQ_SINK:
        _write_previous_target(default)
        return default
    if previous:
        return previous
    sinks = [line.split()[1] for line in _pactl(["list", "short", "sinks"]).stdout.splitlines() if len(line.split()) > 1]
    for sink in sinks:
        if sink != RUNTIME_EQ_SINK:
            _write_previous_target(sink)
            return sink
    raise RuntimeError("No real audio sink was found for the Virtuoso live EQ output.")


def _set_default_sink(sink: str) -> dict[str, object]:
    result = _pactl(["set-default-sink", sink], check=False)
    return {"ok": result.returncode == 0, "stderr": result.stderr.strip(), "sink": sink}


def _move_current_sink_inputs() -> list[dict[str, object]]:
    result = _pactl(["list", "short", "sink-inputs"], check=False)
    moved: list[dict[str, object]] = []
    if result.returncode != 0:
        return moved
    for line in result.stdout.splitlines():
        parts = line.split()
        if not parts:
            continue
        sink_input = parts[0]
        move = _pactl(["move-sink-input", sink_input, RUNTIME_EQ_SINK], check=False)
        moved.append({"sink_input": sink_input, "ok": move.returncode == 0, "stderr": move.stderr.strip()})
    return moved


def _pactl(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["pactl", *args], check=False, capture_output=True, text=True, timeout=5)
    if check and result.returncode != 0:
        raise RuntimeError(f"pactl {' '.join(args)} failed: {result.stderr.strip()}")
    return result


def _read_previous_target() -> str | None:
    try:
        payload = json.loads(RUNTIME_EQ_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    value = str(payload.get("target_sink") or "")
    return value if value and value != RUNTIME_EQ_SINK else None


def _write_previous_target(target: str) -> None:
    if not RUNTIME_EQ_STATE.exists():
        return
    try:
        payload = json.loads(RUNTIME_EQ_STATE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    payload["target_sink"] = target
    RUNTIME_EQ_STATE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _bands(preset: AudioPreset) -> list[float]:
    if preset.bands:
        values = [float(value) for value in preset.bands[:10]]
        values.extend([0.0] * (10 - len(values)))
        return values
    values = [
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
    return [float(value) for value in values]
