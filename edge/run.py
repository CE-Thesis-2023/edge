import multiprocessing as mp
import signal
import sys
import time
from multiprocessing import shared_memory
from typing import List

import picologging as logging

from edge.capture.capture import run_capture
from edge.event.event import run_event_capture
from edge.process.object.detector import ObjectDetectionProcess
from edge.process.process import run_process
from edge.settings import load, validate, with_defaults


class Application:
    def __init__(self):
        self.stopper = mp.Event()
        self.capturers = []
        self.processors = []
        self.events_capturers = []
        self.frame_queue = None
        self.event_queue = None
        self.detected_frames_queue = None
        self.detectors: List[ObjectDetectionProcess] = []
        self.detection_out_events = {}
        self.detection_shms = []
        self.settings = None
        return

    def run(self):
        def stop(_, __):
            self.stopper.set()
            logging.info("Stopping...")

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        self._init()
        self._run()
        self._stop()

    def _init(self):
        logging.basicConfig(level=logging.DEBUG,
                            format="%(asctime)s [%(filename)s:%(lineno)d]\t %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S",
                            stream=sys.stdout)
        self._init_queues()
        self._init_object_detectors()
        self._load_settings()
        self._init_capturers()
        self._init_processors()
        self._init_event_capturers()

    def _load_settings(self):
        self.settings = load("./configs.yaml")
        errs = validate(self.settings)
        if errs:
            for key, value in errs.items():
                logging.error(f"Configuration error: {key}: {value}")
            sys.exit(1)
        else:
            logging.info("Configuration is valid")
        self.settings = with_defaults(self.settings)
        logging.debug(f"Configurations: {self.settings}")

    def _run(self):
        self._start_object_detectors()
        self._start_capturers()
        self._start_processors()
        self._start_event_capturers()

        while not self.stopper.is_set():
            time.sleep(5)

    def _init_capturers(self):
        cameras = self.settings['cameras']
        for name, configs in cameras.items():
            p = mp.Process(
                target=run_capture,
                args=(name,
                      configs,
                      self.stopper,
                      self.frame_queue),
            )
            self.capturers.append(p)

    def _init_processors(self):
        cameras = self.settings['cameras']
        for name, configs in cameras.items():
            p = mp.Process(
                target=run_process,
                args=(
                    name,
                    configs,
                    self.stopper,
                    self.frame_queue,
                    self.event_queue),
            )
            self.processors.append(p)

    def _init_event_capturers(self):
        cameras = self.settings['cameras']
        for name, configs in cameras.items():
            p = mp.Process(
                target=run_event_capture,
                args=(
                    name,
                    configs,
                    self.stopper,
                    self.event_queue),
            )
            self.events_capturers.append(p)

    def _init_object_detectors(self):
        cameras = self.settings['cameras']
        for c in cameras.keys():
            detect = cameras['detect']
            self.detection_out_events[c] = mp.Event()
            try:
                frame_size = detect['width'] * detect['height'] * 3
                shm_in = shared_memory.SharedMemory(
                    name=c,
                    create=True,
                    size=frame_size)
            except FileExistsError:
                shm_in = shared_memory.SharedMemory(
                    name=c)
            try:
                shm_out = shared_memory.SharedMemory(
                    name=f"detection-result_{c}",
                    create=True,
                    size=20 * 6 * 4)
            except FileExistsError:
                shm_out = shared_memory.SharedMemory(
                    name=f"detection-result_{c}")
            self.detection_shms.append(shm_out)
            self.detection_shms.append(shm_in)
        process = ObjectDetectionProcess(
            name="object-detection",
            detection_queue=self.frame_queue,
            out_events=self.detection_out_events,
            stopper=self.stopper,
            model_settings=self.settings['model'],
        )
        self.detectors.append(process)

    def _start_object_detectors(self):
        for p in self.detectors:
            p.start_or_restart()

    def _init_queues(self):
        self.frame_queue = mp.Queue(maxsize=2)
        self.event_queue = mp.Queue(maxsize=2)
        self.detected_frames_queue = mp.Queue(
            maxsize=len(self.settings['cameras'] or 2)
        )

    def _start_capturers(self):
        for p in self.capturers:
            p.start()

    def _start_processors(self):
        for p in self.processors:
            p.start()

    def _start_event_capturers(self):
        for p in self.events_capturers:
            p.start()

    def _stop(self):
        for p in self.capturers:
            if p.is_alive():
                p.join()
        for p in self.processors:
            if p.is_alive():
                p.join()
        for p in self.events_capturers:
            if p.is_alive():
                p.join()
        return
