import queue
from edge.motion.api import MotionDetectorApi
import multiprocessing as mp
import signal


class DefaultMotionDetector(MotionDetectorApi):
    def __init__(self) -> None:
        pass

    def detect(self, frame):
        print("Motion detected!")
        return False

    def stop(self):
        return


class MotionDetectionProcess():
    def __init__(self,
                 fq: mp.Queue,
                 detector: MotionDetectorApi) -> None:
        self.fq = fq
        self.detector = detector
        self._shutdown = False

    def run(self):
        while not self._shutdown:
            try:
                frame = self.fq.get(timeout=1)
            except queue.Empty:
                continue
            self.detector.detect(frame)

        return

    def stop(self):
        self._shutdown = True


def run_motion_detector(
        detector: MotionDetectionProcess):
    print("Motion detection process started")

    def on_exit(_, __):
        detector.stop()
        print("Motion detector exiting")

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    detector.run()
    print("Motion detection process exited")
