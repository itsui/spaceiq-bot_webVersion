# Position Caching - 10x Faster Booking ⚡

## Overview

The bot can now cache desk positions for **10x faster booking**!

- **Before**: ~30 seconds per date (clicking all popups)
- **After**: ~3 seconds per date (instant lookups) ⚡

## How It Works

### Without Cache (Slow - Discovery Mode)
```
[8/9] Using computer vision to detect and click available desks...
       Found 5 blue circles
       ℹ️  No position cache, using discovery mode
       PHASE 1: Identifying all blue circle desks...
       Checking circle 1/5 at (1229, 351)...
       → Identified: 2.24.23
       Checking circle 2/5 at (1329, 240)...
       → Identified: 2.24.35
       ... (clicks all 5 circles)
       PHASE 2: Booking highest priority desk...

Time: ~30 seconds
```

### With Cache (Fast - Cached Mode)
```
[8/9] Using computer vision to detect and click available desks...
       Found 5 blue circles
       ⚡ Using cached desk positions (fast mode)
       PHASE 1: Looking up desk codes from cache... ⚡
       ✓ Identified 5 desks instantly from cache
       PHASE 2: Booking highest priority desk...
       [PRIORITY] Found highest priority desk: 2.24.35

Time: ~3 seconds ⚡
```

## Building the Position Cache

### Step 1: Run the Mapper Tool

```bash
python map_desk_positions.py
```

### What It Does

1. **Finds a weekend date** - Saturday or Sunday in the next 4 weeks
   - Weekends have the most available desks (blue circles)
   - More circles = more complete cache

2. **Navigates to the floor map** for that date

3. **Detects all blue circles** using computer vision

4. **Clicks each circle** to read the desk code from popup:
   ```
   [1/50] Clicking circle at (1229, 351)... ✓ 2.24.23
   [2/50] Clicking circle at (1329, 240)... ✓ 2.24.35
   [3/50] Clicking circle at (875, 75)...  ✓ 2.24.05
   ...
   [50/50] Clicking circle at (920, 180)... ✓ 2.24.68

   ✓ Mapped 50 unique desk positions
   ```

5. **Saves the cache** to `config/desk_positions.json`:
   ```json
   {
     "viewport": {"width": 1920, "height": 1080},
     "floor": "2",
     "building": "LC",
     "desk_positions": {
       "2.24.05": {"x": 875, "y": 75},
       "2.24.23": {"x": 1229, "y": 351},
       "2.24.35": {"x": 1329, "y": 240},
       "2.24.40": {"x": 871, "y": 67},
       ...
     },
     "last_updated": "2025-10-27T10:00:00",
     "mapping_date": "2025-11-23",
     "total_desks": 50
   }
   ```

### Step 2: Run Normal Booking

```bash
python multi_date_book.py --auto
```

The bot will **automatically use the cache** if available! ⚡

## Cache Validation

The bot validates the cache before using it:

### ✅ Valid Cache
- Cache file exists
- Viewport size matches (1920x1080)
- → **Uses fast mode** ⚡

### ❌ Invalid Cache
- No cache file found
- Viewport size mismatch
- → **Falls back to discovery mode** (slow but works)

## Example Output

### First Time (Building Cache)
```bash
$ python map_desk_positions.py

======================================================================
         Desk Position Mapper Tool
======================================================================

This tool will build a cache of desk positions for fast booking.
It will click all blue circles to identify desk locations.

Target date: Sun, Nov 23 (2025-11-23)
Days ahead: 27
======================================================================

Building: LC
Floor: 2

[1/6] Navigating to floor view...
       ✓ Navigated
...
[6/6] Waiting for floor map...
       ✓ Floor map loaded

📸 Screenshot saved

======================================================================
         Detecting Blue Circles
======================================================================

Found 50 blue circles

======================================================================
         Mapping Desk Positions
======================================================================

[1/50] Clicking circle at (1229, 351)... ✓ 2.24.23
[2/50] Clicking circle at (1329, 240)... ✓ 2.24.35
...
[50/50] Clicking circle at (920, 180)... ✓ 2.24.68

✓ Mapped 50 unique desk positions

======================================================================
         Mapping Complete!
======================================================================

Cache saved to: config/desk_positions.json
Total desks mapped: 50

Desks found:
   1. 2.24.05 at (875, 75)
   2. 2.24.08 at (890, 90)
   ...
  50. 2.24.68 at (920, 180)

✓ Position cache is ready!
  Booking will now be 10x faster! ⚡
```

### Using Cache (Fast Booking)
```bash
$ python multi_date_book.py --auto

[8/9] Using computer vision to detect and click available desks...
       Analyzing screenshot: D:\SD\spaceIqBotv01\screenshots\floor_map_loaded_20251027.png
       Found 5 blue circles
       ⚡ Using cached desk positions (fast mode)
       PHASE 1: Looking up desk codes from cache... ⚡
       ✓ Identified 5 desks instantly from cache
       PHASE 2: Booking highest priority desk...
       [PRIORITY] Found highest priority desk: 2.24.35 (Priority position: 1/5)
       Clicking to book 2.24.35 at (1329, 240)...
       [SUCCESS] Successfully selected highest priority desk 2.24.35!
```

## When to Rebuild Cache

Rebuild the cache if:

1. **Floor layout changes** - New desks added or removed
2. **You change browser resolution** - Cache is viewport-specific
3. **Cache seems outdated** - Getting many "not in cache" messages

Simply run `python map_desk_positions.py` again to rebuild!

## Troubleshooting

### "No position cache, using discovery mode"
**Cause:** Cache file doesn't exist

**Solution:** Run `python map_desk_positions.py` to build cache

### "Cache viewport mismatch, using discovery mode"
**Cause:** Browser window size changed

**Solution:** Either:
- Rebuild cache with current viewport: `python map_desk_positions.py`
- Or accept slower discovery mode (still works!)

### "X circle(s) not in cache (may be new desks)"
**Cause:** New desks added since cache was built

**Solution:**
- Bot still works (uses discovery for unknown circles)
- Rebuild cache to include new desks: `python map_desk_positions.py`

## Technical Details

### Position Matching Tolerance
Cache uses **10-pixel tolerance** when matching circle positions:
```python
# CV detects circle at (1230, 352)
# Cache has desk 2.24.23 at (1229, 351)
# Distance: sqrt((1230-1229)^2 + (352-351)^2) = 1.4 pixels
# ✓ Match! (within 10px tolerance)
```

This handles minor pixel variations between runs.

### Cache File Location
```
config/desk_positions.json
```

### Viewport
Fixed at 1920x1080 (set in browser launch)

## Performance Comparison

| Scenario | Time per Date | Details |
|----------|---------------|---------|
| **Discovery Mode** (no cache) | ~30s | Clicks all 5 circles + reads popups |
| **Cached Mode** (with cache) | ~3s | Instant lookup + 1 click ⚡ |
| **Speedup** | **10x faster** | Saves 27 seconds per date! |

### Booking 8 Dates
- **Without cache**: 8 × 30s = **4 minutes**
- **With cache**: 8 × 3s = **24 seconds** ⚡
- **Time saved**: **3.5 minutes per run!**

## Conclusion

Position caching makes the bot **dramatically faster** while maintaining reliability.

**Run once:**
```bash
python map_desk_positions.py
```

**Enjoy 10x faster bookings forever!** ⚡🎉
