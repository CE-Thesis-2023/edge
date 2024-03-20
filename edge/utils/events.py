import datetime
from datetime import datetime as dt


class EventsPerSecond:
    def __init__(self,
                 max_events=1000,
                 last_n_seconds=10) -> None:
        self._start = None
        self._max_events = max_events
        self._last_n_seconds = last_n_seconds
        self._timestamps = []

    def start(self) -> None:
        self._start = self.now()

    def now(self) -> float:
        return dt.now() \
            .timestamp()

    def update(self) -> None:
        now = self.now()
        if self._start is None:
            self._start = now
        self._timestamps.append(now)
        if len(self._timestamps) > (self._max_events + 100):
            self._timestamps[(1-self._max_events):]
        self.expire_timestamps(now)

    def eps(self) -> float:
        now = self.now()
        if self._start is None:
            self._start = now
        self.expire_timestamps(now)
        seconds = min(now - self._start, self._last_n_seconds)
        if seconds == 0:
            seconds = 1
        return len(self._timestamps) / seconds

    def expire_timestamps(self, now):
        threshold = now - self._last_n_seconds
        while self._timestamps and self._timestamps[0] < threshold:
            del self._timestamps[0]
