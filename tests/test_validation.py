import string
import unittest
from types import MappingProxyType

from utilities.validation import (
    is_blank,
    is_valid_email,
    is_valid_phone,
    is_valid_text,
    is_valid_url,
    require_fields,
    validate_text,
)


class IsBlankTests(unittest.TestCase):
    def test_treats_none_and_empty_string_as_blank(self) -> None:
        self.assertTrue(is_blank(None))
        self.assertTrue(is_blank(""))

    def test_treats_unicode_whitespace_only_strings_as_blank(self) -> None:
        blank_values = [
            "   ",
            "\t\n\r",
            "\u00a0",
            "\u2003\u2028\u2029",
        ]

        for value in blank_values:
            with self.subTest(value=repr(value)):
                self.assertTrue(is_blank(value))

    def test_rejects_strings_containing_non_whitespace(self) -> None:
        non_blank_values = ["text", "  text  ", "0", "\u200b"]

        for value in non_blank_values:
            with self.subTest(value=repr(value)):
                self.assertFalse(is_blank(value))

    def test_does_not_treat_arbitrary_falsey_values_as_blank(self) -> None:
        non_blank_values = [0, 0.0, False, [], {}, (), set(), b""]

        for value in non_blank_values:
            with self.subTest(value=value):
                self.assertFalse(is_blank(value))


class RequireFieldsTests(unittest.TestCase):
    def test_accepts_present_nonblank_fields(self) -> None:
        data = {"name": "Jordan", "email": "jordan@example.com"}

        self.assertIsNone(require_fields(data, ["name", "email"]))

    def test_accepts_non_dict_mappings(self) -> None:
        data = MappingProxyType({"name": "Jordan"})

        self.assertIsNone(require_fields(data, ["name"]))

    def test_treats_absent_none_and_blank_strings_as_missing(self) -> None:
        data = {"name": "  ", "email": None}

        with self.assertRaisesRegex(
            ValueError,
            "^Required fields are missing or blank: 'name', 'email', 'phone'$",
        ):
            require_fields(data, ["name", "email", "phone"])

    def test_preserves_requested_order_and_reports_duplicates_once(self) -> None:
        with self.assertRaises(ValueError) as raised:
            require_fields({}, ["email", "name", "email", "phone"])

        self.assertEqual(
            str(raised.exception),
            "Required fields are missing or blank: 'email', 'name', 'phone'",
        )

    def test_treats_other_falsey_values_as_present(self) -> None:
        data = {
            "count": 0,
            "enabled": False,
            "items": [],
            "options": {},
            "payload": b"",
        }

        self.assertIsNone(require_fields(data, data.keys()))

    def test_accepts_empty_and_one_shot_field_iterables(self) -> None:
        self.assertIsNone(require_fields({}, []))
        fields = (field for field in ["name", "email"])
        self.assertIsNone(
            require_fields({"name": "Jordan", "email": "j@example.com"}, fields)
        )

    def test_rejects_non_mapping_data(self) -> None:
        invalid_values = [None, [], (), "name=Jordan", object()]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "data must be a mapping"):
                    require_fields(value, ["name"])  # type: ignore[arg-type]

    def test_rejects_invalid_required_field_collections(self) -> None:
        invalid_values = [None, "name", b"name", 123]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    TypeError,
                    "required_fields must be an iterable, not a string",
                ):
                    require_fields({}, value)  # type: ignore[arg-type]

    def test_rejects_non_string_field_names(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "required_fields must contain only strings",
        ):
            require_fields({}, ["name", 123])  # type: ignore[list-item]

    def test_does_not_modify_the_input_mapping(self) -> None:
        data = {"name": "Jordan"}

        require_fields(data, ["name"])

        self.assertEqual(data, {"name": "Jordan"})


