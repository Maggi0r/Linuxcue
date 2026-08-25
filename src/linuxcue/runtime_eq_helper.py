from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
import time
from pathlib import Path

import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser(description="linuxcue Virtuoso live EQ audio helper")
    parser.add_argument("--state", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--rate", type=int, default=48000)
    parser.add_argument("--channels", type=int, default=2)
    args = parser.parse_args()

    source = subprocess.Popen(
        ["parec", "--raw", f"--format=s16le", f"--rate={args.rate}", f"--channels={args.channels}", f"--device={args.source}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    sink = subprocess.Popen(
        ["paplay", "--raw", f"--format=s16le", f"--rate={args.rate}", f"--channels={args.channels}", f"--device={args.target}"],
        stdin=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        return _run_filter_loop(source, sink, Path(args.state), args.rate, args.channels)
    finally:
        for process in (source, sink):
            process.terminate()
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                process.kill()


def _run_filter_loop(source: subprocess.Popen[bytes], sink: subprocess.Popen[bytes], state_path: Path, sample_rate: int, channels: int) -> int:
    if source.stdout is None or sink.stdin is None:
        return 2
    chunk_frames = 1024
    chunk_bytes = chunk_frames * channels * 2
    last_mtime = 0.0
    filters = _build_filter_bank([0.0] * 10, sample_rate, channels)

    while True:
        data = source.stdout.read(chunk_bytes)
        if not data:
            return source.poll() or sink.poll() or 0
        try:
            mtime = state_path.stat().st_mtime
        except OSError:
            mtime = 0.0
        if mtime != last_mtime:
            filters = _build_filter_bank(_load_bands(state_path), sample_rate, channels)
            last_mtime = mtime

        samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size % channels != 0:
            continue
        frame = samples.reshape((-1, channels))
        for item in filters:
            frame = item.process(frame)
        output = np.clip(frame * 32767.0, -32768.0, 32767.0).astype(np.int16).tobytes()
        try:
            sink.stdin.write(output)
            sink.stdin.flush()
        except BrokenPipeError:
            return sink.poll() or 1


def _load_bands(path: Path) -> list[float]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [0.0] * 10
    bands = [float(value) for value in payload.get("bands", [])[:10]]
    bands.extend([0.0] * (10 - len(bands)))
    return bands


def _build_filter_bank(bands: list[float], sample_rate: int, channels: int) -> list["Biquad"]:
    frequencies = [31.0, 62.0, 125.0, 250.0, 500.0, 1000.0, 2000.0, 4000.0, 8000.0, 16000.0]
    return [Biquad.peaking(frequency, gain, 1.41, sample_rate, channels) for frequency, gain in zip(frequencies, bands)]


class Biquad:
    def __init__(self, b0: float, b1: float, b2: float, a1: float, a2: float, channels: int) -> None:
        self.b0 = b0
        self.b1 = b1
        self.b2 = b2
        self.a1 = a1
        self.a2 = a2
        self.z1 = np.zeros(channels, dtype=np.float32)
        self.z2 = np.zeros(channels, dtype=np.float32)

    @classmethod
    def peaking(cls, frequency: float, gain_db: float, q: float, sample_rate: int, channels: int) -> "Biquad":
        a = math.pow(10.0, gain_db / 40.0)
        omega = 2.0 * math.pi * frequency / sample_rate
        alpha = math.sin(omega) / (2.0 * q)
        cos_omega = math.cos(omega)
        b0 = 1.0 + alpha * a
        b1 = -2.0 * cos_omega
        b2 = 1.0 - alpha * a
        a0 = 1.0 + alpha / a
        a1 = -2.0 * cos_omega
        a2 = 1.0 - alpha / a
        return cls(b0 / a0, b1 / a0, b2 / a0, a1 / a0, a2 / a0, channels)

    def process(self, frame: np.ndarray) -> np.ndarray:
        output = np.empty_like(frame)
        for index in range(frame.shape[0]):
            value = frame[index]
            out = self.b0 * value + self.z1
            self.z1 = self.b1 * value - self.a1 * out + self.z2
            self.z2 = self.b2 * value - self.a2 * out
            output[index] = out
        return output


if __name__ == "__main__":
    raise SystemExit(main())
