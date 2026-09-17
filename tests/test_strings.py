import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from utilities.strings import (
    generate_reference,
    mask_email,
    mask_phone,
    normalize_unicode,
    normalize_whitespace,
    slugify,
    truncate,
)


class GenerateReferenceTests(unittest.TestCase):
    @patch("utilities.strings.secrets.choice", side_effect="A8F2KD")
    def test_generates_expected_prefixed_reference(self, choice_mock) -> None:
        result = generate_reference(
            "inv",
            reference_date=date(2026, 9, 14),
        )

        self.assertEqual(result, "INV-20260914-A8F2KD")
        self.assertEqual(choice_mock.call_count, 6)

    @patch("utilities.strings.secrets.choice", side_effect="Q7WX9Z")
    def test_supports_reference_without_prefix(self, _choice_mock) -> None:
        self.assertEqual(
            generate_reference(reference_date=date(2026, 1, 2)),
            "20260102-Q7WX9Z",
        )

    @patch("utilities.strings.secrets.choice", side_effect="ABC")
    def test_supports_custom_random_length(self, choice_mock) -> None:
        result = generate_reference(
            "job2",
            reference_date=date(2026, 12, 31),
            random_length=3,
        )

        self.assertEqual(result, "JOB2-20261231-ABC")
        self.assertEqual(choice_mock.call_count, 3)

    def test_uses_documented_unambiguous_token_alphabet(self) -> None:
        reference = generate_reference(reference_date=date(2026, 9, 14))
        token = reference.rsplit("-", maxsplit=1)[1]

        self.assertEqual(len(token), 6)
        self.assertTrue(token.isascii())
        self.assertTrue(token.isalnum())
        self.assertTrue(set(token).isdisjoint("IO01"))

    def test_rejects_invalid_prefixes(self) -> None:
        for prefix in ["", "INV-", "INV 2", "INV_2", "Café"]:
            with self.subTest(prefix=prefix):
                with self.assertRaisesRegex(
                    ValueError,
                    "prefix must not be empty and may contain only ASCII letters "
                    "and numbers",
                ):
                    generate_reference(prefix, reference_date=date(2026, 9, 14))

    def test_rejects_non_string_prefix(self) -> None:
        for prefix in [123, b"INV", ["INV"]]:
            with self.subTest(prefix=prefix):
                with self.assertRaisesRegex(
                    TypeError,
                    "prefix must be a string or None",
                ):
                    generate_reference(
                        prefix,  # type: ignore[arg-type]
                        reference_date=date(2026, 9, 14),
                    )

    def test_rejects_non_date_and_datetime_values(self) -> None:
        invalid_dates = [
            "2026-09-14",
            datetime(2026, 9, 14),
            datetime(2026, 9, 14, tzinfo=timezone.utc),
            20260914,
        ]

        for reference_date in invalid_dates:
            with self.subTest(reference_date=reference_date):
                with self.assertRaisesRegex(
                    TypeError,
                    "reference_date must be a date or None",
                ):
                    generate_reference(
                        reference_date=reference_date,  # type: ignore[arg-type]
                    )

    def test_rejects_invalid_random_lengths(self) -> None:
        for random_length in [None, 1.5, "6", True]:
            with self.subTest(random_length=random_length):
                with self.assertRaisesRegex(
                    TypeError,
                    "random_length must be an integer",
                ):
                    generate_reference(
                        reference_date=date(2026, 9, 14),
                        random_length=random_length,  # type: ignore[arg-type]
                    )

        for random_length in [0, -1]:
            with self.subTest(random_length=random_length):
                with self.assertRaisesRegex(
                    ValueError,
                    "random_length must be positive",
                ):
                    generate_reference(
                        reference_date=date(2026, 9, 14),
                        random_length=random_length,
                    )


