import pygame
import random
import src.constants as constants


class Entity(pygame.sprite.Sprite):
    def __init__(self, image, entity_type, x, vx, vy, y=constants.SCREEN_HEIGHT, half='left'):
        super().__init__()
        self.entity_type = entity_type
        if isinstance(image, list):
            self.frames = [pygame.transform.scale(pygame.image.load(f).convert_alpha(), (64, 64)) for f in image]
            self.fruit_image_key = image[0]
            if vx > 0:
                self.animation_speed = 0.2
            else:
                self.animation_speed = -0.2
                self.frame_index = len(self.frames) - 1
            self.frame_index = 0 if vx > 0 else len(self.frames) - 1
            self.image = self.frames[int(self.frame_index)]
        else:
            raw = pygame.image.load(image).convert_alpha()
            self.image = pygame.transform.scale(raw, (64, 64))
            self.frames = None

        self.rect = self.image.get_rect(midbottom=(x, y))

        self.vx = vx
        self.vy = vy
        self.gravity = constants.GRAVITY

    def move(self):
        self.rect.x += self.vx
        self.rect.y += self.vy
        self.vy += self.gravity

        if self.vy > 15:
            self.vy = 15

    def update(self):
        self.move()

        if self.frames:
            self.frame_index += self.animation_speed
            if self.frame_index >= len(self.frames):
                self.frame_index = 0
            elif self.frame_index < 0:
                self.frame_index = len(self.frames) - 1
            self.image = self.frames[int(self.frame_index)]

        if self.rect.top > 700:
            self.kill()

    def get_state(self):
        return (self.rect.x, self.rect.y, self.vx, self.vy)

    def check_slice(self, p1, p2):
        return p1 and p2 and self.rect.clipline(p1, p2)


class Spawner:
    def __init__(self, entity_group, fruits_images, bomb_image):
        self.entity_group = entity_group

        self.bomb_image = bomb_image
        self.fruits_images = fruits_images

        self.timer_fruit = 0
        self.timer_bomb = 0

    def set_chances(self, fruit_chance=0.5, bomb_chance=0.2):
        self.fruit_chance = fruit_chance
        self.bomb_chance = bomb_chance

    def update(self):
        self.timer_fruit += 1
        spawn_fruit = random.random()
        self.timer_bomb += 1
        spawn_bomb = random.random()

        if spawn_fruit < self.fruit_chance + self.timer_fruit/1000 and self.timer_fruit > 75:
            fruit_image = random.choice(self.fruits_images)
            x = random.randint(50, constants.SCREEN_WIDTH-50)
            vx = random.randint(1, 6) * (-1 if x > constants.SCREEN_WIDTH/2 else 1)
            vy = -random.randint(11,18)

            self.entity_group.add(Entity(fruit_image, constants.FRUIT, x, vx, vy))
            self.timer_fruit = 0

        if spawn_bomb < self.bomb_chance + self.timer_bomb/1000 and self.timer_bomb > 140:
            x = random.randint(50, constants.SCREEN_WIDTH-50)
            vx = random.randint(1, 6) * (-1 if x > constants.SCREEN_WIDTH/2 else 1)
            vy = -random.randint(11,18)

            self.entity_group.add(Entity(self.bomb_image, constants.BOMB, x, vx, vy))
            self.timer_bomb = 0

class Explosion(pygame.sprite.Sprite):
    def __init__(self, x, y, frames):
        super().__init__()
        self.frames = frames
        self.frame_index = 0
        self.animation_speed = 0.3
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.kill()
            return
        self.image = self.frames[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.rect.center)

class SwingAnimation(pygame.sprite.Sprite):
    def __init__(self, x, y, frames):
        super().__init__()
        self.frames = frames
        self.frame_index = 0
        self.animation_speed = 0.6
        self.image = self.frames[0]
        self.rect = self.image.get_rect(center=(x, y))

    def update(self):
        self.frame_index += self.animation_speed
        if self.frame_index >= len(self.frames):
            self.kill()
            return
        self.image = self.frames[int(self.frame_index)]
        self.rect = self.image.get_rect(center=self.rect.center)
