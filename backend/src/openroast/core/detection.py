"""Automatic roast event detection (CHARGE, DROP, Turning Point).

Ported from Artisan's BTbreak algorithm — analyzes BT curve gradients
to detect when beans are loaded (CHARGE) and when roasting completes (DROP).
"""

from __future__ import annotations


def check_bt_break(
    samples: list[float],
    d: float = 1.0,
    offset: float = 0.0,
    dpre_dpost_diff: float = 0.0,
) -> bool:
    """Check if the last 6 BT samples indicate a break point.

    A break occurs when the BT curve transitions from falling to rising
    (CHARGE turning point) or from rising to falling (DROP).

    Args:
        samples: Exactly 6 consecutive BT readings, oldest first.
        d: Gradient threshold.
        offset: Offset added to gradient comparison.
        dpre_dpost_diff: Minimum difference between pre and post gradients.

    Returns:
        True if a BT break is detected.
    """
    if len(samples) != 6:
        return False

    s0, s1, s2, s3, s4, s5 = samples

    # Pre-break gradient (first 3 samples)
    dpre = ((s1 - s0) + (s2 - s1)) / 2.0

    # Post-break gradient (last 3 samples)
    dpost = ((s4 - s3) + (s5 - s4)) / 2.0

    # Break detected when gradient reversal exceeds thresholds
    if abs(dpre - dpost) < dpre_dpost_diff:
        return False

    return (dpre - d - offset) > 0 > (dpost + d + offset) or \
           (dpre + d + offset) < 0 < (dpost - d - offset)


def find_turning_point(bt_values: list[float], charge_index: int) -> int:
    """Find the turning point (minimum BT) after CHARGE.

    The turning point is where BT stops falling and begins to rise
    after beans are loaded into the hot drum.

    Args:
        bt_values: Full BT time series.
        charge_index: Index of the CHARGE event.

    Returns:
        Index of the turning point, or -1 if not found.
    """
    if charge_index < 0 or charge_index >= len(bt_values):
        return -1

    search = bt_values[charge_index:]
    if not search:
        return -1

    min_val = min(search)
    return charge_index + search.index(min_val)
