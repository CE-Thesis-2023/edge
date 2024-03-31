from abc import ABC, abstractmethod


class ObjectDetectorAPI(ABC):
    @abstractmethod
    def detect(self, tensor_input):
        pass
