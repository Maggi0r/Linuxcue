from __future__ import annotations

import json
import re
from pathlib import Path

from .models import AudioPreset, Profile

ICUE_EQ_LEGACY_FREQUENCIES = [31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]
ICUE_EQ_FREQUENCIES = [31.0, 45.0, 63.0, 90.0, 125.0, 180.0, 250.0, 355.0, 500.0, 710.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]


def export_virtuoso_easyeffects_presets(profile: Profile, root: Path | None = None) -> list[Path]:
    target_root = root or Path.home() / ".config" / "easyeffects" / "output"
    target_root.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for preset in profile.audio:
        written.append(export_virtuoso_easyeffects_preset(profile, preset, target_root))
    return written


def export_virtuoso_easyeffects_preset(profile: Profile, preset: AudioPreset, root: Path | None = None) -> Path:
    target_root = root or Path.home() / ".config" / "easyeffects" / "output"
    target_root.mkdir(parents=True, exist_ok=True)
    path = target_root / f"{preset_export_name(profile, preset)}.json"
    path.write_text(json.dumps(_preset_payload(preset), indent=2), encoding="utf-8")
    return path


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
        "num-bands": len(ICUE_EQ_FREQUENCIES),
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
        return expand_eq_bands([int(value) for value in preset.bands])
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
    values.extend([0] * (len(ICUE_EQ_FREQUENCIES) - len(values)))
    return values[: len(ICUE_EQ_FREQUENCIES)]


def expand_eq_bands(values: list[int]) -> list[int]:
    if len(values) == len(ICUE_EQ_FREQUENCIES):
        return values[:]
    if len(values) == len(ICUE_EQ_LEGACY_FREQUENCIES):
        return [_interpolate_legacy_band(float(frequency), values) for frequency in ICUE_EQ_FREQUENCIES]
    normalised = values[: len(ICUE_EQ_FREQUENCIES)]
    normalised.extend([0] * (len(ICUE_EQ_FREQUENCIES) - len(normalised)))
    return normalised


def _interpolate_legacy_band(frequency: float, values: list[int]) -> int:
    legacy = ICUE_EQ_LEGACY_FREQUENCIES
    if frequency <= legacy[0]:
        return int(values[0])
    if frequency >= legacy[-1]:
        return int(values[-1])
    for index in range(len(legacy) - 1):
        low = legacy[index]
        high = legacy[index + 1]
        if low <= frequency <= high:
            position = (frequency - low) / (high - low)
            return round(values[index] + (values[index + 1] - values[index]) * position)
    return 0


def _safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip())
    return normalized.strip("-") or "preset"
