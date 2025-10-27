"""
Quick script to suppress all remaining verbose print statements
"""

import re
from pathlib import Path

# File to process
file_path = Path("src/pages/spaceiq_booking_page.py")

# Read file
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Patterns to suppress (comment out)
patterns_to_suppress = [
    r'print\(f"       ⚡',
    r'print\(f"       ⚠️',
    r'print\(f"       ℹ️',
    r'print\("       \[FAILED\]',
    r'print\(f"       Analyzing screenshot',
    r'print\(f"       Found .* circles',
    r'print\(f"       PHASE ',
    r'print\(f"       ✓ Identified',
    r'print\(f"       Identified .* desks',
    r'print\(f"       Clicking to book',
    r'print\(f"       \[PRIORITY\]',
    r'print\(f"       \[SUCCESS\]',
    r'print\(f"       \[WARNING\] Popup',
    r'print\(f"       Available:',
    r'print\(f"       Detected:',
    r'print\(f"       → ',
    r'print\(f"       \[WARNING\] Date .* is disabled',
    r'print\(f"       Trying partial',
    r'print\(f"       Trying by day',
]

# Process lines
modified = False
for i, line in enumerate(lines):
    for pattern in patterns_to_suppress:
        if re.search(pattern, line) and not line.strip().startswith('#'):
            # Comment out the line
            indent = len(line) - len(line.lstrip())
            lines[i] = ' ' * indent + '# ' + line.lstrip()
            modified = True
            print(f"Commented line {i+1}: {line.strip()[:60]}...")

if modified:
    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    print(f"\n✓ Updated {file_path}")
    print(f"✓ Suppressed verbose output statements")
else:
    print("No changes needed")
