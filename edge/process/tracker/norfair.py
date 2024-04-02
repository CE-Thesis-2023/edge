from typing import Dict, List

import numpy as np
from norfair import (
    Detection, Tracker, OptimizedKalmanFilterFactory,
)
from norfair.tracker import TrackedObject

from edge.process.tracker.base import ObjectTracker, TrackingInfo
from edge.process.tracker.ptz import PtzMotionEstimator

THRESHOLD_STATIONARY_IOU_AVERAGE = 0.6
MAX_STATIONARY_HISTORY = 10


# From Frigate
# Normalizes distance from estimate relative to object size
# Other ideas:
# - if estimates are inaccurate for first N detections, compare with last_detection (may be fine)
# - could be variable based on time since last_detection
# - include estimated velocity in the distance (car driving by of a parked car)
# - include some visual similarity factor in the distance for occlusions
def distance(detection: np.array, estimate: np.array) -> float:
    # ultimately, this should try and estimate distance in 3-dimensional space
    # consider change in location, width, and height

    estimate_dim = np.diff(estimate, axis=0).flatten()
    detection_dim = np.diff(detection, axis=0).flatten()

    # get bottom center positions
    detection_position = np.array(
        [np.average(detection[:, 0]), np.max(detection[:, 1])]
    )
    estimate_position = np.array([np.average(estimate[:, 0]), np.max(estimate[:, 1])])

    distance = (detection_position - estimate_position).astype(float)
    # change in x relative to w
    distance[0] /= estimate_dim[0]
    # change in y relative to h
    distance[1] /= estimate_dim[1]

    # get ratio of widths and heights
    # normalize to 1
    widths = np.sort([estimate_dim[0], detection_dim[0]])
    heights = np.sort([estimate_dim[1], detection_dim[1]])
    width_ratio = widths[1] / widths[0] - 1.0
    height_ratio = heights[1] / heights[0] - 1.0

    # change vector is relative x,y change and w,h ratio
    change = np.append(distance, np.array([width_ratio, height_ratio]))

    # calculate Euclidean distance of the change vector
    return np.linalg.norm(change)


def frigate_distance(detection: Detection, tracked_object: TrackedObject) -> float:
    return distance(detection.points,
                    tracked_object.estimate)


class NorfairTracker(ObjectTracker):
    def __init__(self,
                 name: str,
                 camera_settings: Dict):
        self.tracked = {}
        self.untracked_boxes: List[List[int]] = []
        self.disappeared = {}
        self.positions = {}
        self.name = name
        self.camera = camera_settings
        self.detect = camera_settings['detect']
        self.tracked_id_map = {}
        self.stationary_box_history: Dict[str, List[List[int]]] = {}
        self.tracker = Tracker(
            distance_function=frigate_distance,
            distance_threshold=2.5,
            initialization_delay=self.detect['min_initialized'],
            hit_counter_max=self.detect['max_disappear'],
            filter_factory=OptimizedKalmanFilterFactory(R=3.4)
        )
        # TODO: PtzMotionEstimator
        self.ptz_motion_estimator = PtzMotionEstimator()
        return

    def register(self):
        return

    def deregister(self):
        return

    def update_position(self, object_id: str, box: np.array):
        return

    def match_and_update(self, frame_time: float, detections: List) -> None:
        return

    def tracked_objects(self) -> Dict[str, TrackingInfo]:
        return

    def has_disappeared(self, object_id: str) -> bool:
        return

    def untracked_objects(self) -> List:
        return
