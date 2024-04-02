from asyncio import Event
from multiprocessing.sharedctypes import Synchronized
from typing import Dict, TypedDict
import cv2
import picologging as logging
from edge.helpers.frame import SharedMemoryFrameManager
from norfair.camera_motion import TranslationTransformationGetter, MotionEstimator
from edge.process.tracker.const import AUTOTRACKING_MAX_AREA_RATIO, AUTOTRACKING_MOTION_MIN_DISTANCE, AUTOTRACKING_MOTION_MAX_POINTS, AUTOTRACKING_MAX_MOVE_METRICS, AUTOTRACKING_ZOOM_OUT_HYSTERESIS, AUTOTRACKING_ZOOM_IN_HYSTERESIS, AUTOTRACKING_ZOOM_EDGE_THRESHOLD
from edge.settings import get_frame_size_fps_yuv


class PtzMotionEstimatorMetrics(TypedDict):
    autotracking_enabled: Synchronized
    ptz_tracking_active: Event
    ptz_motor_stopped: Event
    ptz_reset: Event
    ptz_start_time: Synchronized
    ptz_stop_time: Synchronized


class PtzMotionEstimator:
    def __init__(self, name: str, camera_settings: Dict, metrics: dict[str, PtzMotionEstimatorMetrics]):
        self.camera_settings = camera_settings
        self.name = name
        self.manager = SharedMemoryFrameManager()
        self.norfair_motion_estimator = None
        self.metrics = metrics
        self.start_time = metrics["ptz_start_time"]
        self.stop_time = metrics["ptz_stop_time"]
        metrics["ptz_reset"].set()
        self.transformation_type: TranslationTransformationGetter = None
        self.coordinate_transformation = None
        self.frame_shape = get_frame_size_fps_yuv(
            detect=camera_settings['detect']
        )
        logging.debug(f"{name}: PTZ motion estimator initialized")

    def motion_estimator(self, detections, frame_time: float, frame_id: str):
        if self.metrics["ptz_reset"].is_set():
            self.metrics["ptz_reset"].clear()

            logging.debug(
                f"{self.name}: PTZ motion estimator reset - only do translation PT no Z")
            self.transformation_type = TranslationTransformationGetter()
            self.norfair_motion_estimator = MotionEstimator(
                transformations_getter=self.transformation_type,
                min_distance=AUTOTRACKING_MOTION_MIN_DISTANCE,
                max_points=AUTOTRACKING_MOTION_MAX_POINTS,
            )
            self.coordinate_transformation = None
        if ptz_moving_at_frame_time(
                frame_time=frame_time,
                ptz_start_time=self.start_time.value,
                ptz_stop_time=self.stop_time.value):
            logging.debug(
                f"{self.name}: PTZ is moving - frame_time: {frame_time}")
            yuv_frame = self.manager.get(
                name=frame_id,
                # (height, width)
                shape=(self.frame_shape[0], self.frame_shape[1])
            )
            grayed_frame = cv2.cvtColor(yuv_frame, cv2.COLOR_YUV2GRAY_I420)
        return

    def estimate(self, detections, frame_time, camera_id):
        return


def ptz_moving_at_frame_time(frame_time: float, ptz_start_time: float, ptz_stop_time: float):
    # Determine if the PTZ was in motion at the set frame time
    # for non ptz/autotracking cameras, this will always return False
    # ptz_start_time is initialized to 0 on startup and only changes
    # when autotracking movements are made
    return (ptz_start_time != 0.0 and frame_time > ptz_start_time) and (
        ptz_stop_time == 0.0 or (ptz_start_time <= frame_time <= ptz_stop_time)
    )


class PtzAutoTracker:
    def __init__(self):
        return

    def track(self, camera_id: str, obj):
        return