class IsValidEmailTests(unittest.TestCase):
    def test_accepts_common_email_addresses(self) -> None:
        valid_values = [
            "user@example.com",
            "first.last+tag@example.co.uk",
            "customer/department=shipping@example.com",
            "o'hara@example.com",
            "admin@localhost",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_email(value))

    def test_accepts_internationalized_addresses(self) -> None:
        valid_values = [
            "用户@例子.测试",
            "pelé@example.com",
            "user@bücher.example",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_email(value))

    def test_rejects_empty_missing_or_multiple_address_parts(self) -> None:
        invalid_values = [
            "",
            "plainaddress",
            "@example.com",
            "user@",
            "user@@example.com",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_email(value))

    def test_rejects_invalid_local_part_syntax(self) -> None:
        invalid_values = [
            ".user@example.com",
            "user.@example.com",
            "first..last@example.com",
            "user name@example.com",
            '"user"@example.com',
            "user(comment)@example.com",
            "user\n@example.com",
            "user\u200b@example.com",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_email(value))

    def test_rejects_invalid_hostname_syntax(self) -> None:
        invalid_values = [
            "user@.example.com",
            "user@example.com.",
            "user@example..com",
            "user@-example.com",
            "user@example-.com",
            "user@example_domain.com",
            "user@[192.0.2.1]",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_email(value))

    def test_enforces_standard_length_limits(self) -> None:
        maximum_length_address = (
            f"{'a' * 64}@{'b' * 63}.{'c' * 63}.{'d' * 61}"
        )
        self.assertEqual(len(maximum_length_address.encode("utf-8")), 254)
        self.assertTrue(is_valid_email(maximum_length_address))

        self.assertFalse(is_valid_email(f"{'a' * 65}@example.com"))
        self.assertFalse(is_valid_email(f"user@{'a' * 64}.com"))

        long_domain = ".".join(["a" * 63] * 4)
        self.assertFalse(is_valid_email(f"a@{long_domain}"))

    def test_rejects_non_string_values_and_invalid_unicode(self) -> None:
        invalid_values = [None, 123, b"user@example.com", ["user@example.com"]]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_email(value))

        self.assertFalse(is_valid_email("user\ud800@example.com"))


class IsValidPhoneTests(unittest.TestCase):
    def test_accepts_normalized_international_numbers(self) -> None:
        valid_values = [
            "+14155552671",
            "+639171234567",
            "+442071838750",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_phone(value))

    def test_accepts_documented_length_boundaries(self) -> None:
        self.assertTrue(is_valid_phone("+12345678"))
        self.assertTrue(is_valid_phone("+123456789012345"))

    def test_rejects_numbers_outside_length_boundaries(self) -> None:
        self.assertFalse(is_valid_phone("+1234567"))
        self.assertFalse(is_valid_phone("+1234567890123456"))

    def test_rejects_non_normalized_formats(self) -> None:
        invalid_values = [
            "14155552671",
            "0014155552671",
            "+1 415 555 2671",
            "+1-415-555-2671",
            "+1 (415) 555-2671",
            "+14155552671x123",
            " +14155552671",
            "+14155552671\n",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_phone(value))

    def test_rejects_zero_prefix_and_unicode_digits(self) -> None:
        self.assertFalse(is_valid_phone("+012345678"))
        self.assertFalse(is_valid_phone("+١٢٣٤٥٦٧٨"))
        self.assertFalse(is_valid_phone("＋12345678"))

    def test_rejects_empty_and_non_string_values(self) -> None:
        invalid_values = ["", "+", None, 14155552671, b"+14155552671"]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_phone(value))


