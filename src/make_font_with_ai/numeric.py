"""Deterministic construction grid, NOT a tolerance in the comparison gate.

GEOS/NumPy on different CPUs can approach an exact half-unit from opposite
floating-point sides. First express a construction coordinate on a 1e-7-font-unit
grid, then apply ties-to-even integer rounding. The final verifier still compares
every integer coordinate with zero tolerance.
"""
from __future__ import annotations
import math

def font_unit_round(value: float) -> int:
    value=float(value)
    if not math.isfinite(value):
        raise ValueError('A font coordinate must be finite')
    return round(round(value,7))
