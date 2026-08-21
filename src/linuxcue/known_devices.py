from __future__ import annotations

from dataclasses import dataclass

from .models import DeviceSupport, ProbeData


@dataclass(frozen=True, slots=True)
class KnownDevice:
    slug: str
    family: str
    model_hint: str
    match_tokens: tuple[str, ...]
    protocol: str
    support_level: str
    next_step: str
    companion_slug: str | None
    companion_role: str | None
    capabilities: tuple[str, ...]
    default_product_id: int
    default_transport: str
    mock_notes: tuple[str, ...]

    def to_support(self) -> DeviceSupport:
        return DeviceSupport(
            family=self.family,
            model_hint=self.model_hint,
            protocol=self.protocol,
            support_level=self.support_level,
            next_step=self.next_step,
            companion_slug=self.companion_slug,
            companion_role=self.companion_role,
            capabilities=list(self.capabilities),
        )


TARGET_DEVICES: tuple[KnownDevice, ...] = (
    KnownDevice(
        slug="k95",
        family="keyboard",
        model_hint="Corsair K95 RGB Platinum",
        match_tokens=("k95", "k95 rgb platinum"),
        protocol="hid",
        support_level="descriptor-mapped",
        next_step="Capture before/after RGB writes from Windows iCUE to replace experimental command bytes with verified values.",
        companion_slug=None,
        companion_role=None,
        capabilities=("device-detection", "profile-mapping", "rgb-zones-descriptor-mapped", "macro-keys-planned"),
        default_product_id=0x1B2D,
        default_transport="hid",
        mock_notes=("Main keyboard endpoint", "Media keys and RGB controller expected over HID"),
    ),
    KnownDevice(
        slug="m65",
        family="mouse",
        model_hint="Corsair M65 Pro RGB",
        match_tokens=("m65", "m65 pro rgb"),
        protocol="hid",
        support_level="scaffolding",
        next_step="Capture HID feature reports for DPI, buttons, and RGB logo control.",
        companion_slug=None,
        companion_role=None,
        capabilities=("device-detection", "profile-mapping", "dpi-profile-mapped", "rgb-profile-mapped", "buttons-profile-mapped"),
        default_product_id=0x1B2E,
        default_transport="hid",
        mock_notes=("Primary mouse endpoint", "DPI stages and RGB logo path to be mapped"),
    ),
    KnownDevice(
        slug="virtuoso-se",
        family="headset",
        model_hint="Corsair Virtuoso SE",
        match_tokens=("virtuoso se", "virtuoso"),
        protocol="usb-audio+hid",
        support_level="descriptor-mapped",
        next_step="Capture before/after EQ, sidetone, mic, battery, and RGB changes from Windows iCUE to verify command bytes.",
        companion_slug="virtuoso-rgb-wireless-receiver",
        companion_role="wireless transport for headset mode",
        capabilities=("device-detection", "audio-standard", "eq-10-band-descriptor-mapped", "headset-controls-descriptor-mapped", "battery-read-candidate", "rgb-descriptor-mapped"),
        default_product_id=0x0A3D,
        default_transport="usb-audio+hid",
        mock_notes=("Audio playback is mostly standard USB audio", "Battery and RGB likely sit on vendor-specific HID interface"),
    ),
    KnownDevice(
        slug="virtuoso-rgb-wireless-receiver",
        family="receiver",
        model_hint="Corsair Virtuoso RGB Wireless USB Receiver",
        match_tokens=("virtuoso rgb wireless receiver", "wireless receiver", "receiver"),
        protocol="hid",
        support_level="descriptor-mapped",
        next_step="Capture receiver link/status transitions while pairing and switching USB/wireless modes.",
        companion_slug="virtuoso-se",
        companion_role="wireless receiver paired to headset",
        capabilities=("device-detection", "wireless-link-descriptor-mapped", "receiver-status-read-candidate", "pairing-planned"),
        default_product_id=0x0A46,
        default_transport="hid",
        mock_notes=("Separate wireless dongle for Virtuoso link path", "Likely carries pairing and wireless transport control reports"),
    ),
)


def support_for_product(product_name: str) -> DeviceSupport:
    name = product_name.casefold()
    for candidate in TARGET_DEVICES:
        if any(token in name for token in candidate.match_tokens):
            return candidate.to_support()

    return DeviceSupport(
        family="unknown",
        model_hint=product_name or "Unknown Corsair Device",
        protocol="unknown",
        support_level="planned",
        next_step="Collect descriptors first, then map this model into a dedicated backend.",
        capabilities=["device-detection"],
    )


def support_for_usb_product(product_id: int, product_name: str = "") -> DeviceSupport:
    for candidate in TARGET_DEVICES:
        if candidate.default_product_id == product_id:
            return candidate.to_support()
    return support_for_product(product_name)


def known_device_by_slug(slug: str) -> KnownDevice | None:
    needle = slug.casefold()
    for candidate in TARGET_DEVICES:
        if candidate.slug == needle:
            return candidate
    return None


def mock_probe_for_slug(slug: str) -> ProbeData | None:
    candidate = known_device_by_slug(slug)
    if candidate is None:
        return None
    return ProbeData(
        slug=candidate.slug,
        product_name=candidate.model_hint,
        vendor_id=0x1B1C,
        product_id=candidate.default_product_id,
        transport=candidate.default_transport,
        serial_number=f"MOCK-{candidate.slug.upper()}-001",
        interface_number=1,
        notes=list(candidate.mock_notes),
    )
