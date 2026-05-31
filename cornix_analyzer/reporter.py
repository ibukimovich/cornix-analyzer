"""Report and suggestion generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .analyzer import AnalysisResult, ErrorPair, KeyErrorStat
from .keycodes import hid_to_qmk
from .layout_reader import KeyEntry, LayoutData, Position, dump_layout, swap_keys


@dataclass(frozen=True)
class SwapSuggestion:
    """Suggested swap between two positions."""

    first: Position
    second: Position
    pair: ErrorPair


def generate_report(result: AnalysisResult, layout: LayoutData) -> str:
    """Generate a human-readable report."""

    lines = ["=== Cornix LP Keymap Optimization Report ==="]
    lines.append(f"Period: {_format_period(result)}")
    lines.append(f"Total keypresses: {result.total_keypresses}")
    lines.append(f"Errors: {result.total_errors} ({result.error_rate:.2%})")
    lines.append("")
    if not result.by_hid:
        lines.append("Insufficient data: no correction patterns were detected.")
        return "\n".join(lines)
    lines.append("=== Keys With Frequent Errors ===")
    for error_hid, stat in _top_keys(result):
        lines.append(_describe_key_stat(error_hid, stat, layout))
    lines.append("")
    lines.append("=== Physical Observations ===")
    lines.extend(_build_observations(result, layout) or ["No strong physical clustering detected."])
    lines.append("")
    lines.append("=== Suggested Changes ===")
    suggestions = suggest_swaps(result, layout)
    lines.extend([_describe_swap(suggestion, layout) for suggestion in suggestions] or ["No safe swap suggestions from the current data."])
    return "\n".join(lines)


def suggest_swaps(result: AnalysisResult, layout: LayoutData, limit: int = 3) -> list[SwapSuggestion]:
    """Suggest symmetric confusion swaps on the base layer."""

    used_hids: set[int] = set()
    suggestions: list[SwapSuggestion] = []
    counts = {(pair.from_hid, pair.to_hid): pair.count for pair in result.pairs}
    for pair in result.pairs:
        reverse = counts.get((pair.to_hid, pair.from_hid), 0)
        if reverse == 0 or pair.from_hid in used_hids or pair.to_hid in used_hids:
            continue
        first = layout.primary_entry_for_hid(pair.from_hid)
        second = layout.primary_entry_for_hid(pair.to_hid)
        if not first or not second:
            continue
        if first.position.layer != 0 or second.position.layer != 0:
            continue
        suggestions.append(SwapSuggestion(first.position, second.position, pair))
        used_hids.update({pair.from_hid, pair.to_hid})
        if len(suggestions) >= limit:
            break
    return suggestions


def write_suggested_layout(
    layout: LayoutData,
    suggestions: list[SwapSuggestion],
    output_path: str | Path,
) -> Path:
    """Apply swap suggestions and write a VIAL file."""

    updated = layout
    for suggestion in suggestions:
        updated = swap_keys(updated, suggestion.first, suggestion.second)
    target = Path(output_path).expanduser()
    dump_layout(updated, target)
    return target


def default_suggested_path(layout_path: str | Path) -> Path:
    """Build a default output path for the suggested VIAL file."""

    source = Path(layout_path)
    return source.with_name(f"{source.stem}_suggested{source.suffix}")


def _format_period(result: AnalysisResult) -> str:
    """Format the analyzed period."""

    if not result.period_start or not result.period_end:
        return "unknown"
    return f"{result.period_start.isoformat()} to {result.period_end.isoformat()}"


def _top_keys(result: AnalysisResult) -> list[tuple[int, KeyErrorStat]]:
    """Sort key stats by descending count."""

    items = list(result.by_hid.items())
    return sorted(items, key=lambda item: (-item[1].count, item[0]))[:10]


def _describe_key_stat(error_hid: int, stat: KeyErrorStat, layout: LayoutData) -> str:
    """Describe an error-prone key."""

    entry = layout.primary_entry_for_hid(error_hid)
    location = _format_position(entry) if entry else "unmapped"
    top_target = max(stat.corrected_to.items(), key=lambda item: item[1])[0]
    return f"{hid_to_qmk(error_hid)} ({location}): {stat.count} errors, mostly corrected to {hid_to_qmk(top_target)}"


def _build_observations(result: AnalysisResult, layout: LayoutData) -> list[str]:
    """Generate coarse physical observations."""

    column_totals: dict[int, int] = {}
    for error_hid, stat in result.by_hid.items():
        entry = layout.primary_entry_for_hid(error_hid)
        if not entry or entry.position.layer != 0:
            continue
        column_totals[entry.position.col] = column_totals.get(entry.position.col, 0) + stat.count
    ranked = sorted(column_totals.items(), key=lambda item: (-item[1], item[0]))
    return [f"Column {column}: {count} corrected errors on the base layer." for column, count in ranked[:3]]


def _describe_swap(suggestion: SwapSuggestion, layout: LayoutData) -> str:
    """Describe a single swap suggestion."""

    first = _entry_at(layout, suggestion.first)
    second = _entry_at(layout, suggestion.second)
    return (
        f"Swap {first.keycode or 'None'} at {_format_position(first)} with "
        f"{second.keycode or 'None'} at {_format_position(second)} "
        f"based on {suggestion.pair.count} repeated corrections."
    )


def _entry_at(layout: LayoutData, position: Position) -> KeyEntry:
    """Resolve an entry by position."""

    return KeyEntry(position=position, keycode=layout.layout[position.layer][position.row][position.col], parsed=None)


def _format_position(entry: KeyEntry | None) -> str:
    """Format a physical position."""

    if entry is None:
        return "unknown"
    pos = entry.position
    return f"layer {pos.layer}, row {pos.row}, col {pos.col}"
