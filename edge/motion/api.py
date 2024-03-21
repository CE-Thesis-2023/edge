from abc import ABC, abstractmethod


class MotionDetectorApi(ABC):
    """
    Standard interface for motion detection
    """
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def detect(self, frame):
        pass

    @abstractmethod
    def stop(self):
        pass
