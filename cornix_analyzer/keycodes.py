"""QMK and macOS keycode helpers."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class ParsedKeycode:
    """Normalized keycode information."""

    original: str
    base_keycode: str | None
    hid_usage: int | None
    is_layer_switch: bool


LETTER_HID = {f"KC_{chr(code)}": 4 + code - 65 for code in range(65, 91)}
DIGIT_HID = {
    "KC_1": 30,
    "KC_2": 31,
    "KC_3": 32,
    "KC_4": 33,
    "KC_5": 34,
    "KC_6": 35,
    "KC_7": 36,
    "KC_8": 37,
    "KC_9": 38,
    "KC_0": 39,
}
SYMBOL_HID = {
    "KC_ENTER": 40,
    "KC_ESCAPE": 41,
    "KC_BSPACE": 42,
    "KC_TAB": 43,
    "KC_SPACE": 44,
    "KC_MINUS": 45,
    "KC_EQUAL": 46,
    "KC_LBRACKET": 47,
    "KC_RBRACKET": 48,
    "KC_BSLASH": 49,
    "KC_SCOLON": 51,
    "KC_QUOTE": 52,
    "KC_GRAVE": 53,
    "KC_COMMA": 54,
    "KC_DOT": 55,
    "KC_SLASH": 56,
    "KC_CAPSLOCK": 57,
    "KC_F10": 67,
    "KC_HOME": 74,
    "KC_DELETE": 76,
    "KC_END": 77,
    "KC_RIGHT": 79,
    "KC_LEFT": 80,
    "KC_DOWN": 81,
    "KC_UP": 82,
    "KC_KP_1": 89,
    "KC_KP_2": 90,
    "KC_KP_3": 91,
    "KC_KP_4": 92,
    "KC_KP_5": 93,
    "KC_KP_6": 94,
    "KC_KP_7": 95,
    "KC_KP_8": 96,
    "KC_KP_9": 97,
    "KC_MUTE": 127,
    "KC_VOLU": 128,
    "KC_VOLD": 129,
    "KC_LCTRL": 224,
    "KC_LSHIFT": 225,
    "KC_LALT": 226,
    "KC_LGUI": 227,
    "KC_RCTRL": 228,
    "KC_RSHIFT": 229,
    "KC_RALT": 230,
    "KC_RGUI": 231,
}
QMK_TO_HID = {**LETTER_HID, **DIGIT_HID, **SYMBOL_HID}
HID_TO_QMK = {value: key for key, value in QMK_TO_HID.items()}

MAC_VK_TO_HID = {
    0: 4,
    1: 22,
    2: 7,
    3: 9,
    4: 11,
    5: 10,
    6: 29,
    7: 27,
    8: 25,
    9: 24,
    11: 5,
    12: 20,
    13: 26,
    14: 8,
    15: 21,
    16: 23,
    17: 28,
    18: 30,
    19: 31,
    20: 32,
    21: 33,
    22: 35,
    23: 34,
    24: 46,
    25: 38,
    26: 36,
    27: 45,
    28: 37,
    29: 39,
    30: 47,
    31: 18,
    32: 19,
    33: 51,
    34: 17,
    35: 16,
    36: 40,
    37: 15,
    38: 13,
    39: 52,
    40: 12,
    41: 54,
    42: 44,
    43: 49,
    44: 14,
    45: 55,
    46: 6,
    47: 53,
    48: 43,
    49: 44,
    50: 53,
    51: 42,
    53: 41,
    115: 74,
    116: 75,
    117: 76,
    119: 77,
    123: 80,
    124: 79,
    125: 81,
    126: 82,
}

FLAG_TO_HID = {
    0x00000001: 57,
    0x00010000: 225,
    0x00020000: 226,
    0x00040000: 224,
    0x00080000: 227,
    0x00100000: 229,
    0x00200000: 230,
    0x00400000: 228,
    0x00800000: 231,
}

_FUNC_RE = re.compile(r"^(?P<name>[A-Z0-9_]+)\((?P<inner>.*)\)$")
_LAYER_PREFIXES = ("MO(", "TG(", "TO(", "TT(", "OSL(", "LT(")


def hid_to_qmk(hid_usage: int) -> str:
    """Return a readable QMK keycode for a HID usage."""

    return HID_TO_QMK.get(hid_usage, f"HID_{hid_usage}")


def parse_keycode(value: object) -> ParsedKeycode:
    """Normalize a VIAL keycode string."""

    if not isinstance(value, str):
        return ParsedKeycode(str(value), None, None, False)
    token = value.strip()
    if not token or token == "KC_NO":
        return ParsedKeycode(token, None, None, False)
    if token.startswith(_LAYER_PREFIXES):
        return ParsedKeycode(token, None, None, True)
    match = _FUNC_RE.match(token)
    if match:
        inner = _split_args(match.group("inner"))
        for candidate in inner:
            if candidate.startswith("KC_"):
                hid = QMK_TO_HID.get(candidate)
                return ParsedKeycode(token, candidate, hid, False)
        return ParsedKeycode(token, None, None, False)
    hid = QMK_TO_HID.get(token)
    return ParsedKeycode(token, token if hid is not None else None, hid, False)


def mac_virtual_keycode_to_hid(keycode: int) -> int | None:
    """Translate a macOS virtual keycode to HID usage."""

    return MAC_VK_TO_HID.get(keycode)


def changed_flag_to_hid(previous_flags: int, current_flags: int) -> int | None:
    """Find the modifier HID usage that changed between two flag states."""

    delta = previous_flags ^ current_flags
    for mask, hid in FLAG_TO_HID.items():
        if delta & mask:
            return hid
    return None


def _split_args(raw: str) -> list[str]:
    """Split function-like keycode arguments."""

    result: list[str] = []
    depth = 0
    start = 0
    for index, char in enumerate(raw):
        if char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
        elif char == "," and depth == 0:
            result.append(raw[start:index].strip())
            start = index + 1
    result.append(raw[start:].strip())
    return [item for item in result if item]

