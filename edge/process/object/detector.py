import datetime
import multiprocessing as mp
import queue
from multiprocessing import shared_memory
from typing import List, Dict

import numpy as np
import picologging as logging
import cv2

from edge.helpers.fps import FPS
from edge.helpers.frame import SharedMemoryFrameManager
from edge.process.object.base import ObjectDetectorAPI
from edge.settings import PixelFormatEnum


class LocalObjectDetector:
    def __init__(self,
                 model_settings: Dict,
                 name: str):
        self.fps = FPS()
        self.model_settings = model_settings
        self.name = name
        self.detect_api: ObjectDetectorAPI = None
        return

    def detect(self, tensor_input, threshold=0.4):
        detections = []
        raw_detections: List = self.detect_api.detect(
            tensor_input=tensor_input)
        for d in raw_detections:
            detections.append(d)
        self.fps.update()
        return detections


def run_object_detector(
        name: str,
        detection_input: mp.Queue,
        out_events: dict[str, mp.Event],
        model_settings: Dict,
        stopper: mp.Event,
):
    with_settings(
        name=name,
        model_settings=model_settings,
    )
    start_detector(
        name=name,
        model_settings=model_settings,
        detection_input=detection_input,
        out_events=out_events,
        stopper=stopper,
    )


def with_settings(name: str, model_settings: Dict):
    logging.debug(f"{name}: Configurations: {model_settings}")


def start_detector(
        name: str,
        model_settings: Dict,
        detection_input: mp.Queue,
        out_events: dict[str, mp.Event],
        stopper: mp.Event,
):
    manager = SharedMemoryFrameManager()
    detector = LocalObjectDetector(
        model_settings=model_settings,
        name=name,
    )

    height = model_settings['height']
    width = model_settings['width']

    outputs = {}
    for key in out_events.keys():
        out_shm = shared_memory.SharedMemory(
            name=f"detection-result_{key}",
            create=False)
        # magic number here, copied from Frigate
        out_nparr = np.ndarray((20, 6),
                               dtype=np.float32,
                               buffer=out_shm.buf)
        outputs[key] = {
            "shm": out_shm,
            "nparr": out_nparr,
        }

    average_fps = FPS()
    average_fps.start()

    while not stopper.is_set():
        try:
            key = detection_input.get(timeout=1, block=True)
        except queue.Empty:
            continue
        logging.debug(f"{name}: ObjectDetection FPS: {average_fps.fps()}")
        input_frame = manager.get(
            key,
            shape=(1, height, width)
        )
        if input_frame is None:
            logging.debug(f"{name}: No frame received")
            continue
        detections = detector.detect(tensor_input=input_frame)
        outputs[key]['nparr'][:] = detections[:]
        out_events[key].set()
        average_fps.update()

    logging.debug(f"{name}: Stopped detector")


def now():
    return datetime. \
        datetime.now(). \
        timestamp()


class ObjectDetectionProcess:
    def __init__(self,
                 name: str,
                 detection_queue: mp.Queue,
                 out_events: dict[str, mp.Event],
                 stopper: mp.Event,
                 model_settings: Dict):
        self.name = name
        self.detection_queue = detection_queue
        self.out_events = out_events
        self.model_settings = model_settings
        self.stopper = stopper
        self.detector_process: mp.Process = None

    def start_or_restart(self):
        if self.detector_process and self.detector_process.is_alive():
            logging.debug("Detector process is already running")
            return
        self.detector_process = mp.Process(
            target=run_object_detector,
            args=(
                self.name,
                self.detection_queue,
                self.out_events,
                self.model_settings,
                self.stopper,
            )
        )
        self.detector_process.daemon = True
        self.detector_process.start()

    def stop(self):
        if self.detector_process and self.detector_process.exitcode:
            logging.debug("Detector process is already stopped")
        self.detector_process.terminate()
        logging.debug("Waiting for Detector to shutdown")
        if self.detector_process.is_alive():
            self.detector_process.join(timeout=30)
        if self.detector_process.exitcode is None:
            logging.error("Detector process did not shutdown properly")
            self.detector_process.kill()
            self.detector_process.join()
        logging.debug("Detector process is stopped")


def detect_with_detector(
        detect_settings: Dict,
        model_settings: Dict,
        detector: LocalObjectDetector,
        frame: np.ndarray,
):
    tensor_input = create_tensor_input(
        frame=frame,
        model_settings=model_settings,
    )
    detections = []
    regions = detector.detect(
        tensor_input=tensor_input)
    for r in regions:
        detections.append(r)
    return detections


def create_tensor_input(
        frame: np.ndarray,
        model_settings: Dict,):
    format = model_settings['input_pixel_format']
    height = model_settings['height']
    width = model_settings['width']
    if format == PixelFormatEnum.RGB:
        converted = cv2.cvtColor(frame, cv2.COLOR_YUV2RGB_I420)
    elif format == PixelFormatEnum.BGR:
        converted = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_I420)
    if converted.shape != (height, width, 3):
        converted = cv2.resize(
            converted,
            (width, height),
            interpolation=cv2.INTER_LINEAR)
    return np.expand_dims(converted, axis=0)
