import logging
import os
import queue
from edge.streams.capture import PreRecordedCapturer, run_capturer
from edge.motion.default import DefaultMotionDetector, MotionDetectionProcess, run_motion_detector
import multiprocessing as mp
import signal
import time
import sys
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from edge.utils.configs import ConfigChangeHandler

DEFAULT_CONFIG_FILE = "./config.json"


class EdgeProcessor:
    def __init__(self) -> None:
        return

    def start(self) -> None:
        def on_exit():
            print("Edge processor exiting")
            self.stop()
            sys.exit()

        self.init_observers()
        self.init_signaler(on_exit)

        self.start_observers()
        while not self.is_shutdown():
            self.reload_event.clear()

            self.init_queues()
            self.init_capturers()
            self.init_detectors()

            self.start_capturers()
            self.start_detectors()

            while not self.is_reload():
                time.sleep(2)

            print("Stop and reload")
            self.reload()

        self.stop_observers()
        print("Edge processor exited")

    def init_observers(self) -> None:
        self.reload_event = mp.Event()

        def on_modified(src_path: str):
            print(f"Config file {src_path} has been modified")
            self.reload_event.set()

        handler = ConfigChangeHandler(
            on_modified=on_modified,
        )

        self.observer = Observer()
        self.observer.schedule(
            event_handler=handler,
            path=DEFAULT_CONFIG_FILE)

    def start_observers(self) -> None:
        self.observer.start()

    def init_signaler(self, handler: any) -> None:
        self.shutdown_event = mp.Event()

        def on_shutdown(_, __):
            self.shutdown_event.set()
            handler()

        signal.signal(signal.SIGINT, on_shutdown)
        signal.signal(signal.SIGTERM, on_shutdown)

    def is_reload(self) -> bool:
        return self.reload_event.is_set()

    def is_shutdown(self) -> bool:
        return self.shutdown_event.is_set()

    def stop_observers(self):
        self.reload_event.clear()
        self.observer.stop()
        self.observer.join()

    def init_capturers(self) -> None:
        self.capturer = PreRecordedCapturer(fq=self.fq)

    def init_detectors(self) -> None:
        motion = DefaultMotionDetector()
        self.motion = MotionDetectionProcess(fq=self.fq, detector=motion)

    def start_capturers(self) -> None:
        self.capturer_proc = mp.Process(
            name="edge.Capturer",
            target=run_capturer,
            args=(self.capturer,))
        self.capturer_proc.start()

    def stop_capturers(self) -> None:
        self.capturer_proc.terminate()

    def start_detectors(self) -> None:
        self.motion_proc = mp.Process(
            name="edge.MotionDetector",
            target=run_motion_detector,
            args=(self.motion,))
        self.motion_proc.start()

    def stop_detectors(self) -> None:
        self.motion_proc.terminate()

    def init_queues(self) -> None:
        self.fq = mp.Queue(maxsize=500)

    def reload(self) -> None:
        self.stop_capturers()
        self.stop_detectors()

        self.stop()

    def stop(self) -> None:
        while not self.fq.empty():
            try:
                self.fq.get(timeout=1)
            except queue.Empty as e:
                break

        self.capturer_proc.join()
        self.motion_proc.join()

        self.fq.close()
