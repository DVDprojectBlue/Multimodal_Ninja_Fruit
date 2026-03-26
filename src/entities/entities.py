import pygame
import random
import src.constants as constants

class Fruit(pygame.sprite.Sprite):
    def __init__(self, image, x, vx, vy):
        super().__init__()
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA) # docelowo self.image = image
        pygame.draw.circle(self.image, (255, 0, 0), (20, 20), 20) 
        self.rect = self.image.get_rect(midbottom = (x, constants.SCREEN_HEIGHT))

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
        
        if self.rect.top > 700:
            self.kill() 


class Bomb(pygame.sprite.Sprite):
    def __init__(self, image, x, vx, vy):
        super().__init__()
        self.image = pygame.Surface((40, 40), pygame.SRCALPHA) # docelowo self.image = image
        pygame.draw.circle(self.image, (255, 255, 0), (20, 20), 20) 
        self.rect = self.image.get_rect(midbottom = (x, constants.SCREEN_HEIGHT))

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
        
        if self.rect.top > 700:
            self.kill()


class Spawner:
    def __init__(self, fruits_group, bombs_group, fruits_images, bomb_image):
        self.fruits = fruits_group
        self.bombs = bombs_group

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

            self.fruits.add(Fruit(fruit_image, x, vx, vy))
            self.timer_fruit = 0

        if spawn_bomb < self.bomb_chance + self.timer_bomb/1000 and self.timer_bomb > 140:
            x = random.randint(50, constants.SCREEN_WIDTH-50)
            vx = random.randint(1, 6) * (-1 if x > constants.SCREEN_WIDTH/2 else 1)
            vy = -random.randint(11,18)

            self.bombs.add(Bomb(self.bomb_image, x, vx, vy))
            self.timer_bomb = 0