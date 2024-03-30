import multiprocessing as mp
import signal
import time

from edge.capture.capture import run_capture


class Application:
    def __init__(self):
        self.stopper = mp.Event()
        self.capturers = []
        self.processors = []
        self.frame_queue = None
        return

    def run(self):
        def stop(_, __):
            self.stopper.set()

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        while not self.stopper.is_set():
            self._run()
            time.sleep(1)

        self._stop()

    def _init(self):
        self.frame_queue = mp.Queue(maxsize=2)

    def _run(self):
        print("Run")

    def _start_capturers(self):
        p = mp.Process(
            target=run_capture,
            args=(self.stopper,
                  self.frame_queue),
        )
        self.capturers.append(p)

    def _start_processors(self):
        p = mp.Process(
            target=run_capture,
            args=(self.stopper,
                  self.frame_queue),
        )
        self.processors.append(p)

    def _stop(self):
        for p in self.capturers:
            p.join()
        for p in self.processors:
            p.join()
        return
