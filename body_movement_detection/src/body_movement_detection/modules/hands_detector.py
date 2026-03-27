import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
import time

from body_movement_detection.config import HANDS_MODEL_PATH


class HandsDetector:
    def __init__(self, smoothing=0.7):
        self.latest_result = None

        self.prev_x = None
        self.prev_y = None
        self.smoothing = smoothing

        self.trajectory = []

        base_options = python.BaseOptions(
            model_asset_path=str(HANDS_MODEL_PATH)
        )

        options = vision.HandLandmarkerOptions(
            base_options=base_options,
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_hands=2,
            result_callback=self.process_result
        )

        self.detector = vision.HandLandmarker.create_from_options(options)

    def process_result(self, result, output_image, timestamp_ms):
        self.latest_result = result

    def detect_async(self, frame):
        # OpenCV → BGR, MediaPipe → RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        mp_image = mp.Image(
            image_format=mp.ImageFormat.SRGB,
            data=frame_rgb
        )

        timestamp_ms = int(time.time() * 1000)
        self.detector.detect_async(mp_image, timestamp_ms)

    def draw_landmarks(self, frame):
        if not self.latest_result or not self.latest_result.hand_landmarks:
            return frame

        h, w, _ = frame.shape

        for hand in self.latest_result.hand_landmarks:
            for landmark in hand:
                x = int(landmark.x * w)
                y = int(landmark.y * h)

                cv2.circle(frame, (x, y), 5, (0, 255, 0), -1)

        return frame
    
    def draw_finger_position(self, frame):
        finger_pos = self.get_index_finger_tip(frame)  # update latest position

        if finger_pos:
            x, y = finger_pos
            cv2.circle(frame, (x, y), 12, (0, 0, 255), -1)
            print("Sterowanie:", (x, y))
        return frame
    
    def draw_finger_trajectories(self, frame):
        finger_pos = self.get_index_finger_tip(frame)

        if finger_pos:
            self.trajectory.append(finger_pos)

            # ograniczenie długości trajektorii
            if len(self.trajectory) > 10:
                self.trajectory.pop(0)

            for i in range(1, len(self.trajectory)):
                cv2.line(frame,
                        self.trajectory[i - 1],
                        self.trajectory[i],
                        (0, 0, 255),
                        3)

        return frame

    def get_index_finger_tip(self, frame):
        if not self.latest_result or not self.latest_result.hand_landmarks:
            return None

        h, w, _ = frame.shape
        hand = self.latest_result.hand_landmarks[0]
        landmark = hand[8]

        x = int(landmark.x * w)
        y = int(landmark.y * h)

        # smoothing
        if self.prev_x is None:
            self.prev_x, self.prev_y = x, y

        x = int(self.prev_x * self.smoothing + x * (1 - self.smoothing))
        y = int(self.prev_y * self.smoothing + y * (1 - self.smoothing))

        self.prev_x, self.prev_y = x, y

        return (x, y)
    
    def check_model_exists():
        return HANDS_MODEL_PATH.exists()
