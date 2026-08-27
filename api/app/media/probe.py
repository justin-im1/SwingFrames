from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.media.ffmpeg import FfmpegError, find_binary, has_ffprobe, run_exec


@dataclass
class ProbeResult:
    width: int
    height: int
    duration_s: float
    packet_count: int
    fps: float
    rotation: float | None
    codec: str | None


def _parse_rate(value: str | None) -> float | None:
    if not value or value in {"0/0", "N/A"}:
        return None
    if "/" in value:
        num, den = value.split("/", 1)
        d = float(den)
        if d == 0:
            return None
        return float(num) / d
    try:
        return float(value)
    except ValueError:
        return None


def rotation_from_probe(data: dict) -> float | None:
    for stream in data.get("streams") or []:
        tags = stream.get("tags") or {}
        rotate = tags.get("rotate")
        if rotate not in (None, "", "0"):
            try:
                return float(rotate)
            except ValueError:
                return None
        for side in stream.get("side_data_list") or []:
            rot = side.get("rotation")
            if rot not in (None, 0, 0.0, "0"):
                try:
                    val = float(rot)
                except (TypeError, ValueError):
                    continue
                if abs(val) > 0.01:
                    return val
    return None


def parse_probe(data: dict) -> ProbeResult:
    streams = data.get("streams") or []
    if not streams:
        raise ValueError("No video stream.")
    stream = streams[0]
    fmt = data.get("format") or {}
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    duration = stream.get("duration") or fmt.get("duration")
    if duration is None:
        raise ValueError("Could not read duration.")
    duration_s = float(duration)
    packets = stream.get("nb_read_packets")
    if packets is None:
        packets = stream.get("nb_frames")
    if packets is None:
        raise ValueError("Could not count packets.")
    packet_count = int(packets)
    if duration_s <= 0 or packet_count <= 0:
        raise ValueError("Invalid duration or packet count.")
    fps = packet_count / duration_s
    return ProbeResult(
        width=width,
        height=height,
        duration_s=duration_s,
        packet_count=packet_count,
        fps=fps,
        rotation=rotation_from_probe(data),
        codec=stream.get("codec_name"),
    )


def _parse_ffmpeg_banner(stderr: str) -> tuple[int, int, float, float | None, str | None]:
    dur_m = re.search(r"Duration: (\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
    if not dur_m:
        raise ValueError("Could not read duration.")
    duration_s = (
        int(dur_m.group(1)) * 3600 + int(dur_m.group(2)) * 60 + float(dur_m.group(3))
    )
    stream_m = re.search(
        r"Video:\s*([a-zA-Z0-9_]+).*?(\d{2,5})x(\d{2,5})", stderr, re.S
    )
    if not stream_m:
        raise ValueError("No video stream.")
    codec = stream_m.group(1)
    width = int(stream_m.group(2))
    height = int(stream_m.group(3))
    rot: float | None = None
    rot_m = re.search(r"rotate\s*:\s*(-?\d+(?:\.\d+)?)", stderr)
    if rot_m:
        rot = float(rot_m.group(1))
        if abs(rot) < 0.01:
            rot = None
    disp_m = re.search(r"rotation of\s*(-?\d+(?:\.\d+)?)\s*degrees", stderr, re.I)
    if disp_m:
        val = float(disp_m.group(1))
        if abs(val) > 0.01:
            rot = val
    return width, height, duration_s, rot, codec


async def _count_packets_ffmpeg(path: Path) -> int:
    _, _, stderr = await run_exec(
        find_binary("ffmpeg"),
        "-y",
        "-i",
        str(path),
        "-map",
        "0:v:0",
        "-c",
        "copy",
        "-f",
        "null",
        "-",
        timeout=180.0,
        allow_nonzero=False,
    )
    text = stderr.decode("utf-8", errors="replace")
    matches = re.findall(r"frame=\s*(\d+)", text)
    if not matches:
        raise ValueError("Could not count packets.")
    return int(matches[-1])


async def probe_with_ffmpeg(path: Path) -> ProbeResult:
    _, _, stderr = await run_exec(
        find_binary("ffmpeg"),
        "-hide_banner",
        "-i",
        str(path),
        timeout=60.0,
        allow_nonzero=True,
    )
    text = stderr.decode("utf-8", errors="replace")
    width, height, duration_s, rotation, codec = _parse_ffmpeg_banner(text)
    packet_count = await _count_packets_ffmpeg(path)
    if duration_s <= 0 or packet_count <= 0:
        raise ValueError("Invalid duration or packet count.")
    return ProbeResult(
        width=width,
        height=height,
        duration_s=duration_s,
        packet_count=packet_count,
        fps=packet_count / duration_s,
        rotation=rotation,
        codec=codec,
    )


async def probe_file(path: Path) -> ProbeResult:
    if has_ffprobe():
        from app.media.ffmpeg import ffprobe

        stdout, _ = await ffprobe(
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-count_packets",
            "-show_entries",
            "stream=nb_read_packets,nb_frames,r_frame_rate,avg_frame_rate,duration,width,height,codec_name",
            "-show_entries",
            "stream_side_data=rotation",
            "-show_entries",
            "stream_tags=rotate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(path),
        )
        data = json.loads(stdout.decode("utf-8"))
        return parse_probe(data)
    return await probe_with_ffmpeg(path)
