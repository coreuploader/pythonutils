import unittest
from datetime import date, datetime, timedelta, timezone, tzinfo
from unittest.mock import patch
from zoneinfo import ZoneInfo

from utilities.datetime import (
    days_between,
    end_of_day,
    ensure_utc,
    format_datetime,
    is_expired,
    minutes_between,
    naive_utc_now,
    parse_datetime,
    start_of_day,
    seconds_between,
    to_timezone,
    utc_now,
)


class _NaiveTimezone(tzinfo):
    """Test timezone that deliberately provides no UTC offset."""

    def utcoffset(self, value: datetime | None) -> None:
        return None


class DurationBetweenTests(unittest.TestCase):
    def test_returns_unrounded_elapsed_units(self) -> None:
        start = datetime(2026, 9, 17, 10, tzinfo=timezone.utc)
        end = datetime(2026, 9, 18, 12, 30, tzinfo=timezone.utc)

        self.assertEqual(seconds_between(start, end), 95400.0)
        self.assertEqual(minutes_between(start, end), 1590.0)
        self.assertEqual(days_between(start, end), 1.1041666666666667)

    def test_preserves_fractional_seconds_without_rounding(self) -> None:
        start = datetime(2026, 9, 17, tzinfo=timezone.utc)
        end = start + timedelta(seconds=1, microseconds=500000)

        self.assertEqual(seconds_between(start, end), 1.5)
        self.assertEqual(minutes_between(start, end), 0.025)
        self.assertEqual(days_between(start, end), 1.5 / 86400)

    def test_preserves_negative_direction(self) -> None:
        start = datetime(2026, 9, 18, tzinfo=timezone.utc)
        end = datetime(2026, 9, 17, tzinfo=timezone.utc)

        self.assertEqual(seconds_between(start, end), -86400.0)
        self.assertEqual(minutes_between(start, end), -1440.0)
        self.assertEqual(days_between(start, end), -1.0)

    def test_different_offsets_for_same_instant_return_zero(self) -> None:
        start = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        end = datetime(
            2026,
            9,
            17,
            20,
            tzinfo=timezone(timedelta(hours=8)),
        )

        self.assertEqual(seconds_between(start, end), 0.0)
        self.assertEqual(minutes_between(start, end), 0.0)
        self.assertEqual(days_between(start, end), 0.0)

    def test_spring_dst_day_is_twenty_three_elapsed_hours(self) -> None:
        new_york = ZoneInfo("America/New_York")
        start = datetime(2026, 3, 8, tzinfo=new_york)
        end = datetime(2026, 3, 9, tzinfo=new_york)

        self.assertEqual(seconds_between(start, end), 23 * 60 * 60)
        self.assertEqual(minutes_between(start, end), 23 * 60)
        self.assertEqual(days_between(start, end), 23 / 24)

    def test_fall_dst_day_is_twenty_five_elapsed_hours(self) -> None:
        new_york = ZoneInfo("America/New_York")
        start = datetime(2026, 11, 1, tzinfo=new_york)
        end = datetime(2026, 11, 2, tzinfo=new_york)

        self.assertEqual(seconds_between(start, end), 25 * 60 * 60)
        self.assertEqual(minutes_between(start, end), 25 * 60)
        self.assertEqual(days_between(start, end), 25 / 24)

    def test_rejects_naive_values(self) -> None:
        aware = datetime(2026, 9, 17, tzinfo=timezone.utc)
        naive = datetime(2026, 9, 17)

        for function in [seconds_between, minutes_between, days_between]:
            with self.subTest(function=function.__name__, argument="start"):
                with self.assertRaisesRegex(
                    ValueError,
                    "start must include timezone information",
                ):
                    function(naive, aware)

            with self.subTest(function=function.__name__, argument="end"):
                with self.assertRaisesRegex(
                    ValueError,
                    "end must include timezone information",
                ):
                    function(aware, naive)

    def test_rejects_non_datetime_values(self) -> None:
        aware = datetime(2026, 9, 17, tzinfo=timezone.utc)

        for function in [seconds_between, minutes_between, days_between]:
            with self.subTest(function=function.__name__, argument="start"):
                with self.assertRaisesRegex(TypeError, "start must be a datetime"):
                    function(None, aware)  # type: ignore[arg-type]

            with self.subTest(function=function.__name__, argument="end"):
                with self.assertRaisesRegex(TypeError, "end must be a datetime"):
                    function(aware, date(2026, 9, 17))  # type: ignore[arg-type]


