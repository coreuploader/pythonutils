import unittest
from types import MappingProxyType

from utilities.collections import (
    chunk,
    compact,
    deep_get,
    flatten,
    group_by,
    index_by,
    unique,
)


class ChunkTests(unittest.TestCase):
    def test_splits_list_and_keeps_smaller_final_chunk(self) -> None:
        self.assertEqual(
            chunk([1, 2, 3, 4, 5], size=2),
            [[1, 2], [3, 4], [5]],
        )

    def test_preserves_encounter_order_for_tuple(self) -> None:
        self.assertEqual(
            chunk(("a", "b", "c", "d"), size=3),
            [["a", "b", "c"], ["d"]],
        )

    def test_eagerly_consumes_generator_once(self) -> None:
        visited: list[int] = []

        def generate_values():
            for value in range(5):
                visited.append(value)
                yield value

        values = generate_values()

        self.assertEqual(chunk(values, size=2), [[0, 1], [2, 3], [4]])
        self.assertEqual(visited, [0, 1, 2, 3, 4])
        self.assertEqual(list(values), [])

    def test_returns_empty_list_for_empty_iterables(self) -> None:
        self.assertEqual(chunk([], size=3), [])
        self.assertEqual(chunk(iter(()), size=3), [])

    def test_handles_size_equal_to_or_larger_than_input(self) -> None:
        self.assertEqual(chunk([1, 2, 3], size=3), [[1, 2, 3]])
        self.assertEqual(chunk([1, 2, 3], size=10), [[1, 2, 3]])

    def test_uses_normal_string_and_bytes_iteration(self) -> None:
        self.assertEqual(chunk("abcd", size=2), [["a", "b"], ["c", "d"]])
        self.assertEqual(chunk(b"abc", size=2), [[97, 98], [99]])

    def test_does_not_mutate_input_or_share_chunk_lists(self) -> None:
        values = [1, 2, 3, 4]

        result = chunk(values, size=2)
        result[0].append(99)

        self.assertEqual(values, [1, 2, 3, 4])
        self.assertEqual(result, [[1, 2, 99], [3, 4]])

    def test_rejects_non_positive_sizes(self) -> None:
        for size in [0, -1, -100]:
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError, "size must be positive"):
                    chunk([1, 2, 3], size=size)

    def test_rejects_non_integer_sizes_and_booleans(self) -> None:
        invalid_sizes = [True, False, 2.0, "2", None]

        for size in invalid_sizes:
            with self.subTest(size=size):
                with self.assertRaisesRegex(TypeError, "size must be an integer"):
                    chunk([1, 2, 3], size=size)  # type: ignore[arg-type]

    def test_rejects_non_iterable_values(self) -> None:
        invalid_values = [None, 123, 1.5, object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    chunk(value, size=2)  # type: ignore[arg-type]


class FlattenTests(unittest.TestCase):
    def test_flattens_one_level_by_default(self) -> None:
        values = [[1, 2], (3, 4), 5, [6]]

        self.assertEqual(flatten(values), [1, 2, 3, 4, 5, 6])

    def test_leaves_deeper_levels_nested_by_default(self) -> None:
        values = [[1, [2, 3]], [[4]], 5]

        self.assertEqual(flatten(values), [1, [2, 3], [4], 5])

    def test_supports_explicit_bounded_depth(self) -> None:
        values = [[1, [2, [3]]], 4]

        self.assertEqual(flatten(values, depth=0), [[1, [2, [3]]], 4])
        self.assertEqual(flatten(values, depth=1), [1, [2, [3]], 4])
        self.assertEqual(flatten(values, depth=2), [1, 2, [3], 4])
        self.assertEqual(flatten(values, depth=3), [1, 2, 3, 4])

    def test_keeps_text_binary_data_and_mappings_atomic(self) -> None:
        mapping = {"name": "Jordan"}
        values = [["hello", b"bytes", bytearray(b"data"), mapping]]

        self.assertEqual(
            flatten(values, depth=2),
            ["hello", b"bytes", bytearray(b"data"), mapping],
        )
        self.assertEqual(flatten("hello", depth=5), ["hello"])
        self.assertEqual(flatten(b"bytes", depth=5), [b"bytes"])
        self.assertEqual(flatten(mapping, depth=5), [mapping])

    def test_consumes_outer_and_nested_generators_once(self) -> None:
        outer_visited: list[int] = []
        inner_visited: list[int] = []

        def inner_values():
            for value in [1, 2]:
                inner_visited.append(value)
                yield value

        def outer_values():
            for value in [inner_values(), (3, 4)]:
                outer_visited.append(1)
                yield value

        values = outer_values()

        self.assertEqual(flatten(values), [1, 2, 3, 4])
        self.assertEqual(outer_visited, [1, 1])
        self.assertEqual(inner_visited, [1, 2])
        self.assertEqual(list(values), [])

    def test_returns_empty_list_for_empty_iterable(self) -> None:
        self.assertEqual(flatten([]), [])
        self.assertEqual(flatten(iter(()), depth=3), [])

    def test_does_not_mutate_nested_input_collections(self) -> None:
        first = [1, 2]
        second = [3, 4]
        values = [first, second]

        result = flatten(values)
        result.append(5)

        self.assertEqual(values, [[1, 2], [3, 4]])
        self.assertEqual(first, [1, 2])
        self.assertEqual(second, [3, 4])

    def test_rejects_negative_depth(self) -> None:
        with self.assertRaisesRegex(ValueError, "depth must not be negative"):
            flatten([[1]], depth=-1)

    def test_rejects_non_integer_depths_and_booleans(self) -> None:
        invalid_depths = [True, False, 1.0, "1", None]

        for depth in invalid_depths:
            with self.subTest(depth=depth):
                with self.assertRaisesRegex(TypeError, "depth must be an integer"):
                    flatten([[1]], depth=depth)  # type: ignore[arg-type]

    def test_rejects_non_iterable_values(self) -> None:
        invalid_values = [None, 123, 1.5, object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    flatten(value)  # type: ignore[arg-type]


class UniqueTests(unittest.TestCase):
    def test_removes_duplicates_and_preserves_first_occurrence_order(self) -> None:
        self.assertEqual(unique([3, 1, 3, 2, 1, 4, 2]), [3, 1, 2, 4])

    def test_supports_tuples_and_generators(self) -> None:
        self.assertEqual(unique(("a", "b", "a", "c")), ["a", "b", "c"])

        visited: list[int] = []

        def generate_values():
            for value in [1, 2, 1, 3]:
                visited.append(value)
                yield value

        values = generate_values()

        self.assertEqual(unique(values), [1, 2, 3])
        self.assertEqual(visited, [1, 2, 1, 3])
        self.assertEqual(list(values), [])

    def test_supports_unhashable_values(self) -> None:
        first_list = [1, 2]
        duplicate_list = [1, 2]
        first_mapping = {"name": "Jordan"}
        duplicate_mapping = {"name": "Jordan"}

        result = unique(
            [
                first_list,
                duplicate_list,
                first_mapping,
                duplicate_mapping,
                {1, 2},
                frozenset({1, 2}),
            ]
        )

        self.assertEqual(result, [first_list, first_mapping, {1, 2}])
        self.assertIs(result[0], first_list)
        self.assertIs(result[1], first_mapping)

    def test_uses_normal_python_equality_semantics(self) -> None:
        self.assertEqual(unique([1, True, 1.0, 2, False, 0]), [1, 2, False])

    def test_returns_empty_list_for_empty_iterables(self) -> None:
        self.assertEqual(unique([]), [])
        self.assertEqual(unique(iter(())), [])

    def test_uses_normal_string_and_bytes_iteration(self) -> None:
        self.assertEqual(unique("banana"), ["b", "a", "n"])
        self.assertEqual(unique(b"abaca"), [97, 98, 99])

    def test_does_not_mutate_input(self) -> None:
        values = [1, 2, 1]

        result = unique(values)
        result.append(3)

        self.assertEqual(values, [1, 2, 1])
        self.assertEqual(result, [1, 2, 3])

    def test_rejects_non_iterable_values(self) -> None:
        invalid_values = [None, 123, 1.5, object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    unique(value)  # type: ignore[arg-type]


class CompactTests(unittest.TestCase):
    def test_removes_none_empty_strings_and_whitespace_by_default(self) -> None:
        values = [None, "", "  ", "\t\n", "value", " another "]

        self.assertEqual(compact(values), ["value", " another "])

    def test_uses_unicode_aware_blank_string_policy(self) -> None:
        values = ["\u00a0", "\u2003\u2028", "\u200b", "text"]

        self.assertEqual(compact(values), ["\u200b", "text"])

    def test_preserves_other_falsy_values_by_default(self) -> None:
        values = [0, 0.0, False, [], {}, (), set(), b"", bytearray()]

        result = compact(values)

        self.assertEqual(result, values)
        for original, retained in zip(values, result):
            self.assertIs(retained, original)

    def test_can_deliberately_remove_all_falsy_values(self) -> None:
        values = [None, "", "  ", 0, 0.0, False, [], {}, (), b"", "value", 1]

        self.assertEqual(
            compact(values, remove_falsy=True),
            ["value", 1],
        )

    def test_preserves_order_for_tuple_and_consumes_generator_once(self) -> None:
        self.assertEqual(compact((None, "a", "", "b")), ["a", "b"])

        visited: list[object] = []

        def generate_values():
            for value in [None, 1, " ", 2]:
                visited.append(value)
                yield value

        values = generate_values()

        self.assertEqual(compact(values), [1, 2])
        self.assertEqual(visited, [None, 1, " ", 2])
        self.assertEqual(list(values), [])

    def test_returns_empty_list_for_empty_or_entirely_blank_input(self) -> None:
        self.assertEqual(compact([]), [])
        self.assertEqual(compact([None, "", "\n"]), [])

    def test_uses_normal_string_and_bytes_iteration(self) -> None:
        self.assertEqual(compact(" a "), ["a"])
        self.assertEqual(compact(b"\x00\x01", remove_falsy=True), [1])

    def test_does_not_mutate_input(self) -> None:
        values = [None, "value", 0]

        result = compact(values)
        result.append("new")

        self.assertEqual(values, [None, "value", 0])
        self.assertEqual(result, ["value", 0, "new"])

    def test_rejects_non_boolean_option(self) -> None:
        for value in [0, 1, None, "yes"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    TypeError,
                    "remove_falsy must be a boolean",
                ):
                    compact([], remove_falsy=value)  # type: ignore[arg-type]

    def test_rejects_non_iterable_values(self) -> None:
        invalid_values = [None, 123, 1.5, object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    compact(value)  # type: ignore[arg-type]


class DeepGetTests(unittest.TestCase):
    def test_retrieves_nested_and_top_level_mapping_values(self) -> None:
        data = {
            "user": {
                "profile": {
                    "email": "jordan@example.com",
                }
            },
            "active": False,
        }

        self.assertEqual(
            deep_get(data, "user.profile.email"),
            "jordan@example.com",
        )
        self.assertIs(deep_get(data, "active"), False)

    def test_returns_default_for_missing_path_at_any_depth(self) -> None:
        data = {"user": {"profile": {}}}
        marker = object()

        self.assertIs(deep_get(data, "missing", default=marker), marker)
        self.assertIs(deep_get(data, "user.missing", default=marker), marker)
        self.assertIs(
            deep_get(data, "user.profile.email", default=marker),
            marker,
        )

    def test_defaults_to_none_for_unresolved_paths(self) -> None:
        self.assertIsNone(deep_get({}, "user.profile.email"))

    def test_returns_present_none_instead_of_the_default(self) -> None:
        marker = object()

        self.assertIsNone(deep_get({"value": None}, "value", default=marker))

    def test_returns_default_for_non_mapping_intermediate_values(self) -> None:
        marker = object()
        data = {
            "user": None,
            "items": [{"name": "first"}],
        }

        self.assertIs(deep_get(data, "user.name", default=marker), marker)
        self.assertIs(deep_get(data, "items.0.name", default=marker), marker)

    def test_supports_non_dict_mapping_implementations(self) -> None:
        data = MappingProxyType(
            {
                "user": MappingProxyType({"name": "Jordan"}),
            }
        )

        self.assertEqual(deep_get(data, "user.name"), "Jordan")

    def test_does_not_mutate_input_and_returns_value_by_reference(self) -> None:
        profile = {"name": "Jordan"}
        data = {"user": {"profile": profile}}

        result = deep_get(data, "user.profile")

        self.assertIs(result, profile)
        self.assertEqual(data, {"user": {"profile": {"name": "Jordan"}}})

    def test_rejects_empty_or_malformed_paths(self) -> None:
        invalid_paths = ["", ".", ".user", "user.", "user..name"]

        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaisesRegex(
                    ValueError,
                    "path must contain keys separated by dots, and each key "
                    "must not be empty",
                ):
                    deep_get({}, path)

    def test_rejects_non_string_paths(self) -> None:
        invalid_paths = [None, 123, ["user", "name"]]

        for path in invalid_paths:
            with self.subTest(path=path):
                with self.assertRaisesRegex(TypeError, "path must be a string"):
                    deep_get({}, path)  # type: ignore[arg-type]

    def test_rejects_non_mapping_root_values(self) -> None:
        invalid_values = [None, [], (), "text", object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "data must be a mapping"):
                    deep_get(value, "name")  # type: ignore[arg-type]


class GroupByTests(unittest.TestCase):
    def test_groups_mapping_items_by_literal_field_name(self) -> None:
        first_admin = {"name": "Ada", "role": "admin"}
        user = {"name": "Grace", "role": "user"}
        second_admin = {"name": "Linus", "role": "admin"}

        result = group_by([first_admin, user, second_admin], "role")

        self.assertEqual(
            result,
            {
                "admin": [first_admin, second_admin],
                "user": [user],
            },
        )
        self.assertEqual(list(result), ["admin", "user"])
        self.assertIs(result["admin"][0], first_admin)

    def test_groups_items_by_callable_result(self) -> None:
        self.assertEqual(
            group_by(["one", "two", "three", "four"], len),
            {3: ["one", "two"], 5: ["three"], 4: ["four"]},
        )

    def test_eagerly_consumes_generator_once(self) -> None:
        visited: list[int] = []

        def generate_values():
            for value in [1, 2, 3, 4]:
                visited.append(value)
                yield value

        values = generate_values()

        self.assertEqual(
            group_by(values, lambda value: value % 2),
            {1: [1, 3], 0: [2, 4]},
        )
        self.assertEqual(visited, [1, 2, 3, 4])
        self.assertEqual(list(values), [])

    def test_returns_empty_dictionary_for_empty_input(self) -> None:
        self.assertEqual(group_by([], "category"), {})
        self.assertEqual(group_by(iter(()), lambda value: value), {})

    def test_rejects_non_mapping_items_for_field_selector(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "item at index 1 must be a mapping when key is a field name",
        ):
            group_by([{"role": "admin"}, "user"], "role")

    def test_reports_missing_field_and_item_index(self) -> None:
        with self.assertRaises(KeyError) as raised:
            group_by([{"role": "admin"}, {"name": "Grace"}], "role")

        self.assertEqual(
            raised.exception.args[0],
            "item at index 1 is missing field 'role'",
        )

    def test_rejects_unhashable_selected_keys(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "group key for item at index 0 must be hashable",
        ):
            group_by([{"tags": ["python"]}], "tags")

        with self.assertRaisesRegex(
            TypeError,
            "group key for item at index 0 must be hashable",
        ):
            group_by([1], lambda value: [value])

    def test_rejects_empty_or_unsupported_selectors(self) -> None:
        with self.assertRaisesRegex(ValueError, "key field name must not be empty"):
            group_by([], "")

        for selector in [None, 123, ["role"]]:
            with self.subTest(selector=selector):
                with self.assertRaisesRegex(
                    TypeError,
                    "key must be a field name string or callable",
                ):
                    group_by([], selector)  # type: ignore[arg-type]

    def test_rejects_non_iterable_values(self) -> None:
        for value in [None, 123, 1.5, object()]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    group_by(value, lambda item: item)  # type: ignore[arg-type]

    def test_does_not_mutate_input_or_share_group_lists(self) -> None:
        first = {"role": "admin"}
        second = {"role": "user"}
        values = [first, second]

        result = group_by(values, "role")
        result["admin"].append({"role": "admin"})

        self.assertEqual(values, [first, second])
        self.assertEqual(len(result["admin"]), 2)


class IndexByTests(unittest.TestCase):
    def test_indexes_mapping_items_by_literal_field_name(self) -> None:
        first = {"id": "a", "name": "Ada"}
        second = {"id": "b", "name": "Grace"}

        result = index_by([first, second], "id")

        self.assertEqual(result, {"a": first, "b": second})
        self.assertEqual(list(result), ["a", "b"])
        self.assertIs(result["a"], first)

    def test_indexes_items_by_callable_result(self) -> None:
        self.assertEqual(
            index_by(["one", "three", "four"], len),
            {3: "one", 5: "three", 4: "four"},
        )

    def test_eagerly_consumes_generator_once(self) -> None:
        visited: list[int] = []

        def generate_values():
            for value in [1, 2, 3]:
                visited.append(value)
                yield value

        values = generate_values()

        self.assertEqual(index_by(values, lambda value: f"id-{value}"), {
            "id-1": 1,
            "id-2": 2,
            "id-3": 3,
        })
        self.assertEqual(visited, [1, 2, 3])
        self.assertEqual(list(values), [])

    def test_returns_empty_dictionary_for_empty_input(self) -> None:
        self.assertEqual(index_by([], "id"), {})
        self.assertEqual(index_by(iter(()), lambda value: value), {})

    def test_rejects_duplicate_keys_without_silently_discarding_items(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "duplicate key 'a' at item index 2",
        ):
            index_by(
                [
                    {"id": "a", "value": 1},
                    {"id": "b", "value": 2},
                    {"id": "a", "value": 3},
                ],
                "id",
            )

        with self.assertRaisesRegex(ValueError, "duplicate key 1 at item index 1"):
            index_by(["a", "b"], lambda value: len(value))

    def test_rejects_non_mapping_items_for_field_selector(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "item at index 1 must be a mapping when key is a field name",
        ):
            index_by([{"id": "a"}, "b"], "id")

    def test_reports_missing_field_and_item_index(self) -> None:
        with self.assertRaises(KeyError) as raised:
            index_by([{"id": "a"}, {"name": "Grace"}], "id")

        self.assertEqual(
            raised.exception.args[0],
            "item at index 1 is missing field 'id'",
        )

    def test_rejects_unhashable_selected_keys(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "index key for item at index 0 must be hashable",
        ):
            index_by([{"tags": ["python"]}], "tags")

    def test_rejects_empty_or_unsupported_selectors(self) -> None:
        with self.assertRaisesRegex(ValueError, "key field name must not be empty"):
            index_by([], "")

        for selector in [None, 123, ["id"]]:
            with self.subTest(selector=selector):
                with self.assertRaisesRegex(
                    TypeError,
                    "key must be a field name string or callable",
                ):
                    index_by([], selector)  # type: ignore[arg-type]

    def test_rejects_non_iterable_values(self) -> None:
        for value in [None, 123, 1.5, object()]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "values must be iterable"):
                    index_by(value, lambda item: item)  # type: ignore[arg-type]

    def test_does_not_mutate_input(self) -> None:
        first = {"id": "a"}
        values = [first]

        result = index_by(values, "id")
        result["b"] = {"id": "b"}

        self.assertEqual(values, [first])
        self.assertIs(result["a"], first)


if __name__ == "__main__":
    unittest.main()