class MaskPhoneTests(unittest.TestCase):
    def test_masks_all_but_the_default_four_digit_suffix(self) -> None:
        self.assertEqual(
            mask_phone("+1 (415) 555-2671"),
            "+* (***) ***-2671",
        )

    def test_preserves_original_non_digit_formatting(self) -> None:
        self.assertEqual(mask_phone("0917 123 4567"), "**** *** 4567")
        self.assertEqual(mask_phone("0917-123-4567"), "****-***-4567")

    def test_supports_a_custom_visible_suffix_length(self) -> None:
        self.assertEqual(
            mask_phone("123-456-7890", visible_digits=2),
            "***-***-**90",
        )
        self.assertEqual(mask_phone("123-456", visible_digits=0), "***-***")

    def test_always_masks_at_least_one_digit(self) -> None:
        self.assertEqual(mask_phone("123", visible_digits=4), "*23")
        self.assertEqual(mask_phone("7", visible_digits=4), "*")

    def test_masks_unicode_decimal_digits(self) -> None:
        self.assertEqual(mask_phone("+٩٦٦ ١٢٣٤٥٦٧٨٩"), "+*** *****٦٧٨٩")

    def test_rejects_text_without_decimal_digits(self) -> None:
        for phone in ["", "+", "not a phone", "(---)"]:
            with self.subTest(phone=phone):
                with self.assertRaisesRegex(
                    ValueError,
                    "phone must contain at least one decimal digit",
                ):
                    mask_phone(phone)

    def test_rejects_negative_visible_digit_count(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "visible_digits must be zero or greater",
        ):
            mask_phone("12345", visible_digits=-1)

    def test_rejects_invalid_argument_types(self) -> None:
        for phone in [None, 123, b"123"]:
            with self.subTest(argument="phone", value=phone):
                with self.assertRaisesRegex(TypeError, "phone must be a string"):
                    mask_phone(phone)  # type: ignore[arg-type]

        for visible_digits in [None, 1.5, "4", True]:
            with self.subTest(argument="visible_digits", value=visible_digits):
                with self.assertRaisesRegex(
                    TypeError,
                    "visible_digits must be an integer",
                ):
                    mask_phone(
                        "12345",
                        visible_digits=visible_digits,  # type: ignore[arg-type]
                    )


class MaskEmailTests(unittest.TestCase):
    def test_masks_local_part_and_preserves_domain(self) -> None:
        self.assertEqual(mask_email("jordan@example.com"), "j*****@example.com")
        self.assertEqual(mask_email("User@Sub.Example.COM"), "U***@Sub.Example.COM")

    def test_fully_masks_one_character_local_part(self) -> None:
        self.assertEqual(mask_email("j@example.com"), "*@example.com")

    def test_masks_unicode_local_part_by_code_point(self) -> None:
        self.assertEqual(mask_email("用户@example.com"), "用*@example.com")

    def test_uses_final_at_sign_without_claiming_syntax_validation(self) -> None:
        result = mask_email("user@tag@example.com")

        self.assertEqual(result.split("@", maxsplit=1)[1], "example.com")
        self.assertEqual(result[0], "u")
        self.assertEqual(result.count("*"), len("user@tag") - 1)

    def test_rejects_missing_or_empty_address_parts(self) -> None:
        for email in ["", "plain-address", "@example.com", "user@"]:
            with self.subTest(email=email):
                with self.assertRaisesRegex(
                    ValueError,
                    "email must contain local and domain parts that are not empty",
                ):
                    mask_email(email)

    def test_rejects_non_string_input(self) -> None:
        for value in [None, 123, b"user@example.com", ["user@example.com"]]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "email must be a string"):
                    mask_email(value)  # type: ignore[arg-type]