class IsExpiredTests(unittest.TestCase):
    def test_returns_true_for_past_expiration(self) -> None:
        reference = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        expires_at = reference - timedelta(microseconds=1)

        self.assertTrue(is_expired(expires_at, reference_time=reference))

    def test_returns_false_for_future_expiration(self) -> None:
        reference = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        expires_at = reference + timedelta(microseconds=1)

        self.assertFalse(is_expired(expires_at, reference_time=reference))

    def test_treats_exact_reference_boundary_as_expired(self) -> None:
        boundary = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)

        self.assertTrue(is_expired(boundary, reference_time=boundary))

    def test_compares_different_offsets_as_absolute_instants(self) -> None:
        expires_at = datetime(
            2026,
            9,
            17,
            20,
            tzinfo=timezone(timedelta(hours=8)),
        )
        reference = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)

        self.assertTrue(is_expired(expires_at, reference_time=reference))

    def test_compares_repeated_dst_hour_as_absolute_instants(self) -> None:
        new_york = ZoneInfo("America/New_York")
        expires_at = datetime(2026, 11, 1, 1, 30, tzinfo=new_york, fold=0)
        reference = datetime(2026, 11, 1, 1, 15, tzinfo=new_york, fold=1)

        self.assertTrue(is_expired(expires_at, reference_time=reference))

    def test_uses_utc_now_when_reference_is_omitted(self) -> None:
        current = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        expires_at = current - timedelta(seconds=1)

        with patch("utilities.datetime.utc_now", return_value=current) as mock:
            result = is_expired(expires_at)

        self.assertTrue(result)
        mock.assert_called_once_with()

    def test_rejects_naive_expiration(self) -> None:
        reference = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)

        with self.assertRaisesRegex(
            ValueError,
            "expires_at must include timezone information",
        ):
            is_expired(datetime(2026, 9, 17, 11), reference_time=reference)

    def test_rejects_naive_reference(self) -> None:
        expires_at = datetime(2026, 9, 17, 11, tzinfo=timezone.utc)

        with self.assertRaisesRegex(
            ValueError,
            "reference_time must include timezone information",
        ):
            is_expired(
                expires_at,
                reference_time=datetime(2026, 9, 17, 12),
            )

    def test_rejects_invalid_argument_types(self) -> None:
        aware_value = datetime(2026, 9, 17, tzinfo=timezone.utc)

        for expires_at in [None, date(2026, 9, 17), "2026-09-17"]:
            with self.subTest(argument="expires_at", value=expires_at):
                with self.assertRaisesRegex(
                    TypeError,
                    "expires_at must be a datetime",
                ):
                    is_expired(
                        expires_at,  # type: ignore[arg-type]
                        reference_time=aware_value,
                    )

        for reference_time in [date(2026, 9, 17), "2026-09-17", 0]:
            with self.subTest(argument="reference_time", value=reference_time):
                with self.assertRaisesRegex(
                    TypeError,
                    "reference_time must be a datetime",
                ):
                    is_expired(
                        aware_value,
                        reference_time=reference_time,  # type: ignore[arg-type]
                    )


