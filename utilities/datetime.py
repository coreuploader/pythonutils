"""Datetime helpers with clear timezone handling."""

import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


_ISO_DATETIME_PATTERN = re.compile(
    r"^[0-9]{4}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}"
    r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})$"
)
_INVALID_DATETIME_MESSAGE = (
    "value must be an ISO 8601 datetime with seconds and an explicit offset"
)


def seconds_between(start: datetime, end: datetime) -> float:
    """Return signed, unrounded elapsed seconds from ``start`` to ``end``.

    Both values must include timezone information. They are converted to UTC
    before subtraction, so different offsets and repeated clock times are
    compared as exact points in time.
    """
    _require_aware_datetime(start, name="start")
    _require_aware_datetime(end, name="end")
    return (ensure_utc(end) - ensure_utc(start)).total_seconds()


def minutes_between(start: datetime, end: datetime) -> float:
    """Return signed, unrounded elapsed minutes from ``start`` to ``end``."""
    return seconds_between(start, end) / 60


def days_between(start: datetime, end: datetime) -> float:
    """Return signed elapsed days from ``start`` to ``end``.

    One day means 24 hours. This does not count local calendar boundaries, so
    a daylight saving change may produce a fraction of a day.
    """
    return seconds_between(start, end) / 86400


def is_expired(
    expires_at: datetime,
    *,
    reference_time: datetime | None = None,
) -> bool:
    """Return whether an aware datetime is at or before a reference instant.

    Both values are converted to UTC before comparison. This handles different
    offsets and repeated local clock times. When no reference is supplied,
    :func:`utc_now` is used.

    Args:
        expires_at: The expiration instant.
        reference_time: The comparison instant, or ``None`` for the current
            aware UTC time.

    Returns:
        ``True`` when ``expires_at`` is equal to or earlier than the reference.

    Raises:
        TypeError: If either supplied value is not a datetime.
        ValueError: If either datetime has no timezone information.
    """
    _require_aware_datetime(expires_at, name="expires_at")

    selected_reference = utc_now() if reference_time is None else reference_time
    _require_aware_datetime(selected_reference, name="reference_time")

    return ensure_utc(expires_at) <= ensure_utc(selected_reference)


def start_of_day(value: datetime) -> datetime:
    """Return midnight for the input's local date and existing timezone.

    No timezone conversion occurs. The result retains the input's ``tzinfo``,
    sets its local time to ``00:00:00``, and resets ``fold`` to zero.

    Raises:
        TypeError: If ``value`` is not a datetime.
        ValueError: If ``value`` has no timezone information.
    """
    _require_aware_datetime(value)
    return value.replace(hour=0, minute=0, second=0, microsecond=0, fold=0)


def end_of_day(value: datetime) -> datetime:
    """Return the final microsecond of the input's local date and timezone.

    No timezone conversion occurs. The result retains the input's ``tzinfo``,
    sets its local time to ``23:59:59.999999``, and resets ``fold`` to zero.

    Raises:
        TypeError: If ``value`` is not a datetime.
        ValueError: If ``value`` has no timezone information.
    """
    _require_aware_datetime(value)
    return value.replace(
        hour=23,
        minute=59,
        second=59,
        microsecond=999999,
        fold=0,
    )


def format_datetime(
    value: datetime | str,
    *,
    timezone_name: str = "UTC",
    format_string: str | None = None,
) -> str:
    """Format an aware datetime or supported datetime string consistently.

    The value is converted to ``timezone_name`` before formatting. Without a
    custom format, the result uses ISO 8601, preserves any microseconds,
    includes numeric offsets, and uses ``Z`` for a zero UTC offset. Strings must
    satisfy :func:`parse_datetime`.

    Args:
        value: A datetime with timezone information or a supported ISO 8601
            string.
        timezone_name: The target IANA timezone identifier. The default is
            ``UTC``.
        format_string: An optional ``datetime.strftime`` format applied after
            timezone conversion.

    Returns:
        The formatted datetime string.

    Raises:
        TypeError: If an argument has an invalid type.
        ValueError: If a datetime is naive, a string is unsupported, or the
            timezone identifier is invalid.
    """
    if not isinstance(value, (datetime, str)):
        raise TypeError("value must be a datetime or string")

    if format_string is not None and not isinstance(format_string, str):
        raise TypeError("format_string must be a string or None")

    parsed_value = parse_datetime(value) if isinstance(value, str) else value
    converted_value = to_timezone(parsed_value, timezone_name)

    if format_string is not None:
        return converted_value.strftime(format_string)

    formatted_value = converted_value.isoformat()
    if formatted_value.endswith("+00:00"):
        return f"{formatted_value[:-6]}Z"
    return formatted_value


