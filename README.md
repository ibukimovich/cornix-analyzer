# Cornix Analyzer

Typing error analysis and keymap suggestion tool for **Cornix LP** column-staggered split keyboard.

Records keystrokes on macOS, detects correction patterns (Backspace → retype), and suggests keymap swaps to reduce errors.

## Requirements

- **macOS** (uses CGEventTap for keyboard capture)
- **Accessibility / Input Monitoring** permission (required once for `record` command)
- Python 3.9+

## Installation

```bash
pip install cornix-analyzer
```

Or from source:

```bash
git clone https://github.com/ibuki/cornix-analyzer.git
cd cornix-analyzer
pip install -e .
```

## Usage

```bash
# Step 1: Start recording keystrokes (Ctrl+C to stop)
cornix-analyzer record

# Step 2: Analyze logs and get swap suggestions
cornix-analyzer analyze --layout ~/my-keymap.vil

# Options
cornix-analyzer analyze --layout ~/my-keymap.vil --all      # All logs
cornix-analyzer analyze --layout ~/my-keymap.vil --days 14   # Last 14 days
cornix-analyzer analyze --layout ~/my-keymap.vil --dry-run   # Report only, no file output
```

## How It Works

1. **Log** — captures every keystroke via macOS CGEventTap and writes JSONL files
2. **Detect** — finds Backspace key presses followed within 100ms by a correction
3. **Analyze** — aggregates error pairs per key, finds symmetric confusion patterns
4. **Suggest** — identifies physical positions with frequent errors and proposes key swaps
5. **Output** — generates a report and a modified `.vil` file ready for VIA/VIAL

## Data Privacy

All keystroke data stays **local**. Logs are stored in `~/.hermes/scripts/cornix_analyzer/logs/`.

## License

MIT
