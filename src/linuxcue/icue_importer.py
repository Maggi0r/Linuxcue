from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .k95_backend import K95_LAYOUT, K95_OPENRGB_ZONE_ORDER, build_k95_default_profile
from .m65_backend import build_m65_default_profile
from .models import AudioPreset, CoolingChannel, DpiStage, HeadsetSetting, LightingZone, Profile
from .virtuoso_backend import build_virtuoso_default_profile


def import_icue_profile(path: str) -> dict[str, Any]:
    source = Path(path)
    root = ET.parse(source).getroot()
    profile_name = _profile_name(root) or source.stem
    group_name = _safe_profile_name(profile_name)
    active_eq_ids = _active_preset_ids(root)
    imported_profiles: list[Profile] = []
    colors = _extract_colors(root)

    group_profile = Profile(
        name=group_name,
        target_device="profile-set",
        target_family="bundle",
        profile_group=group_name,
        group_role="set",
        description=f"Imported iCUE profile set '{profile_name}'. Select this to switch all contained device profiles together.",
        lighting=[],
        cooling=[],
    )
    imported_profiles.append(group_profile)

    k95_lighting = _parse_k95_lighting(root, colors)
    if k95_lighting:
        profile = build_k95_default_profile(_safe_profile_name(f"{profile_name}-k95"))
        profile.profile_group = group_name
        profile.group_role = "keyboard"
        profile.description = f"Imported K95 per-key lighting from iCUE profile '{profile_name}'."
        profile.lighting = k95_lighting
        imported_profiles.append(profile)

    eq_presets = _parse_eq_presets(root, active_eq_ids)
    if eq_presets:
        profile = build_virtuoso_default_profile(_safe_profile_name(f"{profile_name}-virtuoso"))
        profile.profile_group = group_name
        profile.group_role = "headset"
        profile.description = f"Imported Virtuoso EQ/RGB/control profile from iCUE profile '{profile_name}'."
        profile.audio = eq_presets
        if colors and profile.lighting:
            profile.lighting[0].color = colors[0]
        imported_profiles.append(profile)

    dpi_stages = _parse_dpi_stages(root)
    if dpi_stages:
        profile = build_m65_default_profile(_safe_profile_name(f"{profile_name}-m65"))
        profile.profile_group = group_name
        profile.group_role = "mouse"
        profile.description = f"Imported M65 DPI/RGB profile from iCUE profile '{profile_name}'."
        profile.dpi = dpi_stages
        colors = _extract_colors(root)
        if colors:
            profile.lighting = [
                LightingZone(name="logo", color=colors[0], mode="static"),
                LightingZone(name="dpi_indicator", color=colors[1] if len(colors) > 1 else colors[0], mode="static"),
            ]
        imported_profiles.append(profile)

    return {
        "source": str(source),
        "icue_profile_name": profile_name,
        "imported_count": len(imported_profiles),
        "profile_group": group_name,
        "profiles": [profile.to_dict() for profile in imported_profiles],
        "notes": [
            "EQ and DPI values are imported from the iCUE profile XML.",
            "K95 lighting uses concrete iCUE LED layers when present and falls back to a heuristic otherwise.",
            "Imported profiles still use linuxcue's current experimental HID command bytes for live writes.",
        ],
    }


def profiles_from_icue(path: str) -> list[Profile]:
    payload = import_icue_profile(path)
    profiles = []
    for item in payload["profiles"]:
        profile = Profile(
            name=item["name"],
            target_device=item.get("target_device", "generic"),
            target_family=item.get("target_family", "generic"),
            profile_group=item.get("profile_group", ""),
            group_role=item.get("group_role", ""),
            description=item.get("description", ""),
            lighting=[LightingZone(**zone) for zone in item.get("lighting", [])],
            dpi=[DpiStage(**stage) for stage in item.get("dpi", [])],
            audio=[AudioPreset(**preset) for preset in item.get("audio", [])],
            headset=HeadsetSetting(**item.get("headset", {})),
            cooling=[CoolingChannel(**channel) for channel in item.get("cooling", [])],
        )
        profiles.append(profile)
    return profiles


def _profile_name(root: ET.Element) -> str | None:
    profile = root.find(".//profile")
    if profile is None:
        return None
    name = profile.findtext("name")
    return name.strip() if name else None


def _active_preset_ids(root: ET.Element) -> list[str]:
    ids = []
    for item in root.iter("activePresetId"):
        value = (item.text or "").strip()
        if value and value != "{00000000-0000-0000-0000-000000000000}":
            ids.append(value.casefold())
    return ids


