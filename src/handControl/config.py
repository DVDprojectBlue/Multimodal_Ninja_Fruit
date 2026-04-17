from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
POSE_MODEL_PATH = BASE_DIR / "models" / "pose_landmarker.task"
HANDS_MODEL_PATH = BASE_DIR / "models" / "hand_landmarker.task"