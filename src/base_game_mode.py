import pygame
from src.entities import Spawner


class BaseGameMode:

    @classmethod
    def start(cls, game):
        game._shutdown_mode()
        game._set_windowed()
        game.mode = cls()
        game.menu_notice = ""
        game.state = game.MODE_STATE

    def __init__(self):
        self.fruits = pygame.sprite.Group()
        self.bombs = pygame.sprite.Group()
        self.spawner = Spawner(self.fruits, self.bombs, ["apple", "melon", "lemon"], "bomb")
        self.spawner.set_chances(0.5, 0.2)

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_m:
            return "menu"
        return None

    def update(self):
        self.spawner.update()
        self.fruits.update()
        self.bombs.update()

    def draw(self, screen):
        self.fruits.draw(screen)
        self.bombs.draw(screen)

    def shutdown(self):
        return None
