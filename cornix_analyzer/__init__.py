"""Cornix LP typing error analysis and keymap suggestion tool.

.. moduleauthor:: ibuki
"""

__version__ = "0.1.0"

from .analyzer import AnalysisResult, ErrorPair, KeyErrorStat, analyze_events, load_events
from .layout_reader import LayoutData, Position, load_layout

__all__ = [
    "AnalysisResult",
    "ErrorPair",
    "KeyErrorStat",
    "LayoutData",
    "Position",
    "analyze_events",
    "load_events",
    "load_layout",
]

