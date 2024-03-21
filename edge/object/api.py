from abc import ABC, abstractmethod


class ObjectDetectorApi(ABC):
    """
    Standard interface for object detection
    """
    @abstractmethod
    def __init__(self) -> None:
        pass

    @abstractmethod
    def detect(self, tensor_input):
        pass

    @abstractmethod
    def stop(self):
        pass
