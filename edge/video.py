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
                 config: CameraConfig,
                 frame_queue: mp.Queue,
                 stop_event: mp.Event,
                 current_frame: mp.Value,
                 detector: MotionDetectorAPI) -> None:
        threading.Thread.__init__(self)
        self.camera_name = camera_name
        self.frame_queue = frame_queue
        self.detector = detector
        self.config = config
        self.stop_event = stop_event
        self.frame_manager = SharedMemoryFrameManager()
        #######################################
        self.frame_shape = config.frame_shape_yuv
        #######################################
        self.current_frame = current_frame
        self.fps_counter = EventsPerSecond(max_events=1000)
        self.fc = 0

    def run(self):
        logger.info("Motion detection process started")
        self.fps_counter.start()
        shape = self.frame_shape

        while not self.stop_event.is_set():
            fps = self.fps_counter.eps()

            logger.info(f"Motion detection process FPS: {fps}")
            logger.info(f"Motion detection process frames: {self.fc}")
            try:
                frame_time = self.frame_queue.get(True)
                self.current_frame.value = frame_time
                k = f"{self.camera_name}{frame_time}"
                frame = self.frame_manager.get(name=k, shape=shape)
            except queue.Empty:
                logger.error("Frame queue is empty")
                continue
            except Exception as e:
                logger.error(
                    f"Error getting frame from the frame manager: {e}")
                continue
            if frame is None:
                logger.error("Frame is not found in the frame manager")
                continue
            motion_boxes = self.detector.detect(frame)
            logger.debug(f"Motion boxes: {motion_boxes}")

            self.fps_counter.update()
            self.frame_manager.delete(k)
            self.fc += 1

        self.clean()
        logger.info("Motion detection process stopped")
        return

    def clean(self):
        self.frame_manager.clean()
        logger.debug("Frame manager cleaned")
        while not self.frame_queue.empty():
            self.frame_queue.get()
        logger.debug("Frame queue is empty")
        return


def run_camera_processor(
        name: str,
        config: CameraConfig,
        frame_queue: mp.Queue,
        current_frame: mp.Value,
        camera_fps: mp.Value,
        skipped_fps: mp.Value):
    exit_signal = mp.Event()

    md = DefaultMotionDetector(
        frame_shape=config.frame_shape_yuv,
        config=config.motion,
        fps=config.detect.fps,
    )

    motion_proc = CameraDetectorsProcess(
        stop_event=exit_signal,
        config=config,
        detector=md,
        frame_queue=frame_queue,
        camera_name=name,
        current_frame=current_frame
    )

    def on_exit(_, __):
        exit_signal.set()
        logger.info("Camera processor exiting")

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    motion_proc.start()
    motion_proc.join()

    logger.info("Camera processor exited")
