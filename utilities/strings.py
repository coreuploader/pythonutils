"""String normalization and transformation helpers."""

import secrets
import unicodedata
from datetime import date, datetime, timezone


_UNICODE_NORMALIZATION_FORMS = frozenset({"NFC", "NFD", "NFKC", "NFKD"})
_SLUG_SEPARATORS = frozenset({"-", "_"})
_REFERENCE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def generate_reference(
    prefix: str | None = None,
    *,
    reference_date: date | None = None,
    random_length: int = 6,
) -> str:
    """Generate a readable reference using secure random characters.

    References use ``[PREFIX-]YYYYMMDD-TOKEN``. A prefix is optional, may use
    only ASCII letters and numbers, and is converted to uppercase. Tokens omit
    visually ambiguous ``I``, ``O``, ``0``, and ``1`` characters. When no date
    is supplied, the current UTC calendar date is used.

    Args:
        prefix: An optional label made of ASCII letters and numbers. It must
            not be empty.
        reference_date: An optional calendar date, primarily useful for
            deterministic generation and testing. Datetime values are rejected
            so their timezone cannot be interpreted accidentally.
        random_length: The positive number of random token characters. The
            default is six.

    Returns:
        A readable reference string.

    Raises:
        TypeError: If an argument has an invalid type. Booleans are not accepted
            as integer lengths.
        ValueError: If the prefix format or random length is invalid.

    Secure randomness makes references difficult to predict, but this function
    does not guarantee global uniqueness. Callers must enforce uniqueness where
    their application requires it.
    """
    if prefix is not None:
        if not isinstance(prefix, str):
            raise TypeError("prefix must be a string or None")
        if not prefix or not prefix.isascii() or not prefix.isalnum():
            raise ValueError(
                "prefix must not be empty and may contain only ASCII letters "
                "and numbers"
            )

    if reference_date is not None:
        if isinstance(reference_date, datetime) or not isinstance(
            reference_date,
            date,
        ):
            raise TypeError("reference_date must be a date or None")

    if isinstance(random_length, bool) or not isinstance(random_length, int):
        raise TypeError("random_length must be an integer")
    if random_length <= 0:
        raise ValueError("random_length must be positive")

    selected_date = reference_date or datetime.now(timezone.utc).date()
    random_token = "".join(
        secrets.choice(_REFERENCE_ALPHABET) for _ in range(random_length)
    )
    reference_parts = [selected_date.strftime("%Y%m%d"), random_token]

    if prefix is not None:
        reference_parts.insert(0, prefix.upper())

    return "-".join(reference_parts)


def mask_phone(phone: str, visible_digits: int = 4) -> str:
    """Mask a phone number while keeping some digits visible at the end.

    Unicode decimal digits are counted from right to left. Up to
    ``visible_digits`` trailing digits remain visible, while at least one digit
    is always masked. Other characters, including spaces, punctuation, and a
    leading plus sign, stay unchanged.

    This function does not normalize or validate a telephone number. In
    particular, preserved punctuation and text are not evidence of a valid
    international or national format.

    Args:
        phone: The phone number text to mask.
        visible_digits: The maximum number of trailing digits to reveal. It
            must be zero or greater. The default is four.

    Returns:
        The masked value with its original formatting.

    Raises:
        TypeError: If ``phone`` is not a string or ``visible_digits`` is not an
            integer. Booleans are not accepted as integers.
        ValueError: If ``visible_digits`` is negative or ``phone`` contains no
            Unicode decimal digits.

    Masking is intended for safer display. It is not encryption and is not a
    secure storage mechanism.
    """
    if not isinstance(phone, str):
        raise TypeError("phone must be a string")

    if isinstance(visible_digits, bool) or not isinstance(visible_digits, int):
        raise TypeError("visible_digits must be an integer")

    if visible_digits < 0:
        raise ValueError("visible_digits must be zero or greater")

    digit_count = sum(character.isdecimal() for character in phone)
    if digit_count == 0:
        raise ValueError("phone must contain at least one decimal digit")

    visible_count = min(visible_digits, digit_count - 1)
    digits_to_mask = digit_count - visible_count
    digits_seen = 0
    masked_characters: list[str] = []

    for character in phone:
        if not character.isdecimal():
            masked_characters.append(character)
            continue

        if digits_seen < digits_to_mask:
            masked_characters.append("*")
        else:
            masked_characters.append(character)
        digits_seen += 1

    return "".join(masked_characters)


