from __future__ import annotations

import json
import re
from pathlib import Path

from .models import AudioPreset, Profile

ICUE_EQ_FREQUENCIES = [31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]


def export_virtuoso_easyeffects_presets(profile: Profile, root: Path | None = None) -> list[Path]:
    target_root = root or Path.home() / ".config" / "easyeffects" / "output"
    target_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for preset in profile.audio:
        path = target_root / f"{preset_export_name(profile, preset)}.json"
        path.write_text(json.dumps(_preset_payload(preset), indent=2), encoding="utf-8")
        written.append(path)
    return written


def preset_export_name(profile: Profile, preset: AudioPreset) -> str:
    return f"linuxcue-{_safe_name(profile.name)}-{_safe_name(preset.name)}"


def _preset_payload(preset: AudioPreset) -> dict[str, object]:
    bands = _bands(preset)
    left = _equalizer_bands(bands)
    equalizer = {
        "balance": 0.0,
        "bypass": False,
        "input-gain": -3.0,
        "left": left,
        "right": left,
        "mode": "IIR",
        "num-bands": 10,
        "output-gain": 0.0,
        "pitch-left": 0.0,
        "pitch-right": 0.0,
        "split-channels": False,
    }
    return {
        "output": {
            "blocklist": [],
            "equalizer#0": equalizer,
            "equalizer": equalizer,
            "plugins_order": ["equalizer#0"],
        },
    }


def _equalizer_bands(values: list[int]) -> dict[str, dict[str, object]]:
    bands: dict[str, dict[str, object]] = {}
    for index, (frequency, gain) in enumerate(zip(ICUE_EQ_FREQUENCIES, values)):
        bands[f"band{index}"] = {
            "frequency": frequency,
            "gain": float(gain),
            "mode": "APO (DR)",
            "mute": False,
            "q": 1.41,
            "slope": "x1",
            "solo": False,
            "type": "Bell",
        }
    return bands


def _bands(preset: AudioPreset) -> list[int]:
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


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return normalized.strip("-") or "preset"