def _parse_eq_presets(root: ET.Element, active_ids: list[str]) -> list[AudioPreset]:
    groups = []
    for group in root.findall(".//eqPresets/*"):
        value = group.find("value")
        if value is None:
            continue
        group_presets = value.findall(".//presets/*")
        if group_presets:
            groups.append(group_presets)
    if not groups:
        groups = [root.findall(".//presets/*")]

    active_set = set(active_ids)
    non_flat_active_ids = {item for item in active_set if item != "{df65cb3e-f06b-49e4-9376-adba2c0caf6e}"}
    selected_group = groups[0]
    for group in groups:
        group_ids = {(preset.findtext("id") or "").strip().casefold() for preset in group}
        if group_ids & non_flat_active_ids:
            selected_group = group
            break
    selected_ids = {(preset.findtext("id") or "").strip().casefold() for preset in selected_group}
    preferred_active_ids = non_flat_active_ids & selected_ids or active_set & selected_ids

    presets: list[AudioPreset] = []
    seen: set[str] = set()
    for preset in selected_group:
        preset_id = (preset.findtext("id") or "").strip()
        name = (preset.findtext("name") or "").strip()
        stages_node = preset.find("stages")
        if not name or stages_node is None:
            continue
        bands = [_round_band(child.text) for child in list(stages_node)[:10]]
        if len(bands) != 10:
            continue
        dedupe_key = f"{preset_id}:{name}"
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        presets.append(
            AudioPreset(
                name=name,
                bass=round(sum(bands[:3]) / 3),
                mids=round(sum(bands[3:7]) / 4),
                treble=round(sum(bands[7:]) / 3),
                active=preset_id.casefold() in preferred_active_ids,
                bands=bands,
            )
        )
    if presets and not any(preset.active for preset in presets):
        presets[0].active = True
    if sum(1 for preset in presets if preset.active) > 1:
        first_active_seen = False
        for preset in presets:
            if preset.active and not first_active_seen:
                first_active_seen = True
            elif preset.active:
                preset.active = False
    return presets


def _parse_k95_lighting(root: ET.Element, colors: list[str]) -> list[LightingZone]:
    if not _profile_mentions_k95(root) and len(colors) < 6:
        return []
    base_color = _static_lighting_color(root) or (colors[0] if colors else "#00ff00")
    all_keys = [key for key in K95_OPENRGB_ZONE_ORDER if key != "fn"]
    key_colors = {key: base_color for key in all_keys}

    concrete_colors = _concrete_k95_led_colors(root)
    if concrete_colors:
        key_colors.update(concrete_colors)
    else:
        accent_colors = _direct_lighting_colors(root)
        if len(accent_colors) >= 4:
            _apply_accents(key_colors, accent_colors)

    lighting = [
        LightingZone(name=f"key_{key}", color=color, mode="static", keys=[key])
        for key, color in key_colors.items()
    ]
    return lighting


ICUE_K95_KEY_ALIASES = {
    "escape": "esc",
    "bracketleft": "lbracket",
    "bracketright": "rbracket",
    "backslash": "backslash",
    "nonustilde": "iso_slash",
    "nonusbackslash": "iso_backslash",
    "graveaccentandtilde": "grave",
    "semicolon": "semicolon",
    "quote": "quote",
    "comma": "comma",
    "period": "period",
    "slash": "slash",
    "minus": "minus",
    "equals": "equals",
    "backspace": "backspace",
    "tab": "tab",
    "capslock": "caps",
    "enter": "enter",
    "shiftleft": "lshift",
    "shiftright": "rshift",
    "controlleft": "lctrl",
    "controlright": "rctrl",
    "metaleft": "lwin",
    "altleft": "lalt",
    "altright": "ralt",
    "contextmenu": "menu",
    "space": "space",
    "printscreen": "printscreen",
    "scrolllock": "scrolllock",
    "pause": "pause",
    "insert": "insert",
    "home": "home",
    "pageup": "pageup",
    "delete": "delete",
    "end": "end",
    "pagedown": "pagedown",
    "arrowup": "up",
    "arrowleft": "left",
    "arrowdown": "down",
    "arrowright": "right",
    "numlock": "numlock",
    "numpaddivide": "kp_slash",
    "numpadmultiply": "kp_star",
    "numpadsubtract": "kp_minus",
    "numpadadd": "kp_plus",
    "numpadenter": "kp_enter",
    "numpaddecimal": "kp_dot",
    "g3": "g1",
    "g6": "g2",
    "g9": "g3",
    "g12": "g4",
    "g15": "g5",
    "g18": "g6",
}


def _concrete_k95_led_colors(root: ET.Element) -> dict[str, str]:
    key_colors: dict[str, str] = {}
    for data in root.iter("data"):
        base = data.find("base")
        if base is None:
            continue
        if (base.findtext("option") or "").strip() != "ConcreteLeds":
            continue
        keys_node = base.find("keys")
        if keys_node is None:
            continue
        lighting = data.find("lighting")
        if lighting is None:
            continue
        color = None
        for item in lighting.iter("color"):
            color = _parse_color(item.text)
            if color:
                break
        if not color:
            continue
        for item in list(keys_node):
            normalized = _normalize_icue_k95_key(item.text)
            if normalized:
                key_colors[normalized] = color
    return key_colors