def mask_email(email: str) -> str:
    """Mask an email address's local part for display.

    The address is split at its final ``@``. For local parts longer than one
    Unicode code point, the first code point remains visible and every
    remaining code point becomes ``*``. A local part with one code point is
    masked completely. The domain is returned unchanged.

    This function only requires local and domain parts that are not empty. It
    validate email syntax, confirm that the mailbox exists, or establish
    ownership.

    Args:
        email: The email address text to mask.

    Returns:
        The masked value.

    Raises:
        TypeError: If ``email`` is not a string.
        ValueError: If no final separator or a blank local or domain part is
            present.

    Masking is intended for safer display. It is not encryption and is not a
    secure storage mechanism.
    """
    if not isinstance(email, str):
        raise TypeError("email must be a string")

    local_part, separator, domain = email.rpartition("@")
    if not separator or not local_part or not domain:
        raise ValueError(
            "email must contain local and domain parts that are not empty"
        )

    if len(local_part) == 1:
        masked_local_part = "*"
    else:
        masked_local_part = f"{local_part[0]}{'*' * (len(local_part) - 1)}"

    return f"{masked_local_part}@{domain}"


def truncate(text: str, length: int, suffix: str = "...") -> str:
    """Shorten text to at most ``length`` Unicode code points.

    The suffix counts toward the maximum length. Truncation occurs at an exact
    Unicode code point boundary rather than a word or displayed character
    boundary. If the input already fits, it is returned unchanged.

    Args:
        text: The string to shorten.
        length: The maximum result length. It must be zero or greater.
        suffix: Text appended when truncation occurs. The default is ``...``.

    Returns:
        The original string when it fits, otherwise a shortened string ending
        with ``suffix``.

    Raises:
        TypeError: If argument types are invalid. Booleans are not accepted as
            integer lengths.
        ValueError: If ``length`` is negative, or truncation is needed and the
            suffix is longer than ``length``.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if isinstance(length, bool) or not isinstance(length, int):
        raise TypeError("length must be an integer")

    if not isinstance(suffix, str):
        raise TypeError("suffix must be a string")

    if length < 0:
        raise ValueError("length must be zero or greater")

    if len(text) <= length:
        return text

    if len(suffix) > length:
        raise ValueError("suffix cannot be longer than length when truncating")

    content_length = length - len(suffix)
    return f"{text[:content_length]}{suffix}"


def slugify(text: str, separator: str = "-") -> str:
    """Return a lowercase slug that keeps Unicode letters and numbers.

    Text is normalized with NFKC and converted with ``casefold()``. Unicode
    letters, combining
    marks, and decimal digits are preserved without transliteration. Every run
    of other characters becomes one separator, and separators are omitted from
    the beginning and end of the result.

    Args:
        text: The string to convert.
        separator: Either ``-`` (the default) or ``_``.

    Returns:
        The generated slug. Empty input or input containing only punctuation
        produces an empty string.

    Raises:
        TypeError: If ``text`` or ``separator`` is not a string.
        ValueError: If ``separator`` is not ``-`` or ``_``.

    Compatibility normalization and ``casefold()`` can change some characters,
    such as full width Latin text and ``ß``. No transliteration is performed.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not isinstance(separator, str):
        raise TypeError("separator must be a string")

    if separator not in _SLUG_SEPARATORS:
        raise ValueError("separator must be '-' or '_'")

    normalized_text = unicodedata.normalize("NFKC", text).casefold()
    slug_characters: list[str] = []
    separator_pending = False

    for character in normalized_text:
        category = unicodedata.category(character)

        if category.startswith(("L", "M")) or category == "Nd":
            if separator_pending and slug_characters:
                slug_characters.append(separator)
            slug_characters.append(character)
            separator_pending = False
        else:
            separator_pending = True

    return "".join(slug_characters)


def normalize_whitespace(text: str) -> str:
    """Collapse Unicode whitespace runs and strip surrounding whitespace.

    Python's Unicode whitespace rules are used. Spaces, tabs, line
    breaks, and other Unicode whitespace are replaced by a single ASCII space
    between other content. Leading and trailing whitespace is removed. Other
    characters are returned unchanged.

    Args:
        text: The string whose whitespace should be normalized.

    Returns:
        The normalized string, or an empty string when the input contains only
        whitespace.

    Raises:
        TypeError: If ``text`` is not a string.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    return " ".join(text.split())


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """Return text normalized to a supported Unicode normalization form.

    Args:
        text: The string to normalize.
        form: One of ``NFC``, ``NFD``, ``NFKC``, or ``NFKD``. The default is
            canonical composition (``NFC``).

    Returns:
        The normalized string.

    Raises:
        TypeError: If ``text`` or ``form`` is not a string.
        ValueError: If ``form`` is not one of the supported uppercase names.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    if not isinstance(form, str):
        raise TypeError("form must be a string")

    if form not in _UNICODE_NORMALIZATION_FORMS:
        supported_forms = ", ".join(sorted(_UNICODE_NORMALIZATION_FORMS))
        raise ValueError(
            f"form must be one of: {supported_forms}; received {form!r}"
        )

    return unicodedata.normalize(form, text)
