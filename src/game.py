import pygame
import os
import random
import src.constants as constants
from src.entities import Entity, Spawner, Explosion, SwingAnimation

class NinjaFruitGame:
    def __init__(self, title="Multimodal Ninja Fruit"):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 0 # 0 - menu, 1 -gra
        
        self._prepare_assets()

    def _prepare_assets(self):
        # Definicja napisów, żeby było cokolwiek -- tymczasowe
        font_path = pygame.font.match_font("Segoe UI")
        self.font = pygame.font.Font(font_path, 96)
        self.font.set_bold(True)
        self.small_font = pygame.font.Font(font_path, 24)
        
        lines = ["Ninja Fruit"]
        self.line_surfs = [self.font.render(line, True, constants.WHITE) for line in lines]
        
        self.line_rects = []
        current_y = 425
        for surf in self.line_surfs:
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH // 2, current_y))
            self.line_rects.append(rect)
            current_y += surf.get_height()

        # Napisy menu
        self.start_surf = self.small_font.render("Press S to start", True, constants.WHITE)
        self.start_rect = self.start_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 505))
        self.quit_surf = self.small_font.render("Press ESC to quit", True, constants.WHITE)
        self.quit_rect = self.quit_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 530))

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()

        # Ładowanie ścieżek do obrazków
        self.img_orange_frames = [
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange0.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange45.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange90.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange135.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange180.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange225.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange270.png"),
            os.path.join(constants.IMAGES_ORANGE_PATH, "orange315.png"),
        ]
        self.img_orange_left = os.path.join(constants.IMAGES_ORANGE_PATH, "orange_left.png")
        self.img_orange_right = os.path.join(constants.IMAGES_ORANGE_PATH, "orange_right.png")

        self.img_apple_frames = [
            os.path.join(constants.IMAGES_APPLE_PATH, f"apple ({i}).png")
            for i in range(1, 9)
        ]
        self.img_apple_left = os.path.join(constants.IMAGES_APPLE_PATH, "apple_left.png")
        self.img_apple_right = os.path.join(constants.IMAGES_APPLE_PATH, "apple_right.png")

        self.img_banana_frames = [
            os.path.join(constants.IMAGES_BANANA_PATH, f"banana ({i}).png")
            for i in range(1, 9)
        ]
        self.img_banana_left = os.path.join(constants.IMAGES_BANANA_PATH, "banana_left.png")
        self.img_banana_right = os.path.join(constants.IMAGES_BANANA_PATH, "banana_right.png")

        self.img_watermelon_frames = [
            os.path.join(constants.IMAGES_WATERMELON_PATH, f"watermelon ({i}).png")
            for i in range(1, 9)
        ]
        self.img_watermelon_left = os.path.join(constants.IMAGES_WATERMELON_PATH, "watermelon_left.png")
        self.img_watermelon_right = os.path.join(constants.IMAGES_WATERMELON_PATH, "watermelon_right.png")
        
        # Klatki animacji wybuchu
        self.explosion_frames = [
            pygame.transform.scale(
                pygame.image.load(os.path.join(constants.IMAGES_EXPLOSION_PATH, f"explosion ({i}).png")).convert_alpha(),
                (128, 128)
            )
            for i in range(1, 12)
        ]

        # Dźwięki wybuchu
        self.explosion_sounds = [
            pygame.mixer.Sound(os.path.join(constants.SOUNDS_EXPLOSION_PATH, f"explosion_{i}.mp3"))
            for i in range(1, 5)
        ]

        # Dźwięk gongu
        self.gong_sound = pygame.mixer.Sound(os.path.join(constants.SOUNDS_PATH, "gong.mp3"))

        # Klatki animacji cięcia kataną
        self.swing_frames = [
            pygame.transform.scale(
                pygame.image.load(os.path.join(constants.IMAGES_SWING_PATH, f"swing ({i}).png")).convert_alpha(),
                (128, 128)
            )
            for i in range(1, 10)
        ]

        # Dźwięki katany
        self.katana_sounds = [
            pygame.mixer.Sound(os.path.join(constants.SOUNDS_KATANA_PATH, f"katana_{i}.mp3"))
            for i in range(0, 5)
        ]
        self.katana_bonk = pygame.mixer.Sound(os.path.join(constants.SOUNDS_KATANA_PATH, "katana_bomb.mp3"))

        self.img_bomb_frames = [
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb0.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb22.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb45.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb22.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb0.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb-22.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb-45.png"),
            os.path.join(constants.IMAGES_BOMB_PATH, "bomb-22.png"),
        ]

        # Tła
        bg_raw = pygame.image.load(os.path.join(constants.IMAGES_BG_PATH, "background_main.png")).convert()
        self.background_game = pygame.transform.scale(bg_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))

        bg_menu_raw = pygame.image.load(os.path.join(constants.IMAGES_BG_PATH, "background_menu.png")).convert()
        self.background_menu = pygame.transform.scale(bg_menu_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))

        bg_gameover_raw = pygame.image.load(os.path.join(constants.IMAGES_BG_PATH, "background_gameover.png")).convert()
        self.background_gameover = pygame.transform.scale(bg_gameover_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        self.spawner = Spawner(self.entity_group, [
            self.img_orange_frames,
            self.img_apple_frames,
            self.img_banana_frames,
            self.img_watermelon_frames
        ], self.img_bomb_frames)

        self.spawner.set_chances(0.4, 0.1)

        # Muzyka
        self.music_menu = os.path.join(constants.SOUNDS_PATH, "menu_theme.mp3")
        self.music_game = os.path.join(constants.SOUNDS_PATH, "main_theme.mp3")

        # Zacznij od muzyki menu
        pygame.mixer.music.load(self.music_menu)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)  # -1 = zapętlenie

        # Cięcie owoców/bomb
        self.lives = 3
        self.score = 0
        self.death_timer = 0
        self.prev_mouse_pos = None
        self.current_mouse_pos = None

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(constants.FPS)
        pygame.quit()

    def _handle_events(self):
        # Obsługa eventów
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_s and self.state == 0:
                self.state = 1
                pygame.mixer.music.load(self.music_game)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
                self.gong_sound.play()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.state == 2:
                self.score = 0
                self.lives = 3
                self.death_timer = 0
                self.state = 1
                pygame.mixer.music.load(self.music_game)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)

    def _update(self):
        # Tu można robić logikę gry
        if self.state == 1:
            self.spawner.update()
            self.entity_group.update()

            self.prev_mouse_pos = self.current_mouse_pos
            self.current_mouse_pos = pygame.mouse.get_pos()

            for entity in list(self.entity_group):
                if isinstance(entity, (Explosion, SwingAnimation)):
                    continue
                if entity.check_slice(self.prev_mouse_pos, self.current_mouse_pos):
                    if entity.entity_type == constants.FRUIT:
                        self.score += 1
                        x, y, vx, vy = entity.get_state()
                        cx, cy = entity.rect.center
                        entity.kill()

                        fruit_map = {
                            self.img_orange_frames[0]: (self.img_orange_left, self.img_orange_right),
                            self.img_apple_frames[0]: (self.img_apple_left, self.img_apple_right),
                            self.img_banana_frames[0]: (self.img_banana_left, self.img_banana_right),
                            self.img_watermelon_frames[0]: (self.img_watermelon_left, self.img_watermelon_right),
                        }
                        left_img, right_img = fruit_map.get(entity.fruit_image_key, (self.img_orange_left, self.img_orange_right))

                        self.entity_group.add(Entity(left_img, constants.HALF, x, vx-3, int(-4+vy/2), y=y, half='left'))
                        self.entity_group.add(Entity(right_img, constants.HALF, x, vx+3, int(-4+vy/2), y=y, half='right'))
                        offset_x = -20  # ujemna = w lewo, dodatnia = w prawo
                        offset_y = -60  # ujemna = w górę, dodatnia = w dół
                        self.entity_group.add(SwingAnimation(cx + offset_x, cy + offset_y, self.swing_frames))
                        random.choice(self.katana_sounds).play()

                    elif entity.entity_type == constants.BOMB:
                        self.lives -= 1
                        x, y = entity.rect.center
                        entity.kill()
                        self.entity_group.add(Explosion(x, y, self.explosion_frames))
                        random.choice(self.explosion_sounds).play()
                        self.katana_bonk.play()
                if self.lives <= 0 and self.death_timer == 0:
                    self.death_timer = pygame.time.get_ticks()

            if self.death_timer > 0 and pygame.time.get_ticks() - self.death_timer > 1000:
                self.death_timer = 0
                self.state = 2
                pygame.mixer.music.load(self.music_menu)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)

    def _draw(self):
        if self.state == 0:
            self.screen.blit(self.background_menu, (0, 0))
        elif self.state == 1:
            self.screen.blit(self.background_game, (0, 0))
        elif self.state == 2:
            self.screen.blit(self.background_gameover, (0, 0))

        if self.state == 0:
            for surf, rect in zip(self.line_surfs, self.line_rects):
                self.screen.blit(surf, rect)
            self.screen.blit(self.quit_surf, self.quit_rect)
            self.screen.blit(self.start_surf, self.start_rect)

        elif self.state == 1:
            self.entity_group.draw(self.screen)
            if self.prev_mouse_pos and self.current_mouse_pos:
                pygame.draw.line(self.screen, (255, 255, 255), self.prev_mouse_pos, self.current_mouse_pos, 3)
            
            self.score_surf = self.small_font.render(f"Score: {self.score}", True, constants.WHITE)
            self.score_rect = self.score_surf.get_rect(topright=(constants.SCREEN_WIDTH - 20, 20))
            self.screen.blit(self.score_surf, self.score_rect)

            self.lives_surf = self.small_font.render(f"Lives: {self.lives}", True, constants.WHITE)
            self.lives_rect = self.lives_surf.get_rect(topright=(constants.SCREEN_WIDTH - 20, 50))
            self.screen.blit(self.lives_surf, self.lives_rect)
        
        elif self.state == 2:
            self.game_over_surf = self.font.render(f"GAME OVER  Score: {self.score}", True, constants.WHITE)
            self.game_over_rect = self.game_over_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 210))
            self.screen.blit(self.game_over_surf, self.game_over_rect)

            self.restart_surf = self.small_font.render("Press R to restart", True, constants.WHITE)
            self.restart_rect = self.restart_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
            self.screen.blit(self.restart_surf, self.restart_rect)

        pygame.display.flip()