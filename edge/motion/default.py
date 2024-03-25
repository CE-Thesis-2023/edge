import queue
from typing import Tuple
from edge.motion.api import MotionDetectorAPI
import multiprocessing as mp
import signal
from loguru import logger
import threading
from edge.utils.events import EventsPerSecond
from edge.utils.frame import FrameManager
from edge.config import CameraConfig, MotionConfig
import cv2
import numpy as np
from scipy.ndimage import gaussian_filter
import imutils


class DefaultMotionDetector(MotionDetectorAPI):
    def __init__(
            self,
            frame_shape: Tuple[int, int],
            config: MotionConfig,
            fps: int,
            name="default",
            blur_radius=1,
            interpolation=cv2.INTER_NEAREST,
            contrast_frame_history=50) -> None:
        self.name = name
        self.config = config
        self.frame_shape = frame_shape
        self.resize_factor = self.frame_shape[0] / config.frame_height

        logger.debug(f"Frame height: {config.frame_height}")
        logger.debug(f"Frame shape: {frame_shape}")
        logger.debug(f"Resize factor: {self.resize_factor}")
        logger.debug(
            f"Frame width: {config.frame_height * (self.frame_shape[0] // self.frame_shape[1])}")
        # Resized frame size, scaled by the aspect ratio of the original frame
        self.motion_frame_size = (
            config.frame_height,
            config.frame_height * (self.frame_shape[0] // self.frame_shape[1])
        )
        self.avg_frame = np.zeros(self.motion_frame_size, dtype=np.float32)
        self.motion_frame_count = 0
        self.frame_counter = 0
        self.calibrating = True
        self.blur_radius = blur_radius
        self.interpolation = interpolation
        self.contrast_values = np.zeros((contrast_frame_history, 2), np.uint8)
        self.contrast_values[:, 1:2] = 255
        self.contrast_values_index = 0

    def detect(self, frame):
        motion_boxes = []

        if not self.config.enabled:
            return motion_boxes

        gray = frame[0:self.frame_shape[0], 0:self.frame_shape[1]]
        resized_frame = cv2.resize(
            gray,
            dsize=(self.motion_frame_size[1], self.motion_frame_size[0]),
            interpolation=self.interpolation
        )

        resized_frame = gaussian_filter(
            resized_frame, sigma=1, radius=self.blur_radius)

        frame_delta = cv2.absdiff(
            resized_frame, cv2.convertScaleAbs(self.avg_frame))
        threshold = cv2.threshold(
            frame_delta, self.config.threshold, 255, cv2.THRESH_BINARY)[1]
        # dilate the thresholded image to fill in holes, then find contours
        # on thresholded image
        thresh_dilated = cv2.dilate(threshold, None, iterations=1)
        cnts = cv2.findContours(
            thresh_dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cnts = imutils.grab_contours(cnts)
        # loop over the contours
        total_contour_area = 0
        for c in cnts:
            # if the contour is big enough, count it as motion
            contour_area = cv2.contourArea(c)
            total_contour_area += contour_area
            if contour_area > self.config.contour_area:
                x, y, w, h = cv2.boundingRect(c)
                motion_boxes.append(
                    (
                        int(x * self.resize_factor),
                        int(y * self.resize_factor),
                        int((x + w) * self.resize_factor),
                        int((y + h) * self.resize_factor),
                    )
                )

        pct_motion = total_contour_area / (
            self.motion_frame_size[0] * self.motion_frame_size[1]
        )

        # once the motion is less than 5% and the number of contours is < 4, assume its calibrated
        if pct_motion < 0.05 and len(motion_boxes) <= 4:
            self.calibrating = False

        # if calibrating or the motion contours are > 80% of the image area (lightning, ir, ptz) recalibrate
        if self.calibrating or pct_motion > self.config.lightning_threshold:
            self.calibrating = True

        if len(motion_boxes) > 0:
            self.motion_frame_count += 1
            if self.motion_frame_count >= 10:
                # only average in the current frame if the difference persists for a bit
                cv2.accumulateWeighted(
                    resized_frame,
                    self.avg_frame,
                    0.2 if self.calibrating else self.config.frame_alpha,
                )
            else:
                # when no motion, just keep averaging the frames together
                cv2.accumulateWeighted(
                    resized_frame,
                    self.avg_frame,
                    0.2 if self.calibrating else self.config.frame_alpha,
                )
                self.motion_frame_count = 0

            return motion_boxes
        return False

    def stop(self):
        return
