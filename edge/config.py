from typing import List, Dict, Self, Tuple, Union, Optional
from enum import Enum
from pydantic import BaseModel, Field, ValidationInfo,  field_validator, ConfigDict
from edge.ffmpeg import get_ffmpeg_argument_list, parse_preset_hardware_acceleration_scale, parse_preset_input, parse_preset_hardware_acceleration_decode
from yaml import load, CLoader as Loader
import json

FFMPEG_DEFAULT_GLOBAL_ARGS = ["-hide_banner",
                              "-loglevel", "warning", "-threads", "2"]

FFMPEG_DEFAULT_OUTPUTS_ARGS = ["-threads",
                               "2",
                               "-f",
                               "rawvideo",
                               "-pix_fmt",
                               "yuv420p"]


class EdgeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces={})


class FfmpegConfig(BaseModel):
    global_args: Union[str, List[str]] = Field(
        default=FFMPEG_DEFAULT_GLOBAL_ARGS,
        title="Global FFMPEG arguments")
    hwaccel_args: Union[str, List[str]] = Field(
        default="",
        title="FFMPEG Hardware Acceleration Arguments")
    input_args: Union[str, List[str]] = Field(
        default="",
        title="FFMPEG Input Arguments")
    output_args: Union[str, List[str]] = Field(
        default=FFMPEG_DEFAULT_OUTPUTS_ARGS,
        title="FFMPEG Output Arguments")
    retry_interval: float = Field(
        default=5.0,
        title="Retry Interval",
        description="The interval between FFMPEG retries connecting to the camera")


class CameraInput(EdgeBaseModel):
    path: str = Field(
        default="",
        title="Input Path",
        description="The path to the camera input")
    ffmpeg: FfmpegConfig = Field(
        default_factory=FfmpegConfig,
        title="FFMPEG Configuration",
        description="The FFMPEG configuration for the camera input")


class StationaryConfig(EdgeBaseModel):
    interval: Optional[int] = Field(
        None,
        title="Frame interval for checking stationary objects.",
        gt=0,
    )
    threshold: Optional[int] = Field(
        None,
        title="Number of frames without a position change for an object to be considered stationary",
        ge=1,
    )
    max_frames: Optional[int] = Field(
        default=None,
        title="Max frames for stationary objects.",
        ge=1,
    )


class DetectConfig(EdgeBaseModel):
    height: Optional[int] = Field(
        default=None,
        title="Height",
        description="The height of the detection frame")
    width: Optional[int] = Field(
        default=None,
        title="Width",
        description="The width of the detection frame")
    fps: int = Field(
        default=5,
        title="FPS",
        description="The frames per second of the detection frame")
    min_initialized: Optional[int] = Field(
        default=None,
        title="Min Initialized",
        description="The minimum number of frames to initialize the tracker")
    max_disappeared: Optional[int] = Field(
        default=None,
        title="Max Disappeared",
        description="The maximum number of frames the object can disappear before detection ends")
    stationary: StationaryConfig = Field(
        default=None,
        title="Stationary Configuration",
        description="The configuration for stationary objects")


class EventMqttConfig(EdgeBaseModel):
    enabled: bool = Field(
        default=False,
        title="Enable MQTT messaging",
        description="Events and messages are passed to the MQTT broker")
    host: str = Field(
        default="",
        title="MQTT Broker",
        description="The hostname or IP address of the MQTT broker")
    port: int = Field(
        default=1883,
        title="Port",
        description="The port number of the MQTT broker")
    topic_prefix: str = Field(
        default="edge",
        title="Topic Prefix",
        description="The prefix for all MQTT topics")
    client_id: str = Field(
        default="edge-0",
        title="Client ID",
        description="The client ID for the MQTT connection")
    user: str = Field(
        default="",
        title="Username",
        description="The username for the MQTT connection")
    password: str = Field(
        default="",
        title="Password",
        description="The password for the MQTT connection")

    @field_validator("password")
    def user_requires_pass(cls, v, info: ValidationInfo):
        if (v is None) != (info.data["user"] is None):
            raise ValueError("Password must be provided with username.")
        return v


class CameraMqttConfig(EdgeBaseModel):
    enabled: bool = Field(
        default=False,
        title="Enable MQTT messaging",
        description="Events and messages are passed to the MQTT broker")
    host: str = Field(
        default="",
        title="MQTT Broker",
        description="The hostname or IP address of the MQTT broker")
    port: int = Field(
        default=1883,
        title="Port",
        description="The port number of the MQTT broker")
    topic_prefix: str = Field(
        default="edge",
        title="Topic Prefix",
        description="The prefix for all MQTT topics")
    client_id: str = Field(
        default="edge-0",
        title="Client ID",
        description="The client ID for the MQTT connection")
    user: str = Field(
        default="",
        title="Username",
        description="The username for the MQTT connection")
    password: str = Field(
        default="",
        title="Password",
        description="The password for the MQTT connection")

    @field_validator("password")
    def user_requires_pass(cls, v, info: ValidationInfo):
        if (v is None) != (info.data["user"] is None):
            raise ValueError("Password must be provided with username.")
        return v


class DatabaseConfig(EdgeBaseModel):
    path: str = Field(
        default="",
        title="Database Path",
        description="The path to the SQLite database file")


