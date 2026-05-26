from src.handControl.config import HANDS_MODEL_PATH
from src.handControl.hands_detector import HandsDetector
import cv2
import urllib.request
from pathlib import Path
from src.constants import CAM_URL

def main():


    detector = HandsDetector(smoothing=0.3, cam_url=CAM_URL, debug=True)
    detector.start()

    # czekaj aż wątek się skończy (np. naciśnięcie 'q' w oknie kamery)
    detector._thread.join()

if __name__ == "__main__":
    main()