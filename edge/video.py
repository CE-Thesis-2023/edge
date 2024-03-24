import queue
import threading
from typing import Tuple
from edge.motion.api import MotionDetectorAPI
from edge.motion.default import DefaultMotionDetector
import signal
import multiprocessing as mp
from loguru import logger
from edge.config import CameraConfig
from edge.utils.events import EventsPerSecond
from edge.utils.frame import FrameManager, SharedMemoryFrameManager


class CameraDetectorsProcess(threading.Thread):
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


def run_camera_processor(
        name: str,
        config: CameraConfig,
        frame_queue: mp.Queue,
        camera_fps: mp.Value,
        skipped_fps: mp.Value):
    exit_signal = mp.Event()

    def on_exit(_, __):
        exit_signal.set()
        logger.info("Camera processor exiting")

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    frame_manager = SharedMemoryFrameManager()

    motion_proc = CameraDetectorsProcess(
        stop_event=exit_signal,
        detector=DefaultMotionDetector(),
        frame_queue=frame_queue,
        frame_manager=frame_manager,
        frame_shape=config.frame_shape,
        camera_name=name,
    )

    motion_proc.start()
    motion_proc.join()

    logger.info("Camera processor exited")