def parse_datetime(value: str) -> datetime:
    """Parse a supported ISO 8601 datetime string and return aware UTC.

    Supported input is ``YYYY-MM-DDTHH:MM:SS`` or the same form with a space
    instead of ``T``. One to six digits for fractions of a second may follow
    seconds. Every value must end with uppercase ``Z`` or a numeric ``±HH:MM``
    offset. Dates without a time, datetimes without timezone information, and
    other formats are rejected.

    Args:
        value: The datetime string to parse.

    Returns:
        The represented instant as a UTC datetime with timezone information.

    Raises:
        TypeError: If ``value`` is not a string.
        ValueError: If the format or calendar value is invalid.
    """
    if not isinstance(value, str):
        raise TypeError("value must be a string")

    if _ISO_DATETIME_PATTERN.fullmatch(value) is None:
        raise ValueError(_INVALID_DATETIME_MESSAGE)

    normalized_value = f"{value[:-1]}+00:00" if value.endswith("Z") else value

    try:
        parsed_value = datetime.fromisoformat(normalized_value)
    except ValueError as error:
        raise ValueError(_INVALID_DATETIME_MESSAGE) from error

    return ensure_utc(parsed_value)


def to_timezone(value: datetime, timezone_name: str) -> datetime:
    """Convert an aware datetime to an IANA timezone.

    Args:
        value: The datetime to convert. It must include timezone information.
        timezone_name: An IANA identifier such as ``Asia/Manila`` or
            ``America/New_York``.

    Returns:
        The same instant represented in the requested timezone.

    Raises:
        TypeError: If ``value`` is not a datetime or ``timezone_name`` is not a
            string.
        ValueError: If ``value`` is naive or the timezone identifier is invalid.
    """
    if not isinstance(timezone_name, str):
        raise TypeError("timezone_name must be a string")

    utc_value = ensure_utc(value)

    try:
        target_timezone = ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError) as error:
        raise ValueError(f"unknown timezone: {timezone_name!r}") from error

    return utc_value.astimezone(target_timezone)


def ensure_utc(value: datetime) -> datetime:
    """Return an aware datetime converted to UTC.

    Naive datetimes are rejected because their timezone cannot be inferred
    safely. Add the correct source timezone before using this helper.

    Args:
        value: A datetime with timezone information.

    Returns:
        The same instant represented with ``timezone.utc``.

    Raises:
        TypeError: If ``value`` is not a datetime.
        ValueError: If ``value`` is naive, including when its ``tzinfo`` returns
            ``None`` from ``utcoffset()``.
    """
    _require_aware_datetime(value)
    return value.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Return the current UTC datetime with timezone information."""
    return datetime.now(timezone.utc)


def naive_utc_now() -> datetime:
    """Return current UTC clock fields without timezone information.

    Use this helper for database columns or drivers that require UTC values
    without timezone information. The fields represent UTC, but the
    datetime itself cannot show that. Prefer :func:`utc_now` for application
    logic, and do not compare this result with aware datetimes.
    """
    return utc_now().replace(tzinfo=None)


def _require_aware_datetime(value: datetime, *, name: str = "value") -> None:
    """Raise when a value is not a datetime with timezone information."""
    if not isinstance(value, datetime):
        raise TypeError(f"{name} must be a datetime")

    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must include timezone information")
