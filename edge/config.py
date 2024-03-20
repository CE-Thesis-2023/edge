from typing import List, Dict, Union, Optional, Enum
from pydantic import BaseModel, Field, ValidationInfo,  field_validator, ConfigDict

FFMPEG_DEFAULT_GLOBAL_ARGS = ["-hide_banner",
                              "-loglevel", "warning", "-threads", "2"]


class EdgeBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces={})


class FfmpegConfig():
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
        default="",
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
        default=FfmpegConfig(),
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
        default=None,
        title="Motion Configuration",
        description="The motion detection configuration for the camera")
    source: CameraInput = Field(
        default=None,
        title="Input Configuration",
        description="The input configuration for the camera")


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
