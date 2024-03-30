import multiprocessing as mp
import signal
import time

from edge.capture.capture import run_capture
from edge.event.event import run_event_capture
from edge.process.process import run_process


class Application:
    def __init__(self):
        self.stopper = mp.Event()
        self.capturers = []
        self.processors = []
        self.events_capturers = []
        self.frame_queue = None
        return

    def run(self):
        def stop(_, __):
            self.stopper.set()
            print("Stopping...")

        signal.signal(signal.SIGINT, stop)
        signal.signal(signal.SIGTERM, stop)

        self._run()
        self._stop()

    def _init(self):
        self.frame_queue = mp.Queue(maxsize=2)

        self._init_capturers()
        self._init_processors()
        self._init_event_capturer()

    def _run(self):
        self._start_capturers()
        self._start_processors()
        # self._start_event_capturer()

        while not self.stopper.is_set():
            time.sleep(1)

    def _init_capturers(self):
        p = mp.Process(
            target=run_capture,
            args=(self.stopper,
                  self.frame_queue),
        )
        self.capturers.append(p)

    def _init_processors(self):
        p = mp.Process(
            target=run_process,
            args=(self.stopper,
                  self.frame_queue),
        )
        self.processors.append(p)

    def _init_event_capturer(self):
        p = mp.Process(
            target=run_event_capture,
            args=(self.stopper,
                  self.frame_queue),
        )
        self.events_capturers.append(p)

    def _start_capturers(self):
        for p in self.capturers:
            p.start()

    def _start_processors(self):
        for p in self.processors:
            p.start()

    def _start_event_capturer(self):
        for p in self.events_capturers:
            p.start()

    def _stop(self):
        for p in self.capturers:
            p.join()
        for p in self.processors:
            p.join()
        # for p in self.events_capturer:
        #     p.join()
        return
