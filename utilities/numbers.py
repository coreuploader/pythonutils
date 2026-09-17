"""Helpers for common numeric operations."""

import math
import re


_FLOAT_PATTERN = re.compile(
    r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
)


def clamp(
    value: int | float,
    minimum: int | float,
    maximum: int | float,
) -> int | float:
    """Restrict an integer or float to an inclusive numeric range.

    Integers and floats may be mixed. Booleans are rejected even though Python
    treats them as integer subclasses. NaN is rejected because it has no
    meaningful ordering. Positive and negative infinity are accepted and use
    normal Python comparison behavior.

    The selected argument is returned unchanged: ``minimum`` when ``value`` is
    below the range, ``maximum`` when it is above, and ``value`` when it is on
    a boundary or within the range.

    Args:
        value: Number to restrict.
        minimum: Inclusive lower bound.
        maximum: Inclusive upper bound.

    Returns:
        ``value``, ``minimum``, or ``maximum`` according to the range.

    Raises:
        TypeError: If any argument is not an integer or float, or is a boolean.
        ValueError: If any argument is NaN or ``minimum`` exceeds ``maximum``.
    """
    _require_number("value", value)
    _require_number("minimum", minimum)
    _require_number("maximum", maximum)

    if minimum > maximum:
        raise ValueError("minimum must not exceed maximum")
    if value < minimum:
        return minimum
    if value > maximum:
        return maximum
    return value


def percentage(
    part: int | float,
    whole: int | float,
) -> float:
    """Return ``part`` as a percentage of ``whole``.

    Both arguments must be finite integers or floats. Booleans are rejected.
    Signed inputs use ordinary arithmetic, so results
    may be below zero or above 100. The return value is always a float and is
    not rounded.

    Args:
        part: Numerator whose relative percentage should be calculated.
        whole: The whole amount. It must not be zero.

    Returns:
        ``part / whole * 100`` as an unrounded float.

    Raises:
        TypeError: If either argument is not an integer or float, or is a
            boolean.
        ValueError: If either argument is NaN or infinite.
        ZeroDivisionError: If ``whole`` is zero, including negative float zero.
    """
    _require_finite_number("part", part)
    _require_finite_number("whole", whole)

    if whole == 0:
        raise ZeroDivisionError("whole must not be zero")

    return part / whole * 100.0


def safe_int(
    value: object,
    *,
    default: int | None = None,
) -> int | None:
    """Convert a narrowly supported value to an integer or return ``default``.

    Accepted values are integers other than booleans, and strings containing an
    optional leading ``+`` or ``-`` followed by ASCII decimal digits. Leading
    and trailing Unicode whitespace in strings is ignored. Floats, booleans,
    bytes, international digits, decimal or exponent notation, base prefixes,
    and digit separators are not converted.

    Args:
        value: Value to convert.
        default: Integer or ``None`` returned when ``value`` is unsupported or
            contains invalid integer syntax.

    Returns:
        The original integer, the parsed string value, or ``default``.

    Raises:
        TypeError: If ``default`` is not an integer or ``None``, or is a
            boolean.
    """
    if default is not None and (
        isinstance(default, bool) or not isinstance(default, int)
    ):
        raise TypeError("default must be an integer or None")

    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if not isinstance(value, str):
        return default

    candidate = value.strip()
    if candidate[:1] in {"+", "-"}:
        digits = candidate[1:]
    else:
        digits = candidate

    if not digits or any(digit not in "0123456789" for digit in digits):
        return default

    try:
        return int(candidate, 10)
    except ValueError:
        return default


def safe_float(
    value: object,
    *,
    default: float | None = None,
) -> float | None:
    """Convert a narrowly supported finite value to float or return a default.

    Accepted values are finite floats, integers other than booleans, and ASCII
    decimal strings with an optional sign, decimal point, and exponent using
    base 10. Surrounding Unicode whitespace in strings is ignored. Bytes,
    international digits, separators, hexadecimal notation, NaN, infinity,
    and values that overflow float range are not converted.

    The fallback must be a finite float or ``None``. It is validated even when
    ``value`` is already valid, so an invalid default is never ignored.

    Args:
        value: Value to convert.
        default: Finite float or ``None`` returned for unsupported or invalid
            input.

    Returns:
        A finite float or ``default``.

    Raises:
        TypeError: If ``default`` is not a float or ``None``, or is a boolean.
        ValueError: If ``default`` is NaN or infinite.
    """
    if default is not None:
        if isinstance(default, bool) or not isinstance(default, float):
            raise TypeError("default must be a float or None")
        if not math.isfinite(default):
            raise ValueError("default must be finite")

    if isinstance(value, bool):
        return default
    if isinstance(value, float):
        return value if math.isfinite(value) else default
    if isinstance(value, int):
        try:
            converted = float(value)
        except OverflowError:
            return default
        return converted if math.isfinite(converted) else default
    if not isinstance(value, str):
        return default

    candidate = value.strip()
    if not _FLOAT_PATTERN.fullmatch(candidate):
        return default

    try:
        converted = float(candidate)
    except ValueError:
        return default
    return converted if math.isfinite(converted) else default


def between(
    value: int | float,
    minimum: int | float,
    maximum: int | float,
    *,
    inclusive_minimum: bool = True,
    inclusive_maximum: bool = True,
) -> bool:
    """Return whether a number lies within a configurable ordered range.

    Both boundaries are inclusive by default and can be made independently
    exclusive. Integers and floats may be mixed. Booleans and NaN are rejected;
    infinities follow normal Python ordering.

    Args:
        value: Number to test.
        minimum: Lower range boundary.
        maximum: Upper range boundary.
        inclusive_minimum: Include equality with ``minimum``.
        inclusive_maximum: Include equality with ``maximum``.

    Returns:
        Whether ``value`` satisfies both configured boundaries.

    Raises:
        TypeError: If a numeric argument is not an integer or float, is a
            boolean, or a boundary option is not boolean.
        ValueError: If a numeric argument is NaN or ``minimum`` exceeds
            ``maximum``.
    """
    _require_number("value", value)
    _require_number("minimum", minimum)
    _require_number("maximum", maximum)

    if not isinstance(inclusive_minimum, bool):
        raise TypeError("inclusive_minimum must be a boolean")
    if not isinstance(inclusive_maximum, bool):
        raise TypeError("inclusive_maximum must be a boolean")
    if minimum > maximum:
        raise ValueError("minimum must not exceed maximum")

    if inclusive_minimum:
        satisfies_minimum = value >= minimum
    else:
        satisfies_minimum = value > minimum

    if inclusive_maximum:
        satisfies_maximum = value <= maximum
    else:
        satisfies_maximum = value < maximum

    return satisfies_minimum and satisfies_maximum


def _require_number(name: str, value: object) -> None:
    """Require an integer other than a boolean, or a float that is not NaN."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be an integer or float")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError(f"{name} must not be NaN")


def _require_finite_number(name: str, value: object) -> None:
    """Require a supported number that is neither NaN nor infinite."""
    _require_number(name, value)
    if isinstance(value, float) and math.isinf(value):
        raise ValueError(f"{name} must be finite")
