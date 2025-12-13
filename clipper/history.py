"""Compression history tracking"""

import json
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List

HISTORY_FILE = Path.home() / ".config" / "clipper" / "history.json"
MAX_HISTORY = 50  # Keep last 50 compressions


@dataclass
class HistoryEntry:
    input_path: str
    output_path: str
    timestamp: str
    original_size: int
    compressed_size: int
    reduction_percent: float
    preset: str

    @property
    def output_exists(self) -> bool:
        return Path(self.output_path).exists()

    @property
    def time_ago(self) -> str:
        """Human-readable time ago"""
        dt = datetime.fromisoformat(self.timestamp)
        delta = datetime.now() - dt
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"


def load_history() -> List[HistoryEntry]:
    """Load history from file"""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE) as f:
            data = json.load(f)
        return [HistoryEntry(**entry) for entry in data]
    except (json.JSONDecodeError, TypeError, KeyError):
        return []


def save_history(history: List[HistoryEntry]) -> None:
    """Save history to file"""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w") as f:
        json.dump([asdict(e) for e in history], f, indent=2)


def add_to_history(
    input_path: Path,
    output_path: Path,
    original_size: int,
    compressed_size: int,
    reduction_percent: float,
    preset: str,
) -> None:
    """Add a compression to history"""
    history = load_history()

    entry = HistoryEntry(
        input_path=str(input_path),
        output_path=str(output_path),
        timestamp=datetime.now().isoformat(),
        original_size=original_size,
        compressed_size=compressed_size,
        reduction_percent=reduction_percent,
        preset=preset,
    )

    # Add to front, keep max entries
    history.insert(0, entry)
    history = history[:MAX_HISTORY]

    save_history(history)


def clear_history() -> None:
    """Clear all history"""
    save_history([])