class TruncateTests(unittest.TestCase):
    def test_truncates_with_suffix_inside_maximum_length(self) -> None:
        result = truncate("This is a long message", length=12)

        self.assertEqual(result, "This is a...")
        self.assertEqual(len(result), 12)

    def test_returns_shorter_and_exact_length_text_unchanged(self) -> None:
        self.assertEqual(truncate("short", length=10), "short")
        self.assertEqual(truncate("exact", length=5), "exact")

    def test_supports_custom_and_empty_suffixes(self) -> None:
        self.assertEqual(truncate("Hello world", 8, suffix="…"), "Hello w…")
        self.assertEqual(truncate("Hello world", 5, suffix=""), "Hello")

    def test_supports_unicode_text_using_code_point_length(self) -> None:
        result = truncate("你好世界", length=3, suffix="…")

        self.assertEqual(result, "你好…")
        self.assertEqual(len(result), 3)

    def test_supports_zero_length_with_an_empty_suffix(self) -> None:
        self.assertEqual(truncate("Hello", length=0, suffix=""), "")
        self.assertEqual(truncate("", length=0), "")

    def test_allows_suffix_to_use_the_entire_result(self) -> None:
        self.assertEqual(truncate("Hello", length=3, suffix="..."), "...")

    def test_rejects_suffix_that_cannot_fit_when_truncating(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "suffix cannot be longer than length when truncating",
        ):
            truncate("Hello", length=2)

    def test_ignores_suffix_length_when_text_does_not_need_truncation(self) -> None:
        self.assertEqual(truncate("Hi", length=2, suffix="too long"), "Hi")

    def test_rejects_negative_length(self) -> None:
        with self.assertRaisesRegex(ValueError, "length must be zero or greater"):
            truncate("Hello", length=-1)

    def test_rejects_invalid_argument_types(self) -> None:
        for text in [None, 123, b"text"]:
            with self.subTest(argument="text", value=text):
                with self.assertRaisesRegex(TypeError, "text must be a string"):
                    truncate(text, 5)  # type: ignore[arg-type]

        for length in [None, 1.5, "5", True]:
            with self.subTest(argument="length", value=length):
                with self.assertRaisesRegex(TypeError, "length must be an integer"):
                    truncate("Hello", length)  # type: ignore[arg-type]

        for suffix in [None, 123, b"..."]:
            with self.subTest(argument="suffix", value=suffix):
                with self.assertRaisesRegex(TypeError, "suffix must be a string"):
                    truncate("Hello", 3, suffix=suffix)  # type: ignore[arg-type]


class SlugifyTests(unittest.TestCase):
    def test_normalizes_case_whitespace_and_punctuation(self) -> None:
        self.assertEqual(
            slugify("  Hello,   World!  "),
            "hello-world",
        )

    def test_collapses_repeated_and_existing_separators(self) -> None:
        self.assertEqual(slugify("one---two___three"), "one-two-three")

    def test_omits_leading_and_trailing_separators(self) -> None:
        self.assertEqual(slugify("---hello world---"), "hello-world")

    def test_preserves_international_letters_and_combining_marks(self) -> None:
        values = [
            ("Café déjà vu", "café-déjà-vu"),
            ("Cafe\u0301 au lait", "café-au-lait"),
            ("你好 世界", "你好-世界"),
            ("こんにちは 世界", "こんにちは-世界"),
            ("한글 제목", "한글-제목"),
            ("नमस्ते दुनिया", "नमस्ते-दुनिया"),
        ]

        for text, expected in values:
            with self.subTest(text=text):
                self.assertEqual(slugify(text), expected)

    def test_uses_compatibility_normalization_and_case_folding(self) -> None:
        self.assertEqual(slugify("Ｆｕｌｌ Ｗｉｄｔｈ"), "full-width")
        self.assertEqual(slugify("Straße"), "strasse")

    def test_preserves_unicode_decimal_digits(self) -> None:
        self.assertEqual(slugify("Version 2 ١٢٣"), "version-2-١٢٣")

    def test_supports_underscore_separator(self) -> None:
        self.assertEqual(slugify("Hello 世界", separator="_"), "hello_世界")

    def test_returns_empty_string_without_slug_characters(self) -> None:
        self.assertEqual(slugify(""), "")
        self.assertEqual(slugify(" --- 😊 !!! "), "")

    def test_rejects_non_string_input(self) -> None:
        for value in [None, 123, b"text", ["text"]]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "text must be a string"):
                    slugify(value)  # type: ignore[arg-type]

    def test_rejects_unsupported_separator(self) -> None:
        for separator in ["", "--", ".", " ", "x"]:
            with self.subTest(separator=separator):
                with self.assertRaisesRegex(
                    ValueError,
                    "separator must be '-' or '_'",
                ):
                    slugify("Hello world", separator=separator)

        with self.assertRaisesRegex(TypeError, "separator must be a string"):
            slugify("Hello world", separator=None)  # type: ignore[arg-type]


