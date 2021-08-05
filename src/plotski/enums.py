"""Enums."""
from enum import Enum


class Position(str, Enum):
    """Position enum"""

    ABOVE = "above"
    RIGHT = "right"
    LEFT = "left"
