from enum import Enum


class PixelFormatEnum(str, Enum):
    RGB = "rgb"
    BGR = "bgr"
    YUV = "yuv"


class ModelTypeEnum(str, Enum):
    SSD = "ssd"
    YOLOx = "yolox"
    YOLOv5 = "yolov5"
    YOLOv8 = "yolov8"


class InputTensorEnum(str, Enum):
    NCHW = "nchw"
    NHWC = "nhwc"
