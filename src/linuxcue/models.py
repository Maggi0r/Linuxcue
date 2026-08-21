from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class DeviceSupport:
    family: str = "unknown"
    model_hint: str = "Unknown Corsair Device"
    protocol: str = "unknown"
    support_level: str = "planned"
    next_step: str = "Collect USB/HID report descriptors and control traces."
    companion_slug: str | None = None
    companion_role: str | None = None
    capabilities: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Device:
    vendor_id: int
    product_id: int
    product_name: str
    serial_number: str | None = None
    path: str | None = None
    interface_number: int | None = None
    transport: str = "unknown"
    support: DeviceSupport = field(default_factory=DeviceSupport)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["support"] = self.support.to_dict()
        return payload


@dataclass(slots=True)
class ProbeData:
    slug: str
    product_name: str
    vendor_id: int
    product_id: int
    transport: str
    serial_number: str | None = None
    interface_number: int | None = None
    notes: list[str] = field(default_factory=list)

    def to_device(self, support: DeviceSupport) -> Device:
        return Device(
            vendor_id=self.vendor_id,
            product_id=self.product_id,
            product_name=self.product_name,
            serial_number=self.serial_number,
            interface_number=self.interface_number,
            transport=self.transport,
            support=support,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class LightingZone:
    name: str
    color: str = "#ffffff"
    mode: str = "static"
    keys: list[str] = field(default_factory=list)


@dataclass(slots=True)
class CoolingChannel:
    name: str
    curve: list[tuple[int, int]] = field(default_factory=lambda: [(30, 25), (50, 50), (70, 100)])


@dataclass(slots=True)
class DpiStage:
    name: str
    x: int
    y: int
    color: str = "#ffffff"
    active: bool = False


@dataclass(slots=True)
class AudioPreset:
    name: str
    bass: int = 0
    mids: int = 0
    treble: int = 0
    active: bool = False
    bands: list[int] = field(default_factory=list)


@dataclass(slots=True)
class HeadsetSetting:
    sidetone: int = 0
    mic_level: int = 50
    sleep_timer_minutes: int = 15
    voice_prompt_enabled: bool = True


@dataclass(slots=True)
class Profile:
    name: str
    target_device: str = "generic"
    target_family: str = "generic"
    profile_group: str = ""
    group_role: str = ""
    description: str = ""
    lighting: list[LightingZone] = field(default_factory=lambda: [LightingZone(name="default")])
    dpi: list[DpiStage] = field(default_factory=list)
    audio: list[AudioPreset] = field(default_factory=list)
    headset: HeadsetSetting = field(default_factory=HeadsetSetting)
    cooling: list[CoolingChannel] = field(default_factory=lambda: [CoolingChannel(name="cpu")])
    options: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["target_device"] = self.target_device
        payload["target_family"] = self.target_family
        payload["profile_group"] = self.profile_group
        payload["group_role"] = self.group_role
        payload["description"] = self.description
        payload["lighting"] = [asdict(zone) for zone in self.lighting]
        payload["dpi"] = [asdict(stage) for stage in self.dpi]
        payload["audio"] = [asdict(preset) for preset in self.audio]
        payload["headset"] = asdict(self.headset)
        payload["cooling"] = [asdict(channel) for channel in self.cooling]
        payload["options"] = dict(self.options)
        return payload
