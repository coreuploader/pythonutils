"""Helpers for working with collections and iterables."""

from collections.abc import Callable, Iterable, Iterator, Mapping
from typing import TypeVar

from utilities.validation import is_blank


_T = TypeVar("_T")
_K = TypeVar("_K")


def chunk(values: Iterable[_T], size: int) -> list[list[_T]]:
    """Split an iterable into ordered lists of at most ``size`` items.

    The function reads the iterable once and keeps its order. The final chunk
    may be smaller than ``size``. It does not change data passed by the caller.
    Strings and bytes use their normal Python iteration behavior.

    Args:
        values: Iterable whose items should be grouped.
        size: Maximum number of items in each result list.

    Returns:
        A new list containing new chunk lists.

    Raises:
        TypeError: If ``values`` is not iterable or ``size`` is not an integer.
            Booleans are not accepted as integer sizes.
        ValueError: If ``size`` is not positive.
    """
    if isinstance(size, bool) or not isinstance(size, int):
        raise TypeError("size must be an integer")
    if size <= 0:
        raise ValueError("size must be positive")

    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    result: list[list[_T]] = []
    current_chunk: list[_T] = []

    for value in iterator:
        current_chunk.append(value)
        if len(current_chunk) == size:
            result.append(current_chunk)
            current_chunk = []

    if current_chunk:
        result.append(current_chunk)

    return result


def flatten(values: Iterable[object], *, depth: int = 1) -> list[object]:
    """Flatten up to ``depth`` levels of nested iterables.

    One nesting level is flattened by default. A depth of zero returns the
    outer iterable's items unchanged. Item order is preserved. Each outer or
    nested iterable that is flattened is read once.

    Strings, bytes, bytearrays, and mappings are always treated as atomic
    values, including when supplied as the outer value. This prevents text,
    binary data, and mapping keys from being split unexpectedly. Other nested
    iterables, including generators, tuples, sets, and ranges, are flattened;
    their existing iteration order is retained. The function does not change
    data passed by the caller, but it does not copy the contained objects.

    Args:
        values: Iterable containing values to flatten.
        depth: Maximum number of nested iterable levels to flatten.

    Returns:
        A new list containing the resulting values.

    Raises:
        TypeError: If ``values`` is not iterable or ``depth`` is not an integer.
            Booleans are not accepted as integer depths.
        ValueError: If ``depth`` is negative.
    """
    if isinstance(depth, bool) or not isinstance(depth, int):
        raise TypeError("depth must be an integer")
    if depth < 0:
        raise ValueError("depth must not be negative")

    if _is_atomic_iterable(values):
        return [values]

    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    return list(_flatten_iterator(iterator, depth))


def unique(values: Iterable[_T]) -> list[_T]:
    """Return the first copy of each value while keeping the original order.

    Values are compared with normal Python hashing and equality rules. A set
    tracks values that can be hashed. Other values are compared for equality,
    which can be slower when there are many different values. The input is read
    once and is not changed. Returned objects are not copied.

    Strings and bytes follow their normal iteration behavior. For example,
    unique characters or byte integers are returned in their original order.

    Args:
        values: Finite iterable whose duplicate values should be removed.

    Returns:
        A new list containing the first copy of each distinct value.

    Raises:
        TypeError: If ``values`` is not iterable.
    """
    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    result: list[_T] = []
    seen_hashable: set[object] = set()
    seen_unhashable: list[_T] = []

    for value in iterator:
        try:
            hash(value)
        except TypeError:
            if _contains_equal(result, value):
                continue
            seen_unhashable.append(value)
        else:
            if value in seen_hashable or _contains_equal(seen_unhashable, value):
                continue
            seen_hashable.add(value)

        result.append(value)

    return result


def compact(
    values: Iterable[_T],
    *,
    remove_falsy: bool = False,
) -> list[_T]:
    """Remove selected empty values while preserving order.

    By default, only ``None``, empty strings, and strings containing only
    Unicode whitespace are removed. Zero, ``False``, empty containers, and
    empty bytes are preserved. Set ``remove_falsy`` to ``True`` to also remove
    those values according to normal Python truth testing. Blank strings are
    removed in either mode.

    The input is read once and is not changed. Retained objects are returned
    without being copied.
    Strings and bytes follow their normal iteration behavior.

    Args:
        values: Iterable containing values to filter.
        remove_falsy: Also remove values whose truth value is false.

    Returns:
        A new list of retained values in their original order.

    Raises:
        TypeError: If ``values`` is not iterable or ``remove_falsy`` is not a
            boolean.
    """
    if not isinstance(remove_falsy, bool):
        raise TypeError("remove_falsy must be a boolean")

    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    result: list[_T] = []
    for value in iterator:
        if is_blank(value):
            continue
        if remove_falsy and not value:
            continue
        result.append(value)

    return result


