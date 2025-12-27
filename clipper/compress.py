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

# Special output formats (not regular presets)
SPECIAL_FORMATS = {"gif", "loop"}

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


def detect_special_format(path: Path) -> str | None:
    """
    Detect special format from filename suffix.
    e.g., "video-gif.mp4" -> "gif", "video-loop.mp4" -> "loop"
    """
    stem = path.stem.lower()
    for fmt in SPECIAL_FORMATS:
        if stem.endswith(f"-{fmt}") or f"-{fmt}-" in stem:
            return fmt
    return None


def parse_time(time_str: str | None) -> float | None:
    """
    Parse time string into seconds.
    Supports: "5" (seconds), "5s", "1:30" (mm:ss), "1:30:00" (hh:mm:ss)
    """
    if time_str is None or time_str.strip() == "":
        return None

    time_str = time_str.strip().lower()

    # Remove 's' suffix if present
    if time_str.endswith("s"):
        time_str = time_str[:-1]

    # Handle mm:ss or hh:mm:ss format
    if ":" in time_str:
        parts = time_str.split(":")
        if len(parts) == 2:
            mins, secs = parts
            return float(mins) * 60 + float(secs)
        elif len(parts) == 3:
            hrs, mins, secs = parts
            return float(hrs) * 3600 + float(mins) * 60 + float(secs)

    # Plain number (seconds)
    return float(time_str)


def parse_trim_from_filename(path: Path) -> tuple[str | None, float | None, float | None]:
    """
    Parse special format and trim points from filename.
    e.g., "video-gif-5s-10s.mp4" -> ("gif", 5.0, 10.0)
          "video-loop-0-3.mp4" -> ("loop", 0.0, 3.0)
          "video-gif-5s.mp4" -> ("gif", 5.0, None)  # start only
    """
    stem = path.stem.lower()

    for fmt in SPECIAL_FORMATS:
        # Match patterns like -gif-5s-10s, -gif-5-10, -gif-5s, -loop-0-3
        import re
        # Pattern: -format-start-end or -format-start
        pattern = rf"-{fmt}-(\d+(?:\.\d+)?s?)-(\d+(?:\.\d+)?s?)"
        match = re.search(pattern, stem)
        if match:
            start = parse_time(match.group(1))
            end = parse_time(match.group(2))
            return fmt, start, end

        # Pattern: -format-start (no end)
        pattern = rf"-{fmt}-(\d+(?:\.\d+)?s?)(?:$|[^0-9])"
        match = re.search(pattern, stem)
        if match:
            start = parse_time(match.group(1))
            return fmt, start, None

        # Just -format with no times
        if stem.endswith(f"-{fmt}"):
            return fmt, None, None

    return None, None, None


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
        "-pix_fmt", "yuv420p",  # Ensure compatibility with all players
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


