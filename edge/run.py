from edge.streams.capture import PreRecordedCapturer, run_capturer
from edge.motion.default import DefaultMotionDetector, MotionDetectionProcess, run_motion_detector
import multiprocessing as mp
import signal
import time
import sys


class EdgeProcessor:
    def __init__(self) -> None:
        return

    def start(self) -> None:
        self.init_queues()
        self.init_capturers()
        self.init_detectors()

        self.start_capturers()
        self.start_detectors()

        event = mp.Event()

        def on_exit(_, __):
            print("Edge processor exiting")
            event.set()

        signal.signal(signal.SIGINT, on_exit)
        signal.signal(signal.SIGTERM, on_exit)

        while not event.is_set():
            time.sleep(5)
            continue

        print("Edge processor exited")
        self.stop()

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

    def start_detectors(self) -> None:
        self.motion_proc = mp.Process(
            name="edge.MotionDetector",
            target=run_motion_detector,
            args=(self.motion,))
        self.motion_proc.start()

    def init_queues(self) -> None:
        self.fq = mp.Queue(maxsize=500)

    def stop(self) -> None:
        while not self.fq.empty():
            self.fq.get(timeout=1)

        self.capturer_proc.join()
        self.motion_proc.join()

        self.fq.close()
        sys.exit()