class DayBoundaryTests(unittest.TestCase):
    def test_returns_boundaries_in_existing_fixed_offset_timezone(self) -> None:
        source_timezone = timezone(timedelta(hours=8))
        value = datetime(2026, 9, 17, 12, 30, 45, 123456, tzinfo=source_timezone)

        self.assertEqual(
            start_of_day(value),
            datetime(2026, 9, 17, tzinfo=source_timezone),
        )
        self.assertEqual(
            end_of_day(value),
            datetime(2026, 9, 17, 23, 59, 59, 999999, tzinfo=source_timezone),
        )

    def test_does_not_convert_the_input_calendar_date(self) -> None:
        source_timezone = timezone(timedelta(hours=8))
        value = datetime(2026, 9, 17, 0, 30, tzinfo=source_timezone)

        self.assertEqual(start_of_day(value).date(), date(2026, 9, 17))
        self.assertEqual(end_of_day(value).date(), date(2026, 9, 17))
        self.assertIs(start_of_day(value).tzinfo, source_timezone)
        self.assertIs(end_of_day(value).tzinfo, source_timezone)

    def test_spring_day_boundaries_reflect_short_day(self) -> None:
        new_york = ZoneInfo("America/New_York")
        value = datetime(2026, 3, 8, 12, tzinfo=new_york)

        start = start_of_day(value)
        end = end_of_day(value)

        self.assertEqual(start.utcoffset(), timedelta(hours=-5))
        self.assertEqual(end.utcoffset(), timedelta(hours=-4))
        elapsed = ensure_utc(end) - ensure_utc(start)
        self.assertEqual(elapsed, timedelta(hours=23) - timedelta(microseconds=1))

    def test_fall_day_boundaries_reflect_long_day(self) -> None:
        new_york = ZoneInfo("America/New_York")
        value = datetime(2026, 11, 1, 12, tzinfo=new_york)

        start = start_of_day(value)
        end = end_of_day(value)

        self.assertEqual(start.utcoffset(), timedelta(hours=-4))
        self.assertEqual(end.utcoffset(), timedelta(hours=-5))
        elapsed = ensure_utc(end) - ensure_utc(start)
        self.assertEqual(elapsed, timedelta(hours=25) - timedelta(microseconds=1))

    def test_resets_fold_at_day_boundaries(self) -> None:
        value = datetime(
            2026,
            11,
            1,
            1,
            30,
            tzinfo=ZoneInfo("America/New_York"),
            fold=1,
        )

        self.assertEqual(start_of_day(value).fold, 0)
        self.assertEqual(end_of_day(value).fold, 0)

    def test_rejects_naive_datetime(self) -> None:
        value = datetime(2026, 9, 17, 12)

        for function in [start_of_day, end_of_day]:
            with self.subTest(function=function.__name__):
                with self.assertRaisesRegex(
                    ValueError,
                    "value must include timezone information",
                ):
                    function(value)

    def test_rejects_non_datetime_input(self) -> None:
        for function in [start_of_day, end_of_day]:
            for value in [None, date(2026, 9, 17), "2026-09-17"]:
                with self.subTest(function=function.__name__, value=value):
                    with self.assertRaisesRegex(
                        TypeError,
                        "value must be a datetime",
                    ):
                        function(value)  # type: ignore[arg-type]


class FormatDatetimeTests(unittest.TestCase):
    def test_defaults_to_utc_iso_8601_with_z_suffix(self) -> None:
        value = datetime(2026, 9, 17, 12, 30, 45, tzinfo=timezone.utc)

        self.assertEqual(format_datetime(value), "2026-09-17T12:30:45Z")

    def test_preserves_non_zero_microseconds(self) -> None:
        value = datetime(
            2026,
            9,
            17,
            12,
            30,
            45,
            123456,
            tzinfo=timezone.utc,
        )

        self.assertEqual(
            format_datetime(value),
            "2026-09-17T12:30:45.123456Z",
        )

    def test_accepts_supported_datetime_string(self) -> None:
        self.assertEqual(
            format_datetime("2026-09-17T08:30:45+08:00"),
            "2026-09-17T00:30:45Z",
        )

    def test_converts_to_requested_timezone_before_formatting(self) -> None:
        value = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)

        self.assertEqual(
            format_datetime(value, timezone_name="Asia/Manila"),
            "2026-09-17T08:30:00+08:00",
        )

    def test_custom_format_is_applied_after_timezone_conversion(self) -> None:
        value = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)

        self.assertEqual(
            format_datetime(
                value,
                timezone_name="Asia/Manila",
                format_string="%Y/%m/%d %H:%M",
            ),
            "2026/09/17 08:30",
        )

    def test_target_timezone_uses_date_specific_daylight_saving_offset(self) -> None:
        value = datetime(2026, 7, 15, 12, tzinfo=timezone.utc)

        self.assertEqual(
            format_datetime(value, timezone_name="America/New_York"),
            "2026-07-15T08:00:00-04:00",
        )

    def test_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must include timezone information",
        ):
            format_datetime(datetime(2026, 9, 17, 12, 30))

    def test_rejects_unsupported_string_format(self) -> None:
        with self.assertRaisesRegex(ValueError, "ISO 8601 datetime"):
            format_datetime("2026-09-17 12:30:45")

    def test_rejects_invalid_value_type(self) -> None:
        for value in [None, date(2026, 9, 17), 20260917, b"datetime"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    TypeError,
                    "value must be a datetime or string",
                ):
                    format_datetime(value)  # type: ignore[arg-type]

    def test_rejects_invalid_format_string_type(self) -> None:
        value = datetime(2026, 9, 17, tzinfo=timezone.utc)

        for format_string in [123, b"%Y", []]:
            with self.subTest(format_string=format_string):
                with self.assertRaisesRegex(
                    TypeError,
                    "format_string must be a string or None",
                ):
                    format_datetime(
                        value,
                        format_string=format_string,  # type: ignore[arg-type]
                    )

    def test_rejects_invalid_timezone_identifier(self) -> None:
        value = datetime(2026, 9, 17, tzinfo=timezone.utc)

        with self.assertRaisesRegex(ValueError, "unknown timezone"):
            format_datetime(value, timezone_name="Mars/Olympus")


