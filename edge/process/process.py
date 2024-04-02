import multiprocessing as mp
import queue
import time
from typing import Dict

import cv2
import numpy as np
import picologging as logging

from edge.helpers.fps import FPS
from edge.helpers.frame import SharedMemoryFrameManager
from edge.process.motion.motion import MotionDetector
from edge.process.tracker.base import ObjectTracker


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
        object_tracker: ObjectTracker = None,
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
    stationary_frame_counter = 0
    stationary_check_interval = detect['stationary']['interval']
    stationary_threshold = detect['stationary']['threshold']

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
            logging.error(
                f"Failed to read frame from SharedMemoryFrameManager: {err}")

        motion_boxes = motion_detector.detect(frame=frame)
        if len(motion_boxes) > 0:
            logging.info(f"Motion detected: {motion_boxes}")

        # if stationary_frame_counter == stationary_check_interval:
        #     stationary_frame_counter = 0
        #     stationary_object_ids = []
        # else:
        #     stationary_frame_counter += 1
        #     stationary_object_ids = []
        #     for object_id, obj in object_tracker.tracked_objects().items():
        #         is_stable = (obj.motionless_count >= stationary_threshold)
        #         has_disappeared = object_tracker.has_disappeared(object_id)
        #         if is_stable and not has_disappeared:
        #             stationary_object_ids.append(object_id)
        #         # TODO: Intersect any of the motion boxes

        # tracked_object_boxes = []
        # for object_id, obj in object_tracker.tracked_objects().items():
        #     if object_id not in stationary_object_ids:
        #         if obj.motionless_count < stationary_threshold:
        #             estimate = obj.estimate
        #             tracked_object_boxes.append(estimate)
        #         else:
        #             box = obj.box
        #             tracked_object_boxes.append(box)

        # object_boxes = tracked_object_boxes + object_tracker.untracked_objects()

        # regions = []
        # # TODO: Get cluster regions

        if event_queue.full():
            logging.warning(f"Event queue is full, dropping frame: {key}")
            manager.delete(name=key)
            continue
        else:
            fps.update()
            event_queue.put(None)
            manager.close(name=key)


def with_settings(name: str, settings: Dict):
    detect = settings['detect']
    logging.debug(f"Processor {name}: {detect}")
