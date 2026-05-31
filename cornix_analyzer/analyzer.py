"""Typing error analysis."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
import json
from pathlib import Path


BACKSPACE_HID = 42
CORRECTION_WINDOW_MS = 100


@dataclass(frozen=True)
class Event:
    """Recorded input event."""

    ts: int
    hid: int
    type: str
    modifiers: int
    source: str | None = None


@dataclass(frozen=True)
class ErrorInstance:
    """Single correction pattern around a backspace."""

    ts: int
    error_hid: int
    corrected_hid: int


@dataclass
class KeyErrorStat:
    """Aggregate stats for one mistaken key."""

    count: int = 0
    corrected_to: dict[int, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ErrorPair:
    """Mistake pair summary."""

    from_hid: int
    to_hid: int
    count: int


@dataclass
class AnalysisResult:
    """Complete analysis output."""

    total_keypresses: int
    total_errors: int
    error_rate: float
    by_hid: dict[int, KeyErrorStat]
    pairs: list[ErrorPair]
    errors: list[ErrorInstance]
    source_files: list[str]
    period_start: date | None
    period_end: date | None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation."""

        return {
            "total_keypresses": self.total_keypresses,
            "total_errors": self.total_errors,
            "error_rate": self.error_rate,
            "by_hid": {
                hid: asdict(stat) for hid, stat in sorted(self.by_hid.items())
            },
            "pairs": [asdict(pair) for pair in self.pairs],
            "errors": [asdict(error) for error in self.errors],
            "source_files": self.source_files,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }


def load_events(log_dir: str | Path, days: int | None = None, include_all: bool = False) -> list[Event]:
    """Load recorded events from JSONL files."""

    root = Path(log_dir).expanduser()
    files = _select_log_files(root, days, include_all)
    events: list[Event] = []
    for path in files:
        events.extend(_load_one_file(path))
    return sorted(events, key=lambda item: item.ts)


def analyze_events(events: list[Event], source_files: list[str] | None = None) -> AnalysisResult:
    """Analyze a stream of events."""

    keydowns = [event for event in events if event.type == "down"]
    errors = _detect_errors(keydowns)
    by_hid: dict[int, KeyErrorStat] = {}
    for error in errors:
        stat = by_hid.setdefault(error.error_hid, KeyErrorStat())
        stat.count += 1
        stat.corrected_to[error.corrected_hid] = stat.corrected_to.get(error.corrected_hid, 0) + 1
    pairs = _build_pairs(by_hid)
    period_start, period_end = _period_bounds(events)
    total_keypresses = len(keydowns)
    total_errors = len(errors)
    error_rate = total_errors / total_keypresses if total_keypresses else 0.0
    return AnalysisResult(
        total_keypresses=total_keypresses,
        total_errors=total_errors,
        error_rate=error_rate,
        by_hid=by_hid,
        pairs=pairs,
        errors=errors,
        source_files=source_files or sorted({event.source for event in events if event.source}),
        period_start=period_start,
        period_end=period_end,
    )


def _select_log_files(root: Path, days: int | None, include_all: bool) -> list[Path]:
    """Select JSONL files from the log directory."""

    if not root.exists():
        return []
    files = sorted(root.glob("*.jsonl"))
    if include_all or days is None:
        return files
    cutoff = date.today() - timedelta(days=max(days - 1, 0))
    return [path for path in files if _date_from_name(path) and _date_from_name(path) >= cutoff]


def _load_one_file(path: Path) -> list[Event]:
    """Read one JSONL log file, skipping invalid lines."""

    items: list[Event] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            items.append(
                Event(
                    ts=int(payload["ts"]),
                    hid=int(payload["hid"]),
                    type=str(payload["type"]),
                    modifiers=int(payload.get("modifiers", 0)),
                    source=path.name,
                )
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            continue
    return items


def _detect_errors(keydowns: list[Event]) -> list[ErrorInstance]:
    """Find backspace correction patterns."""

    errors: list[ErrorInstance] = []
    for index, event in enumerate(keydowns):
        if event.hid != BACKSPACE_HID:
            continue
        if index == 0 or index + 1 >= len(keydowns):
            continue
        previous_event = keydowns[index - 1]
        next_event = keydowns[index + 1]
        if previous_event.hid == BACKSPACE_HID or next_event.hid == BACKSPACE_HID:
            continue
        if event.ts - previous_event.ts > CORRECTION_WINDOW_MS:
            continue
        if next_event.ts - event.ts > CORRECTION_WINDOW_MS:
            continue
        errors.append(
            ErrorInstance(
                ts=event.ts,
                error_hid=previous_event.hid,
                corrected_hid=next_event.hid,
            )
        )
    return errors


def _build_pairs(by_hid: dict[int, KeyErrorStat]) -> list[ErrorPair]:
    """Flatten key correction stats."""

    pairs: list[ErrorPair] = []
    for error_hid, stat in by_hid.items():
        for corrected_hid, count in stat.corrected_to.items():
            pairs.append(ErrorPair(error_hid, corrected_hid, count))
    return sorted(pairs, key=lambda item: (-item.count, item.from_hid, item.to_hid))


def _period_bounds(events: list[Event]) -> tuple[date | None, date | None]:
    """Determine analysis period."""

    if not events:
        return None, None
    start = datetime.fromtimestamp(events[0].ts / 1000).date()
    end = datetime.fromtimestamp(events[-1].ts / 1000).date()
    return start, end


def _date_from_name(path: Path) -> date | None:
    """Parse YYYY-MM-DD from a log filename."""

    try:
        return date.fromisoformat(path.stem)
    except ValueError:
        return None

