"""
Desk Priority Utilities

Handles desk preference sorting based on configured priority ranges.
"""

from typing import List, Dict, Any
import re


def parse_desk_number(desk_code: str) -> int:
    """
    Extract the desk number from desk code.

    Args:
        desk_code: Desk code like "2.24.30" or "2.24.05"

    Returns:
        Desk number as integer (e.g., 30, 5)
    """
    # Extract last part after final dot
    parts = desk_code.split('.')
    if len(parts) >= 3:
        return int(parts[-1])
    return 999  # Unknown format, low priority


def parse_range(range_str: str) -> tuple:
    """
    Parse a range string into start and end desk codes.

    Args:
        range_str: Range like "2.24.20-2.24.30"

    Returns:
        Tuple of (start_desk, end_desk) as strings
    """
    parts = range_str.split('-')
    if len(parts) == 2:
        return (parts[0].strip(), parts[1].strip())
    return (None, None)


def is_desk_in_range(desk_code: str, range_str: str) -> bool:
    """
    Check if a desk code falls within a range.

    Args:
        desk_code: Desk like "2.24.25"
        range_str: Range like "2.24.20-2.24.30"

    Returns:
        True if desk is in range
    """
    start_desk, end_desk = parse_range(range_str)

    if not start_desk or not end_desk:
        return False

    # Extract desk numbers for comparison
    desk_num = parse_desk_number(desk_code)
    start_num = parse_desk_number(start_desk)
    end_num = parse_desk_number(end_desk)

    return start_num <= desk_num <= end_num


def get_desk_priority(desk_code: str, priority_config: List[Dict[str, Any]]) -> int:
    """
    Get priority score for a desk based on configuration.

    Args:
        desk_code: Desk like "2.24.25"
        priority_config: List of priority range configs like:
            [
                {"range": "2.24.20-2.24.30", "priority": 1, "reason": "Near window"},
                {"range": "2.24.02-2.24.12", "priority": 2, "reason": "Quiet area"},
                ...
            ]

    Returns:
        Priority score (lower is better, 999 = no priority/default)
    """
    if not priority_config:
        return 999  # No priorities configured

    for config in priority_config:
        range_str = config.get("range", "")
        priority = config.get("priority", 999)

        if is_desk_in_range(desk_code, range_str):
            return priority

    return 999  # Desk not in any priority range


def sort_desks_by_priority(
    desks: List[str],
    priority_config: List[Dict[str, Any]]
) -> List[str]:
    """
    Sort desks by priority (most preferred first).

    Args:
        desks: List of desk codes like ["2.24.25", "2.24.05", "2.24.40"]
        priority_config: List of priority range configs

    Returns:
        Sorted list of desks (highest priority first)

    Example:
        >>> priority_config = [
        ...     {"range": "2.24.20-2.24.30", "priority": 1},
        ...     {"range": "2.24.02-2.24.12", "priority": 2},
        ... ]
        >>> desks = ["2.24.40", "2.24.25", "2.24.05"]
        >>> sort_desks_by_priority(desks, priority_config)
        ["2.24.25", "2.24.05", "2.24.40"]  # Priority 1, then 2, then no priority
    """
    if not priority_config:
        return desks  # No sorting needed

    # Sort by priority (lower priority number = higher preference)
    # Then by desk number for consistency within same priority
    def priority_key(desk_code: str):
        priority = get_desk_priority(desk_code, priority_config)
        desk_num = parse_desk_number(desk_code)
        return (priority, desk_num)

    return sorted(desks, key=priority_key)


def explain_desk_priorities(
    desks: List[str],
    priority_config: List[Dict[str, Any]]
) -> str:
    """
    Generate a human-readable explanation of desk priorities.

    Args:
        desks: List of available desks
        priority_config: Priority configuration

    Returns:
        Formatted string explaining the priority ordering
    """
    if not priority_config or not desks:
        return "No desk priorities configured."

    sorted_desks = sort_desks_by_priority(desks, priority_config)

    lines = ["Desk Priority Order (best to worst):"]

    current_priority = None
    for desk in sorted_desks:
        priority = get_desk_priority(desk, priority_config)

        # Find reason for this priority
        reason = "No specific preference"
        for config in priority_config:
            if is_desk_in_range(desk, config.get("range", "")):
                reason = config.get("reason", "Preferred")
                break

        # Group by priority level
        if priority != current_priority:
            if priority == 999:
                lines.append(f"\n  Priority: Default")
            else:
                lines.append(f"\n  Priority {priority}:")
            current_priority = priority

        lines.append(f"    - {desk} ({reason})")

    return "\n".join(lines)
