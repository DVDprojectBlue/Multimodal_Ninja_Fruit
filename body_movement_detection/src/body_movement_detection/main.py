from body_movement_detection.config import HANDS_MODEL_PATH
import cv2
from body_movement_detection import PoseDetector, HandsDetector
import urllib.request
from pathlib import Path

def main():

    url = "http://192.168.10.18:8080/video"
    cap = cv2.VideoCapture(url)

    if not HandsDetector.check_model_exists():
        url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task"
        urllib.request.urlretrieve(url, HANDS_MODEL_PATH)    

    detector = HandsDetector(smoothing=0.3)

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        frame = cv2.flip(frame, 1)

        detector.detect_async(frame)

        # frame = detector.draw_landmarks(frame)

        # frame = detector.draw_finger_position(frame)

        frame = detector.draw_finger_trajectories(frame)

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()