# Cornix Analyzer

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![macOS](https://img.shields.io/badge/platform-macOS-black.svg)](https://www.apple.com/macos)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PyPI version](https://img.shields.io/badge/pypi-v0.1.0-orange.svg)](https://github.com/ibukimovich/cornix-analyzer)
[![GitHub](https://img.shields.io/badge/github-ibukimovich%2Fcornix--analyzer-181717?logo=github)](https://github.com/ibukimovich/cornix-analyzer)

> **Typing error analysis and keymap suggestion tool for Cornix LP column-staggered split keyboard.**
> Records keystrokes on macOS, detects correction patterns (Backspace → retype), and suggests keymap swaps to reduce errors.

---

## ✨ What It Does

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  1. 🎯 RECORD  ──→  Captures every keystroke via CGEventTap      │
│                     Writes JSONL logs to ~/projects/cornix-       │
│                     analyzer/logs/                                │
│                                                                  │
│  2. 🔍 ANALYZE ──→  Detects Backspace correction patterns        │
│                     (error key → Backspace → correction key)      │
│                     Aggregates by HID usage & physical position   │
│                                                                  │
│  3. 💡 SUGGEST ──→  Finds symmetric confusion pairs              │
│                     Suggests key swaps on layer 0                 │
│                     Outputs a modified .vil file for VIA/VIAL    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📋 Requirements

- **macOS** (uses CGEventTap — Accessibility / Input Monitoring permission required)
- **Cornix LP** keyboard (or any QMK/VIAL keyboard with `.vil` keymap files)
- Python 3.9+

---

## 🚀 Installation

```bash
# From GitHub (recommended)
pip install git+https://github.com/ibukimovich/cornix-analyzer.git

# Or from local source after cloning
git clone https://github.com/ibukimovich/cornix-analyzer.git
cd cornix-analyzer
pip install -e .
```

**Verify installation:**

```bash
cornix-analyzer --help
```

Expected output:

```
usage: cornix-analyzer [-h] {record,analyze} ...

positional arguments:
  {record,analyze}
    record          Record keyboard events
    analyze         Analyze recorded logs

options:
  -h, --help        show this help message and exit
```

---

## 🎬 Quick Start

### Step 1: Grant macOS permission (first time only)

```bash
cornix-analyzer record
```

If you see:

```
CGEventTapCreate failed: Grant Accessibility and Input Monitoring permission.
```

**Go to:** `System Settings → Privacy & Security → Accessibility`

Add **Terminal** (or your terminal app) to the allowed list. Then retry:

```bash
cornix-analyzer record
```

It will start silently. Type a few characters to confirm it's working, then press `Ctrl+C` to stop.

### Step 2: Collect typing data

```bash
cornix-analyzer record
```

Let it run in the background while you type normally. **Collect at least 1–3 days** of data for meaningful analysis.

To stop: press `Ctrl+C`

**Check the logs:**

```bash
ls ~/projects/cornix-analyzer/logs/
```

You should see date-stamped `.jsonl` files:

```
2026-05-31.jsonl
2026-06-01.jsonl
```

### Step 3: Run analysis

```bash
# Analyze the last 7 days (default)
cornix-analyzer analyze --layout ~/path/to/your-keymap.vil

# Analyze all collected data
cornix-analyzer analyze --layout ~/path/to/your-keymap.vil --all

# View the raw JSON data
cornix-analyzer analyze --layout ~/path/to/your-keymap.vil --report-json
```

---

## 📊 Understanding the Report

### Example output

```
=== Cornix LP Keymap Optimization Report ===
Period: 2026-05-31 to 2026-05-31
Total keypresses: 1,045
Errors: 15 (1.44%)

=== Keys With Frequent Errors ===
KC_E (layer 0, row 0, col 3): 10 errors, mostly corrected to KC_R
KC_R (layer 0, row 0, col 4): 5 errors, mostly corrected to KC_E

=== Physical Observations ===
Column 3: 10 corrected errors on the base layer.
Column 4: 5 corrected errors on the base layer.

=== Suggested Changes ===
Swap KC_E at layer 0, row 0, col 3 with KC_L at layer 0, row 5, col 2
based on 10 repeated corrections.
```

### What to look for

| Section | What it means |
|---------|---------------|
| **Keys With Frequent Errors** | Which keys you mistype most often, and what you retype them to |
| **Physical Observations** | Which physical columns on the keyboard have the most errors |
| **Suggested Changes** | Concrete key swap proposals with estimated impact |

---

## 🔧 Applying Suggestions

### Dry-run first (no file output)

```bash
cornix-analyzer analyze --layout ~/Downloads/0521.vil --dry-run
```

### Generate a modified .vil file

```bash
# Without --dry-run, it writes a _suggested.vil file
cornix-analyzer analyze --layout ~/Downloads/0521.vil
```

This creates `~/Downloads/0521_suggested.vil`.

### Load into VIA / VIAL

1. Open **VIA** or **VIAL** configurator
2. Load the `_suggested.vil` file
3. Review the proposed changes
4. Flash to your Cornix LP
5. Type for a few days to see if error rate improves

---

## 🎹 How It Analyzes Your Keyboard

### Physical layout reference (Cornix LP)

```
Left half (rows 0-3)              Right half (rows 4-7)

┌────┬────┬────┬────┬────┬────┐  ┌────┬────┬────┬────┬────┬────┐
│TAB │ Q  │ W  │ E  │ R  │ T  │  │BSP │ P  │ O  │ I  │ U  │ Y  │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│CTL │ A  │ S  │ D  │ F  │ G  │  │ENT │ \  │ L  │ K  │ J  │ H  │ BTN3
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│SFT │ Z  │ X  │ C  │ V  │ B  │MUT│ /↑ │ .  │ ,  │ M  │ N  │
├────┼────┼────┼────┼────┼────┤  ├────┼────┼────┼────┼────┼────┤
│CTL │GUI │ALT │SPC │SPC │LYR1│  │ →  │ ↓  │ ←  │TD0 │ENT │TGL2│
└────┴────┴────┴────┴────┴────┘  └────┴────┴────┴────┴────┴────┘
      Left thumb cluster               Right thumb cluster
```

### Error detection logic

```
  User types:        K  C  _E_  ←Backspace→  _R_  I  N  G
                                                   ↑
  Timestamp (ms):    0  80  160  190  220  300  380
                                         │
  Correction window: └──── 100ms ────┘
                       (error key)  (corrected key)

→ Recorded as: error_hid=8 (KC_E), corrected_hid=21 (KC_R)
```

### Data flow

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  You     │     │  Logger  │     │ Analyzer │     │ Reporter │
│  typing  │────▶│CGEventTap│────▶│  Detect  │────▶│ Generate │
│ on       │     │  →JSONL  │     │ Backspace│     │ Report + │
│Cornix LP │     │  (queue) │     │ patterns │     │  .vil    │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

---

## ⚙️ Advanced Options

### Command reference

```bash
# Record — start/stop key capture
cornix-analyzer record
cornix-analyzer record --log-dir ~/custom/log/path

# Analyze — generate reports
cornix-analyzer analyze --layout ~/keymap.vil
cornix-analyzer analyze --layout ~/keymap.vil --days 14
cornix-analyzer analyze --layout ~/keymap.vil --all
cornix-analyzer analyze --layout ~/keymap.vil --dry-run
cornix-analyzer analyze --layout ~/keymap.vil --report-json
cornix-analyzer analyze --layout ~/keymap.vil --output ~/modified.vil
```

### All flags

| Flag | Default | Description |
|------|---------|-------------|
| `--layout` | `0521.vil` | Path to your VIAL keymap `.vil` file |
| `--log-dir` | `~/projects/cornix-analyzer/logs/` | Log file directory |
| `--days` | `7` | Number of recent days to analyze |
| `--all` | `false` | Analyze all logs (ignores --days) |
| `--dry-run` | `false` | Show suggestions without writing a file |
| `--report-json` | `false` | Also print JSON-format analysis |
| `--output` | auto (`{name}_suggested.vil`) | Output path for modified .vil |

---

## 🔒 Privacy

All keystroke data stays **local on your machine**. Logs are stored in:

```
~/projects/cornix-analyzer/logs/
```

The tool never sends data anywhere. No telemetry, no analytics, no network calls.

---

## 🚧 Roadmap

- [ ] Real-time typing heatmap visualization
- [ ] Multi-keyboard support (HHKB, standard mechanical, etc.)
- [ ] Web-based dashboard for long-term tracking
- [ ] Automatic VIA/VIAL keymap flashing
- [ ] Brew formula for easy macOS installation

---

## 📄 License

MIT © ibukimovich
