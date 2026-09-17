import math
import unittest
from decimal import Decimal
from fractions import Fraction

from utilities.numbers import between, clamp, percentage, safe_float, safe_int


class ClampTests(unittest.TestCase):
    def test_returns_value_within_inclusive_range(self) -> None:
        self.assertEqual(clamp(50, minimum=0, maximum=100), 50)
        self.assertEqual(clamp(-5, minimum=-10, maximum=0), -5)

    def test_returns_bounds_for_values_outside_range(self) -> None:
        self.assertEqual(clamp(-20, minimum=-10, maximum=10), -10)
        self.assertEqual(clamp(120, minimum=0, maximum=100), 100)

    def test_includes_exact_boundaries(self) -> None:
        self.assertEqual(clamp(0, minimum=0, maximum=100), 0)
        self.assertEqual(clamp(100, minimum=0, maximum=100), 100)

    def test_supports_mixed_integers_and_floats(self) -> None:
        self.assertEqual(clamp(2.5, minimum=0, maximum=5), 2.5)
        self.assertEqual(clamp(10, minimum=0.5, maximum=5.5), 5.5)

    def test_supports_single_value_range(self) -> None:
        self.assertEqual(clamp(-10, minimum=3, maximum=3), 3)
        self.assertEqual(clamp(3, minimum=3, maximum=3), 3)
        self.assertEqual(clamp(10, minimum=3, maximum=3), 3)

    def test_preserves_selected_argument_type(self) -> None:
        self.assertIsInstance(clamp(-1, minimum=0.0, maximum=10), float)
        self.assertIsInstance(clamp(11.0, minimum=0, maximum=10), int)
        self.assertIsInstance(clamp(5, minimum=0.0, maximum=10.0), int)

    def test_supports_very_large_integers_without_float_conversion(self) -> None:
        large = 10**10_000

        self.assertEqual(clamp(large, minimum=0, maximum=large + 1), large)

    def test_rejects_inverted_range(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "minimum must not exceed maximum",
        ):
            clamp(5, minimum=10, maximum=0)

    def test_rejects_booleans_for_every_argument(self) -> None:
        invalid_arguments = [
            {"value": True, "minimum": 0, "maximum": 1},
            {"value": 1, "minimum": False, "maximum": 2},
            {"value": 1, "minimum": 0, "maximum": True},
        ]

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(TypeError, "must be an integer or float"):
                    clamp(**arguments)

    def test_rejects_non_numeric_values_for_every_argument(self) -> None:
        invalid_arguments = [
            {"value": "5", "minimum": 0, "maximum": 10},
            {"value": 5, "minimum": None, "maximum": 10},
            {"value": 5, "minimum": 0, "maximum": Decimal("10")},
            {"value": Fraction(1, 2), "minimum": 0, "maximum": 1},
            {"value": complex(1, 0), "minimum": 0, "maximum": 1},
        ]

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(TypeError, "must be an integer or float"):
                    clamp(**arguments)

    def test_rejects_nan_for_every_argument(self) -> None:
        invalid_arguments = [
            {"value": math.nan, "minimum": 0, "maximum": 10},
            {"value": 5, "minimum": math.nan, "maximum": 10},
            {"value": 5, "minimum": 0, "maximum": math.nan},
        ]

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ValueError, "must not be NaN"):
                    clamp(**arguments)

    def test_applies_normal_ordering_to_infinity(self) -> None:
        self.assertEqual(clamp(math.inf, minimum=0, maximum=100), 100)
        self.assertEqual(clamp(-math.inf, minimum=0, maximum=100), 0)
        self.assertEqual(
            clamp(50, minimum=-math.inf, maximum=math.inf),
            50,
        )


