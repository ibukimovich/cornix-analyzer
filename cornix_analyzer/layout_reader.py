"""Read and normalize VIAL layout files."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from .keycodes import ParsedKeycode, parse_keycode


@dataclass(frozen=True)
class Position:
    """Physical key position."""

    layer: int
    row: int
    col: int


@dataclass(frozen=True)
class KeyEntry:
    """Single key entry from a layout."""

    position: Position
    keycode: str | None
    parsed: ParsedKeycode | None


@dataclass
class LayoutData:
    """Normalized layout model."""

    source_path: Path
    raw: dict[str, object]
    layout: list[list[list[str | None]]]
    entries_by_hid: dict[int, list[KeyEntry]]

    def primary_entry_for_hid(self, hid_usage: int) -> KeyEntry | None:
        """Return the first layer-0 match, else any match."""

        matches = self.entries_by_hid.get(hid_usage, [])
        if not matches:
            return None
        layer_zero = [entry for entry in matches if entry.position.layer == 0]
        return layer_zero[0] if layer_zero else matches[0]


def load_layout(path: str | Path) -> LayoutData:
    """Load a VIAL layout JSON file."""

    source = Path(path).expanduser().resolve()
    raw = json.loads(source.read_text(encoding="utf-8"))
    layout = _normalize_layout(raw.get("layout", []))
    entries = _index_entries(layout)
    return LayoutData(source_path=source, raw=raw, layout=layout, entries_by_hid=entries)


def _serialize_layout(layout: list[list[list[str | None]]]) -> list[list[list[object]]]:
    """Convert None back to -1 for VIAL compatibility."""

    return [
        [[-1 if cell is None else cell for cell in row] for row in layer]
        for layer in layout
    ]


def dump_layout(layout_data: LayoutData, path: str | Path) -> None:
    """Write a VIAL layout JSON file."""

    target = Path(path).expanduser()
    payload = dict(layout_data.raw)
    payload["layout"] = _serialize_layout(layout_data.layout)
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def swap_keys(layout_data: LayoutData, first: Position, second: Position) -> LayoutData:
    """Swap two keys and rebuild indexes."""

    new_layout = [
        [[cell for cell in row] for row in layer]
        for layer in layout_data.layout
    ]
    left = new_layout[first.layer][first.row][first.col]
    right = new_layout[second.layer][second.row][second.col]
    new_layout[first.layer][first.row][first.col] = right
    new_layout[second.layer][second.row][second.col] = left
    return LayoutData(
        source_path=layout_data.source_path,
        raw=dict(layout_data.raw),
        layout=new_layout,
        entries_by_hid=_index_entries(new_layout),
    )


def _normalize_layout(raw_layout: object) -> list[list[list[str | None]]]:
    """Convert raw layout values to strings and None."""

    normalized: list[list[list[str | None]]] = []
    for layer in raw_layout if isinstance(raw_layout, list) else []:
        normalized_layer: list[list[str | None]] = []
        for row in layer if isinstance(layer, list) else []:
            normalized_row = [None if cell == -1 else str(cell) for cell in row]
            normalized_layer.append(normalized_row)
        normalized.append(normalized_layer)
    return normalized


def _index_entries(layout: list[list[list[str | None]]]) -> dict[int, list[KeyEntry]]:
    """Build HID usage to positions index."""

    entries: dict[int, list[KeyEntry]] = {}
    for layer_index, layer in enumerate(layout):
        for row_index, row in enumerate(layer):
            for col_index, keycode in enumerate(row):
                parsed = parse_keycode(keycode) if keycode else None
                if not parsed or parsed.hid_usage is None:
                    continue
                entry = KeyEntry(
                    position=Position(layer_index, row_index, col_index),
                    keycode=keycode,
                    parsed=parsed,
                )
                entries.setdefault(parsed.hid_usage, []).append(entry)
    return entries

