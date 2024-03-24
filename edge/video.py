from typing import Tuple
from edge.motion.api import MotionDetectorAPI
from edge.motion.default import DefaultMotionDetector, MotionDetectionProcess
import signal
import multiprocessing as mp
from loguru import logger
from edge.config import CameraConfig
from edge.utils.frame import FrameManager, SharedMemoryFrameManager


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

    motion_proc = MotionDetectionProcess(
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