class ParseDatetimeTests(unittest.TestCase):
    def test_parses_utc_z_suffix(self) -> None:
        self.assertEqual(
            parse_datetime("2026-09-17T12:30:45Z"),
            datetime(2026, 9, 17, 12, 30, 45, tzinfo=timezone.utc),
        )

    def test_normalizes_positive_offset_to_utc(self) -> None:
        self.assertEqual(
            parse_datetime("2026-09-17T08:30:45+08:00"),
            datetime(2026, 9, 17, 0, 30, 45, tzinfo=timezone.utc),
        )

    def test_normalizes_negative_offset_across_date_boundary(self) -> None:
        self.assertEqual(
            parse_datetime("2026-09-17T22:30:45-05:00"),
            datetime(2026, 9, 18, 3, 30, 45, tzinfo=timezone.utc),
        )

    def test_accepts_space_separator_and_fractional_seconds(self) -> None:
        self.assertEqual(
            parse_datetime("2026-09-17 12:30:45.1Z"),
            datetime(2026, 9, 17, 12, 30, 45, 100000, tzinfo=timezone.utc),
        )
        self.assertEqual(
            parse_datetime("2026-09-17T12:30:45.123456+00:00"),
            datetime(2026, 9, 17, 12, 30, 45, 123456, tzinfo=timezone.utc),
        )

    def test_rejects_unsupported_formats(self) -> None:
        invalid_values = [
            "",
            "2026-09-17",
            "2026-09-17T12:30:45",
            "2026-09-17T12:30Z",
            "2026-09-17T12:30:45z",
            "2026/09/17T12:30:45Z",
            "2026-09-17T12:30:45+0800",
            "2026-09-17T12:30:45.1234567Z",
            " 2026-09-17T12:30:45Z",
            "2026-09-17T12:30:45Z ",
            "Thu, 17 Sep 2026 12:30:45 GMT",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "ISO 8601 datetime with seconds and an explicit offset",
                ):
                    parse_datetime(value)

    def test_rejects_invalid_calendar_and_offset_values(self) -> None:
        invalid_values = [
            "2026-02-29T12:30:45Z",
            "2026-13-01T12:30:45Z",
            "2026-09-17T24:00:00Z",
            "2026-09-17T12:60:00Z",
            "2026-09-17T12:30:60Z",
            "2026-09-17T12:30:45+24:00",
        ]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    "ISO 8601 datetime with seconds and an explicit offset",
                ):
                    parse_datetime(value)

    def test_rejects_non_string_input(self) -> None:
        for value in [None, datetime(2026, 9, 17), 20260917, b"datetime"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "value must be a string"):
                    parse_datetime(value)  # type: ignore[arg-type]


class ToTimezoneTests(unittest.TestCase):
    def test_converts_utc_to_iana_timezone(self) -> None:
        value = datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc)

        result = to_timezone(value, "Asia/Manila")

        self.assertEqual(
            result,
            datetime(2026, 9, 17, 8, 30, tzinfo=ZoneInfo("Asia/Manila")),
        )
        self.assertEqual(result.tzinfo.key, "Asia/Manila")

    def test_preserves_instant_from_non_utc_source(self) -> None:
        source_timezone = timezone(timedelta(hours=5, minutes=30))
        value = datetime(2026, 9, 17, 15, 0, tzinfo=source_timezone)

        result = to_timezone(value, "Europe/London")

        self.assertEqual(result.astimezone(timezone.utc), ensure_utc(value))
        self.assertEqual(result.tzinfo.key, "Europe/London")

    def test_applies_daylight_saving_offset_for_target_date(self) -> None:
        winter = to_timezone(
            datetime(2026, 1, 15, 12, tzinfo=timezone.utc),
            "America/New_York",
        )
        summer = to_timezone(
            datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
            "America/New_York",
        )

        self.assertEqual(winter.hour, 7)
        self.assertEqual(winter.utcoffset(), timedelta(hours=-5))
        self.assertEqual(summer.hour, 8)
        self.assertEqual(summer.utcoffset(), timedelta(hours=-4))

    def test_preserves_fold_during_repeated_daylight_saving_hour(self) -> None:
        first = to_timezone(
            datetime(2026, 11, 1, 5, 30, tzinfo=timezone.utc),
            "America/New_York",
        )
        second = to_timezone(
            datetime(2026, 11, 1, 6, 30, tzinfo=timezone.utc),
            "America/New_York",
        )

        self.assertEqual((first.hour, first.minute, first.fold), (1, 30, 0))
        self.assertEqual((second.hour, second.minute, second.fold), (1, 30, 1))
        self.assertNotEqual(first.utcoffset(), second.utcoffset())

    def test_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must include timezone information",
        ):
            to_timezone(datetime(2026, 9, 17, 12), "Asia/Manila")

    def test_rejects_non_datetime_input(self) -> None:
        for value in [None, date(2026, 9, 17), "2026-09-17T12:00:00Z"]:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "value must be a datetime"):
                    to_timezone(value, "UTC")  # type: ignore[arg-type]

    def test_rejects_invalid_timezone_identifier(self) -> None:
        for timezone_name in ["", "Mars/Olympus", "../UTC", "/etc/localtime"]:
            with self.subTest(timezone_name=timezone_name):
                with self.assertRaisesRegex(ValueError, "unknown timezone"):
                    to_timezone(
                        datetime(2026, 9, 17, tzinfo=timezone.utc),
                        timezone_name,
                    )

    def test_rejects_non_string_timezone_identifier(self) -> None:
        for timezone_name in [None, 123, ZoneInfo("UTC")]:
            with self.subTest(timezone_name=timezone_name):
                with self.assertRaisesRegex(
                    TypeError,
                    "timezone_name must be a string",
                ):
                    to_timezone(
                        datetime(2026, 9, 17, tzinfo=timezone.utc),
                        timezone_name,  # type: ignore[arg-type]
                    )


