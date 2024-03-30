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

    def _on_exit(_, __):
        exit_signal.set()
        logger.info("Camera processor exiting")

    signal.signal(signal.SIGINT, _on_exit)
    signal.signal(signal.SIGTERM, _on_exit)

    run_detectors(
        camera_name=name,
        config=config,
        frame_queue=frame_queue,
        current_frame=current_frame,
        stop_event=exit_signal,
        detector=md,
        frame_shape=config.frame_shape_yuv,
        frame_manager=SharedMemoryFrameManager(),
        fps_counter=EventsPerSecond(max_events=1000),
    )

    logger.info("Camera processor exited")


def run_detectors(
    camera_name: str,
    config: CameraConfig,
    frame_queue: mp.Queue,
    stop_event: mp.Event,
    current_frame: mp.Value,
    detector: MotionDetectorAPI,
    frame_shape: Tuple[int, int],
    frame_manager: SharedMemoryFrameManager = SharedMemoryFrameManager(),
    fps_counter: EventsPerSecond = EventsPerSecond(max_events=1000),
):
    logger.info("Motion detection process started")
    fps_counter.start()
    shape = frame_shape
    fc = 0
    while not stop_event.is_set():
        fps = fps_counter.eps()
        logger.info(f"Motion detection process FPS: {fps}")
        logger.info(f"Motion detection process frames: {fc}")
        try:
            frame_time = frame_queue.get(True)
            current_frame.value = frame_time
            k = f"{camera_name}{frame_time}"
            frame = frame_manager.get(name=k, shape=shape)
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
        motion_boxes = detector.detect(frame)
        logger.debug(f"Motion boxes: {motion_boxes}")
        fps_counter.update()
        frame_manager.delete(k)
        fc += 1

    frame_manager.clean()
    logger.debug("Frame manager cleaned")
    logger.debug("Frame queue is empty")
    logger.info("Motion detection process stopped")
