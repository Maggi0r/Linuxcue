from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


AUDIO_CONTROL_ROOT = Path.home() / ".config" / "linuxcue"
SIDETONE_STATE = AUDIO_CONTROL_ROOT / "headset-sidetone.json"


def set_headset_source_volume(percent: int, *, match_hint: str = "") -> dict[str, object]:
    if shutil.which("pactl") is None:
        raise RuntimeError("pactl was not found. Install PulseAudio/PipeWire Pulse tools first.")
    source = _best_source(match_hint)
    clamped = max(0, min(150, int(percent)))
    result = _pactl(["set-source-volume", source, f"{clamped}%"], check=False)
    return {
        "ok": result.returncode == 0,
        "source": source,
        "volume": clamped,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }


def set_headset_sidetone(percent: int, *, match_hint: str = "") -> dict[str, object]:
    if shutil.which("pactl") is None:
        raise RuntimeError("pactl was not found. Install PulseAudio/PipeWire Pulse tools first.")
    _unload_previous_sidetone()
    clamped = max(0, min(100, int(percent)))
    if clamped == 0:
        return {"ok": True, "enabled": False, "volume": 0, "module_id": None}

    source = _best_source(match_hint)
    sink = _default_sink()
    result = _pactl(
        [
            "load-module",
            "module-loopback",
            f"source={source}",
            f"sink={sink}",
            "latency_msec=18",
        ],
        check=False,
    )
    module_id = result.stdout.strip()
    ok = result.returncode == 0 and module_id.isdigit()
    if ok:
        _write_sidetone_state(int(module_id), source, sink, clamped)
    return {
        "ok": ok,
        "enabled": ok,
        "volume": clamped,
        "module_id": int(module_id) if module_id.isdigit() else None,
        "source": source,
        "sink": sink,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
        "note": "Sidetone uses a local PipeWire/Pulse loopback. The slider stores the desired level; PipeWire controls the exact loopback gain.",
    }


def _best_source(match_hint: str) -> str:
    sources = _source_names()
    hint_tokens = [token for token in match_hint.casefold().replace("-", " ").split() if token]
    for source in sources:
        lowered = source.casefold()
        if lowered.endswith(".monitor"):
            continue
        if hint_tokens and any(token in lowered for token in hint_tokens):
            return source
        if any(token in lowered for token in ("void", "virtuoso", "corsair")):
            return source
    default = _pactl(["get-default-source"], check=False).stdout.strip()
    if default:
        return default
    for source in sources:
        if not source.casefold().endswith(".monitor"):
            return source
    raise RuntimeError("No usable microphone source was found.")


def _source_names() -> list[str]:
    result = _pactl(["list", "short", "sources"], check=False)
    sources: list[str] = []
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) > 1:
            sources.append(parts[1])
    return sources


def _default_sink() -> str:
    sink = _pactl(["get-default-sink"], check=False).stdout.strip()
    if sink:
        return sink
    result = _pactl(["list", "short", "sinks"], check=False)
    for line in result.stdout.splitlines():
        parts = line.split()
        if len(parts) > 1:
            return parts[1]
    raise RuntimeError("No audio output sink was found for sidetone.")


def _unload_previous_sidetone() -> None:
    try:
        payload = json.loads(SIDETONE_STATE.read_text(encoding="utf-8"))
        module_id = int(payload.get("module_id"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return
    _pactl(["unload-module", str(module_id)], check=False)
    try:
        SIDETONE_STATE.unlink()
    except OSError:
        pass


def _write_sidetone_state(module_id: int, source: str, sink: str, volume: int) -> None:
    AUDIO_CONTROL_ROOT.mkdir(parents=True, exist_ok=True)
    SIDETONE_STATE.write_text(
        json.dumps(
            {
                "module_id": module_id,
                "source": source,
                "sink": sink,
                "volume": volume,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _pactl(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["pactl", *args], check=False, capture_output=True, text=True, timeout=5)
    if check and result.returncode != 0:
        raise RuntimeError(f"pactl {' '.join(args)} failed: {result.stderr.strip()}")
    return result
