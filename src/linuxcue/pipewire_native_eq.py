from __future__ import annotations

import json
import re
import shutil
import subprocess

from .easyeffects_export import ICUE_EQ_FREQUENCIES
from .models import AudioPreset, Profile
from .pipewire_eq import PIPEWIRE_EQ_CONFIG, set_default_virtuoso_eq_sink, write_virtuoso_pipewire_eq


PIPEWIRE_EQ_NODE_NAMES = (
    "effect_input.linuxcue_virtuoso_eq",
    "effect_output.linuxcue_virtuoso_eq",
)


def apply_virtuoso_native_pipewire_eq(profile: Profile, preset: AudioPreset) -> dict[str, object]:
    if shutil.which("pw-cli") is None:
        raise RuntimeError("pw-cli was not found. Install PipeWire tools first.")
    config_path = write_virtuoso_pipewire_eq(profile, preset)
    node = _find_eq_node()
    if node is None:
        return {
            "ok": False,
            "config": str(config_path),
            "node": None,
            "needs_activation": True,
            "message": "linuxcue PipeWire EQ node is not running yet. Activate it once with the PipeWire EQ button.",
        }
    graph = _runtime_filter_graph(preset)
    attempts = _try_live_update_payloads(str(node["id"]), graph)
    success = next((attempt for attempt in attempts if attempt["ok"]), None)
    route_result = set_default_virtuoso_eq_sink() if success is not None else None
    enum_result = _pw_cli(["enum-params", str(node["id"]), "Props"], check=False)
    return {
        "ok": success is not None,
        "config": str(config_path),
        "node": node,
        "attempts": attempts,
        "command": success["command"] if success else attempts[-1]["command"],
        "stdout": success["stdout"] if success else attempts[-1]["stdout"],
        "stderr": "" if success else attempts[-1]["stderr"],
        "route": route_result,
        "enum_props": enum_result.stdout[-4000:],
        "message": "Native PipeWire EQ updated." if success else "PipeWire rejected live EQ parameter update.",
    }


def pipewire_native_eq_doctor() -> dict[str, object]:
    if shutil.which("pw-cli") is None:
        return {"ok": False, "error": "pw-cli was not found"}
    node = _find_eq_node()
    if node is None:
        return {"ok": False, "node": None, "config": str(PIPEWIRE_EQ_CONFIG)}
    return {
        "ok": True,
        "node": node,
        "props": _pw_cli(["enum-params", str(node["id"]), "Props"], check=False).stdout[-8000:],
        "all_params": _pw_cli(["enum-params", str(node["id"]), "all"], check=False).stdout[-8000:],
    }


def _find_eq_node() -> dict[str, object] | None:
    result = _pw_cli(["ls", "Node"], check=False)
    if result.returncode != 0:
        return None
    blocks = re.split(r"\n(?=id \d+,)", result.stdout)
    for block in blocks:
        if not any(name in block for name in PIPEWIRE_EQ_NODE_NAMES):
            continue
        match = re.search(r"id (\d+),", block)
        if not match:
            continue
        node_name = _extract_quoted_property(block, "node.name")
        description = _extract_quoted_property(block, "node.description")
        return {"id": int(match.group(1)), "node_name": node_name, "description": description}
    return None


def _runtime_filter_graph(preset: AudioPreset) -> dict[str, object]:
    filters = [
        {"type": "bq_peaking", "freq": frequency, "gain": gain, "q": 1.41}
        for frequency, gain in zip(ICUE_EQ_FREQUENCIES, _bands(preset))
    ]
    return {
        "nodes": [
            {
                "type": "builtin",
                "name": "eq",
                "label": "param_eq",
                "config": {"filters": filters},
            }
        ],
        "inputs": ["eq:In 1", "eq:In 2"],
        "outputs": ["eq:Out 1", "eq:Out 2"],
    }


def _try_live_update_payloads(node_id: str, graph: dict[str, object]) -> list[dict[str, object]]:
    payloads = [
        ("Props/filter.graph", "Props", {"filter.graph": graph}),
        ("Props/node.param.Props", "Props", {"node.param.Props": {"filter.graph": graph}}),
        ("Props/params-array", "Props", {"params": ["filter.graph", graph]}),
        ("Props/filter-graph-flat", "Props", {"filter.graph.nodes": graph["nodes"], "filter.graph.inputs": graph["inputs"], "filter.graph.outputs": graph["outputs"]}),
        ("Param/filter.graph", "Param", {"filter.graph": graph}),
    ]
    attempts: list[dict[str, object]] = []
    for label, param, payload in payloads:
        encoded = json.dumps(payload, separators=(",", ":"))
        result = _pw_cli(["set-param", node_id, param, encoded], check=False)
        attempts.append(
            {
                "label": label,
                "param": param,
                "payload": encoded,
                "command": result.args,
                "returncode": result.returncode,
                "stdout": result.stdout.strip(),
                "stderr": result.stderr.strip(),
                "ok": result.returncode == 0,
            }
        )
        if result.returncode == 0:
            break
    return attempts


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


def _extract_quoted_property(block: str, key: str) -> str:
    match = re.search(rf"{re.escape(key)}\\s*=\\s*\"([^\"]*)\"", block)
    return match.group(1) if match else ""


def _pw_cli(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["pw-cli", *args], check=False, capture_output=True, text=True, timeout=5)
    if check and result.returncode != 0:
        raise RuntimeError(f"pw-cli {' '.join(args)} failed: {result.stderr.strip()}")
    return result
