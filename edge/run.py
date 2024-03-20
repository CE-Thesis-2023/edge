from edge.streams.capture import CameraCapturer


class EdgeProcessor:
    def __init__(self) -> None:
        return

    def start(self) -> None:
        capturer = CameraCapturer()
        capturer.start()