class EnsureUtcTests(unittest.TestCase):
    def test_returns_utc_datetime_unchanged_in_value(self) -> None:
        value = datetime(2026, 9, 17, 12, 30, 45, 123456, tzinfo=timezone.utc)

        result = ensure_utc(value)

        self.assertEqual(result, value)
        self.assertIs(result.tzinfo, timezone.utc)

    def test_converts_positive_offset_and_preserves_instant(self) -> None:
        source_timezone = timezone(timedelta(hours=8))
        value = datetime(2026, 9, 17, 8, 30, tzinfo=source_timezone)

        result = ensure_utc(value)

        self.assertEqual(
            result,
            datetime(2026, 9, 17, 0, 30, tzinfo=timezone.utc),
        )

    def test_converts_negative_offset_across_date_boundary(self) -> None:
        source_timezone = timezone(timedelta(hours=-5))
        value = datetime(2026, 9, 17, 22, 30, tzinfo=source_timezone)

        result = ensure_utc(value)

        self.assertEqual(
            result,
            datetime(2026, 9, 18, 3, 30, tzinfo=timezone.utc),
        )

    def test_rejects_naive_datetime(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "value must include timezone information",
        ):
            ensure_utc(datetime(2026, 9, 17, 12, 30))

    def test_rejects_tzinfo_without_an_offset(self) -> None:
        value = datetime(2026, 9, 17, 12, 30, tzinfo=_NaiveTimezone())

        with self.assertRaisesRegex(
            ValueError,
            "value must include timezone information",
        ):
            ensure_utc(value)

    def test_rejects_non_datetime_input(self) -> None:
        invalid_values = [None, "2026-09-17", date(2026, 9, 17), 0]

        for value in invalid_values:
            with self.subTest(value=value):
                with self.assertRaisesRegex(TypeError, "value must be a datetime"):
                    ensure_utc(value)  # type: ignore[arg-type]


class UtcNowTests(unittest.TestCase):
    def test_returns_timezone_aware_utc_datetime(self) -> None:
        result = utc_now()

        self.assertIsInstance(result, datetime)
        self.assertIs(result.tzinfo, timezone.utc)
        self.assertEqual(result.utcoffset(), timedelta(0))

    def test_reads_the_clock_with_explicit_utc_timezone(self) -> None:
        expected = datetime(2026, 9, 17, 12, 30, tzinfo=timezone.utc)

        with patch("utilities.datetime.datetime") as datetime_mock:
            datetime_mock.now.return_value = expected

            result = utc_now()

        self.assertIs(result, expected)
        datetime_mock.now.assert_called_once_with(timezone.utc)


class NaiveUtcNowTests(unittest.TestCase):
    def test_removes_only_timezone_information_from_aware_utc_now(self) -> None:
        aware_value = datetime(
            2026,
            9,
            17,
            12,
            30,
            45,
            123456,
            tzinfo=timezone.utc,
        )

        with patch("utilities.datetime.utc_now", return_value=aware_value) as mock:
            result = naive_utc_now()

        self.assertEqual(result, datetime(2026, 9, 17, 12, 30, 45, 123456))
        self.assertIsNone(result.tzinfo)
        self.assertIs(aware_value.tzinfo, timezone.utc)
        mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
