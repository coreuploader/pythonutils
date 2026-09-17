# Python Utilities

A small set of Python helpers for common application tasks.

The helpers use standard Python values, so they can be used in web apps,
command line tools, background workers, and standalone scripts. They do not
depend on Django, FastAPI, Tornado, or another framework.

Looking for a specific helper? Start with the [utility map](UTILITY_MAP.md).
It maps common tasks to the helper and module that handle them.

## Requirements

- Python 3.11 or newer
- No runtime dependencies

This project is used directly from its source folder. It is not a PyPI package.

## Setup and tests

Create the virtual environment:

```bash
make venv
```

Run all tests:

```bash
make test
```

Tests use Python's built in `unittest` module.

GitHub Actions runs the same test command with Python 3.11, 3.12, and 3.13
after each push and for each pull request.

## String helpers

These helpers clean, shorten, mask, and format text.

```python
from datetime import date

from utilities.strings import (
    generate_reference,
    mask_email,
    mask_phone,
    normalize_unicode,
    normalize_whitespace,
    slugify,
    truncate,
)
```

`normalize_unicode()` - Normalizes Unicode text. NFC is the default.

```python
normalize_unicode("Cafe\u0301")
# "Café"
```

`normalize_whitespace()` - Removes whitespace at the ends and changes each
run of whitespace to one space.

```python
normalize_whitespace("  Hello\t世界\n")
# "Hello 世界"
```

`slugify()` - Creates a lowercase slug and keeps Unicode letters and numbers.

```python
slugify("Café 世界")
# "café-世界"
```

`truncate()` - Shortens text. The suffix is included in the requested length.

```python
truncate("This is a long message", length=12)
# "This is a..."
```

`mask_email()` - Hides most of the part before `@` for display.

```python
mask_email("jordan@example.com")
# "j*****@example.com"
```

`mask_phone()` - Hides digits but keeps the last four visible by default.

```python
mask_phone("+1 (415) 555-2671")
# "+* (***) ***-2671"
```

`generate_reference()` - Creates a readable reference with a date and random
characters.

```python
generate_reference("inv", reference_date=date(2026, 9, 17))
# Example: "INV-20260917-A8F2KD"
```

Masking is for display only. It is not encryption. Generated references use
secure randomness, but the function does not guarantee that every reference is
unique.

## Datetime helpers

These helpers use timezone aware datetimes. Naive datetimes are rejected unless
the function name clearly says otherwise.

```python
from datetime import datetime, timedelta, timezone

from utilities.datetime import (
    days_between,
    end_of_day,
    ensure_utc,
    format_datetime,
    is_expired,
    minutes_between,
    naive_utc_now,
    parse_datetime,
    seconds_between,
    start_of_day,
    to_timezone,
    utc_now,
)
```

`utc_now()` - Returns the current aware UTC datetime.

```python
current = utc_now()
current.tzinfo is not None
# True
```

`naive_utc_now()` - Returns current UTC clock values without timezone data.
Use this only at a database boundary that requires naive UTC.

```python
database_value = naive_utc_now()
database_value.tzinfo is None
# True
```

`ensure_utc()` - Converts an aware datetime to UTC.

```python
source = datetime(
    2026, 9, 17, 8, 30,
    tzinfo=timezone(timedelta(hours=8)),
)
ensure_utc(source)
# datetime.datetime(2026, 9, 17, 0, 30, tzinfo=datetime.timezone.utc)
```

`to_timezone()` - Converts an aware datetime to an IANA timezone.

```python
instant = parse_datetime("2026-09-17T00:30:00Z")
to_timezone(instant, "Asia/Manila").isoformat()
# "2026-09-17T08:30:00+08:00"
```

`parse_datetime()` - Parses a small ISO 8601 format with seconds and a
required UTC offset.

```python
parse_datetime("2026-09-17T08:30:00+08:00")
# datetime.datetime(2026, 9, 17, 0, 30, tzinfo=datetime.timezone.utc)
```

`format_datetime()` - Converts the timezone and formats a datetime.

```python
format_datetime("2026-09-17T08:30:00+08:00")
# "2026-09-17T00:30:00Z"
```

`start_of_day()` and `end_of_day()` - Return the first or last moment of the
same local date without changing its timezone.

```python
value = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
start_of_day(value).isoformat()
# "2026-09-17T00:00:00+00:00"

end_of_day(value).isoformat()
# "2026-09-17T23:59:59.999999+00:00"
```

`is_expired()` - Checks whether a datetime is at or before a reference time.

```python
expires = datetime(2026, 9, 17, tzinfo=timezone.utc)
reference = datetime(2026, 9, 18, tzinfo=timezone.utc)
is_expired(expires, reference_time=reference)
# True
```

`seconds_between()`, `minutes_between()`, and `days_between()` - Return
signed elapsed time without rounding. A day means 24 hours.

```python
start = datetime(2026, 9, 17, tzinfo=timezone.utc)
end = datetime(2026, 9, 18, tzinfo=timezone.utc)

seconds_between(start, end)  # 86400.0
minutes_between(start, end)  # 1440.0
days_between(start, end)     # 1.0
```