def convert_to_gif(
    input_path: Path,
    output_path: Path | None = None,
    fps: int = 15,
    width: int = 480,
    start: float | None = None,
    end: float | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> CompressionResult:
    """
    Convert video to high-quality GIF using palette generation.

    Args:
        input_path: Source video file
        output_path: Destination (default: same name with .gif)
        fps: Frame rate (default: 15)
        width: Output width, height auto-scaled (default: 480)
        start: Start time in seconds (default: beginning)
        end: End time in seconds (default: end of video)
        on_progress: Callback with progress 0.0-1.0
    """
    input_path = Path(input_path)

    if output_path is None:
        stem = input_path.stem
        # Remove -gif suffix and any time markers
        import re
        stem = re.sub(r'-gif(-\d+s?(-\d+s?)?)?$', '', stem, flags=re.IGNORECASE)
        output_path = input_path.parent / f"{stem}.gif"
    output_path = Path(output_path)

    info = probe_video(input_path)

    # Calculate effective duration for progress tracking
    effective_start = start or 0
    effective_end = end or info.duration
    effective_duration = effective_end - effective_start

    # Two-pass GIF: generate palette, then use it
    palette_path = output_path.parent / f".{output_path.stem}_palette.png"

    filters = f"fps={fps},scale={width}:-1:flags=lanczos"

    # Build seek/trim args
    seek_args = []
    if start is not None:
        seek_args.extend(["-ss", str(start)])
    trim_args = []
    if end is not None:
        if start is not None:
            # Use duration (-t) when we have a start time
            trim_args.extend(["-t", str(end - start)])
        else:
            # Use end time (-to) when no start time
            trim_args.extend(["-to", str(end)])

    # Pass 1: Generate palette
    cmd1 = ["ffmpeg"]
    cmd1.extend(seek_args)
    cmd1.extend(["-i", str(input_path)])
    cmd1.extend(trim_args)
    cmd1.extend(["-vf", f"{filters},palettegen=stats_mode=diff", "-y", str(palette_path)])

    subprocess.run(cmd1, capture_output=True, check=True)

    if on_progress:
        on_progress(0.3)

    # Pass 2: Create GIF with palette
    cmd2 = ["ffmpeg"]
    cmd2.extend(seek_args)
    cmd2.extend(["-i", str(input_path), "-i", str(palette_path)])
    cmd2.extend(trim_args)
    cmd2.extend([
        "-filter_complex", f"{filters}[x];[x][1:v]paletteuse=dither=bayer:bayer_scale=5",
        "-y", "-progress", "pipe:1",
        str(output_path)
    ])

    process = subprocess.Popen(
        cmd2,
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
                    # Scale progress from 0.3 to 1.0 for pass 2
                    prog = 0.3 + 0.7 * min(1.0, (time_ms / 1_000_000) / effective_duration)
                    now = time.time()
                    if now - last_update > 0.1:
                        on_progress(prog)
                        last_update = now
                except (ValueError, ZeroDivisionError):
                    pass

    process.wait()

    # Cleanup palette
    palette_path.unlink(missing_ok=True)

    if process.returncode != 0:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"ffmpeg failed: {stderr}")

    # Create a dummy preset for result
    gif_preset = Preset("gif", 1.0, 0, "", "animated GIF")

    return CompressionResult(
        input_path=input_path,
        output_path=output_path,
        original_size=input_path.stat().st_size,
        compressed_size=output_path.stat().st_size,
        preset=gif_preset,
    )


def convert_to_loop(
    input_path: Path,
    output_path: Path | None = None,
    scale: float = 0.5,
    start: float | None = None,
    end: float | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> CompressionResult:
    """
    Convert video to silent looping video for iMessage.

    Creates a compact, silent h264 video optimized for messaging apps.

    Args:
        input_path: Source video file
        output_path: Destination (default: same name with -loop.mp4)
        scale: Scale factor (default: 0.5)
        start: Start time in seconds (default: beginning)
        end: End time in seconds (default: end of video)
        on_progress: Callback with progress 0.0-1.0
    """
    input_path = Path(input_path)

    if output_path is None:
        stem = input_path.stem
        # Remove -loop suffix and any time markers
        import re
        stem = re.sub(r'-loop(-\d+s?(-\d+s?)?)?$', '', stem, flags=re.IGNORECASE)
        output_path = input_path.parent / f"{stem}-loop.mp4"
    output_path = Path(output_path)

    info = probe_video(input_path)

    # Calculate effective duration for progress tracking
    effective_start = start or 0
    effective_end = end or info.duration
    effective_duration = effective_end - effective_start

    # Build filter for scaling (ensure dimensions divisible by 2)
    scale_filter = f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"

    # Build seek/trim args
    seek_args = []
    if start is not None:
        seek_args.extend(["-ss", str(start)])
    trim_args = []
    if end is not None:
        if start is not None:
            trim_args.extend(["-t", str(end - start)])
        else:
            trim_args.extend(["-to", str(end)])

    cmd = ["ffmpeg"]
    cmd.extend(seek_args)
    cmd.extend(["-i", str(input_path)])
    cmd.extend(trim_args)
    cmd.extend([
        "-vf", scale_filter,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",  # Ensure compatibility with all players
        "-crf", "23",
        "-preset", "medium",
        "-an",  # No audio for loops
        "-movflags", "+faststart",  # Optimize for streaming
        "-y", "-progress", "pipe:1",
        str(output_path)
    ])

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
                    prog = min(1.0, (time_ms / 1_000_000) / effective_duration)
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

    # Create a dummy preset for result
    loop_preset = Preset("loop", scale, 23, "", "iMessage loop")

    return CompressionResult(
        input_path=input_path,
        output_path=output_path,
        original_size=input_path.stat().st_size,
        compressed_size=output_path.stat().st_size,
        preset=loop_preset,
    )
