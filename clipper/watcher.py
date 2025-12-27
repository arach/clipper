"""Watch folder for automatic video processing"""

import time
import threading
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from .compress import (
    compress,
    convert_to_gif,
    convert_to_loop,
    probe_video,
    detect_preset_from_filename,
    detect_special_format,
    parse_trim_from_filename,
    DEFAULT_PRESET,
    VideoInfo,
    CompressionResult,
    Preset,
)


class JobStatus(Enum):
    QUEUED = "queued"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


@dataclass
class Job:
    input_path: Path
    preset: Preset
    status: JobStatus = JobStatus.QUEUED
    progress: float = 0.0
    result: CompressionResult | None = None
    error: str | None = None
    info: VideoInfo | None = None
    special_format: str | None = None  # "gif" or "loop"
    start_time: float | None = None  # Trim start in seconds
    end_time: float | None = None  # Trim end in seconds


@dataclass
class WatchFolders:
    """Folder structure for watch-based processing"""
    inbox: Path
    processing: Path
    done: Path

    @classmethod
    def create(cls, base: Path) -> "WatchFolders":
        """Create folder structure under base path"""
        folders = cls(
            inbox=base / "inbox",
            processing=base / "processing",
            done=base / "done",
        )
        folders.inbox.mkdir(parents=True, exist_ok=True)
        folders.processing.mkdir(parents=True, exist_ok=True)
        folders.done.mkdir(parents=True, exist_ok=True)
        return folders


class VideoHandler(FileSystemEventHandler):
    """Handle new video files in inbox"""

    VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".gif"}

    def __init__(
        self,
        on_new_file: Callable[[Path], None],
    ):
        self.on_new_file = on_new_file
        self._seen: set[Path] = set()

    def _is_video(self, path: Path) -> bool:
        return path.suffix.lower() in self.VIDEO_EXTENSIONS

    def _handle_file(self, path: Path):
        if not self._is_video(path):
            return
        if path in self._seen:
            return
        # Wait briefly for file to finish writing
        time.sleep(0.5)
        if path.exists():
            self._seen.add(path)
            self.on_new_file(path)

    def on_created(self, event: FileCreatedEvent):
        if not event.is_directory:
            self._handle_file(Path(event.src_path))

    def on_moved(self, event: FileMovedEvent):
        if not event.is_directory:
            self._handle_file(Path(event.dest_path))


class Watcher:
    """
    Watch inbox folder and auto-process videos.

    Uses macOS FSEvents - zero CPU when idle, instant response on file drop.
    """

    def __init__(
        self,
        folders: WatchFolders,
        on_job_added: Callable[[Job], None] | None = None,
        on_job_updated: Callable[[Job], None] | None = None,
        on_job_done: Callable[[Job], None] | None = None,
    ):
        self.folders = folders
        self.on_job_added = on_job_added
        self.on_job_updated = on_job_updated
        self.on_job_done = on_job_done

        self.jobs: list[Job] = []
        self._queue: list[Job] = []
        self._lock = threading.Lock()
        self._processing = False
        self._observer: Observer | None = None
        self._worker_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def _on_new_file(self, path: Path):
        """Called when a new video appears in inbox"""
        # Check for special format and trim points from filename
        special_format, start_time, end_time = parse_trim_from_filename(path)

        # If no special format found via parse, try simple detection
        if special_format is None:
            special_format = detect_special_format(path)

        preset = detect_preset_from_filename(path) or DEFAULT_PRESET

        try:
            info = probe_video(path)
        except Exception:
            info = None

        job = Job(
            input_path=path,
            preset=preset,
            info=info,
            special_format=special_format,
            start_time=start_time,
            end_time=end_time,
        )

        with self._lock:
            self.jobs.append(job)
            self._queue.append(job)

        if self.on_job_added:
            self.on_job_added(job)

        self._maybe_start_processing()

    def _maybe_start_processing(self):
        """Start processing thread if not already running"""
        with self._lock:
            if self._processing or not self._queue:
                return
            self._processing = True

        thread = threading.Thread(target=self._process_queue, daemon=True)
        thread.start()

    def _process_queue(self):
        """Process jobs from queue"""
        while True:
            with self._lock:
                if not self._queue or self._stop_event.is_set():
                    self._processing = False
                    return
                job = self._queue.pop(0)

            self._process_job(job)

    def _process_job(self, job: Job):
        """Process a single job"""
        job.status = JobStatus.PROCESSING
        if self.on_job_updated:
            self.on_job_updated(job)

        try:
            # Move to processing folder
            processing_path = self.folders.processing / job.input_path.name
            job.input_path.rename(processing_path)
            job.input_path = processing_path

            def on_progress(p: float):
                job.progress = p
                if self.on_job_updated:
                    self.on_job_updated(job)

            # Handle special formats (gif, loop) or regular compression
            if job.special_format == "gif":
                # Remove -gif suffix and time markers for output name
                import re
                stem = job.input_path.stem
                stem = re.sub(r'-gif(-\d+s?(-\d+s?)?)?$', '', stem, flags=re.IGNORECASE)
                output_path = self.folders.done / f"{stem}.gif"
                result = convert_to_gif(
                    job.input_path,
                    output_path=output_path,
                    start=job.start_time,
                    end=job.end_time,
                    on_progress=on_progress,
                )
            elif job.special_format == "loop":
                # Remove -loop suffix and time markers for output name
                import re
                stem = job.input_path.stem
                stem = re.sub(r'-loop(-\d+s?(-\d+s?)?)?$', '', stem, flags=re.IGNORECASE)
                output_path = self.folders.done / f"{stem}-loop.mp4"
                result = convert_to_loop(
                    job.input_path,
                    output_path=output_path,
                    start=job.start_time,
                    end=job.end_time,
                    on_progress=on_progress,
                )
            else:
                # Regular compression
                output_path = self.folders.done / f"{job.input_path.stem}-out.mp4"
                result = compress(
                    job.input_path,
                    output_path=output_path,
                    preset=job.preset,
                    on_progress=on_progress,
                )

            job.result = result
            job.status = JobStatus.DONE
            job.progress = 1.0

            # Clean up source file from processing folder
            if job.input_path.exists():
                job.input_path.unlink()

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error = str(e)

        if self.on_job_done:
            self.on_job_done(job)
        elif self.on_job_updated:
            self.on_job_updated(job)

    def scan_inbox(self):
        """Scan inbox for existing files"""
        for path in self.folders.inbox.iterdir():
            if path.suffix.lower() in VideoHandler.VIDEO_EXTENSIONS:
                self._on_new_file(path)

    def start(self):
        """Start watching inbox folder"""
        self._stop_event.clear()

        handler = VideoHandler(on_new_file=self._on_new_file)
        self._observer = Observer()
        self._observer.schedule(handler, str(self.folders.inbox), recursive=False)
        self._observer.start()

        # Process any existing files
        self.scan_inbox()

    def stop(self):
        """Stop watching"""
        self._stop_event.set()
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    @property
    def is_running(self) -> bool:
        return self._observer is not None and self._observer.is_alive()