class MotionConfig(EdgeBaseModel):
    enabled: bool = Field(
        default=True,
        title="Enable Motion Detection",
        description="Enable or disable motion detection")
    threshold: int = Field(
        default=30,
        title="Threshold",
        ge=1,
        le=255,
        description="The threshold for motion detection")
    lightning_threshold: float = Field(
        default=0.8, title="Lightning detection threshold (0.3-1.0).", ge=0.3, le=1.0
    )
    improve_contrast: bool = Field(
        default=True,
        title="Improve Contrast",
        description="Improve contrast for motion detection")
    contour_area: Optional[int] = Field(default=10, title="Contour Area")
    delta_alpha: float = Field(default=0.2, title="Delta Alpha")
    frame_alpha: float = Field(default=0.01, title="Frame Alpha")
    frame_height: Optional[int] = Field(default=100, title="Frame Height")


class CameraConfig(EdgeBaseModel):
    name: Optional[str] = Field(
        default=None,
        title="Name",
        description="The name of the camera")
    enabled: bool = Field(
        default=True,
        title="Enabled",
        description="Enable or disable the camera")
    best_image_timeout: int = Field(
        default=30,
        title="Best Image Timeout",
        description="The time in seconds to wait for the best image")
    mqtt: CameraMqttConfig = Field(
        default=CameraMqttConfig(),
        title="MQTT Configuration",
        description="The MQTT configuration for the camera")
    motion: Optional[MotionConfig] = Field(
        default_factory=MotionConfig,
        title="Motion Configuration",
        description="The motion detection configuration for the camera")
    source: CameraInput = Field(
        default=None,
        title="Input Configuration",
        description="The input configuration for the camera")
    detect: DetectConfig = Field(
        default_factory=DetectConfig,
        title="Object detection configs"
    )

    @property
    def frame_size(self):
        return self.detect.height * self.detect.width

    @property
    def frame_shape(self) -> Tuple[int, int]:
        return (self.detect.width, self.detect.height)

    @property
    def frame_shape_yuv(self) -> Tuple[int, int]:
        return self.detect.height * 3 // 2, self.detect.width

    @property
    def ffmpeg_cmd(self):
        return self._build_ffmpeg_cmd(self.source)

    def _build_ffmpeg_cmd(self, input: CameraInput) -> List[str]:
        scale_detect_args = parse_preset_hardware_acceleration_scale(
            args=input.ffmpeg.hwaccel_args,
            extra_args=[],
            fps=self.detect.fps,
            width=self.detect.width,
            height=self.detect.height
        )
        output_args = get_ffmpeg_argument_list(
            arg=input.ffmpeg.output_args,
        )
        input_args = get_ffmpeg_argument_list(
            arg=parse_preset_input(args=input.ffmpeg.input_args)
        )
        global_args = get_ffmpeg_argument_list(
            arg=input.ffmpeg.global_args,
        )
        decode_args = get_ffmpeg_argument_list(
            arg=parse_preset_hardware_acceleration_decode(
                args=input.ffmpeg.hwaccel_args,
                extra_args=[],
                fps=self.detect.fps,
                width=self.detect.width,
                height=self.detect.height
            )
        )
        cmd = (
            ["ffmpeg"]
            + global_args
            + decode_args
            + input_args
            + ["-i", input.path]
            + scale_detect_args
            + output_args
            + ["pipe:"]
        )
        return [part for part in cmd if part != ""]


class InputTensorEnum(str, Enum):
    nchw = "nchw"
    nhwc = "nhwc"


class ModelTypeEnum(str, Enum):
    ssd = "ssd"
    yolox = "yolox"
    yolov5 = "yolov5"
    yolov8 = "yolov8"


class PixelFormatEnum(str, Enum):
    rgb = "rgb"
    bgr = "bgr"
    yuv = "yuv"


class ModelConfig(EdgeBaseModel):
    path: Optional[str] = Field(
        default=None,
        title="Path",
        description="The path to the model file")
    width: int = Field(
        default=320,
        title="Width",
        description="The width of the model input")
    height: int = Field(
        default=320,
        title="Height",
        description="The height of the model input")
    labelmap: Dict[int, str] = Field(
        default_factory=dict, title="Labelmap customization."
    )
    input_tensor: InputTensorEnum = Field(
        default=InputTensorEnum.nhwc, title="Model Input Tensor Shape"
    )
    input_pixel_format: PixelFormatEnum = Field(
        default=PixelFormatEnum.rgb, title="Model Input Pixel Color Format"
    )
    model_type: ModelTypeEnum = Field(
        default=ModelTypeEnum.ssd, title="Object Detection Model Type"
    )


class EdgeConfig(EdgeBaseModel):
    mqtt: EventMqttConfig = Field(
        default_factory=EventMqttConfig,
        title="MQTT Configuration",
        description="The MQTT configuration for the edge")
    database: DatabaseConfig = Field(
        default_factory=DatabaseConfig,
        title="Database Configuration",
        description="The database configuration for the edge")
    cameras: Dict[str, CameraConfig] = Field(
        default={},
        title="Cameras",
        description="The cameras connected to the edge")
    model: ModelConfig = Field(
        default_factory=ModelConfig,
        title="Model Configuration",
        description="The model configuration for the edge")

    @classmethod
    def parse_file(cls, config_file: str) -> Self:
        with open(config_file) as f:
            raw: str = f.read()
            if raw is None:
                raise Exception("unable to read configuration file")
        if config_file.endswith(".yaml"):
            config = load(stream=raw, Loader=Loader)
            if config is None:
                raise Exception("unable to read configuration file as YAML")
        elif config_file.endswith(".json"):
            config = json.loads(raw)
            if config is None:
                raise Exception("unable to read configuration file as JSON")
        return cls.model_validate(obj=config)
