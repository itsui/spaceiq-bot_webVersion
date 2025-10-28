"""
Sound Notification Utility

Plays sound alerts when important events occur (e.g., successful bookings).
Uses Windows winsound for reliable, built-in sound playback.
"""

import logging
from typing import Optional


def play_success_sound(duration_ms: int = 500, frequency_hz: int = 1000) -> bool:
    """
    Play a success sound notification.

    Uses Windows beep for headless mode compatibility.
    Falls back gracefully if sound playback fails.

    Args:
        duration_ms: Duration of the sound in milliseconds (default: 500ms)
        frequency_hz: Frequency of the beep in Hz (default: 1000Hz)

    Returns:
        True if sound played successfully, False otherwise

    Example:
        play_success_sound()  # Play default beep
        play_success_sound(duration_ms=1000, frequency_hz=800)  # Custom beep
    """
    try:
        import winsound
        # Play a pleasant success beep (3 short beeps)
        for i in range(3):
            winsound.Beep(frequency_hz + (i * 100), duration_ms // 3)
        return True
    except ImportError:
        # winsound is Windows-only, fall back gracefully
        logging.warning("winsound not available (non-Windows platform)")
        return False
    except Exception as e:
        logging.warning(f"Failed to play success sound: {e}")
        return False


def play_custom_beep_pattern(pattern: list[tuple[int, int]]) -> bool:
    """
    Play a custom beep pattern.

    Args:
        pattern: List of (frequency_hz, duration_ms) tuples

    Returns:
        True if sound played successfully, False otherwise

    Example:
        # Play ascending melody
        play_custom_beep_pattern([
            (500, 200),   # Low note
            (700, 200),   # Mid note
            (1000, 400)   # High note
        ])
    """
    try:
        import winsound
        import time

        for frequency, duration in pattern:
            winsound.Beep(frequency, duration)
            time.sleep(0.05)  # Small gap between beeps
        return True
    except ImportError:
        logging.warning("winsound not available (non-Windows platform)")
        return False
    except Exception as e:
        logging.warning(f"Failed to play custom beep pattern: {e}")
        return False


def play_booking_success_alert() -> bool:
    """
    Play a cheerful success alert for successful bookings.

    Plays an ascending 3-note melody that's pleasant and noticeable.

    Returns:
        True if sound played successfully, False otherwise
    """
    # Cheerful ascending melody
    success_pattern = [
        (600, 150),   # C5
        (800, 150),   # E5
        (1000, 300),  # C6 (hold longer)
    ]
    return play_custom_beep_pattern(success_pattern)


# Quick test function
if __name__ == "__main__":
    print("Testing sound notifications...")
    print("\n1. Testing basic success sound...")
    play_success_sound()

    print("\n2. Testing booking success alert...")
    import time
    time.sleep(1)
    play_booking_success_alert()

    print("\nSound test complete!")
