import multiprocessing as mp
import queue
import time
from typing import Dict

import numpy as np
import picologging as logging

from edge.helpers.fps import FPS
from edge.helpers.frame import SharedMemoryFrameManager
from edge.process.motion.motion import MotionDetector


def run_process(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
        event_queue: mp.Queue,
):
    with_settings(
        name=name,
        settings=settings,
    )

    time.sleep(3)  # delay for the capturer to start
    run_detectors(
        name=name,
        settings=settings,
        stopper=stopper,
        frame_queue=frame_queue,
        event_queue=event_queue,
    )


def run_detectors(
        name: str,
        settings: Dict,
        stopper: mp.Event,
        frame_queue: mp.Queue,
        event_queue: mp.Queue,
):
    manager = SharedMemoryFrameManager()
    fps = FPS(max_events=200)

    detect = settings['detect']
    frame_shape = (detect['width'], detect['height'])

    motion_detector = MotionDetector(
        name=name,
        detect=detect,
        fps=detect['fps'],
        shape=frame_shape,
    )

    while not stopper.is_set():
        key = ""
        try:
            key = frame_queue.get(timeout=1, block=True)
            if key is None:
                continue
            curr_fps = fps.fps()
            logging.info(f"Processor {name}: {curr_fps} fps")
        except queue.Empty:
            continue
        except Exception as err:
            logging.exception(err)
            logging.error(f"Failed to read key and frame from Capturer: {err}")

        frame: np.ndarray = None
        try:
            frame = manager.get(name=key, shape=frame_shape)
            logging.info(f"Processor received frame: {frame.shape}")
            if frame is None:
                continue
        except Exception as err:
            logging.exception(err)
            logging.error(f"Failed to read frame from SharedMemoryFrameManager: {err}")

        motion_boxes = motion_detector.detect(frame=frame)
        if len(motion_boxes) > 0:
            logging.info(f"Motion detected: {motion_boxes}")

        fps.update()
        manager.delete(name=key)


def with_settings(name: str, settings: Dict):
    detect = settings['detect']
    logging.debug(f"Processor {name}: {detect}")
