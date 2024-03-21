from enum import Enum


class Parameters:
    def __init__(self, key: str, values: str | list[str]) -> None:
        return

    def __str__(self) -> str:
        if self.values:
            joined_values = ",".join(self.values)
            return f"{self.key} {joined_values}"


class PresetsInputType(Enum):
    RTSP_GENERIC = 1
    MP4_GENERIC = 2


PRESETS_INPUT = {
    PresetsInputType.RTSP_GENERIC: [
        Parameters("-avoid_negative_ts", "make_zero"),
        Parameters("-fflags", "nobuffer"),
        Parameters("-flags", "low_delay"),
        Parameters("-fflags", "+genpts+discardcorrupt"),
        Parameters("-rw_timeout", "5000000"),
        Parameters("-use_wallclock_as_timestamps", "1"),
        Parameters("-f", "live_flv")
    ],
    PresetsInputType.MP4_GENERIC: [
    ]
}
