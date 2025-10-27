"""
Computer Vision module to detect blue circles (available desks) on floor map screenshots.
"""

import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple


class DeskDetector:
    """Detects blue circles (available desks) in floor map screenshots"""

    def __init__(self):
        # Blue color range in HSV
        # Blue circles appear as a bright blue
        self.lower_blue = np.array([90, 50, 50])    # Lower HSV bound
        self.upper_blue = np.array([130, 255, 255]) # Upper HSV bound

    def find_blue_circles(self, screenshot_path: str, debug: bool = False) -> List[Tuple[int, int]]:
        """
        Find all blue circles in a screenshot.

        Args:
            screenshot_path: Path to screenshot image
            debug: If True, save debug images showing detection

        Returns:
            List of (x, y) coordinates for blue circle centers
        """
        # Read image
        img = cv2.imread(screenshot_path)
        if img is None:
            print(f"[ERROR] Could not read screenshot: {screenshot_path}")
            return []

        # print(f"       Image size: {img.shape[1]}x{img.shape[0]}")

        # Convert to HSV color space
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        # Create mask for blue color
        mask = cv2.inRange(hsv, self.lower_blue, self.upper_blue)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        # print(f"       Found {len(contours)} blue regions")

        # Extract circle centers
        circles = []
        for contour in contours:
            # Get contour area
            area = cv2.contourArea(contour)

            # Filter by area (blue dots should be small but visible)
            if 10 < area < 500:  # Adjust these thresholds if needed
                # Get bounding box
                M = cv2.moments(contour)
                if M["m00"] != 0:
                    cx = int(M["m10"] / M["m00"])
                    cy = int(M["m01"] / M["m00"])
                    circles.append((cx, cy))

                    if debug:
                        cv2.circle(img, (cx, cy), 5, (0, 255, 0), -1)

        # print(f"       Detected {len(circles)} blue circles")

        # Save debug image if requested
        if debug:
            debug_path = screenshot_path.replace('.png', '_debug.png')
            cv2.imwrite(debug_path, img)
            # print(f"       Saved debug image: {debug_path}")

        return circles

    def filter_circles_by_region(
        self,
        circles: List[Tuple[int, int]],
        min_x: int = 0,
        max_x: int = 10000,
        min_y: int = 0,
        max_y: int = 10000
    ) -> List[Tuple[int, int]]:
        """
        Filter circles to specific region of the map.

        Args:
            circles: List of (x, y) coordinates
            min_x, max_x, min_y, max_y: Region bounds

        Returns:
            Filtered list of coordinates
        """
        return [
            (x, y) for x, y in circles
            if min_x <= x <= max_x and min_y <= y <= max_y
        ]


def test_detector(screenshot_path: str):
    """Test the detector on a screenshot"""
    detector = DeskDetector()
    circles = detector.find_blue_circles(screenshot_path, debug=True)

    print(f"\nFound {len(circles)} blue circles:")
    for i, (x, y) in enumerate(circles, 1):
        print(f"  {i}. ({x}, {y})")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        test_detector(sys.argv[1])
    else:
        print("Usage: python desk_detector.py <screenshot_path>")
