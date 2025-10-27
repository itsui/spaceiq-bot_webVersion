"""
Desk Position Cache Utility

Loads and queries the desk position cache for fast desk lookups.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Tuple
import math


class DeskPositionCache:
    """
    Manages cached desk positions for fast lookups.
    """

    def __init__(self, cache_file: Path = None):
        self.cache_file = cache_file or Path("config/desk_positions.json")
        self.cache = None
        self.desk_positions = {}
        self.load()

    def load(self) -> bool:
        """
        Load cache from file.

        Returns:
            True if cache loaded successfully, False otherwise
        """
        if not self.cache_file.exists():
            return False

        try:
            with open(self.cache_file, 'r') as f:
                self.cache = json.load(f)
                self.desk_positions = self.cache.get("desk_positions", {})
            return True
        except Exception as e:
            print(f"[WARNING] Failed to load desk position cache: {e}")
            return False

    def is_available(self) -> bool:
        """Check if cache is loaded and available."""
        return self.cache is not None and len(self.desk_positions) > 0

    def get_position(self, desk_code: str) -> Optional[Tuple[int, int]]:
        """
        Get (x, y) coordinates for a desk.

        Args:
            desk_code: Desk code (e.g., "2.24.35")

        Returns:
            (x, y) tuple if found, None otherwise
        """
        if desk_code not in self.desk_positions:
            return None

        pos = self.desk_positions[desk_code]
        return (pos["x"], pos["y"])

    def find_desk_at_position(self, x: int, y: int, tolerance: int = 10) -> Optional[str]:
        """
        Find desk code at given coordinates (with tolerance).

        Args:
            x: X coordinate
            y: Y coordinate
            tolerance: Maximum distance in pixels (default: 10)

        Returns:
            Desk code if found, None otherwise
        """
        for desk_code, pos in self.desk_positions.items():
            distance = math.sqrt((x - pos["x"]) ** 2 + (y - pos["y"]) ** 2)
            if distance <= tolerance:
                return desk_code

        return None

    def lookup_desks_from_circles(self, circles: list, tolerance: int = 10) -> Dict[str, Tuple[int, int]]:
        """
        Map blue circle coordinates to desk codes using cache.

        Args:
            circles: List of (x, y) tuples from CV detection
            tolerance: Maximum distance in pixels for matching (default: 10)

        Returns:
            Dictionary mapping desk_code -> (x, y)
        """
        result = {}

        for (x, y) in circles:
            desk_code = self.find_desk_at_position(x, y, tolerance=tolerance)
            if desk_code:
                result[desk_code] = (x, y)

        return result

    def get_all_desks(self) -> list:
        """Get list of all desk codes in cache."""
        return list(self.desk_positions.keys())

    def get_cache_info(self) -> dict:
        """Get cache metadata."""
        if not self.cache:
            return {}

        return {
            "viewport": self.cache.get("viewport"),
            "floor": self.cache.get("floor"),
            "building": self.cache.get("building"),
            "total_desks": self.cache.get("total_desks"),
            "last_updated": self.cache.get("last_updated"),
            "mapping_date": self.cache.get("mapping_date")
        }

    def validate_viewport(self, current_viewport: dict) -> bool:
        """
        Check if cache viewport matches current viewport.

        Args:
            current_viewport: Dict with 'width' and 'height'

        Returns:
            True if matches, False if mismatch
        """
        if not self.cache:
            return False

        cached_viewport = self.cache.get("viewport", {})

        return (
            cached_viewport.get("width") == current_viewport.get("width") and
            cached_viewport.get("height") == current_viewport.get("height")
        )


# Global cache instance
_cache = None


def get_cache() -> DeskPositionCache:
    """Get global cache instance (singleton)."""
    global _cache
    if _cache is None:
        _cache = DeskPositionCache()
    return _cache
