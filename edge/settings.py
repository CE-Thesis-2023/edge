import os
import subprocess as sp
from typing import Dict, Tuple, Optional

import picologging as logging
import yaml
from cerberus import Validator

from edge.process.object.settings import PixelFormatEnum, ModelTypeEnum, InputTensorEnum

DEFAULT_CAMERA_GLOBAL_ARGUMENTS = ["-hide_banner",
                                   "-loglevel", "warning"]

DEFAULT_CAMERA_OUTPUT_ARGUMENTS = [
    "-f",
    "rawvideo",
    "-pix_fmt",
    "yuv420p"]

schema = {
    'cameras': {
        'type': 'dict',
        'keysrules': {
            'type': 'string',
        },
        'valuesrules': {
            'type': 'dict',
            'schema': {
                'best_image_timeout': {
                    'type': 'integer',
                },
                'source': {
                    'type': 'dict',
                    'schema': {
                        'path': {
                            'type': 'string',
                            'required': True,
                        },
                        'global-args': {
                            'type': 'string',
                        },
                        'input-args': {
                            'type': 'string',
                            'required': True,
                        },
                        'output-args': {
                            'type': 'string',
                        },
                        'hardware-acceleration': {
                            'type': 'string',
                            'required': True,
                        },
                    },
                },
                'detect': {
                    'type': 'dict',
                    'schema': {
                        'height': {
                            'type': 'integer',
                        },
                        'width': {
                            'type': 'integer',
                        },
                        'fps': {
                            'type': 'integer',
                        },
                        'min_initialized': {
                            'type': 'integer',
                        },
                        'max_disappear': {
                            'type': 'integer',
                        },
                        'stationary': {
                            'type': 'dict',
                            'schema': {
                                'interval': {
                                    'type': 'integer'
                                },
                                'threshold': {
                                    'type': 'integer'
                                },
                                'max_frames': {
                                    'type': 'integer'
                                }
                            }
                        }
                    },
                },
                'mqtt': {
                    'type': 'dict',
                    'schema': {
                        'host': {
                            'type': 'string',
                        },
                        'port': {
                            'type': 'integer',
                        },
                        'topic': {
                            'type': 'string',
                        },
                    },
                },
            }
        }
    },
    'model': {
        'type': 'dict',
        'schema': {
            'path': {
                'type': 'string',
                'required': True,
            },
            'input_pixel_format': {
                'type': 'string',
                'required': True,
                'allowed': list(PixelFormatEnum),
            },
            'type': {
                'type': 'string',
                'required': True,
                'allowed': list(ModelTypeEnum),
            },
            'labels': {
                'type': 'list',
                'required': True,
                'schema': {
                    'type': 'string'
                },
            },
            'input_tensor': {
                'type': 'string',
                'required': True,
                'allowed': list(InputTensorEnum),
            },
            'width': {
                'type': 'integer',
                'required': True,
            },
            'height': {
                'type': 'integer',
                'required': True,
            },
        }
    }
}


def validate(data) -> Dict:
    v = Validator(schema)
    if not v.validate(data):
        return v.errors
    return {}


def load(path) -> Dict:
    with open(path, 'r') as f:
        data = yaml.safe_load(f)
    return data


def with_defaults(settings: Dict):
    cameras = settings['cameras']
    for _, values in cameras.items():
        if values.get('best_image_timeout') is None:
            values['best_image_timeout'] = 10
        if values.get('detect') is None:
            values['detect'] = {}
        detect = values['detect']
        if detect.get('height') is None:
            detect['height'] = 320
        if detect.get('width') is None:
            detect['width'] = 320
        if detect.get('fps') is None:
            detect['fps'] = 10
        if detect.get('min_initialized') is None:
            detect['min_initialized'] = 10
        if detect.get('max_disappear') is None:
            detect['max_disappear'] = 10
        if detect.get('stationary') is None:
            detect['stationary'] = {}
        stationary = detect.get('stationary')
        if stationary.get('interval') is None:
            stationary['interval'] = 0
        if stationary.get('threshold''threshold') is None:
            stationary['threshold'] = 1
        if stationary.get('max_frames') is None:
            stationary['max_frames'] = 1
        if values.get('source') is None:
            values['source'] = {}
        source = values['source']
        if source.get('global-args') is None:
            source['global-args'] = " ".join(DEFAULT_CAMERA_GLOBAL_ARGUMENTS)
        if source.get('output-args') is None:
            source['output-args'] = " ".join(DEFAULT_CAMERA_OUTPUT_ARGUMENTS)

    model = settings['model']
    if model.get('input_pixel_format') is None:
        model['input_pixel_format'] = PixelFormatEnum.RGB.value
    if model.get('type') is None:
        model['type'] = ModelTypeEnum.YOLOv8
    if model.get('input_tensor') is None:
        model['input_tensor'] = InputTensorEnum.NCHW.value

    return settings


