import pygame

SCREEN_WIDTH = 1000
SCREEN_HEIGHT = 600
FPS = 60
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
TITLE_COLOR = (200, 50, 40)
INNER_GLOW_COLOR = (255, 140, 100)
OUTER_SHADOW_COLOR = (40, 0, 0)
GRAVITY = 0.3
FRUIT = "Fruit"
BOMB = "Bomb"
HALF = "Half"

CAM_URL = "http://192.168.10.67:8080/video"

import os

ASSETS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
IMAGES_PATH = os.path.join(ASSETS_PATH, "images")
SOUNDS_PATH = os.path.join(ASSETS_PATH, "sounds")
