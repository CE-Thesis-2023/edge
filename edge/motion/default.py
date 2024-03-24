import queue
from typing import Tuple
from edge.motion.api import MotionDetectorAPI
import multiprocessing as mp
import signal
from loguru import logger
import threading
from edge.utils.events import EventsPerSecond
from edge.utils.frame import FrameManager


class DefaultMotionDetector(MotionDetectorAPI):
    def __init__(self) -> None:
        pass

    def detect(self, frame):
        print("Motion detected!")
        return False

    def stop(self):
        return