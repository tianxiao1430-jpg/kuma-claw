"""
Kuma Claw Gateway - Adapters
===========================
"""

from .base import BaseAdapter
from .slack import SlackAdapter
from .telegram import TelegramAdapter
from .web import WebAdapter

__all__ = [
    "BaseAdapter",
    "SlackAdapter",
    "TelegramAdapter",
    "WebAdapter",
]
