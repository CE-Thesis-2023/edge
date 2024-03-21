from abc import ABC, abstractmethod


class StreamCollectorApi(ABC):
    """
    Standard interface for 
    any video source collector that transforms a real-time video stream 
    into a sequence of frames
    """
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def run(self):
        pass

    @abstractmethod
    def stop(self):
        pass
