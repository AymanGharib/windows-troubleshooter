from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .models import TimeWindow

NS_PER_SEC = 1_000_000_000
NS_PER_MS = 1_000_000


def utc_now() -> datetime:
    return datetime.now(UTC)


def datetime_to_ns(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return int(value.timestamp() * NS_PER_SEC)


def ns_to_datetime(value_ns: int) -> datetime:
    return datetime.fromtimestamp(value_ns / NS_PER_SEC, tz=UTC)


def seconds_to_ns(value_s: float) -> int:
    return int(value_s * NS_PER_SEC)


def ns_to_seconds(value_ns: int) -> float:
    return value_ns / NS_PER_SEC


def build_window_from_alert(
    starts_at: datetime,
    ends_at: datetime | None,
    lookback_seconds: int,
    is_resolved: bool,
    now_utc: datetime | None = None,
) -> TimeWindow:
    if now_utc is None:
        now_utc = utc_now()

    start = starts_at - timedelta(seconds=lookback_seconds)
    end = ends_at if (is_resolved and ends_at is not None) else now_utc

    start_ns = datetime_to_ns(start)
    end_ns = datetime_to_ns(end)
    if end_ns <= start_ns:
        end_ns = start_ns + NS_PER_SEC
    return TimeWindow(start_ns=start_ns, end_ns=end_ns)
