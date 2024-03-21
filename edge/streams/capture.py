import signal
from edge.utils.events import EventsPerSecond
from edge.streams.api import StreamCollectorApi
import time
import multiprocessing as mp


class CameraWatchdog():
    def __init__(self) -> None:
        pass

    def run(self) -> None:
        return

    def stop(self) -> None:
        return


class CameraCapturer(StreamCollectorApi):
    def __init__(self) -> None:
        pass

    def run(self) -> None:
        fr = EventsPerSecond()
        fr.start()
        starttime = time.monotonic()
        while True:
            print(fr.eps())
            time.sleep(2.0 - ((time.monotonic() - starttime) % 2.0))
            fr.update()

    def stop(self) -> None:
        return

    def restart_ffmpeg(self) -> None:
        return


class PreRecordedCapturer(StreamCollectorApi):
    def __init__(self, fq: mp.Queue) -> None:
        self.fq = fq
        self._stopped = False

    def run(self) -> None:
        start_time = time.monotonic()

        while not self._stopped:
            self.fq.put(f"Frame at {time.monotonic()}")
            time.sleep(2.0 - ((time.monotonic() - start_time) % 2.0))

        return

    def stop(self) -> None:
        self._stopped = True


def run_capturer(capturer: StreamCollectorApi):
    print("Capturer process started")

    def on_exit(_, __):
        capturer.stop()
        print("Capturer process exiting")

    signal.signal(signal.SIGINT, on_exit)
    signal.signal(signal.SIGTERM, on_exit)

    capturer.run()
    print("Capturer process exited")