class IsValidUrlTests(unittest.TestCase):
    def test_accepts_absolute_http_and_https_urls(self) -> None:
        valid_values = [
            "http://example.com",
            "https://example.com/path/to/page?name=value#section",
            "HTTPS://EXAMPLE.COM:443/",
            "http://localhost:8000/health",
            "https://user:password@example.com/private",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_url(value))

    def test_accepts_internationalized_and_ip_hosts(self) -> None:
        valid_values = [
            "https://例子.测试/路径",
            "http://192.0.2.1/resource",
            "http://[2001:db8::1]:8080/resource",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertTrue(is_valid_url(value))

    def test_rejects_unsupported_or_missing_schemes(self) -> None:
        invalid_values = [
            "ftp://example.com/file",
            "javascript:alert(1)",
            "mailto:user@example.com",
            "//example.com/path",
            "example.com/path",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_url(value))

    def test_rejects_missing_or_malformed_hosts(self) -> None:
        invalid_values = [
            "https:///path",
            "https://",
            "https://.example.com",
            "https://example..com",
            "https://-example.com",
            "https://example_domain.com",
            "http://999.999.999.999",
            "http://2001:db8::1",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_url(value))

    def test_validates_explicit_ports(self) -> None:
        self.assertTrue(is_valid_url("https://example.com:1"))
        self.assertTrue(is_valid_url("https://example.com:65535"))
        self.assertFalse(is_valid_url("https://example.com:0"))
        self.assertFalse(is_valid_url("https://example.com:65536"))
        self.assertFalse(is_valid_url("https://example.com:not-a-port"))
        self.assertFalse(is_valid_url("https://example.com:"))

    def test_rejects_raw_whitespace_controls_and_backslashes(self) -> None:
        invalid_values = [
            " https://example.com",
            "https://example.com/path with spaces",
            "https://example.com/line\nbreak",
            "https://example.com/zero\u200bwidth",
            "https://example.com\\path",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_url(value))

    def test_rejects_malformed_percent_escapes_and_authority(self) -> None:
        self.assertTrue(is_valid_url("https://example.com/a%20valid%20path"))
        self.assertFalse(is_valid_url("https://example.com/incomplete%2"))
        self.assertFalse(is_valid_url("https://example.com/invalid%zz"))
        self.assertFalse(is_valid_url("https://user@@example.com"))

    def test_rejects_empty_and_non_string_values(self) -> None:
        invalid_values = ["", None, 123, b"https://example.com"]

        for value in invalid_values:
            with self.subTest(value=value):
                self.assertFalse(is_valid_url(value))

class ValidateTextTests(unittest.TestCase):
    def test_accepts_letters_marks_and_decimal_digits_from_unicode(self) -> None:
        valid_values = [
            "Hello",
            "Café",
            "你好",
            "こんにちは",
            "한글",
            "Cafe\u0301",
            "\u0301",
            "12345",
            "١٢٣",
        ]

        for value in valid_values:
            with self.subTest(value=value):
                self.assertEqual(validate_text(value), value)

    def test_accepts_empty_string(self) -> None:
        self.assertEqual(validate_text(""), "")

    def test_returns_the_original_string_unchanged(self) -> None:
        text = "  Cafe\u0301 世界  "

        self.assertIs(validate_text(text), text)

    def test_accepts_unicode_currency_symbols_by_default(self) -> None:
        for symbol in ["$", "€", "¥", "₱"]:
            with self.subTest(symbol=symbol):
                value = f"Price {symbol}100"
                self.assertEqual(validate_text(value), value)

    def test_accepts_all_ascii_punctuation_by_default(self) -> None:
        self.assertEqual(validate_text(string.punctuation), string.punctuation)

    def test_accepts_documented_whitespace_by_default(self) -> None:
        whitespace = [
            " ",
            "\u00a0",
            "\u2003",
            "\u2028",
            "\u2029",
            "\t",
            "\n",
            "\r",
        ]

        for character in whitespace:
            with self.subTest(character=repr(character)):
                value = f"before{character}after"
                self.assertEqual(validate_text(value), value)

    def test_rejects_unsupported_numbers_punctuation_and_symbols(self) -> None:
        invalid_characters = [
            "½",  # Other number (No)
            "Ⅳ",  # Letter number (Nl)
            "—",  # Dash punctuation (Pd)
            "“",  # Initial punctuation (Pi)
            "©",  # Other symbol (So)
            "™",  # Other symbol (So)
            "😊",  # Other symbol (So)
        ]

        for character in invalid_characters:
            with self.subTest(character=character):
                with self.assertRaises(ValueError):
                    validate_text(f"before{character}after")

    def test_rejects_undocumented_controls_and_special_categories(self) -> None:
        invalid_characters = [
            "\0",  # Control (Cc)
            "\b",  # Control (Cc)
            "\v",  # Control (Cc)
            "\f",  # Control (Cc)
            "\x1b",  # Control (Cc)
            "\u200b",  # Format (Cf)
            "\ud800",  # Surrogate (Cs)
            "\ue000",  # Private use (Co)
            "\u0378",  # Unassigned (Cn)
        ]

        for character in invalid_characters:
            with self.subTest(character=repr(character)):
                with self.assertRaises(ValueError):
                    validate_text(f"before{character}after")

    def test_currency_can_be_disabled_independently(self) -> None:
        for symbol in ["$", "€", "¥", "₱"]:
            with self.subTest(symbol=symbol):
                with self.assertRaises(ValueError):
                    validate_text(
                        f"Price {symbol}100",
                        allow_currency=False,
                        allow_ascii_punctuation=True,
                    )

        self.assertEqual(
            validate_text(
                "Price €100",
                allow_currency=True,
                allow_ascii_punctuation=False,
            ),
            "Price €100",
        )

    def test_ascii_punctuation_can_be_disabled(self) -> None:
        with self.assertRaises(ValueError):
            validate_text("Hello!", allow_ascii_punctuation=False)

        self.assertEqual(
            validate_text("Hello world", allow_ascii_punctuation=False),
            "Hello world",
        )

    def test_whitespace_can_be_disabled(self) -> None:
        whitespace = [" ", "\u00a0", "\u2028", "\u2029", "\t", "\n", "\r"]

        for character in whitespace:
            with self.subTest(character=repr(character)):
                with self.assertRaises(ValueError):
                    validate_text(
                        f"before{character}after",
                        allow_whitespace=False,
                    )

    def test_rejects_non_string_input(self) -> None:
        for value in [None, 123, b"text", ["text"], {"text": "value"}]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "text must be a string"):
                    validate_text(value)  # type: ignore[arg-type]

    def test_rejects_non_boolean_configuration(self) -> None:
        invalid_options = [
            ("allow_currency", {"allow_currency": 1}),
            ("allow_ascii_punctuation", {"allow_ascii_punctuation": "yes"}),
            ("allow_whitespace", {"allow_whitespace": None}),
        ]

        for option_name, options in invalid_options:
            with self.subTest(option=option_name):
                with self.assertRaisesRegex(
                    TypeError,
                    f"{option_name} must be a boolean",
                ):
                    validate_text("Hello", **options)  # type: ignore[arg-type]

    def test_error_reports_character_code_point_category_and_index(self) -> None:
        with self.assertRaises(ValueError) as raised:
            validate_text("A😊B")

        self.assertEqual(
            str(raised.exception),
            "Invalid character: '😊' (U+1F60A, category=So, index=1)",
        )

    def test_reports_only_the_first_invalid_character(self) -> None:
        with self.assertRaises(ValueError) as raised:
            validate_text("ok©😊")

        self.assertIn("'©'", str(raised.exception))
        self.assertIn("index=2", str(raised.exception))


class IsValidTextTests(unittest.TestCase):
    def test_returns_true_for_valid_text(self) -> None:
        self.assertTrue(is_valid_text("Hello 世界 ₱100\n"))
        self.assertTrue(is_valid_text(""))

    def test_returns_false_for_invalid_text_and_input_types(self) -> None:
        self.assertFalse(is_valid_text("Hello 😊"))
        self.assertFalse(is_valid_text(None))
        self.assertFalse(is_valid_text(123))

    def test_uses_the_same_configuration_policy(self) -> None:
        self.assertFalse(is_valid_text("$100", allow_currency=False))
        self.assertFalse(is_valid_text("Hello!", allow_ascii_punctuation=False))
        self.assertFalse(is_valid_text("Hello world", allow_whitespace=False))
        self.assertFalse(is_valid_text("Hello", allow_currency=1))


if __name__ == "__main__":
    unittest.main()
