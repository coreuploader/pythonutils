"""Input validation helpers for Python applications."""

import ipaddress
import string
import unicodedata
from collections.abc import Iterable, Mapping
from urllib.parse import urlsplit


_ASCII_PUNCTUATION = frozenset(string.punctuation)
_ALLOWED_CONTROL_WHITESPACE = frozenset({"\t", "\n", "\r"})
_EMAIL_LOCAL_ASCII = frozenset(
    string.ascii_letters + string.digits + "!#$%&'*+-/=?^_`{|}~"
)
_URL_SCHEMES = frozenset({"http", "https"})


def is_blank(value: object) -> bool:
    """Return whether ``value`` is ``None`` or contains only whitespace.

    Empty strings are blank. Whitespace follows Python's Unicode rules through
    :meth:`str.strip`. Other values,
    including empty collections, bytes, zero, and ``False``, are not blank.
    """
    return value is None or (isinstance(value, str) and not value.strip())


def require_fields(
    data: Mapping[str, object],
    required_fields: Iterable[str],
) -> None:
    """Require mapping fields to be present and nonblank.

    A field is missing when its key is absent or its value satisfies
    :func:`is_blank`. Consequently, ``None`` and blank strings are missing,
    while values such as zero, ``False``, and empty collections are present.
    Each requested field is checked once, in the order first given.

    Args:
        data: Mapping containing the values to check.
        required_fields: Iterable of string keys in reporting order.

    Raises:
        TypeError: If ``data`` is not a mapping, ``required_fields`` is a
            string or is not iterable, or a requested field is not a string.
        ValueError: If any required field is absent or blank. All such fields
            are listed in the order they were requested.
    """
    if not isinstance(data, Mapping):
        raise TypeError("data must be a mapping")
    if isinstance(required_fields, (str, bytes)) or not isinstance(
        required_fields, Iterable
    ):
        raise TypeError("required_fields must be an iterable, not a string")

    ordered_fields: list[str] = []
    seen_fields: set[str] = set()
    for field in required_fields:
        if not isinstance(field, str):
            raise TypeError("required_fields must contain only strings")
        if field not in seen_fields:
            ordered_fields.append(field)
            seen_fields.add(field)

    missing_fields = [
        field
        for field in ordered_fields
        if field not in data or is_blank(data[field])
    ]
    if missing_fields:
        formatted_fields = ", ".join(repr(field) for field in missing_fields)
        raise ValueError(f"Required fields are missing or blank: {formatted_fields}")


def is_valid_email(value: object) -> bool:
    """Return whether ``value`` has practical email address syntax.

    The accepted form has an unquoted local part, ``@``, and a hostname. Dots
    may separate parts of the local name. Common ASCII punctuation and
    printable international characters are supported. International hostnames
    are checked with Python's IDNA codec. Hostnames with one label are accepted
    for private applications. IP addresses and quoted local parts are not.

    This is syntax validation only. It does not prove that a mailbox exists,
    accepts delivery, or belongs to a particular user.
    """
    if not isinstance(value, str):
        return False

    try:
        encoded_value = value.encode("utf-8")
    except UnicodeEncodeError:
        return False

    if not encoded_value or len(encoded_value) > 254 or value.count("@") != 1:
        return False

    local_part, domain = value.split("@")
    if not _is_valid_email_local_part(local_part) or not domain:
        return False

    try:
        ascii_domain = domain.encode("idna").decode("ascii")
    except UnicodeError:
        return False

    if len(ascii_domain) > 253:
        return False

    labels = ascii_domain.split(".")
    return all(_is_valid_hostname_label(label) for label in labels)


def is_valid_phone(value: object) -> bool:
    """Return whether ``value`` uses the supported international phone format.

    Accepted values consist of ``+`` followed by 8 to 15 ASCII digits. The
    first digit after ``+`` must be from 1 through 9. The format is based on
    E.164 and the input must already be normalized. Spaces, punctuation,
    extensions, national prefixes, and Unicode digits are not accepted.

    This function checks format only. It does not confirm that a country code
    or telephone number is assigned, reachable, or owned by a user.
    """
    if not isinstance(value, str):
        return False
    if not 9 <= len(value) <= 16:
        return False
    if value[0] != "+" or value[1] not in "123456789":
        return False
    return all(character in string.digits for character in value[1:])


def is_valid_url(value: object) -> bool:
    """Return whether ``value`` is a supported absolute HTTP(S) URL.

    Only ``http`` and ``https`` schemes are accepted. A hostname is required;
    international hostnames, hostnames with one label, IPv4 addresses, and
    bracketed IPv6 addresses are supported. Explicit ports must be between 1
    and 65535. Raw whitespace and control characters are rejected rather than
    stripped. Encode them with percent escapes where appropriate.

    This function validates URL structure only. It does not establish that the
    host exists, is reachable, or is safe to request.
    """
    if not isinstance(value, str) or not value:
        return False
    if any(
        character.isspace() or unicodedata.category(character).startswith("C")
        for character in value
    ):
        return False
    if "\\" in value:
        return False
    if not _has_valid_percent_escapes(value):
        return False

    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except (UnicodeError, ValueError):
        return False

    if parsed.scheme.lower() not in _URL_SCHEMES or not parsed.netloc:
        return False
    if parsed.netloc.count("@") > 1:
        return False
    if hostname is None or not _is_valid_url_hostname(hostname):
        return False

    authority = parsed.netloc.rsplit("@", maxsplit=1)[-1]
    if authority.endswith(":"):
        return False
    return port is None or 1 <= port <= 65535


