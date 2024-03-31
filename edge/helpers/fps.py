from datetime import datetime as dt


class FPS:
    def __init__(self,
                 max_events=1000,
                 last_n_seconds=10) -> None:
        self._start = None
        self._max_events = max_events
        self._last_n_seconds = last_n_seconds
        self._timestamps = []

    def start(self) -> None:
        self._start = now()

    def update(self) -> None:
        curr = now()
        if self._start is None:
            self._start = curr
        self._timestamps.append(curr)
        if len(self._timestamps) > (self._max_events + 100):
            self._timestamps = self._timestamps[(1 - self._max_events):]
        self.expire_timestamps(curr)

    def fps(self) -> float:
        curr = now()
        if self._start is None:
            self._start = curr
        self.expire_timestamps(curr)
        seconds = min(curr - self._start, self._last_n_seconds)
        if seconds == 0:
            seconds = 1
        return len(self._timestamps) / seconds

    def expire_timestamps(self, curr):
        threshold = curr - self._last_n_seconds
        while self._timestamps and self._timestamps[0] < threshold:
            del self._timestamps[0]


def now() -> float:
    return dt.now() \
        .timestamp()
