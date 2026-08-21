from __future__ import annotations

import json
from pathlib import Path

from .models import ProbeData


class ProbeStore:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or (Path.cwd() / "fixtures")
        self.root.mkdir(parents=True, exist_ok=True)

    def probe_path(self, slug: str) -> Path:
        return self.root / f"{slug}.json"

    def save(self, probe: ProbeData) -> Path:
        path = self.probe_path(probe.slug)
        path.write_text(json.dumps(probe.to_dict(), indent=2) + "\n", encoding="utf-8")
        return path

    def load(self, slug: str) -> ProbeData | None:
        path = self.probe_path(slug)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ProbeData(**payload)

    def list_probes(self) -> list[str]:
        return sorted(path.stem for path in self.root.glob("*.json"))