def validate_text(
    text: str,
    *,
    allow_currency: bool = True,
    allow_ascii_punctuation: bool = True,
    allow_whitespace: bool = True,
) -> str:
    """Validate and return text using Unicode character categories.

    Letters, combining marks, and decimal digits from every Unicode script are
    always accepted. Currency symbols, ASCII punctuation, and whitespace are
    accepted by default and may be disabled independently. Allowed whitespace
    consists of Unicode separators plus tab, line feed, and carriage return.

    Empty strings are valid. The returned string is unchanged; this function
    does not normalize or sanitize input.

    Args:
        text: The string to validate.
        allow_currency: Accept characters in Unicode category ``Sc``.
        allow_ascii_punctuation: Accept characters in ``string.punctuation``.
        allow_whitespace: Accept Unicode separators, tabs, line feeds, and
            carriage returns.

    Returns:
        The original validated string.

    Raises:
        TypeError: If ``text`` is not a string or an option is not a boolean.
        ValueError: If the string contains a character that is not allowed.

    Character validation is not sanitization and does not protect against
    security risks tied to its use, such as SQL, HTML, or command injection.
    """
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    _require_bool("allow_currency", allow_currency)
    _require_bool("allow_ascii_punctuation", allow_ascii_punctuation)
    _require_bool("allow_whitespace", allow_whitespace)

    for index, character in enumerate(text):
        category = unicodedata.category(character)

        if category.startswith(("L", "M")) or category == "Nd":
            continue

        if category == "Sc":
            if allow_currency:
                continue
            _raise_invalid_character(character, category, index)

        if character in _ASCII_PUNCTUATION:
            if allow_ascii_punctuation:
                continue
            _raise_invalid_character(character, category, index)

        if category.startswith("Z") or character in _ALLOWED_CONTROL_WHITESPACE:
            if allow_whitespace:
                continue
            _raise_invalid_character(character, category, index)

        _raise_invalid_character(character, category, index)

    return text


def is_valid_text(
    text: object,
    *,
    allow_currency: bool = True,
    allow_ascii_punctuation: bool = True,
    allow_whitespace: bool = True,
) -> bool:
    """Return whether a value follows the rules in :func:`validate_text`.

    Unlike :func:`validate_text`, this convenience function returns ``False``
    for values that are not strings and options with the wrong type.
    """
    try:
        validate_text(
            text,  # type: ignore[arg-type]
            allow_currency=allow_currency,
            allow_ascii_punctuation=allow_ascii_punctuation,
            allow_whitespace=allow_whitespace,
        )
    except (TypeError, ValueError):
        return False

    return True


def _is_valid_email_local_part(local_part: str) -> bool:
    """Validate an unquoted email local part."""
    try:
        encoded_local_part = local_part.encode("utf-8")
    except UnicodeEncodeError:
        return False

    if not encoded_local_part or len(encoded_local_part) > 64:
        return False

    atoms = local_part.split(".")
    if any(not atom for atom in atoms):
        return False

    for character in local_part:
        if character == ".":
            continue
        if character.isascii():
            if character not in _EMAIL_LOCAL_ASCII:
                return False
        elif not character.isprintable() or character.isspace():
            return False

    return True


def _is_valid_hostname_label(label: str) -> bool:
    """Validate one ASCII hostname label produced by IDNA encoding."""
    if not 1 <= len(label) <= 63:
        return False
    if label.startswith("-") or label.endswith("-"):
        return False
    return all(
        (character.isascii() and character.isalnum()) or character == "-"
        for character in label
    )


def _is_valid_url_hostname(hostname: str) -> bool:
    """Validate an IP address or IDNA hostname from a parsed URL."""
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        pass
    else:
        return True

    if all(character in string.digits + "." for character in hostname):
        return False

    try:
        ascii_hostname = hostname.encode("idna").decode("ascii")
    except UnicodeError:
        return False

    if len(ascii_hostname) > 253:
        return False
    return all(
        _is_valid_hostname_label(label) for label in ascii_hostname.split(".")
    )


def _has_valid_percent_escapes(value: str) -> bool:
    """Return whether every percent sign begins a two digit hex escape."""
    for index, character in enumerate(value):
        if character != "%":
            continue
        escape = value[index + 1 : index + 3]
        if len(escape) != 2 or any(
            digit not in string.hexdigits for digit in escape
        ):
            return False
    return True


def _require_bool(name: str, value: object) -> None:
    """Require an option to be ``True`` or ``False``."""
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a boolean")


def _raise_invalid_character(
    character: str,
    category: str,
    index: int,
) -> None:
    """Raise an error that describes a character that is not allowed."""
    code_point = f"U+{ord(character):04X}"
    raise ValueError(
        f"Invalid character: {character!r} "
        f"({code_point}, category={category}, index={index})"
    )
