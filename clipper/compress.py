"""Core video compression functionality"""

import subprocess
import json
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Preset:
    """Compression preset configuration"""
    name: str
    scale: float
    crf: int
    audio_bitrate: str
    description: str


# Quality presets - detected from filename suffix (e.g., "video-social.mp4")
PRESETS: dict[str, Preset] = {
    "social": Preset(
        name="social",
        scale=0.5,
        crf=28,
        audio_bitrate="128k",
        description="50% · sharing",
    ),
    "web": Preset(
        name="web",
        scale=0.75,
        crf=23,
        audio_bitrate="192k",
        description="75% · balanced",
    ),
    "archive": Preset(
        name="archive",
        scale=1.0,
        crf=18,
        audio_bitrate="256k",
        description="100% · high quality",
    ),
    "tiny": Preset(
        name="tiny",
        scale=0.25,
        crf=32,
        audio_bitrate="96k",
        description="25% · preview",
    ),
}

DEFAULT_PRESET = PRESETS["social"]


def detect_preset_from_filename(path: Path) -> Preset | None:
    """
    Detect preset from filename suffix.
    e.g., "vacation-social.mp4" -> social preset
    """
    stem = path.stem.lower()
    for preset_name in PRESETS:
        if stem.endswith(f"-{preset_name}"):
            return PRESETS[preset_name]
    return None


def get_output_name(input_path: Path, preset: Preset) -> Path:
    """Generate output filename based on input and preset"""
    stem = input_path.stem
    # Remove preset suffix if present to avoid duplication
    for preset_name in PRESETS:
        if stem.lower().endswith(f"-{preset_name}"):
            stem = stem[: -(len(preset_name) + 1)]
            break
    return input_path.parent / f"{stem}-{preset.name}-out.mp4"


@dataclass
class VideoInfo:
    path: Path
    width: int
    height: int
    duration: float
    bitrate: int
    codec: str
    fps: float
    size_bytes: int

    @property
    def size_mb(self) -> float:
        return self.size_bytes / (1024 * 1024)

    @property
    def dimensions(self) -> str:
        return f"{self.width}x{self.height}"


@dataclass
class CompressionResult:
    input_path: Path
    output_path: Path
    original_size: int
    compressed_size: int
    preset: Preset | None = None

    @property
    def reduction_percent(self) -> float:
        return (1 - self.compressed_size / self.original_size) * 100


def probe_video(path: Path) -> VideoInfo:
    """Get video metadata using ffprobe"""
    cmd = [
        "ffprobe", "-v", "quiet",
        "-print_format", "json",
        "-show_streams", "-show_format",
        str(path)
    ]
    # Use Popen with start_new_session to avoid signal issues in threads
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True
    )
    stdout, stderr = process.communicate(timeout=30)
    data = json.loads(stdout)

    video_stream = next(s for s in data["streams"] if s["codec_type"] == "video")

    return VideoInfo(
        path=path,
        width=video_stream["width"],
        height=video_stream["height"],
        duration=float(data["format"]["duration"]),
        bitrate=int(data["format"].get("bit_rate", 0)),
        codec=video_stream["codec_name"],
        fps=eval(video_stream.get("r_frame_rate", "30/1")),
        size_bytes=path.stat().st_size,
    )


def compress(
    input_path: Path,
    output_path: Path | None = None,
    preset: Preset | str | None = None,
    scale: float | None = None,
    crf: int | None = None,
    audio_bitrate: str | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> CompressionResult:
    """
    Compress a video file.

    Args:
        input_path: Source video file
        output_path: Destination (default: auto-generated based on preset)
        preset: Preset name or Preset object (default: auto-detect from filename, or 'social')
        scale: Scale factor override (0.5 = half dimensions)
        crf: Quality override (0-51, higher = more compression)
        audio_bitrate: Audio bitrate override
        on_progress: Callback with progress 0.0-1.0
    """
    input_path = Path(input_path)

    # Resolve preset
    if preset is None:
        preset = detect_preset_from_filename(input_path) or DEFAULT_PRESET
    elif isinstance(preset, str):
        preset = PRESETS.get(preset, DEFAULT_PRESET)

    # Allow individual overrides
    _scale = scale if scale is not None else preset.scale
    _crf = crf if crf is not None else preset.crf
    _audio_bitrate = audio_bitrate if audio_bitrate is not None else preset.audio_bitrate

    if output_path is None:
        output_path = get_output_name(input_path, preset)
    output_path = Path(output_path)

    # Get duration for progress calculation
    info = probe_video(input_path)
    duration = info.duration

    # Build ffmpeg command - ensure both dimensions are divisible by 2 for h264
    scale_filter = f"scale=trunc(iw*{_scale}/2)*2:trunc(ih*{_scale}/2)*2" if _scale != 1.0 else None

    cmd = ["ffmpeg", "-i", str(input_path)]

    if scale_filter:
        cmd.extend(["-vf", scale_filter])

    cmd.extend([
        "-c:v", "libx264",
        "-crf", str(_crf),
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", _audio_bitrate,
        "-y",
        "-progress", "pipe:1",
        str(output_path)
    ])

    # Run with progress tracking
    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
        universal_newlines=True,
        start_new_session=True,
    )

    if on_progress and process.stdout:
        import time
        last_update = 0
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line.startswith("out_time_ms="):
                try:
                    time_ms = int(line.split("=")[1])
                    prog = min(1.0, (time_ms / 1_000_000) / duration)
                    # Throttle updates to ~10fps max
                    now = time.time()
                    if now - last_update > 0.1:
                        on_progress(prog)
                        last_update = now
                except (ValueError, ZeroDivisionError):
                    pass

    process.wait()

    if process.returncode != 0:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"ffmpeg failed: {stderr}")

    return CompressionResult(
        input_path=input_path,
        output_path=output_path,
        original_size=input_path.stat().st_size,
        compressed_size=output_path.stat().st_size,
        preset=preset,
    )
