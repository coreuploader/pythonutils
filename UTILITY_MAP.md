# Utility Map

Use this page to find an existing helper before writing a new one. Reuse a
helper when its documented behavior matches the task. Read its docstring or the
[README](README.md) before relying on details that are not listed here.

Import helpers from the module shown in each table. Do not assume that a
validator performs security checks or verifies that an email address, phone
number, or URL exists.

## String helpers

| Need | Use | Import from | Important behavior |
| --- | --- | --- | --- |
| Normalize Unicode text | `normalize_unicode()` | `utilities.strings` | Uses NFC by default and supports NFC, NFD, NFKC, and NFKD. |
| Clean up whitespace | `normalize_whitespace()` | `utilities.strings` | Trims the ends and changes each whitespace run to one space. |
| Create a slug | `slugify()` | `utilities.strings` | Keeps Unicode letters and numbers. It does not transliterate text. |
| Shorten text | `truncate()` | `utilities.strings` | The suffix counts toward the requested length. |
| Mask an email address | `mask_email()` | `utilities.strings` | Masks the local part for display. It does not validate the address. |
| Mask a phone number | `mask_phone()` | `utilities.strings` | Keeps a chosen number of trailing digits. It does not validate the number. |
| Create a readable reference | `generate_reference()` | `utilities.strings` | Uses secure randomness but does not guarantee uniqueness. |

## Datetime helpers

| Need | Use | Import from | Important behavior |
| --- | --- | --- | --- |
| Get the current UTC time | `utc_now()` | `utilities.datetime` | Returns a UTC datetime with timezone information. |
| Get UTC fields without timezone data | `naive_utc_now()` | `utilities.datetime` | Intended for database columns or drivers that cannot store timezone data. |
| Convert a datetime to UTC | `ensure_utc()` | `utilities.datetime` | Rejects datetimes without timezone information. |
| Convert to another timezone | `to_timezone()` | `utilities.datetime` | Accepts an IANA name such as `Asia/Manila`. |
| Parse a datetime string | `parse_datetime()` | `utilities.datetime` | Accepts the documented ISO 8601 forms with an explicit offset and returns UTC. |
| Format a datetime | `format_datetime()` | `utilities.datetime` | Converts to the requested timezone before formatting. |
| Find the start of a local day | `start_of_day()` | `utilities.datetime` | Keeps the existing timezone and local date. |
| Find the end of a local day | `end_of_day()` | `utilities.datetime` | Keeps the existing timezone and local date. |
| Check whether a time has passed | `is_expired()` | `utilities.datetime` | Accepts a reference time for deterministic tests. Equality counts as expired. |
| Get elapsed seconds | `seconds_between()` | `utilities.datetime` | Returns a signed, unrounded duration between aware datetimes. |
| Get elapsed minutes | `minutes_between()` | `utilities.datetime` | Returns a signed, unrounded duration between aware datetimes. |
| Get elapsed 24 hour days | `days_between()` | `utilities.datetime` | Measures duration, not local calendar boundaries. |

## Validation helpers

| Need | Use | Import from | Important behavior |
| --- | --- | --- | --- |
| Validate allowed text characters | `validate_text()` | `utilities.validation` | Returns the text or raises an error that identifies the invalid character. |
| Check allowed text characters | `is_valid_text()` | `utilities.validation` | Uses the same rules as `validate_text()` and returns a boolean. |
| Check email syntax | `is_valid_email()` | `utilities.validation` | Checks syntax only. It does not verify the mailbox or its owner. |
| Check phone number format | `is_valid_phone()` | `utilities.validation` | Accepts `+` followed by 8 to 15 ASCII digits, with no spaces or punctuation. |
| Check URL structure | `is_valid_url()` | `utilities.validation` | Accepts absolute HTTP and HTTPS URLs only. It does not test the connection. |
| Check for a blank value | `is_blank()` | `utilities.validation` | Treats `None`, an empty string, or a string containing only whitespace as blank. |
| Require mapping fields | `require_fields()` | `utilities.validation` | Raises `ValueError` when a requested key is absent or blank. |

## Collection helpers

| Need | Use | Import from | Important behavior |
| --- | --- | --- | --- |
| Split items into groups | `chunk()` | `utilities.collections` | Keeps input order and rejects sizes below one. |
| Flatten nested items | `flatten()` | `utilities.collections` | Flattens one level by default. Text, bytes, bytearrays, and mappings stay whole. |
| Remove duplicate values | `unique()` | `utilities.collections` | Keeps the first copy of each value in its original order. |
| Remove blank values | `compact()` | `utilities.collections` | Keeps zero, `False`, empty containers, and empty bytes by default. |
| Read a nested mapping value | `deep_get()` | `utilities.collections` | Uses keys separated by dots and returns a chosen default when a path is missing. |
| Group items by a key | `group_by()` | `utilities.collections` | Accepts a mapping field name or callable and keeps input order. |
| Index items by a key | `index_by()` | `utilities.collections` | Accepts a mapping field name or callable and raises an error for duplicate keys. |

## Number helpers

| Need | Use | Import from | Important behavior |
| --- | --- | --- | --- |
| Limit a number to a range | `clamp()` | `utilities.numbers` | Uses inclusive limits and rejects an invalid range. |
| Calculate a percentage | `percentage()` | `utilities.numbers` | Returns an unrounded float and raises an error when the whole is zero. |
| Convert supported input to an integer | `safe_int()` | `utilities.numbers` | Uses a chosen default for unsupported input and accepts only narrow decimal syntax. |
| Convert supported input to a float | `safe_float()` | `utilities.numbers` | Returns only finite floats and uses a chosen default for unsupported input. |
| Check whether a number is in a range | `between()` | `utilities.numbers` | Includes both limits by default. Each limit can be made exclusive. |