class NormalizeWhitespaceTests(unittest.TestCase):
    def test_collapses_repeated_spaces_and_strips_edges(self) -> None:
        self.assertEqual(
            normalize_whitespace("   Hello    world   "),
            "Hello world",
        )

    def test_collapses_tabs_and_line_breaks(self) -> None:
        self.assertEqual(
            normalize_whitespace("Hello\tworld\r\nfrom\nPython"),
            "Hello world from Python",
        )

    def test_collapses_international_unicode_whitespace(self) -> None:
        whitespace = "\u00a0\u2003\u2009\u2028\u2029"

        self.assertEqual(
            normalize_whitespace(f"Hello{whitespace}世界"),
            "Hello 世界",
        )

    def test_returns_empty_string_for_empty_or_whitespace_only_input(self) -> None:
        self.assertEqual(normalize_whitespace(""), "")
        self.assertEqual(normalize_whitespace(" \t\n\u2003"), "")

    def test_preserves_non_whitespace_unicode_characters(self) -> None:
        self.assertEqual(
            normalize_whitespace("  Café  世界  한글  "),
            "Café 世界 한글",
        )

    def test_rejects_non_string_input(self) -> None:
        for value in [None, 123, b"text", ["text"]]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "text must be a string"):
                    normalize_whitespace(value)  # type: ignore[arg-type]


class NormalizeUnicodeTests(unittest.TestCase):
    def test_defaults_to_nfc_canonical_composition(self) -> None:
        self.assertEqual(normalize_unicode("Cafe\u0301"), "Café")

    def test_supports_nfd_canonical_decomposition(self) -> None:
        self.assertEqual(normalize_unicode("Café", form="NFD"), "Cafe\u0301")

    def test_supports_nfkc_compatibility_composition(self) -> None:
        self.assertEqual(
            normalize_unicode("① Ａ ½", form="NFKC"),
            "1 A 1⁄2",
        )

    def test_supports_nfkd_compatibility_decomposition(self) -> None:
        self.assertEqual(
            normalize_unicode("Café ①", form="NFKD"),
            "Cafe\u0301 1",
        )

    def test_accepts_empty_and_already_normalized_text(self) -> None:
        self.assertEqual(normalize_unicode(""), "")
        self.assertEqual(normalize_unicode("Hello 世界"), "Hello 世界")

    def test_rejects_non_string_text(self) -> None:
        for value in [None, 123, b"text", ["text"]]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "text must be a string"):
                    normalize_unicode(value)  # type: ignore[arg-type]

    def test_rejects_non_string_form(self) -> None:
        for value in [None, 123, b"NFC"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "form must be a string"):
                    normalize_unicode("text", form=value)  # type: ignore[arg-type]

    def test_rejects_unknown_or_inexact_form_names(self) -> None:
        for form in ["", "nfc", "NFC ", "XYZ"]:
            with self.subTest(form=form):
                with self.assertRaisesRegex(
                    ValueError,
                    r"form must be one of: NFC, NFD, NFKC, NFKD",
                ):
                    normalize_unicode("text", form=form)


if __name__ == "__main__":
    unittest.main()