def deep_get(
    data: Mapping[str, object],
    path: str,
    *,
    default: object = None,
) -> object:
    """Retrieve a nested mapping value using a simple dotted key path.

    Each path segment must contain text and is used as a literal mapping key.
    Dots in
    key names cannot be escaped, and sequence indexes or object attributes are
    not supported. If a key is absent or an intermediate value is not a
    mapping, ``default`` is returned unchanged. A present final value, including
    ``None``, is returned unchanged.

    The input mappings are not modified and returned objects are not copied.

    Args:
        data: Root mapping to traverse.
        path: Mapping keys separated by dots. Each key must contain text.
        default: Value returned when the path cannot be resolved.

    Returns:
        The resolved value or ``default``.

    Raises:
        TypeError: If ``data`` is not a mapping or ``path`` is not a string.
        ValueError: If ``path`` is empty or contains an empty segment.
    """
    if not isinstance(data, Mapping):
        raise TypeError("data must be a mapping")
    if not isinstance(path, str):
        raise TypeError("path must be a string")

    segments = path.split(".")
    if not path or any(not segment for segment in segments):
        raise ValueError(
            "path must contain keys separated by dots, and each key must not "
            "be empty"
        )

    current: object = data
    for segment in segments:
        if not isinstance(current, Mapping) or segment not in current:
            return default
        current = current[segment]

    return current


def group_by(
    values: Iterable[_T],
    key: str | Callable[[_T], _K],
) -> dict[object, list[_T]]:
    """Group iterable items by a mapping field or callable result.

    A string selector reads that exact key from every mapping item. A callable
    selector receives each item and its return value becomes the group key.
    Dotted paths, attributes, and fallback selection are not inferred.

    Group keys must be hashable. Groups appear in the order their keys are first
    found, and items within each group keep their input order. The iterable is
    read once and is not changed. Result lists are new, but grouped items are
    not copied.

    Args:
        values: Iterable of items to group.
        key: Mapping field name that is not empty, or a callable selector.

    Returns:
        A new dictionary mapping selected keys to new item lists.

    Raises:
        TypeError: If ``values`` is not iterable, ``key`` is unsupported, a
            field selector receives an item that is not a mapping, or a
            selected key cannot be hashed.
        ValueError: If a string field selector is empty.
        KeyError: If a mapping item does not contain the selected field.

    Exceptions raised by a callable selector propagate unchanged.
    """
    field_name, selector = _prepare_key_selector(key)

    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    groups: dict[object, list[_T]] = {}
    for index, item in enumerate(iterator):
        group_key = _select_item_key(item, index, field_name, selector)

        try:
            hash(group_key)
        except TypeError:
            raise TypeError(
                f"group key for item at index {index} must be hashable"
            ) from None

        groups.setdefault(group_key, []).append(item)

    return groups


def index_by(
    values: Iterable[_T],
    key: str | Callable[[_T], _K],
) -> dict[object, _T]:
    """Index iterable items by a mapping field or callable result.

    Selection matches :func:`group_by`: a string reads that exact key from each
    mapping item, while a callable receives each item. Selected keys must be
    hashable. Duplicate keys raise ``ValueError`` so an item is never silently
    replaced.

    Keys follow the order of the input items. The iterable is read once and is
    not changed. The returned dictionary is new, but its item values are not
    copied.

    Args:
        values: Iterable of items to index.
        key: Mapping field name that is not empty, or a callable selector.

    Returns:
        A new dictionary mapping each selected key to exactly one item.

    Raises:
        TypeError: If ``values`` is not iterable, ``key`` is unsupported, a
            field selector receives an item that is not a mapping, or a
            selected key cannot be hashed.
        ValueError: If a field selector is empty or a selected key is repeated.
        KeyError: If a mapping item does not contain the selected field.

    Exceptions raised by a callable selector propagate unchanged.
    """
    field_name, selector = _prepare_key_selector(key)

    try:
        iterator = iter(values)
    except TypeError:
        raise TypeError("values must be iterable") from None

    result: dict[object, _T] = {}
    for index, item in enumerate(iterator):
        index_key = _select_item_key(item, index, field_name, selector)

        try:
            hash(index_key)
        except TypeError:
            raise TypeError(
                f"index key for item at index {index} must be hashable"
            ) from None

        if index_key in result:
            raise ValueError(f"duplicate key {index_key!r} at item index {index}")
        result[index_key] = item

    return result


def _flatten_iterator(
    values: Iterator[object],
    depth: int,
) -> Iterator[object]:
    """Yield values while flattening no more than the requested depth."""
    for value in values:
        if depth > 0 and isinstance(value, Iterable) and not _is_atomic_iterable(
            value
        ):
            yield from _flatten_iterator(iter(value), depth - 1)
        else:
            yield value


def _is_atomic_iterable(value: object) -> bool:
    """Return whether an iterable should remain a single flattened value."""
    return isinstance(value, (str, bytes, bytearray, Mapping))


def _contains_equal(values: Iterable[object], candidate: object) -> bool:
    """Return whether an existing value compares equal to a candidate."""
    return any(existing == candidate for existing in values)


def _prepare_key_selector(
    key: object,
) -> tuple[str | None, Callable[[object], object] | None]:
    """Validate and normalize the selector shared by grouping helpers."""
    if isinstance(key, str):
        if not key:
            raise ValueError("key field name must not be empty")
        return key, None
    if callable(key):
        return None, key
    raise TypeError("key must be a field name string or callable")


def _select_item_key(
    item: object,
    index: int,
    field_name: str | None,
    selector: Callable[[object], object] | None,
) -> object:
    """Select one item's key with consistent indexed field errors."""
    if field_name is None:
        assert selector is not None
        return selector(item)

    if not isinstance(item, Mapping):
        raise TypeError(
            f"item at index {index} must be a mapping when key is a field name"
        )
    if field_name not in item:
        raise KeyError(f"item at index {index} is missing field {field_name!r}")
    return item[field_name]
