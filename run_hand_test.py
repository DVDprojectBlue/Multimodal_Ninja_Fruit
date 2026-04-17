from src.handControl.config import HANDS_MODEL_PATH
from src.handControl.hands_detector import HandsDetector
import cv2
import urllib.request
from pathlib import Path

def main():

    url = "http://192.168.10.67:8080/video"

    detector = HandsDetector(smoothing=0.3, cam_url=url, debug=True)
    detector.start()

    # czekaj aż wątek się skończy (np. naciśnięcie 'q' w oknie kamery)
    detector._thread.join()

if __name__ == "__main__":
    main()