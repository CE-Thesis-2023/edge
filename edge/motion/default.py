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


class MotionDetectionProcess(threading.Thread):
    def __init__(self,
                 camera_name: str,
                 frame_queue: mp.Queue,
                 stop_event: mp.Event,
                 frame_manager: FrameManager,
                 frame_shape: Tuple[int, int],
                 detector: MotionDetectorAPI) -> None:
        self.camera_name = camera_name
        self.frame_queue = frame_queue
        self.detector = detector
        self.stop_event = stop_event
        self.frame_manager = frame_manager
        self.frame_shape = frame_shape
        self.fps_counter = EventsPerSecond(max_events=1000)

    def run(self):
        logger.info("Motion detection process started")
        self.fps_counter.start()
        shape = (self.frame_shape[0] * 3 // 2, self.frame_shape[1])

        while not self.stop_event.is_set():
            fps = self.fps_counter.eps()

            logger.info(f"Motion detection process FPS: {fps}")
            try:
                frame_time = self.frame_queue.get(timeout=1)
                k = f"{self.camera_name}@{frame_time}"
                frame = self.frame_manager.get(name=k, shape=shape)
                self.fps_counter.update()
            except queue.Empty:
                logger.error("Frame queue is empty")
                continue
            if frame is None:
                logger.error("Frame is not found in the frame manager")
                continue
            self.detector.detect(frame)

        logger.info("Motion detection process stopped")
        return

    def stop(self):
        return