def _normalize_icue_k95_key(value: str | None) -> str | None:
    raw = (value or "").strip()
    if not raw:
        return None
    led_match = re.fullmatch(r"Led_(TopZone|GamepadZone)(\d+)", raw, flags=re.IGNORECASE)
    if led_match:
        return f"led_{led_match.group(1).casefold()}{led_match.group(2)}"
    compact = re.sub(r"[^A-Za-z0-9]", "", raw).casefold()
    if len(compact) == 1 and compact.isalpha():
        return compact
    if len(compact) == 1 and compact.isdigit():
        return compact
    if compact == "nonustilde":
        return "iso_slash"
    if re.fullmatch(r"f\d{1,2}", compact):
        return compact
    if compact.startswith("numpad") and compact[-1:].isdigit():
        return f"kp{compact[-1]}"
    return ICUE_K95_KEY_ALIASES.get(compact)


def _parse_dpi_stages(root: ET.Element) -> list[DpiStage]:
    stages: list[DpiStage] = []
    seen_names: set[str] = set()
    for entry in root.findall(".//dpiModes//settings/*"):
        key = (entry.findtext("key") or "").strip()
        data = entry.find(".//data")
        if not key or data is None:
            continue
        dpi_x = _int_text(data.findtext("dpiX"))
        dpi_y = _int_text(data.findtext("dpiY"))
        if dpi_x is None or dpi_y is None:
            continue
        enabled = (data.findtext("enabled") or "true").strip().casefold() == "true"
        if not enabled:
            continue
        name = _dpi_name(key)
        if name in seen_names:
            continue
        seen_names.add(name)
        stages.append(
            DpiStage(
                name=name,
                x=dpi_x,
                y=dpi_y,
                color=_parse_color(data.findtext("color")) or "#ffffff",
                active=len(stages) == 0 and name != "sniper",
            )
        )
    return stages[:6]


def _extract_colors(root: ET.Element) -> list[str]:
    colors: list[str] = []
    seen: set[str] = set()
    for item in root.iter("color"):
        color = _parse_color(item.text)
        if color and color not in seen:
            seen.add(color)
            colors.append(color)
    for item in root.iter("first"):
        color = _parse_int_color(item.text)
        if color and color not in seen:
            seen.add(color)
            colors.append(color)
    for item in root.iter("second"):
        color = _parse_int_color(item.text)
        if color and color not in seen:
            seen.add(color)
            colors.append(color)
    return colors


def _static_lighting_color(root: ET.Element) -> str | None:
    for lighting in root.iter("lighting"):
        if (lighting.findtext("polymorphic_name") or "").strip() != "StaticLighting":
            continue
        for item in lighting.iter("color"):
            color = _parse_color(item.text)
            if color:
                return color
    return None


def _direct_lighting_colors(root: ET.Element) -> list[str]:
    colors: list[str] = []
    seen: set[str] = set()
    for lighting in root.iter("lighting"):
        if (lighting.findtext("polymorphic_name") or "").strip():
            continue
        if (lighting.findtext("polymorphic_id") or "").strip() != "14":
            continue
        for item in lighting.iter("color"):
            color = _parse_color(item.text)
            if color and color not in seen:
                seen.add(color)
                colors.append(color)
    return colors


def _apply_accents(key_colors: dict[str, str], colors: list[str]) -> None:
    groups = [
        ["w", "a", "s", "d"],
        ["q", "e", "r", "f"],
        ["1", "2", "3", "4", "5"],
        ["lshift", "lctrl", "space"],
        ["g1", "g2", "g3", "g4", "g5", "g6"],
        ["up", "left", "down", "right"],
        ["kp7", "kp8", "kp9", "kp4", "kp5", "kp6", "kp1", "kp2", "kp3", "kp0"],
    ]
    for index, group in enumerate(groups):
        color = colors[index % len(colors)]
        for key in group:
            if key in key_colors:
                key_colors[key] = color


def _profile_mentions_k95(root: ET.Element) -> bool:
    for item in root.iter("deviceLightingType"):
        value = (item.text or "").strip().casefold()
        if value in {"platinum", "default"}:
            return True
    return False


def _round_band(value: str | None) -> int:
    try:
        return max(-12, min(12, round(float((value or "0").strip()))))
    except ValueError:
        return 0


def _int_text(value: str | None) -> int | None:
    try:
        return int(float((value or "").strip()))
    except ValueError:
        return None


def _dpi_name(value: str) -> str:
    normalized = value.strip().casefold()
    if "sniper" in normalized:
        return "sniper"
    match = re.search(r"(\d+)", value)
    return f"stage{match.group(1)}" if match else normalized.replace(" ", "_")


def _parse_color(value: str | None) -> str | None:
    if not value:
        return None
    text = value.strip()
    match = re.fullmatch(r"rgb\(([^)]+)\)", text)
    if match:
        parts = match.group(1).split()
        if len(parts) != 3:
            return None
        values = []
        for part in parts:
            number = float(part)
            values.append(round(number * 255) if number <= 1 else round(number))
        return "#{:02x}{:02x}{:02x}".format(*(max(0, min(255, item)) for item in values))
    return _parse_int_color(text)


def _parse_int_color(value: str | None) -> str | None:
    try:
        number = int(float((value or "").strip()))
    except ValueError:
        return None
    if number <= 0:
        return None
    return f"#{(number >> 16) & 0xff:02x}{(number >> 8) & 0xff:02x}{number & 0xff:02x}"


def _safe_profile_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_. -]+", "-", value).strip(" .-") or "imported-icue-profile"
