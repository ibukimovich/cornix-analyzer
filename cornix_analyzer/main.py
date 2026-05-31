#!/usr/bin/env python3
"""CLI entry point for the Cornix analyzer."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""

    parser = argparse.ArgumentParser(prog="cornix-analyzer")
    subparsers = parser.add_subparsers(dest="command", required=True)

    record_parser = subparsers.add_parser("record", help="Record keyboard events")
    record_parser.add_argument("--log-dir", type=Path, default=None, help="Directory for JSONL logs")
    record_parser.set_defaults(handler=_handle_record)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze recorded logs")
    analyze_parser.add_argument("--log-dir", type=Path, default=None, help="Directory for JSONL logs")
    analyze_parser.add_argument("--layout", type=Path, default=Path("0521.vil"), help="Input VIAL layout")
    analyze_parser.add_argument("--days", type=int, default=7, help="Number of recent days to analyze")
    analyze_parser.add_argument("--all", action="store_true", help="Analyze all log files")
    analyze_parser.add_argument("--dry-run", action="store_true", help="Skip writing the suggested layout")
    analyze_parser.add_argument("--report-json", action="store_true", help="Also print JSON analysis")
    analyze_parser.add_argument("--output", type=Path, default=None, help="Suggested VIAL output path")
    analyze_parser.set_defaults(handler=_handle_analyze)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the CLI."""

    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.handler(args))


def _handle_record(args: argparse.Namespace) -> int:
    """Execute the record subcommand."""

    from .logger import CornixLogger, PermissionError, default_log_dir

    logger = CornixLogger(args.log_dir or default_log_dir())
    try:
        logger.run()
    except PermissionError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


def _handle_analyze(args: argparse.Namespace) -> int:
    """Execute the analyze subcommand."""

    from .analyzer import analyze_events, load_events
    from .layout_reader import load_layout
    from .logger import default_log_dir
    from .reporter import default_suggested_path, generate_report, suggest_swaps, write_suggested_layout

    log_dir = args.log_dir or default_log_dir()
    events = load_events(log_dir, days=args.days, include_all=args.all)
    layout = load_layout(args.layout)
    result = analyze_events(events)
    print(generate_report(result, layout))
    if args.report_json:
        print("")
        print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    suggestions = suggest_swaps(result, layout)
    if args.dry_run:
        return 0
    output = args.output or default_suggested_path(args.layout)
    write_suggested_layout(layout, suggestions, output)
    print(f"\nSuggested layout written to {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