class PercentageTests(unittest.TestCase):
    def test_calculates_unrounded_percentage_as_float(self) -> None:
        self.assertEqual(percentage(1, 4), 25.0)
        self.assertIsInstance(percentage(1, 4), float)
        self.assertAlmostEqual(percentage(1, 3), 33.33333333333333)

    def test_supports_zero_numerator_and_results_above_one_hundred(self) -> None:
        self.assertEqual(percentage(0, 10), 0.0)
        self.assertEqual(percentage(15, 10), 150.0)

    def test_uses_normal_signed_arithmetic(self) -> None:
        self.assertEqual(percentage(-1, 4), -25.0)
        self.assertEqual(percentage(1, -4), -25.0)
        self.assertEqual(percentage(-1, -4), 25.0)

    def test_supports_mixed_integers_and_floats(self) -> None:
        self.assertEqual(percentage(1, 2.0), 50.0)
        self.assertEqual(percentage(2.5, 10), 25.0)

    def test_supports_equal_very_large_integers(self) -> None:
        large = 10**10_000

        self.assertEqual(percentage(large, large), 100.0)

    def test_rejects_positive_and_negative_zero_denominators(self) -> None:
        for whole in [0, 0.0, -0.0]:
            with self.subTest(whole=whole):
                with self.assertRaisesRegex(
                    ZeroDivisionError,
                    "whole must not be zero",
                ):
                    percentage(1, whole)

    def test_rejects_booleans_for_both_arguments(self) -> None:
        for part, whole in [(True, 1), (1, False)]:
            with self.subTest(part=part, whole=whole):
                with self.assertRaisesRegex(TypeError, "must be an integer or float"):
                    percentage(part, whole)

    def test_rejects_non_numeric_values_for_both_arguments(self) -> None:
        invalid_arguments = [
            ("1", 2),
            (1, None),
            (Decimal("1"), 2),
            (1, Fraction(1, 2)),
            (complex(1, 0), 2),
        ]

        for part, whole in invalid_arguments:
            with self.subTest(part=part, whole=whole):
                with self.assertRaisesRegex(TypeError, "must be an integer or float"):
                    percentage(part, whole)  # type: ignore[arg-type]

    def test_rejects_nan_for_both_arguments(self) -> None:
        for part, whole in [(math.nan, 1), (1, math.nan)]:
            with self.subTest(part=part, whole=whole):
                with self.assertRaisesRegex(ValueError, "must not be NaN"):
                    percentage(part, whole)

    def test_rejects_infinity_for_both_arguments(self) -> None:
        invalid_arguments = [
            (math.inf, 1),
            (-math.inf, 1),
            (1, math.inf),
            (1, -math.inf),
        ]

        for part, whole in invalid_arguments:
            with self.subTest(part=part, whole=whole):
                with self.assertRaisesRegex(ValueError, "must be finite"):
                    percentage(part, whole)


