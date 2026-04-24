import pygame
import os

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

ASSETS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
IMAGES_PATH = os.path.join(ASSETS_PATH, "images")
SOUNDS_PATH = os.path.join(ASSETS_PATH, "sounds")
IMAGES_ORANGE_PATH = os.path.join(IMAGES_PATH, "orange")
IMAGES_APPLE_PATH = os.path.join(IMAGES_PATH, "apple")
IMAGES_BANANA_PATH = os.path.join(IMAGES_PATH, "banana")
IMAGES_WATERMELON_PATH = os.path.join(IMAGES_PATH, "watermelon")
IMAGES_BOMB_PATH = os.path.join(IMAGES_PATH, "bomb")
IMAGES_EXPLOSION_PATH = os.path.join(IMAGES_PATH, "explosion")
SOUNDS_EXPLOSION_PATH = os.path.join(SOUNDS_PATH, "explosions")
IMAGES_SWING_PATH = os.path.join(IMAGES_PATH, "swing")
SOUNDS_KATANA_PATH = os.path.join(SOUNDS_PATH, "katana_swings")
IMAGES_BG_PATH = os.path.join(IMAGES_PATH, "backgrounds")
