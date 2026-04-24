import os
import math
import random
import pygame
from collections import deque

import src.constants as constants
from src.entities import Entity, Spawner, Explosion, SwingAnimation
from src.voskListener import VoskListener
from src.handControl import PoseDetector, HandsDetector
from src.eye_tracking.eye_tracking_game_mode import EyeTrackingGameMode


class NinjaFruitGame:

    # TODO: dodać inne tryby sterowania
    CONTROL_MOUSE = "mouse"
    CONTROL_HAND = "hand"
    CONTROL_EYE = "eye"

    MODE_CLASSIC = "CLASSIC"
    MODE_TIME_ATTACK = "TIME_ATTACK"
    MODE_TIME_TIME = 45
    MODE_LEVELS = "LEVELS"
    MODE_LEVELS_TIME = 20
    STATE_CALIBRATION = 4

    def __init__(self, title="Multimodal Ninja Fruit"):
        pygame.init()
        self.screen = pygame.display.set_mode(
            (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 0  # 0 - menu, 1 - gra, 2 - game over, 3 - level transition
        self.voice_listener = None
        self.hand_detector = None
        self.eye_mode = None
        self.control_mode = self.CONTROL_MOUSE
        self._pending_start_after_calibration = False

        self.best_score_classic = 0
        self.best_score_time = 0
        self.best_score_level = 0

        self.game_mode = self.MODE_CLASSIC
        self.time_left = self.MODE_TIME_TIME * constants.FPS
        self.times_up = 0

        self.level = 1
        self.level_time = self.MODE_LEVELS_TIME * constants.FPS
        self.transition_timer = 0
        self.level_end = 0

        self.pointer_trail = deque(maxlen=15)  # bufor do rysowania śladu ruchu

        self._prepare_assets()
        self._setup_voice_control()
        self._setup_motion_control()

        self.title_glow_time = 0.0

        self.clock = pygame.time.Clock()

        self.new_pos = self._get_pointer_position()
        # TODO: setup sterowania wzrokiem itp.

    def _prepare_assets(self):
        # Definicja napisów, żeby było cokolwiek -- tymczasowe
        title_font_path = pygame.font.match_font(
            "assets/fonts/Noto_Serif_JP/static/NotoSerifJP-ExtraBold.ttf"
        )
        self.title_font = pygame.font.Font(title_font_path, 96)
        self.title_font.set_bold(True)

        medium_font_path = pygame.font.match_font(
            "assets/fonts/Noto_Serif_JP/static/NotoSerifJP-SemiBold.ttf"
        )
        self.medium_font = pygame.font.Font(medium_font_path, 50)
        self.medium_font.set_italic(True)

        regular_font_path = pygame.font.match_font(
            "assets/fonts/Noto_Serif_JP/static/NotoSerifJP-SemiBold.ttf"
        )
        self.small_font = pygame.font.Font(regular_font_path, 24)
        self.small_font.set_italic(True)

        # --- Tytuł ---
        lines = ["NINJA FRUIT"]

        self.line_surfs = [
            self.title_font.render(line, True, constants.TITLE_COLOR) for line in lines
        ]

        self.line_rects = []

        # 🔼 TYTUŁ WYŻEJ (np. górna 1/4 ekranu)
        start_y = constants.SCREEN_HEIGHT * 0.55
        spacing = 10

        current_y = int(start_y)

        self.start_surf = self.small_font.render(
            "Press S to start", True, constants.WHITE
        )
        self.start_rect = self.start_surf.get_rect(
            center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT * 0.68)
        )
        self.quit_surf = self.small_font.render(
            "Press ESC to quit", True, constants.WHITE
        )
        self.quit_rect = self.quit_surf.get_rect(
            center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT * 0.73)
        )

        for surf in self.line_surfs:
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH // 2, current_y))
            self.line_rects.append(rect)
            current_y += surf.get_height() + spacing

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()
        self.fruit_chance_current = 0.5
        self.bomb_chance_current = 0.3

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
        self.spawner.set_chances(self.fruit_chance_current, self.bomb_chance_current)

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
        self.prev_pos = None
        self.current_pos = None

    def _setup_voice_control(self):
        phrases = [
            (["start", "run", "go", "begin", "play"], self._start_game),
            (["menu", "back", "man", "men", "many"], self._go_to_menu),
            (["restart", "retry", "play again"], self._restart_game),
            (["quit", "exit", "stop"], self._quit_game),
            (
                ["hand", "hand control", "and"],
                self._set_hand_control,
            ),  # sterowanie ręką
            (["mouse", "mouse control"], self._set_mouse_control),  # sterowanie myszką
            (
                ["eye", "eyes", "gaze", "eye control", "gaze control"],
                self._set_eye_control,
            ),
            (["calibrate", "recalibrate", "calibration"], self._recalibrate_eye),
            (["classic", "normal mode", "normal", "one"], self._set_classic_mode),
            (["time", "time attack", "two", "too"], self._set_time_mode),
            (["level", "levels", "level mode", "three", "free"], self._set_levels_mode),
            # TODO: sterowanie wzrokiem i inne
        ]

        self.voice_listener = VoskListener(
            phrases=phrases,
            use_grammar=False,
            confidence_threshold=0.2,
            grammar_confidence_threshold=0.2,
            vad_threshold=500,
        )
        self.voice_listener.start()

    def _setup_motion_control(self):
        self.hand_detector = HandsDetector(
            cam_url=constants.CAM_URL, smoothing=0.7, debug=True
        )

    def _start_game(self):
        pygame.mixer.music.load(self.music_game)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
        if self.state == 0:
            if self.control_mode == self.CONTROL_EYE:
                if not self._start_eye_mode():
                    self.state = 0
                    return

                if self.eye_mode is not None and self.eye_mode.is_calibrating():
                    self._pending_start_after_calibration = True
                    self.state = self.STATE_CALIBRATION
                    return

            self._pending_start_after_calibration = False
            self.state = 1

    def _go_to_menu(self):
        self._reset_game()
        self.state = 0
        self._pending_start_after_calibration = False

    def _restart_game(self):
        self._reset_game()
        self._start_game()

    def _reset_game(self):
        if self.state == 2:
            self.score = 0
            self.lives = 3
            self.entity_group.empty()
            self.prev_pos = None
            self.current_pos = None
            self.times_up = 0
            self.state = 1

            if self.game_mode == self.MODE_TIME_ATTACK:
                self.time_left = self.MODE_TIME_TIME * constants.FPS
            if self.game_mode == self.MODE_LEVELS:
                self.level = 1
                self.level_time = self.MODE_LEVELS_TIME * constants.FPS
        self._pending_start_after_calibration = False

    def _set_classic_mode(self):
        self.game_mode = self.MODE_CLASSIC
        self._reset_game()

    def _update_classic_difficulty(self):
        self.fruit_chance_current += 0.0001
        self.bomb_chance_current += 0.00008

        self.fruit_chance_current = min(self.fruit_chance_current, 0.8)
        self.bomb_chance_current = min(self.bomb_chance_current, 0.65)

        self.spawner.set_chances(self.fruit_chance_current, self.bomb_chance_current)

    def _set_time_mode(self):
        self.spawner.set_chances(0.7, 0.55)
        self.game_mode = self.MODE_TIME_ATTACK
        self._reset_game()

    def _update_time(self):
        self.time_left -= 1
        if self.time_left <= 0:
            self.score += self.lives * 10
            pygame.mixer.music.load(self.music_menu)
            pygame.mixer.music.set_volume(0.5)
            pygame.mixer.music.play(-1)
            self.state = 2
            self.times_up = 1

    def _set_levels_mode(self):
        self.game_mode = self.MODE_LEVELS
        self._reset_game()

    def _update_level(self):
        self.level_time -= 1

        if self.level == 1:
            self.spawner.set_chances(0.55, 0.3)
        elif self.level == 2:
            self.spawner.set_chances(0.40, 0.85)
        elif self.level == 3:
            self.spawner.set_chances(0.85, 0.40)
        elif self.level == 4:
            self.spawner.set_chances(0.8, 0.8)

        if self.level_time <= 0:
            self.level += 1
            self.level_time = self.MODE_LEVELS_TIME * constants.FPS

            if self.level > 4:
                self.score += self.lives * 10
                self.level_end = 1
                pygame.mixer.music.load(self.music_menu)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
                self.state = 2
            else:
                self.state = 3
                self.transition_timer = 2 * constants.FPS
                self.entity_group.empty()

    def _quit_game(self):
        self.running = False

    def _set_mouse_control(self):
        self.set_control_mode(self.CONTROL_MOUSE)

    def _set_hand_control(self):
        self.set_control_mode(self.CONTROL_HAND)

    def _set_eye_control(self):
        self.set_control_mode(self.CONTROL_EYE)

    def _recalibrate_eye(self):
        if self.control_mode == self.CONTROL_EYE and self.eye_mode is not None:
            self.eye_mode.reset_session()
            if self.state == 0:
                self._pending_start_after_calibration = True

    def _shutdown_eye_mode(self):
        if self.eye_mode is not None:
            self.eye_mode.shutdown()
            self.eye_mode = None
        self._pending_start_after_calibration = False

    def _start_eye_mode(self):
        if self.eye_mode is None:
            width, height = self.screen.get_size()
            self.eye_mode = EyeTrackingGameMode(width, height)

        if self.eye_mode.start():
            return True

        self._shutdown_eye_mode()
        return False

    def _get_pointer_position(self):

        # Zwraca (x, y) w pikselach gry

        if self.control_mode == self.CONTROL_MOUSE:
            return pygame.mouse.get_pos()

        if self.control_mode == self.CONTROL_HAND:
            return self.hand_detector.get_screen_position(
                constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
            )

        if self.control_mode == self.CONTROL_EYE and self.eye_mode is not None:
            return self.eye_mode.get_control_position()

        return None

    def set_control_mode(self, mode):

        if mode == self.control_mode:
            return

        # reset pozycji
        self.prev_pos = None
        self.current_pos = None
        self.pointer_trail.clear()

        if mode == self.CONTROL_HAND:
            self._shutdown_eye_mode()
            self.hand_detector.start()
            self.control_mode = self.CONTROL_HAND
            print("[CONTROL] Switched to HAND")

        elif mode == self.CONTROL_MOUSE:
            self._shutdown_eye_mode()
            self.hand_detector.stop()
            self.control_mode = self.CONTROL_MOUSE
            print("[CONTROL] Switched to MOUSE")

        elif mode == self.CONTROL_EYE:
            self.hand_detector.stop()
            self._shutdown_eye_mode()
            self.control_mode = self.CONTROL_EYE
            print("[CONTROL] Switched to EYE")

        # TODO: inne tryby sterowania (wzrok itp.)

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(constants.FPS)

        if self.voice_listener is not None:
            self.voice_listener.stop()
        if self.hand_detector is not None:
            self.hand_detector.stop()
        self._shutdown_eye_mode()
        # TODO: zatrzymać inne moduły sterowania
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
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit_game()
                elif event.key == pygame.K_s and self.state == 0:
                    self._start_game()
                elif event.key == pygame.K_r and self.state == 2:
                    self._reset_game()
                    self._start_game()
                elif event.key == pygame.K_m and self.state == 0:
                    self._set_mouse_control()
                elif event.key == pygame.K_h and self.state == 0:
                    self._set_hand_control()
                elif event.key == pygame.K_e and self.state == 0:
                    self._set_eye_control()
                elif event.key == pygame.K_1 and self.state == 0:
                    self._set_classic_mode()
                elif event.key == pygame.K_2 and self.state == 0:
                    self._set_time_mode()
                elif event.key == pygame.K_n and self.state == 2:
                    self._go_to_menu()
                elif event.key == pygame.K_3 and self.state == 0:
                    self._set_levels_mode()
                elif event.key == pygame.K_c and self.state == 1:
                    self._recalibrate_eye()
                # TODO: inne skróty klawiszowe do sterowania itp.
                # self.running = False

    def _update(self):
        # Tu można robić logikę gry
        if self.state == 1:
            if self.control_mode == self.CONTROL_EYE and self.eye_mode is not None:
                self.eye_mode.update()

            self.spawner.update()
            self.entity_group.update()

            # uniwersalne pobieranie pozycji sterowania bez względu na tryb sterowania
            self.prev_pos = self.new_pos
            self.new_pos = self._get_pointer_position()

            if self.new_pos is not None:
                self.prev_pos = self.current_pos
                self.current_pos = self.new_pos
                self.pointer_trail.append(self.new_pos)
            else:
                self.prev_pos = None
                self.current_pos = None
                self.pointer_trail.clear()

            for entity in list(self.entity_group):
                if isinstance(entity, (Explosion, SwingAnimation)):
                    continue
                if entity.check_slice(self.prev_pos, self.new_pos):
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
                        offset_x = -20
                        offset_y = -60
                        self.entity_group.add(SwingAnimation(cx + offset_x, cy + offset_y, self.swing_frames))
                        random.choice(self.katana_sounds).play()

                    elif entity.entity_type == constants.BOMB:
                        self.lives -= 1
                        x, y = entity.rect.center
                        entity.kill()
                        self.entity_group.add(Explosion(x, y, self.explosion_frames))
                        random.choice(self.explosion_sounds).play()
                        self.katana_bonk.play()
                        entity.kill()
                if self.lives <= 0:
                    self.state = 2
                    pygame.mixer.music.load(self.music_menu)
                    pygame.mixer.music.set_volume(0.5)
                    pygame.mixer.music.play(-1)

            if self.game_mode == self.MODE_CLASSIC:
                self._update_classic_difficulty()
            elif self.game_mode == self.MODE_TIME_ATTACK:
                self._update_time()
            elif self.game_mode == self.MODE_LEVELS:
                self._update_level()
        elif self.state == self.STATE_CALIBRATION:
            if self.control_mode != self.CONTROL_EYE or self.eye_mode is None:
                self._pending_start_after_calibration = False
                self.state = 0
                return

            self.eye_mode.update()

            if (
                self._pending_start_after_calibration
                and not self.eye_mode.is_calibrating()
            ):
                self._pending_start_after_calibration = False
                self.state = 1
        elif self.state == 3:
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                self.state = 1

    # def _draw(self):
    #     self.screen.fill(constants.BLACK)
    #     # 0 - menu  1 - gra  2 - game over
    def draw_text_with_glow(
        self,
        screen,
        font,
        text,
        center_pos,
        color,
        glow_color=(255, 255, 255),
        glow_alpha=80,
        glow_radius=2,
    ):
        base = font.render(text, True, color)

        glow = font.render(text, True, glow_color)
        glow.set_alpha(glow_alpha)

        x, y = center_pos

        # draw glow around
        for dx in range(-glow_radius, glow_radius + 1):
            for dy in range(-glow_radius, glow_radius + 1):
                if dx != 0 or dy != 0:
                    rect = glow.get_rect(center=(x + dx, y + dy))
                    screen.blit(glow, rect)

    def draw_text_with_shadow(
        self,
        screen,
        font,
        text,
        center_pos,
        color,
        shadow_color=(0, 0, 0),
        offset=(2, 2),
    ):
        text_surf = font.render(text, True, color)
        shadow_surf = font.render(text, True, shadow_color)

        text_rect = text_surf.get_rect(center=center_pos)
        shadow_rect = shadow_surf.get_rect(
            center=(center_pos[0] + offset[0], center_pos[1] + offset[1])
        )

        screen.blit(shadow_surf, shadow_rect)
        screen.blit(text_surf, text_rect)

    def _draw(self):
        if self.state == 0:
            self.screen.blit(self.background_menu, (0, 0))
        elif self.state == 1:
            self.screen.blit(self.background_game, (0, 0))
        elif self.state == 2:
            self.screen.blit(self.background_gameover, (0, 0))

        if self.state == 0:
            # for surf, rect in zip(self.line_surfs, self.line_rects):
            #     self.screen.blit(surf, rect)
            # self.screen.blit(self.quit_surf, self.quit_rect)
            # self.screen.blit(self.start_surf, self.start_rect)

            # # pokaż aktualny tryb
            # best_text = f"Best Classic: {self.best_score_classic}  |  Best Time: {self.best_score_time}  |  Best Level: {self.best_score_level}"
            # best_surf = self.small_font.render(best_text, True, (120, 200, 255))
            # # Set Y to 500
            # best_rect = best_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
            # self.screen.blit(best_surf, best_rect)

            # mode_text = f"Control: {self.control_mode.upper()}  (M=mouse, H=hand)"
            # mode_surf = self.small_font.render(mode_text, True, (200, 200, 0))
            # # Set Y to 500 to conflict with best_text
            # mode_rect = mode_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
            # self.screen.blit(mode_surf, mode_rect)

            # mode_info = self.small_font.render(
            #     f"Mode: {self.game_mode} (1=classic, 2=time, 3=levels)",
            #     True,
            #     (180, 180, 180),
            # )
            # # Set Y to 500 to conflict with both previous texts
            # mode_info_rect = mode_info.get_rect(
            #     center=(constants.SCREEN_WIDTH // 2, 500)
            # )
            # self.screen.blit(mode_info, mode_info_rect)

            center_x = constants.SCREEN_WIDTH // 2
            start_y = 471
            line_spacing = 30

            self.title_glow_time += self.clock.tick(60) / 1000

            glow_phase = (math.sin(self.title_glow_time * 2) + 1) * 0.5
            inner_alpha = int(100 + glow_phase * 80)
            outer_alpha = 180

            # Próba dodania "glow". nie wyszło ale wygląda ok
            for surf, rect in zip(self.line_surfs, self.line_rects):
                shadow = surf.copy()
                shadow.fill(
                    constants.OUTER_SHADOW_COLOR, special_flags=pygame.BLEND_RGBA_MULT
                )
                shadow.set_alpha(outer_alpha)

                for dx, dy in [(-3, 0), (3, 0), (0, -3), (0, 3)]:
                    self.screen.blit(shadow, rect.move(dx, dy))

                glow = surf.copy()
                glow.fill(
                    constants.INNER_GLOW_COLOR, special_flags=pygame.BLEND_RGBA_MULT
                )
                glow.set_alpha(inner_alpha)

                for dx, dy in [
                    (-1, 0),
                    (1, 0),
                    (0, -1),
                    (0, 1),
                    (-1, -1),
                    (1, 1),
                    (1, -1),
                    (-1, 1),
                ]:
                    self.screen.blit(glow, rect.move(dx, dy))

                self.screen.blit(surf, rect)

            self.screen.blit(self.quit_surf, self.quit_rect)
            self.screen.blit(self.start_surf, self.start_rect)

            best_text = (
                f"Best Classic: {self.best_score_classic}  |  "
                f"Best Time: {self.best_score_time}  |  "
                f"Best Level: {self.best_score_level}"
            )

            self.draw_text_with_shadow(
                self.screen,
                self.small_font,
                best_text,
                (center_x, start_y),
                (120, 200, 255),
            )

            mode_text = (
                f"Control: {self.control_mode.upper()}  (M=mouse, H=hand, E=eye)"
            )

            self.draw_text_with_shadow(
                self.screen,
                self.small_font,
                mode_text,
                (center_x, start_y + line_spacing),
                (200, 200, 0),
            )

            mode_info_text = f"Mode: {self.game_mode} (1=classic, 2=time, 3=levels)"

            self.draw_text_with_shadow(
                self.screen,
                self.small_font,
                mode_info_text,
                (center_x, start_y + 2 * line_spacing),
                (180, 180, 180),
            )

        elif self.state == 1:
            self.entity_group.draw(self.screen)

            # stare rysowanie ruchu
            # if self.prev_pos and self.current_pos:
            #     pygame.draw.line(self.screen, (255, 255, 255), self.prev_pos, self.current_pos, 3)

            # rysowanie śladu ruchu
            if len(self.pointer_trail) >= 2:
                points = list(self.pointer_trail)
                for i in range(1, len(points)):
                    p1 = points[i - 1]
                    p2 = points[i]

                    intensity = int(
                        255 * (i / len(points))
                    )  # starsze ciemniejsze, nowsze jaśniejsze
                    width = max(1, int(6 * (i / len(points))))  # nowsze grubsze

                    color = (intensity, intensity, intensity)
                    pygame.draw.line(self.screen, color, p1, p2, width)

            self.score_surf = self.small_font.render(
                f"Score: {self.score}", True, constants.WHITE
            )
            self.score_rect = self.score_surf.get_rect(
                topright=(constants.SCREEN_WIDTH - 20, 20)
            )
            self.screen.blit(self.score_surf, self.score_rect)

            self.lives_surf = self.small_font.render(
                f"Lives: {self.lives}", True, constants.WHITE
            )
            self.lives_rect = self.lives_surf.get_rect(
                topright=(constants.SCREEN_WIDTH - 20, 50)
            )
            self.screen.blit(self.lives_surf, self.lives_rect)

            # tryb sterowania
            ctrl_surf = self.small_font.render(
                f"[{self.control_mode.upper()}]", True, (150, 150, 150)
            )
            self.screen.blit(ctrl_surf, (10, 10))

            if self.game_mode == self.MODE_TIME_ATTACK:
                seconds = self.time_left // constants.FPS
                minutes = seconds // 60
                seconds = seconds % 60

                time_surf = self.small_font.render(
                    f"Time: {minutes:02}:{seconds:02}", True, (255, 200, 50)
                )
                self.screen.blit(time_surf, (10, 40))

            if self.game_mode == self.MODE_LEVELS:
                seconds = self.level_time // constants.FPS

                time_surf = self.small_font.render(
                    f"Time: {seconds:02}", True, (255, 200, 50)
                )
                self.screen.blit(time_surf, (10, 40))

                level_surf = self.small_font.render(
                    f"Level: {self.level}", True, (100, 255, 100)
                )
                self.screen.blit(level_surf, (10, 70))

            if self.control_mode == self.CONTROL_EYE and self.eye_mode is not None:
                self.eye_mode.draw_overlay(self.screen)

                recalibrate_surf = self.small_font.render(
                    "C = recalibrate", True, (120, 220, 220)
                )
                self.screen.blit(recalibrate_surf, (10, 100))

        elif self.state == self.STATE_CALIBRATION:
            self.screen.fill(constants.BLACK)
            title = self.title_font.render("Calibrating", True, constants.WHITE)
            title_rect = title.get_rect(center=(constants.SCREEN_WIDTH // 2, 120))
            self.screen.blit(title, title_rect)

            info = self.small_font.render(
                "Keep your gaze on the target points", True, (200, 200, 200)
            )
            info_rect = info.get_rect(center=(constants.SCREEN_WIDTH // 2, 200))
            self.screen.blit(info, info_rect)

            if self.eye_mode is not None:
                self.eye_mode.draw_overlay(self.screen)

        elif self.state == 2:
            center_x = constants.SCREEN_WIDTH // 2

            if self.game_mode == self.MODE_TIME_ATTACK and self.times_up:
                self.draw_text_with_glow(
                    self.screen,
                    self.title_font,
                    f"Time's Up  Score: {self.score}",
                    (center_x, 250),
                    constants.WHITE,
                    glow_color=(255, 220, 180),
                    glow_alpha=90,
                    glow_radius=2,
                )

                self.draw_text_with_shadow(
                    self.screen,
                    self.title_font,
                    f"Time's Up  Score: {self.score}",
                    (center_x, 250),
                    constants.WHITE,
                    offset=(3, 3),
                )

                if self.best_score_time < self.score:
                    self.best_score_time = self.score

            elif self.game_mode == self.MODE_LEVELS and self.level_end:
                self.draw_text_with_glow(
                    self.screen,
                    self.title_font,
                    "All levels completed",
                    (center_x, 250),
                    constants.WHITE,
                    glow_color=(255, 220, 180),
                    glow_alpha=90,
                    glow_radius=2,
                )

                self.draw_text_with_shadow(
                    self.screen,
                    self.title_font,
                    "All levels completed",
                    (center_x, 250),
                    constants.WHITE,
                    offset=(3, 3),
                )

                self.draw_text_with_glow(
                    self.screen,
                    self.title_font,
                    f"Score: {self.score}",
                    (center_x, 220),
                    constants.WHITE,
                    glow_color=(255, 220, 180),
                    glow_alpha=90,
                    glow_radius=2,
                )

                self.draw_text_with_shadow(
                    self.screen,
                    self.title_font,
                    f"Score: {self.score}",
                    (center_x, 220),
                    constants.WHITE,
                    offset=(3, 3),
                )

                if self.best_score_level < self.score:
                    self.best_score_level = self.score

            else:
                self.draw_text_with_glow(
                    self.screen,
                    self.title_font,
                    f"GAME OVER  Score: {self.score}",
                    (center_x, 250),
                    constants.WHITE,
                    glow_color=(255, 220, 180),
                    glow_alpha=90,
                    glow_radius=2,
                )

                self.draw_text_with_shadow(
                    self.screen,
                    self.title_font,
                    f"GAME OVER  Score: {self.score}",
                    (center_x, 250),
                    constants.WHITE,
                    offset=(3, 3),
                )

                if (
                    self.game_mode == self.MODE_TIME_ATTACK
                    and self.best_score_time < self.score
                ):
                    self.best_score_time = self.score
                elif (
                    self.game_mode == self.MODE_CLASSIC
                    and self.best_score_classic < self.score
                ):
                    self.best_score_classic = self.score
                elif (
                    self.game_mode == self.MODE_LEVELS
                    and self.best_score_level < self.score
                ):
                    self.best_score_level = self.score

            self.draw_text_with_shadow(
                self.screen,
                self.medium_font,
                "Press R to restart",
                (center_x, 380),
                constants.WHITE,
                offset=(1, 1),
            )

            self.draw_text_with_shadow(
                self.screen,
                self.medium_font,
                "Press N to go to menu",
                (center_x, 420),
                constants.WHITE,
                offset=(1, 1),
            )

        elif self.state == 3:
            center_x = constants.SCREEN_WIDTH // 2
            center_y = constants.SCREEN_HEIGHT // 2

            self.draw_text_with_shadow(
                self.screen,
                self.title_font,
                "NEXT LEVEL",
                (center_x, center_y),
                constants.WHITE,
                shadow_color=(0, 0, 0),
                offset=(3, 3),
            )

            self.draw_text_with_shadow(
                self.screen,
                self.small_font,
                "Get Ready...",
                (center_x, center_y + 80),
                (200, 200, 200),
                shadow_color=(0, 0, 0),
                offset=(1, 1),
            )

        pygame.display.flip()
