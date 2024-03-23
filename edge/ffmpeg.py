from enum import Enum
import os
import shlex
from typing import Any, List, Optional, Self, Tuple
from venv import logger
import subprocess as sp
import requests


def vainfo_hwaccel(device_name: Optional[str] = None) -> sp.CompletedProcess:
    """Run vainfo."""
    ffprobe_cmd = (
        ["vainfo"]
        if not device_name
        else ["vainfo", "--display", "drm", "--device", f"/dev/dri/{device_name}"]
    )
    return sp.run(ffprobe_cmd, capture_output=True)


class LibvaGpuSelector:
    "Automatically selects the correct libva GPU."

    _selected_gpu = None

    def get_selected_gpu(self) -> str:
        """Get selected libva GPU."""
        if not os.path.exists("/dev/dri"):
            return ""

        if self._selected_gpu:
            return self._selected_gpu

        devices = list(filter(lambda d: d.startswith(
            "render"), os.listdir("/dev/dri")))

        if len(devices) < 2:
            self._selected_gpu = "/dev/dri/renderD128"
            return self._selected_gpu

        for device in devices:
            check = vainfo_hwaccel(device_name=device)

            logger.debug(
                f"{device} return vainfo status code: {check.returncode}")

            if check.returncode == 0:
                self._selected_gpu = f"/dev/dri/{device}"
                return self._selected_gpu

        return ""


class Parameters:
    def __init__(self, key: str, values: str | list[str]) -> None:
        return

    def __str__(self) -> str:
        if self.values:
            joined_values = ",".join(self.values)
            return f"{self.key} {joined_values}"


class PresetsInputType(str, Enum):
    RTSP_GENERIC = "rtsp_generic"
    MP4_GENERIC = "mp4_generic"

    @staticmethod
    def from_str(inp: str, default: Self) -> Self:
        for e in PresetsInputType:
            if e.value == inp:
                return e
        return default


PRESETS_INPUT = {
    PresetsInputType.RTSP_GENERIC: [
        "-avoid_negative_ts", "make_zero",
        "-fflags", "nobuffer",
        "-flags", "low_delay",
        "-fflags", "+genpts+discardcorrupt",
        "-rw_timeout", "5000000",
        "-use_wallclock_as_timestamps", "1",
        "-f", "live_flv",
    ],
    PresetsInputType.MP4_GENERIC: [
    ]
}


class HardwareAccelationScaleType(str, Enum):
    DEFAULT = "default",
    INTEL_QUICKSYNC_H264 = "intel_quicksync_h264",
    NVIDIA_CUDA = "nvidia_cuda"
    VA_API = "va_api"

    @staticmethod
    def from_str(inp: str, default: Self) -> Self:
        for e in HardwareAccelationScaleType:
            if e.value == inp:
                return e
        return default


PRESET_HARDWARE_ACCEL_SCALE = {
    HardwareAccelationScaleType.DEFAULT: "-r {0} -vf fps={0},scale={1}:{2}",
    HardwareAccelationScaleType.VA_API: f"-r {0} -vf fps={0},scale_vaapi=w={1}:h={2}:format=nv12,hwdownload,format=nv12,format=yuv420p",
    HardwareAccelationScaleType.NVIDIA_CUDA: f"-r {0} -vf fps={0},scale_cuda=w={1}:h={2}:format=nv12,hwdownload,format=nv12,format=yuv420p",
    HardwareAccelationScaleType.INTEL_QUICKSYNC_H264: "-r {0} -vf vpp_qsv=framerate={0}:w={1}:h={2}:format=nv12,hwdownload,format=nv12,format=yuv420p"
}


class HardwareAccelerationDecodeType(str, Enum):
    INTEL_QUICKSYNC_H264 = "intel_quicksync_h264"
    NVIDIA_CUDA = "nvidia_cuda"
    VA_API = "va_api"

    @staticmethod
    def from_str(inp: str, default: Self) -> Self:
        for e in HardwareAccelerationDecodeType:
            if e.value == inp:
                return e
        return default


_gpu_selector = LibvaGpuSelector()
PRESET_HARDWARE_ACCEL_DECODE = {
    HardwareAccelerationDecodeType.INTEL_QUICKSYNC_H264: f"-hwaccel qsv -qsv_device {_gpu_selector.get_selected_gpu()} -hwaccel_output_format qsv -c:v h264_qsv",
    HardwareAccelerationDecodeType.VA_API: f"-hwaccel_flags allow_profile_mismatch -hwaccel vaapi -hwaccel_device {_gpu_selector.get_selected_gpu()} -hwaccel_output_format vaapi",
    HardwareAccelerationDecodeType.NVIDIA_CUDA: "-hwaccel cuda -hwaccel_output_format cuda",
}


def parse_preset_hardware_acceleration_decode(
        args: Any,
        extra_args: List[str],
        fps: int,
        width: int,
        height: int) -> List[str]:
    if not isinstance(args, str):
        scale = PRESET_HARDWARE_ACCEL_DECODE[HardwareAccelerationDecodeType.VA_API]
    else:
        key = HardwareAccelerationDecodeType.from_str(
            inp=args, default=HardwareAccelerationDecodeType.VA_API)
        scale = PRESET_HARDWARE_ACCEL_DECODE.get(key)
    with_inputs = scale.format(fps, width, height).split(" ")
    with_inputs.extend(extra_args)
    return with_inputs


def autodetect_hwaccel() -> Tuple[HardwareAccelationScaleType, HardwareAccelerationDecodeType]:
    try:
        cuda = False
        vaapi = False
        resp = requests.get(
            "http://127.0.0.1:1984/api/ffmpeg/hardware", timeout=3)

        if resp.status_code == 200:
            data: dict[str, list[dict[str, str]]] = resp.json()
            for source in data.get("sources", []):
                if "cuda" in source.get("url", "") and source.get("name") == "OK":
                    cuda = True

                if "vaapi" in source.get("url", "") and source.get("name") == "OK":
                    vaapi = True
    except requests.RequestException:
        pass

    if cuda:
        logger.info("Automatically detected nvidia hwaccel for video decoding")
        return (HardwareAccelationScaleType.NVIDIA_CUDA, HardwareAccelerationDecodeType.NVIDIA_CUDA)

    if vaapi:
        logger.info("Automatically detected vaapi hwaccel for video decoding")
        return (HardwareAccelationScaleType.VA_API, HardwareAccelerationDecodeType.VA_API)

    logger.warning(
        "Did not detect hwaccel, using a GPU for accelerated video decoding is highly recommended"
    )
    return ""


def get_ffmpeg_argument_list(arg: Any) -> List[str]:
    if isinstance(arg, list) is True:
        return arg
    else:
        return shlex.split(arg)


def parse_preset_hardware_acceleration_scale(
        args: Any,
        extra_args: List[str],
        fps: int,
        width: int,
        height: int) -> List[str]:
    if not isinstance(args, str):
        scale = PRESET_HARDWARE_ACCEL_SCALE[HardwareAccelationScaleType.DEFAULT]
    else:
        key = HardwareAccelationScaleType.from_str(
            inp=args, default=HardwareAccelationScaleType.DEFAULT)
        scale = PRESET_HARDWARE_ACCEL_SCALE.get(key)
    with_inputs = scale.format(fps, width, height).split(" ")
    with_inputs.extend(extra_args)
    return with_inputs


def parse_preset_input(args: Any) -> List[str]:
    if not isinstance(args, str):
        return PresetsInputType.RTSP_GENERIC
    key = PresetsInputType.from_str(
        args, default=PresetsInputType.RTSP_GENERIC)
    return PRESETS_INPUT.get(key)