def get_ffmpeg_cmd(source: Dict, detect: Dict) -> str:
    info = get_frame_size_fps(detect)
    fps = info[2]
    height, width = info[:2]
    decode_args = get_hardware_acceleration_decode(
        hardware_acceleration_args=source['hardware-acceleration'])
    scale_args = get_hardware_acceleration_scale(
        hardware_acceleration_args=source['hardware-acceleration'],
        fps=fps,
        width=width,
        height=height)
    input_args = get_preset_input(preset=source['input-args'])
    cmd = [
        "ffmpeg",
        source['global-args'],
        decode_args,
        input_args,
        f"-i {source['path']}",
        scale_args,
        source['output-args'],
        "pipe:"
    ]
    return ' '.join(cmd)


def get_frame_size_fps(detect: Dict) -> Tuple[int, int, int]:
    return (detect['height'],
            detect['width'],
            detect['fps'])


def get_frame_size_fps_yuv(detect: Dict) -> Tuple[int, int, int]:
    return (detect['height'],
            (detect['height'] * 3//2),
            detect['fps'])


def run_check_vainfo(device_name: Optional[str] = None) -> sp.CompletedProcess:
    ffprobe_cmd = (
        ["vainfo"]
        if not device_name
        else ["vainfo", "--display", "drm", "--device", f"/dev/dri/{device_name}"]
    )
    return sp.run(ffprobe_cmd, capture_output=True)


class LibvaGpuSelector:
    _selected_gpu = None

    def get_selected_gpu(self) -> str:
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
            check = run_check_vainfo(device_name=device)

            logging.debug(
                f"{device} return vainfo status code: {check.returncode}")

            if check.returncode == 0:
                self._selected_gpu = f"/dev/dri/{device}"
                return self._selected_gpu

        return ""


FFMPEG_PRESETS_INPUT = {
    'rtsp-generic': [
        "-avoid_negative_ts",
        "make_zero",
        "-fflags",
        "+genpts+discardcorrupt",
        "-rtsp_transport",
        "tcp",
        "-timeout",
        "5000000",
        "-use_wallclock_as_timestamps",
        "1",
    ]
}

_gpu_selector = LibvaGpuSelector()

FFMPEG_HARDWARE_ACCELERATION_SCALE = {
    "va-api": "-r {0} -vf fps={0},scale_vaapi=w={1}:h={2}:format=nv12,hwdownload,format=nv12,format=yuv420p",
    "quicksync": "-r {0} -vf vpp_qsv=framerate={0}:w={1}:h={2}:format=nv12,hwdownload,format=nv12,format=yuv420p",
    "default": "-r {0} -vf fps={0},scale=w={1}:h={2}",
}

FFMPEG_HARDWARE_ACCELERATION_DECODE = {
    "va-api": f"-hwaccel_flags allow_profile_mismatch -hwaccel vaapi -hwaccel_device {_gpu_selector.get_selected_gpu()} -hwaccel_output_format vaapi",
    "quicksync": f"-hwaccel qsv -qsv_device {_gpu_selector.get_selected_gpu()} -hwaccel_output_format qsv -c:v h264_qsv",
}


def get_preset_input(preset: str) -> str:
    return ' '.join(FFMPEG_PRESETS_INPUT.get(
        preset, FFMPEG_PRESETS_INPUT['rtsp-generic']))


def get_hardware_acceleration_scale(hardware_acceleration_args: str,
                                    fps: int,
                                    width: int,
                                    height: int) -> str:
    template = FFMPEG_HARDWARE_ACCELERATION_SCALE.get(hardware_acceleration_args,
                                                      FFMPEG_HARDWARE_ACCELERATION_SCALE["va-api"])
    return template.format(fps, width, height)


def get_hardware_acceleration_decode(hardware_acceleration_args: str) -> str:
    return FFMPEG_HARDWARE_ACCELERATION_DECODE.get(hardware_acceleration_args,
                                                   FFMPEG_HARDWARE_ACCELERATION_DECODE["va-api"])
