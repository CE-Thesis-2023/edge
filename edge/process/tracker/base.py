from abc import ABC, abstractmethod
from typing import Dict, List


class TrackingInfo:
    def __init__(self,
                 motionless_count: int,
                 estimate: any,
                 box: any):
        self.motionless_count = motionless_count
        self.estimate = estimate
        self.box = box
        return


class ObjectTracker(ABC):
    @abstractmethod
    def __init__(self, settings: Dict):
        pass

    @abstractmethod
    def match_and_update(self, frame_time: float, detections: List) -> None:
        pass

    @abstractmethod
    def tracked_objects(self) -> Dict[str, TrackingInfo]:
        pass

    @abstractmethod
    def has_disappeared(self, object_id: str) -> bool:
        pass

    @abstractmethod
    def untracked_objects(self) -> List:
        pass