class SafeIntTests(unittest.TestCase):
    def test_returns_non_boolean_integers_unchanged(self) -> None:
        value = 10**100

        self.assertIs(safe_int(value), value)
        self.assertEqual(safe_int(0), 0)
        self.assertEqual(safe_int(-42), -42)

    def test_parses_ascii_decimal_integer_strings(self) -> None:
        valid_values = {
            "0": 0,
            "42": 42,
            "-42": -42,
            "+42": 42,
            "00042": 42,
            "  42\t": 42,
            "\u2003-42\u00a0": -42,
        }

        for value, expected in valid_values.items():
            with self.subTest(value=value):
                self.assertEqual(safe_int(value), expected)

    def test_returns_none_for_invalid_strings_by_default(self) -> None:
        invalid_values = [
            "",
            "   ",
            "+",
            "-",
            "1.0",
            "1e3",
            "0x10",
            "1_000",
            "+ 1",
            "12abc",
            "１２",
            "١٢",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertIsNone(safe_int(value))

    def test_returns_supplied_default_for_invalid_values(self) -> None:
        invalid_values = [
            None,
            True,
            False,
            1.0,
            math.nan,
            math.inf,
            Decimal("1"),
            Fraction(1, 1),
            b"1",
            ["1"],
            {"value": 1},
            object(),
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertEqual(safe_int(value, default=-1), -1)

    def test_supports_zero_as_an_explicit_default(self) -> None:
        self.assertEqual(safe_int("invalid", default=0), 0)
        self.assertEqual(safe_int(None, default=0), 0)

    def test_validates_default_even_when_value_is_valid(self) -> None:
        invalid_defaults = [True, False, 1.0, "0", Decimal("0"), object()]

        for default in invalid_defaults:
            with self.subTest(default=default):
                with self.assertRaisesRegex(
                    TypeError,
                    "default must be an integer or None",
                ):
                    safe_int(42, default=default)  # type: ignore[arg-type]


class SafeFloatTests(unittest.TestCase):
    def test_returns_finite_floats_unchanged(self) -> None:
        value = 1.25

        self.assertIs(safe_float(value), value)
        self.assertEqual(safe_float(-0.0), -0.0)

    def test_converts_non_boolean_integers_to_float(self) -> None:
        self.assertEqual(safe_float(0), 0.0)
        self.assertEqual(safe_float(42), 42.0)
        self.assertEqual(safe_float(-42), -42.0)
        self.assertIsInstance(safe_float(42), float)

    def test_parses_documented_ascii_float_strings(self) -> None:
        valid_values = {
            "0": 0.0,
            "42": 42.0,
            "-1.5": -1.5,
            "+1.5": 1.5,
            "1.": 1.0,
            ".5": 0.5,
            "-.5": -0.5,
            "1e3": 1000.0,
            "-1.5E-2": -0.015,
            "  2.5\t": 2.5,
            "\u2003.25\u00a0": 0.25,
        }

        for value, expected in valid_values.items():
            with self.subTest(value=value):
                self.assertEqual(safe_float(value), expected)

    def test_returns_none_for_invalid_strings_by_default(self) -> None:
        invalid_values = [
            "",
            "   ",
            ".",
            "+",
            "1e",
            "0x1.0p0",
            "1_000.0",
            "1,000.0",
            "１２.５",
            "١٢.٥",
            "NaN",
            "Infinity",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertIsNone(safe_float(value))

    def test_returns_default_for_unsupported_values(self) -> None:
        invalid_values = [
            None,
            True,
            False,
            Decimal("1.5"),
            Fraction(3, 2),
            b"1.5",
            ["1.5"],
            {"value": 1.5},
            object(),
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertEqual(safe_float(value, default=-1.0), -1.0)

    def test_returns_default_for_nan_infinity_and_overflow(self) -> None:
        invalid_values = [
            math.nan,
            math.inf,
            -math.inf,
            10**10_000,
            "1e309",
            "-1e309",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertEqual(safe_float(value, default=0.0), 0.0)

    def test_supports_finite_float_default(self) -> None:
        self.assertEqual(safe_float("invalid", default=0.0), 0.0)
        self.assertEqual(safe_float(None, default=-1.5), -1.5)

    def test_validates_default_type_even_when_value_is_valid(self) -> None:
        invalid_defaults = [True, False, 0, "0.0", Decimal("0"), object()]

        for default in invalid_defaults:
            with self.subTest(default=default):
                with self.assertRaisesRegex(
                    TypeError,
                    "default must be a float or None",
                ):
                    safe_float(1.5, default=default)  # type: ignore[arg-type]

    def test_rejects_non_finite_defaults(self) -> None:
        for default in [math.nan, math.inf, -math.inf]:
            with self.subTest(default=default):
                with self.assertRaisesRegex(ValueError, "default must be finite"):
                    safe_float("invalid", default=default)


class BetweenTests(unittest.TestCase):
    def test_uses_inclusive_boundaries_by_default(self) -> None:
        self.assertTrue(between(0, minimum=0, maximum=10))
        self.assertTrue(between(5, minimum=0, maximum=10))
        self.assertTrue(between(10, minimum=0, maximum=10))
        self.assertFalse(between(-1, minimum=0, maximum=10))
        self.assertFalse(between(11, minimum=0, maximum=10))

    def test_supports_independently_exclusive_boundaries(self) -> None:
        self.assertFalse(
            between(
                0,
                minimum=0,
                maximum=10,
                inclusive_minimum=False,
            )
        )
        self.assertTrue(
            between(
                10,
                minimum=0,
                maximum=10,
                inclusive_minimum=False,
            )
        )
        self.assertTrue(
            between(
                0,
                minimum=0,
                maximum=10,
                inclusive_maximum=False,
            )
        )
        self.assertFalse(
            between(
                10,
                minimum=0,
                maximum=10,
                inclusive_maximum=False,
            )
        )

    def test_supports_fully_exclusive_range(self) -> None:
        options = {
            "inclusive_minimum": False,
            "inclusive_maximum": False,
        }

        self.assertFalse(between(0, 0, 10, **options))
        self.assertTrue(between(5, 0, 10, **options))
        self.assertFalse(between(10, 0, 10, **options))

    def test_handles_single_value_range_according_to_boundary_policy(self) -> None:
        self.assertTrue(between(3, minimum=3, maximum=3))
        self.assertFalse(
            between(3, minimum=3, maximum=3, inclusive_minimum=False)
        )
        self.assertFalse(
            between(3, minimum=3, maximum=3, inclusive_maximum=False)
        )

    def test_supports_negative_mixed_and_infinite_values(self) -> None:
        self.assertTrue(between(-2.5, minimum=-3, maximum=-2))
        self.assertTrue(between(0, minimum=-math.inf, maximum=math.inf))
        self.assertTrue(between(math.inf, minimum=0, maximum=math.inf))
        self.assertFalse(
            between(
                math.inf,
                minimum=0,
                maximum=math.inf,
                inclusive_maximum=False,
            )
        )

    def test_rejects_inverted_range(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "minimum must not exceed maximum",
        ):
            between(5, minimum=10, maximum=0)

    def test_rejects_booleans_and_non_numeric_arguments(self) -> None:
        invalid_arguments = [
            {"value": True, "minimum": 0, "maximum": 1},
            {"value": 1, "minimum": False, "maximum": 2},
            {"value": 1, "minimum": 0, "maximum": True},
            {"value": "1", "minimum": 0, "maximum": 2},
            {"value": 1, "minimum": None, "maximum": 2},
            {"value": Decimal("1"), "minimum": 0, "maximum": 2},
        ]

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(TypeError, "must be an integer or float"):
                    between(**arguments)

    def test_rejects_nan_for_every_numeric_argument(self) -> None:
        invalid_arguments = [
            {"value": math.nan, "minimum": 0, "maximum": 1},
            {"value": 0, "minimum": math.nan, "maximum": 1},
            {"value": 0, "minimum": 0, "maximum": math.nan},
        ]

        for arguments in invalid_arguments:
            with self.subTest(arguments=arguments):
                with self.assertRaisesRegex(ValueError, "must not be NaN"):
                    between(**arguments)

    def test_rejects_non_boolean_boundary_options(self) -> None:
        invalid_options = [
            {"inclusive_minimum": 1},
            {"inclusive_maximum": 0},
            {"inclusive_minimum": None},
            {"inclusive_maximum": "yes"},
        ]

        for options in invalid_options:
            with self.subTest(options=options):
                with self.assertRaisesRegex(TypeError, "must be a boolean"):
                    between(5, minimum=0, maximum=10, **options)


if __name__ == "__main__":
    unittest.main()
