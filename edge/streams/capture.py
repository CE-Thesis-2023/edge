from edge.utils.events import EventsPerSecond
import time


class CameraWatchdog():
    def __init__(self) -> None:
        pass

    def start(self) -> None:
        return

    def stop(self) -> None:
        return


class CameraCapturer():
    def __init__(self) -> None:
        pass

    def start(self) -> None:
        self.capture()

    def capture(self) -> None:
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