## Validation helpers

These helpers validate common values without using a web framework.

```python
from utilities.validation import (
    is_blank,
    is_valid_email,
    is_valid_phone,
    is_valid_text,
    is_valid_url,
    require_fields,
    validate_text,
)
```

`validate_text()` - Checks text with a Unicode aware character policy. It
raises `ValueError` for a character that is not allowed.

```python
validate_text("Hello 世界: ₱100")
# "Hello 世界: ₱100"
```

`is_valid_text()` - Runs the same check and returns `True` or `False`.

```python
is_valid_text("Hello 世界")  # True
is_valid_text("Hello 😊")   # False
```

Text validation is not sanitization. It does not prevent SQL injection, XSS,
HTML injection, or command injection.

`is_valid_email()` - Checks practical email syntax.

```python
is_valid_email("first.last+tag@example.com")  # True
is_valid_email("not an address")              # False
```

This does not prove that the mailbox exists or belongs to the user. Quoted
local parts and IP address literals are not accepted.

`is_valid_phone()` - Checks a normalized international phone number. The
accepted format is `+` followed by 8 to 15 ASCII digits.

```python
is_valid_phone("+639171234567")   # True
is_valid_phone("+63 917 123 4567")  # False
```

`is_valid_url()` - Checks an absolute HTTP or HTTPS URL.

```python
is_valid_url("https://example.com/path")  # True
is_valid_url("ftp://example.com/file")    # False
```

A valid result does not mean the host exists or is safe to request.

`is_blank()` - Returns `True` for `None`, an empty string, or a string that
contains only whitespace.

```python
is_blank(None)     # True
is_blank(" \t\n")  # True
is_blank([])       # False
```

`require_fields()` - Raises `ValueError` when a mapping is missing a required
field or the field is blank.

```python
require_fields(
    {"name": "Jordan", "active": False},
    ["name", "active"],
)
# No error
```

`0`, `False`, and empty collections count as present values.

## Collection helpers

These helpers work with finite iterables and do not change data passed by the
caller.

```python
from utilities.collections import (
    chunk,
    compact,
    deep_get,
    flatten,
    group_by,
    index_by,
    unique,
)
```

`chunk()` - Splits values into lists of a chosen size.

```python
chunk([1, 2, 3, 4, 5], size=2)
# [[1, 2], [3, 4], [5]]
```

`flatten()` - Flattens one nested level by default. Strings, bytes,
bytearrays, and mappings stay whole.

```python
flatten([[1, 2], [3, [4]]])
# [1, 2, 3, [4]]

flatten([[1, 2], [3, [4]]], depth=2)
# [1, 2, 3, 4]
```

`unique()` - Removes duplicates and keeps the first value. Lists and other
values that cannot be hashed are supported.

```python
unique([3, 1, 3, 2, 1])
# [3, 1, 2]
```

`compact()` - Removes `None` and blank strings. It keeps `0`, `False`, and
empty collections unless `remove_falsy=True`.

```python
compact([None, "", "value", 0, False])
# ["value", 0, False]
```

`deep_get()` - Gets a value from nested mappings with keys separated by dots.

```python
deep_get({"user": {"name": "Jordan"}}, "user.name")
# "Jordan"

deep_get({}, "user.name", default="unknown")
# "unknown"
```

`group_by()` - Groups items by a mapping field or a function.

```python
items = [
    {"name": "Ada", "role": "admin"},
    {"name": "Grace", "role": "user"},
    {"name": "Linus", "role": "admin"},
]
group_by(items, "role")
# {"admin": [items[0], items[2]], "user": [items[1]]}
```

`index_by()` - Builds a dictionary by a mapping field or a function.
Duplicate keys raise `ValueError`.

```python
items = [
    {"id": "a", "name": "Ada"},
    {"id": "b", "name": "Grace"},
]
index_by(items, "id")
# {"a": items[0], "b": items[1]}
```

## Number helpers

These helpers accept integers and floats. Booleans are not treated as numbers.

```python
from utilities.numbers import between, clamp, percentage, safe_float, safe_int
```

`clamp()` - Keeps a number inside an inclusive range.

```python
clamp(120, minimum=0, maximum=100)
# 100
```

`percentage()` - Returns one number as a percentage of another.

```python
percentage(1, 4)
# 25.0
```

A zero denominator raises `ZeroDivisionError`.

`safe_int()` - Converts an integer or an ASCII decimal integer string. Invalid
input returns the chosen default.

```python
safe_int("  -42 ")                 # -42
safe_int("not-a-number", default=0)  # 0
```

`safe_float()` - Converts a finite float, integer, or ASCII decimal string.
NaN, infinity, overflow, and invalid input return the chosen default.

```python
safe_float("-1.5e2")             # -150.0
safe_float("NaN", default=0.0)   # 0.0
```

`between()` - Checks whether a number is inside a range. Both ends are
included by default.

```python
between(5, minimum=0, maximum=10)
# True

between(0, minimum=0, maximum=10, inclusive_minimum=False)
# False
```

## Project structure

Public helpers live in `utilities/`. Tests live in `tests/`.

The modules use standard Python values and have no framework dependencies.
