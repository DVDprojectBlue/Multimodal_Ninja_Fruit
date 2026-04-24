import threading
import urllib.request
import time

import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from .config import HANDS_MODEL_PATH

class HandsDetector:
    MODEL_URL = (
        "https://storage.googleapis.com/mediapipe-models/"
        "hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
    )

    def __init__(self, cam_url=0, smoothing=0.7, debug=False):
        self.cam_url = cam_url
        self.smoothing = smoothing
        self.debug = debug

        self._ensure_model()

        # ── wynik MediaPipe (wątek MP → odczyt w workerze) ──
        self._result_lock = threading.Lock()
        self._latest_result = None

        # ── wygładzona pozycja w 0..1 (wątek MP → odczyt w grze) ──
        self._pos_lock = threading.Lock()
        self._norm_x = None
        self._norm_y = None

        # ── trajektoria do debugowania (tylko w wątku workera) ──
        self._trajectory = []   # lista (x_norm, y_norm)

        self._running = False
        self._thread = None

        self._detector = self._build_detector()

    def _ensure_model(self):
        if not HANDS_MODEL_PATH.exists():
            print(f"[HandsDetector] Pobieranie modelu...")
            HANDS_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(self.MODEL_URL, HANDS_MODEL_PATH)
            print("[HandsDetector] Model pobrany.")

    def _build_detector(self):
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(
                model_asset_path=str(HANDS_MODEL_PATH)
            ),
            running_mode=vision.RunningMode.LIVE_STREAM,
            num_hands=1,
            result_callback=self._on_result,
        )
        return vision.HandLandmarker.create_from_options(options)

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._worker, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)

        # reset stanu
        self._thread = None
        with self._pos_lock:
            self._norm_x = None
            self._norm_y = None
        with self._result_lock:
            self._latest_result = None
        self._trajectory.clear()

    def _worker(self):
        cap = cv2.VideoCapture(self.cam_url)
        if not cap.isOpened():
            print(f"[HandsDetector] Nie można otworzyć: {self.cam_url}")
            return

        while self._running and cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame = cv2.flip(frame, 1)
            self._send_to_mediapipe(frame)

            if self.debug:
                debug = self._draw_debug(frame)
                cv2.imshow("HandsDetector", debug)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                self._running = False
                break

        cap.release()
        cv2.destroyAllWindows()

    def _send_to_mediapipe(self, frame):
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame_rgb)
        timestamp_ms = int(time.time() * 1000)
        self._detector.detect_async(mp_image, timestamp_ms)

    def _on_result(self, result, output_image, timestamp_ms):
        with self._result_lock:
            self._latest_result = result

        self._update_position(result)

    def _update_position(self, result):
        if not result or not result.hand_landmarks:
            with self._pos_lock:
                self._norm_x = None
                self._norm_y = None
            return

        lm = result.hand_landmarks[0][8]  # index finger tip
        x = max(0.0, min(1.0, lm.x))
        y = max(0.0, min(1.0, lm.y))

        with self._pos_lock:
            if self._norm_x is None:
                self._norm_x, self._norm_y = x, y
            else:
                s = self.smoothing
                self._norm_x = self._norm_x * s + x * (1 - s)
                self._norm_y = self._norm_y * s + y * (1 - s)

    def get_normalized_position(self):

        # (x, y) od 0 do 1

        with self._pos_lock:
            if self._norm_x is None:
                return None
            return (self._norm_x, self._norm_y)

    def get_screen_position(self, screen_width, screen_height):
        # (x,y) w pikselach ekranu, lub None jeśli brak detekcji
        pos = self.get_normalized_position()
        if pos is None:
            return None
        x, y = pos
        return (int(x * screen_width), int(y * screen_height))

    def _draw_debug(self, frame):
        h, w, _ = frame.shape
        pos = self.get_normalized_position()

        if pos:
            px, py = int(pos[0] * w), int(pos[1] * h)

            self._trajectory.append(pos)
            if len(self._trajectory) > 20:
                self._trajectory.pop(0)

            for i in range(1, len(self._trajectory)):
                p1 = (int(self._trajectory[i-1][0] * w),
                      int(self._trajectory[i-1][1] * h))
                p2 = (int(self._trajectory[i][0] * w),
                      int(self._trajectory[i][1] * h))
                cv2.line(frame, p1, p2, (0, 0, 255), 2)

            cv2.circle(frame, (px, py), 10, (0, 0, 255), -1)
            cv2.putText(frame, f"({pos[0]:.2f}, {pos[1]:.2f})",
                       (px + 12, py - 8),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
        else:
            self._trajectory.clear()
            cv2.putText(frame, "No hand", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 200), 2)

        # landmarki
        with self._result_lock:
            result = self._latest_result
        if result and result.hand_landmarks:
            for hand in result.hand_landmarks:
                for lm in hand:
                    cv2.circle(frame,
                               (int(lm.x * w), int(lm.y * h)),
                               4, (0, 255, 0), -1)
        return frame

    @staticmethod
    def check_model_exists():
        return HANDS_MODEL_PATH.exists()