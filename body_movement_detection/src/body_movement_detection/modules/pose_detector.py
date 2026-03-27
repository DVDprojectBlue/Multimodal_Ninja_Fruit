import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from body_movement_detection.config import POSE_MODEL_PATH


class PoseDetector:
    def __init__(self):
        base_options = python.BaseOptions(model_asset_path=str(POSE_MODEL_PATH))
        options = vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.IMAGE,
        )

        self.detector = vision.PoseLandmarker.create_from_options(options)

    def detect(self, image):
        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=image
        )

        result = self.detector.detect(mp_image)
        return result