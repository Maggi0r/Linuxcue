from __future__ import annotations

import json
import os
from pathlib import Path

from .models import AudioPreset, CoolingChannel, DpiStage, HeadsetSetting, LightingZone, Profile


class ProfileStore:
    def __init__(self, root: Path | None = None) -> None:
        preferred_root = root or self._default_root()
        self.root = self._ensure_writable_root(preferred_root)

    def profile_path(self, name: str) -> Path:
        return self.root / f"{name}.json"

    def save(self, profile: Profile) -> Path:
        path = self.profile_path(profile.name)
        path.write_text(json.dumps(profile.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def delete(self, name: str) -> bool:
        path = self.profile_path(name)
        if not path.exists():
            return False
        try:
            path.unlink()
        except OSError:
            return False
        return True

    def rename(self, old_name: str, new_name: str) -> Path | None:
        source = self.profile_path(old_name)
        target = self.profile_path(new_name)
        if not source.exists() or target.exists():
            return None
        source.rename(target)
        return target

    def load(self, name: str) -> Profile | None:
        path = self.profile_path(name)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            return None
        lighting = [LightingZone(**zone) for zone in payload.get("lighting", []) if isinstance(zone, dict)]
        dpi = [DpiStage(**stage) for stage in payload.get("dpi", []) if isinstance(stage, dict)]
        audio = [AudioPreset(**preset) for preset in payload.get("audio", []) if isinstance(preset, dict)]
        headset_payload = payload.get("headset", {})
        headset = HeadsetSetting(**headset_payload) if isinstance(headset_payload, dict) else HeadsetSetting()
        cooling = [CoolingChannel(**channel) for channel in payload.get("cooling", []) if isinstance(channel, dict)]
        profile_name = str(payload.get("name") or path.stem)
        return Profile(
            name=profile_name,
            target_device=payload.get("target_device", "generic"),
            target_family=payload.get("target_family", "generic"),
            profile_group=payload.get("profile_group", ""),
            group_role=payload.get("group_role", ""),
            description=payload.get("description", ""),
            lighting=lighting,
            dpi=dpi,
            audio=audio,
            headset=headset,
            cooling=cooling,
            options=payload.get("options", {}),
        )

    def list_profiles(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))

    @staticmethod
    def _default_root() -> Path:
        xdg_config_home = os.getenv("XDG_CONFIG_HOME")
        if xdg_config_home:
            return Path(xdg_config_home) / "linuxcue"

        appdata = os.getenv("APPDATA")
        if appdata:
            return Path(appdata) / "linuxcue"

        return Path.home() / ".config" / "linuxcue"

    @staticmethod
    def _ensure_writable_root(path: Path) -> Path:
        try:
            path.mkdir(parents=True, exist_ok=True)
            return path
        except OSError:
            fallback = Path.cwd() / ".linuxcue"
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback
