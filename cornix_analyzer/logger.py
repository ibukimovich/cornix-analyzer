"""macOS keyboard event logger."""

from __future__ import annotations

import ctypes
import ctypes.util
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
import queue
import signal
import threading
import time
from typing import Any

from .keycodes import changed_flag_to_hid, mac_virtual_keycode_to_hid


kCGEventKeyDown = 10
kCGEventKeyUp = 11
kCGEventFlagsChanged = 12
kCGHIDEventTap = 0
kCGHeadInsertEventTap = 0
kCGEventTapOptionDefault = 0
kCGKeyboardEventKeycode = 9
kCFRunLoopCommonModes = ctypes.c_void_p.in_dll(
    ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation")),
    "kCFRunLoopCommonModes",
)


@dataclass
class RecordedEvent:
    """Serializable event payload."""

    ts: int
    hid: int
    type: str
    modifiers: int


class PermissionError(RuntimeError):
    """Raised when the macOS event tap cannot be created."""


class CornixLogger:
    """Capture keyboard events via CGEventTap and write as JSONL.

    Events are pushed to a thread-safe queue from the CGEventTap
    callback and flushed to disk by a background writer thread.
    This keeps the tap callback fast, preventing macOS from
    disabling the tap due to I/O latency.
    """

    def __init__(self, log_dir: str | Path) -> None:
        self.log_dir = Path(log_dir).expanduser()
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / f"{datetime.now().date().isoformat()}.jsonl"
        self._file = self.log_path.open("a", encoding="utf-8")
        self._last_flush = time.monotonic()
        self._previous_flags = 0
        self._running = False
        self._callback_ref: Any = None
        self._tap = None
        self._run_loop = _CF.CFRunLoopGetCurrent()
        self._queue: queue.Queue[RecordedEvent | None] = queue.Queue(maxsize=10000)
        self._writer_thread = threading.Thread(target=self._writer_loop, daemon=True)

    def run(self) -> None:
        """Start recording until interrupted."""

        self._install_signal_handlers()
        self._create_tap()
        self._writer_thread.start()
        self._running = True
        _CF.CFRunLoopRun()
        self.close()

    def close(self) -> None:
        """Flush pending data and close resources."""

        self._queue.put(None)  # sentinel to stop writer
        self._writer_thread.join(timeout=2)
        if not self._file.closed:
            self._file.flush()
            self._file.close()

    def stop(self) -> None:
        """Stop the event loop."""

        self._running = False
        _CF.CFRunLoopStop(self._run_loop)

    def handle_event(self, event_type: int, event: ctypes.c_void_p) -> None:
        """Convert a native event and push to the write queue.

        Fast path: no I/O, just queue push. Keeps the CGEventTap
        callback under macOS's latency threshold.
        """

        modifiers = int(_CG.CGEventGetFlags(event))
        if event_type == kCGEventFlagsChanged:
            hid = changed_flag_to_hid(self._previous_flags, modifiers)
            self._previous_flags = modifiers
            if hid is None:
                return
            self._queue.put_nowait(RecordedEvent(_now_ms(), hid, "flags", modifiers))
            return
        keycode = int(_CG.CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode))
        hid = mac_virtual_keycode_to_hid(keycode)
        if hid is None:
            return
        event_name = "down" if event_type == kCGEventKeyDown else "up"
        self._queue.put_nowait(RecordedEvent(_now_ms(), hid, event_name, modifiers))

    def _writer_loop(self) -> None:
        """Background thread: drain the queue and write to disk."""

        while True:
            item = self._queue.get()
            if item is None:
                break
            self._file.write(json.dumps(item.__dict__) + "\n")
            if time.monotonic() - self._last_flush >= 1.0:
                self._file.flush()
                self._last_flush = time.monotonic()

    def _create_tap(self) -> None:
        """Create the event tap and add it to the run loop."""

        mask = (1 << kCGEventKeyDown) | (1 << kCGEventKeyUp) | (1 << kCGEventFlagsChanged)
        self._callback_ref = _CALLBACK(self._callback)
        self._tap = _CG.CGEventTapCreate(
            kCGHIDEventTap,
            kCGHeadInsertEventTap,
            kCGEventTapOptionDefault,
            ctypes.c_uint64(mask),
            self._callback_ref,
            None,
        )
        if not self._tap:
            raise PermissionError(
                "CGEventTapCreate failed. Grant Accessibility and Input Monitoring permission."
            )
        source = _CF.CFMachPortCreateRunLoopSource(None, self._tap, 0)
        _CF.CFRunLoopAddSource(self._run_loop, source, kCFRunLoopCommonModes)
        _CG.CGEventTapEnable(self._tap, True)

    def _callback(
        self,
        _proxy: ctypes.c_void_p,
        event_type: int,
        event: ctypes.c_void_p,
        _user_info: ctypes.c_void_p,
    ) -> ctypes.c_void_p:
        """Native event tap callback."""

        if self._running and event_type in {kCGEventKeyDown, kCGEventKeyUp, kCGEventFlagsChanged}:
            self.handle_event(event_type, event)
        return event

    def _install_signal_handlers(self) -> None:
        """Stop cleanly on Ctrl+C and SIGTERM."""

        def stop_handler(_signum: int, _frame: Any) -> None:
            self.stop()

        signal.signal(signal.SIGINT, stop_handler)
        signal.signal(signal.SIGTERM, stop_handler)


def default_log_dir() -> Path:
    """Return the default log directory."""

    return Path.home() / "projects" / "cornix-analyzer" / "logs"


def _now_ms() -> int:
    """Return the current UNIX time in milliseconds."""

    return int(time.time() * 1000)


_CG = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreGraphics"))
_CF = ctypes.cdll.LoadLibrary(ctypes.util.find_library("CoreFoundation"))
_CALLBACK = ctypes.CFUNCTYPE(
    ctypes.c_void_p,
    ctypes.c_void_p,
    ctypes.c_uint32,
    ctypes.c_void_p,
    ctypes.c_void_p,
)
_CG.CGEventTapCreate.restype = ctypes.c_void_p
_CG.CGEventTapCreate.argtypes = [
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_uint32,
    ctypes.c_uint64,
    _CALLBACK,
    ctypes.c_void_p,
]
_CG.CGEventGetIntegerValueField.restype = ctypes.c_int64
_CG.CGEventGetIntegerValueField.argtypes = [ctypes.c_void_p, ctypes.c_int32]
_CG.CGEventGetFlags.restype = ctypes.c_uint64
_CG.CGEventGetFlags.argtypes = [ctypes.c_void_p]
_CG.CGEventTapEnable.argtypes = [ctypes.c_void_p, ctypes.c_bool]
_CF.CFMachPortCreateRunLoopSource.restype = ctypes.c_void_p
_CF.CFMachPortCreateRunLoopSource.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_long]
_CF.CFRunLoopGetCurrent.restype = ctypes.c_void_p
_CF.CFRunLoopAddSource.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p]
_CF.CFRunLoopRun.argtypes = []
_CF.CFRunLoopStop.argtypes = [ctypes.c_void_p]

