import picologging as logging
from typing import Tuple, Dict

import cv2
import imutils
import numpy as np
from scipy.ndimage import gaussian_filter


class MotionDetector:
    def __init__(self,
                 name: str,
                 detect: Dict,
                 fps: int,
                 shape: Tuple[int, int],
                 blur_radius=1,
                 interpolation=cv2.INTER_NEAREST):
        self.name = name
        self.settings = detect
        self.fps = fps
        self.shape = shape
        self.blur_radius = blur_radius
        self.interpolation = interpolation
        self.height = shape[0]
        self.width = shape[1]
        self.size = shape[0] * shape[1]
        self.motion_frame_size = (
            self.height,
            self.height * (self.width // self.height)
        )
        self.avg_frame = np.zeros(shape=self.motion_frame_size, dtype=np.float32)
        self.motion_frame_count = 0
        self.calibrating = True
        self.frame_counter = 0
        ######
        self.save_imgs = True
        return

    def detect(self, frame: np.ndarray):
        motion_boxes = []
        gray = frame[0:self.height, 0:self.width]
        resized = cv2.resize(
            gray,
            dsize=self.motion_frame_size,
            interpolation=self.interpolation
        )
        resized = gaussian_filter(
            input=resized,
            sigma=1,
            radius=self.blur_radius
        )
        self.frame_counter += 1
        difference = cv2.absdiff(
            src1=resized,
            src2=cv2.convertScaleAbs(self.avg_frame)
        )
        threshold = cv2.threshold(
            src=difference,
            thresh=50,
            maxval=255,
            type=cv2.THRESH_BINARY
        )
        threshold = threshold[1]
        dilated_threshold = cv2.dilate(
            threshold,
            None,
            iterations=1
        )
        contours = cv2.findContours(
            dilated_threshold,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )
        contours = imutils.grab_contours(contours)
        total_contours_area = 0
        for c in contours:
            area = cv2.contourArea(c)
            total_contours_area += area
            if total_contours_area > 30:
                x, y, w, h = cv2.boundingRect(c)
                motion_boxes.append((x, y, int(x + w), int(y + h)))
        pct_motion = total_contours_area / self.size
        if pct_motion < 0.05 and len(motion_boxes) <= 4:
            self.calibrating = False
        if self.calibrating or pct_motion > 0.60:
            self.calibrating = True

        if self.save_imgs:
            dilated_threshold = cv2.cvtColor(dilated_threshold,
                                             cv2.COLOR_GRAY2BGR)
            for box in motion_boxes:
                cv2.rectangle(
                    dilated_threshold,
                    (box[0], box[1]),
                    (box[2], box[3]),
                    (0, 255, 0),
                    2,
                )
            frames = [
                dilated_threshold,
            ]
            cv2.imwrite(
                f"debug/motions/{self.name}-{self.frame_counter}.jpg",
                (
                    cv2.hconcat(frames)
                    if self.height > self.width else cv2.vconcat(frames)
                ))
            logging.debug(f"Saved motion image: {self.name}-{self.frame_counter}.jpg")

        if len(motion_boxes) > 0:
            self.motion_frame_count += 1
            if self.motion_frame_count > 10:
                self.avg_frame = cv2.accumulateWeighted(
                    src=resized,
                    dst=self.avg_frame,
                    alpha=0.2 if self.calibrating else 0.5
                )
                self.motion_frame_count = 0
            else:
                self.avg_frame = cv2.accumulateWeighted(
                    src=resized,
                    dst=self.avg_frame,
                    alpha=0.2
                )
                self.motion_frame_count = 0
            return motion_boxes
        return []
