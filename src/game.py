import os
import pygame
from collections import deque

import src.constants as constants
from src.entities import Spawner, Entity
from src.voskListener import VoskListener
from src.handControl import PoseDetector, HandsDetector


class NinjaFruitGame:

    # TODO: dodać inne tryby sterowania
    CONTROL_MOUSE = "mouse"
    CONTROL_HAND = "hand"

    MODE_CLASSIC = "CLASSIC"
    MODE_TIME_ATTACK = "TIME_ATTACK"
    MODE_TIME_TIME = 45
    MODE_LEVELS = "LEVELS"
    MODE_LEVELS_TIME = 20

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
        self.control_mode = self.CONTROL_MOUSE

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
        # TODO: setup sterowania wzrokiem itp.

    def _prepare_assets(self):
        # Definicja napisów, żeby było cokolwiek -- tymczasowe
        font_path = pygame.font.match_font("Segoe UI")
        self.font = pygame.font.Font(font_path, 96)
        self.font.set_bold(True)
        self.small_font = pygame.font.Font(font_path, 24)

        lines = ["Ninja Fruit"]
        self.line_surfs = [
            self.font.render(line, True, constants.WHITE) for line in lines
        ]

        self.line_rects = []
        current_y = 425
        for surf in self.line_surfs:
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH // 2, current_y))
            self.line_rects.append(rect)
            current_y += surf.get_height()

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()
        self.spawner = Spawner(self.entity_group, ["apple", "melon", "lemon"], "bomb")
        self.fruit_chance_current = 0.5
        self.bomb_chance_current = 0.3
        self.spawner.set_chances(self.fruit_chance_current, self.bomb_chance_current)
        self.start_surf = self.small_font.render(
            "Press S to start", True, constants.WHITE
        )
        self.start_rect = self.start_surf.get_rect(
            center=(constants.SCREEN_WIDTH // 2, 505)
        )
        self.quit_surf = self.small_font.render(
            "Press ESC to quit", True, constants.WHITE
        )
        self.quit_rect = self.quit_surf.get_rect(
            center=(constants.SCREEN_WIDTH // 2, 530)
        )

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()

        # Ładowanie ścieżek do obrazków
        self.img_orange = os.path.join(constants.IMAGES_PATH, "orange.png")
        self.img_orange_left = os.path.join(constants.IMAGES_PATH, "orange_left.png")
        self.img_orange_right = os.path.join(constants.IMAGES_PATH, "orange_right.png")
        self.img_bomb = os.path.join(constants.IMAGES_PATH, "bomb.png")

        # Tła
        bg_raw = pygame.image.load(
            os.path.join(constants.IMAGES_PATH, "background_main.png")
        ).convert()
        self.background_game = pygame.transform.scale(
            bg_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )

        bg_menu_raw = pygame.image.load(
            os.path.join(constants.IMAGES_PATH, "background_menu.png")
        ).convert()
        self.background_menu = pygame.transform.scale(
            bg_menu_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )

        bg_gameover_raw = pygame.image.load(
            os.path.join(constants.IMAGES_PATH, "background_gameover.png")
        ).convert()
        self.background_gameover = pygame.transform.scale(
            bg_gameover_raw, (constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)
        )

        self.spawner = Spawner(self.entity_group, [self.img_orange], self.img_bomb)

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
            (["menu", "back", "man"], self._go_to_menu),
            (["restart", "retry", "play again"], self._restart_game),
            (["quit", "exit", "stop"], self._quit_game),
            (["mouse", "mouse control"], self._set_mouse_control),  # sterowanie myszką
            (["hand", "hand control"], self._set_hand_control),  # sterowanie ręką
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
        if self.state == 0:
            self.state = 1

    def _go_to_menu(self):
        self._restart_game()
        self.state = 0

    def _restart_game(self):
        if self.state == 2:
            self.score = 0
            self.lives = 3
            self.entity_group.empty()
            self.prev_pos = None
            self.current_pos = None
            self.times_up = 0
            if self.state == 2:
                self.state = 1
            else:
                self.state = 0
            if self.game_mode == self.MODE_TIME_ATTACK:
                self.time_left = self.MODE_TIME_TIME * constants.FPS
            if self.game_mode == self.MODE_LEVELS:
                self.level = 1
                self.level_time = self.MODE_LEVELS_TIME * constants.FPS

    def _set_classic_mode(self):
        self.game_mode = self.MODE_CLASSIC
        self._restart_game()

    def _update_classic_difficulty(self):
        self.fruit_chance_current += 0.0001
        self.bomb_chance_current += 0.00008

        self.fruit_chance_current = min(self.fruit_chance_current, 0.8)
        self.bomb_chance_current = min(self.bomb_chance_current, 0.65)

        self.spawner.set_chances(self.fruit_chance_current, self.bomb_chance_current)

    def _set_time_mode(self):
        self.spawner.set_chances(0.7, 0.55)
        self.game_mode = self.MODE_TIME_ATTACK
        self._restart_game()

    def _update_time(self):
        self.time_left -= 1
        if self.time_left <= 0:
            self.score += self.lives * 10
            self.state = 2
            self.times_up = 1

    def _set_levels_mode(self):
        self.game_mode = self.MODE_LEVELS
        self._restart_game()

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

    def _get_pointer_position(self):

        # Zwraca (x, y) w pikselach gry

        if self.control_mode == self.CONTROL_MOUSE:
            return pygame.mouse.get_pos()

        if self.control_mode == self.CONTROL_HAND:
            return self.hand_detector.get_screen_position(
                constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT
            )

        return None

    def set_control_mode(self, mode):

        if mode == self.control_mode:
            return

        # reset pozycji
        self.prev_pos = None
        self.current_pos = None

        if mode == self.CONTROL_HAND:
            self.hand_detector.start()
            self.control_mode = self.CONTROL_HAND
            print("[CONTROL] Switched to HAND")

        elif mode == self.CONTROL_MOUSE:
            self.hand_detector.stop()
            self.control_mode = self.CONTROL_MOUSE
            print("[CONTROL] Switched to MOUSE")

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
        # TODO: zatrzymać inne moduły sterowania
        pygame.quit()

    def _handle_events(self):
        # Obsługa eventów
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self._quit_game()
                elif event.key == pygame.K_s and self.state == 0:
                    self._start_game()
                elif event.key == pygame.K_r and self.state == 2:
                    self._restart_game()
                elif event.key == pygame.K_m and self.state == 0:
                    self._set_mouse_control()
                elif event.key == pygame.K_h and self.state == 0:
                    self._set_hand_control()
                elif event.key == pygame.K_1 and self.state == 0:
                    self._set_classic_mode()
                elif event.key == pygame.K_2 and self.state == 0:
                    self._set_time_mode()
                elif event.key == pygame.K_n and self.state == 2:
                    self._go_to_menu()
                elif event.key == pygame.K_3 and self.state == 0:
                    self._set_levels_mode()
                # TODO: inne skróty klawiszowe do sterowania itp.
                self.running = False
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_s
                and self.state == 0
            ):
                self.state = 1
                pygame.mixer.music.load(self.music_game)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)
            elif (
                event.type == pygame.KEYDOWN
                and event.key == pygame.K_r
                and self.state == 2
            ):
                self.score = 0
                self.lives = 3
                self.state = 1
                pygame.mixer.music.load(self.music_game)
                pygame.mixer.music.set_volume(0.5)
                pygame.mixer.music.play(-1)

    def _update(self):
        # Tu można robić logikę gry
        if self.state == 1:
            self.spawner.update()
            self.entity_group.update()

            # uniwersalne pobieranie pozycji sterowania bez względu na tryb sterowania
            new_pos = self._get_pointer_position()

            if new_pos is not None:
                self.prev_pos = self.current_pos
                self.current_pos = new_pos
                self.pointer_trail.append(new_pos)
            else:
                self.prev_pos = None
                self.current_pos = None
                self.pointer_trail.clear()

            self.prev_mouse_pos = self.current_mouse_pos
            self.current_mouse_pos = pygame.mouse.get_pos()

            for entity in self.entity_group:
                if entity.check_slice(self.prev_mouse_pos, self.current_mouse_pos):
                    if entity.entity_type == constants.FRUIT:
                        self.score += 1
                        x, y, vx, vy = entity.get_state()
                        entity.kill()

                        self.entity_group.add(
                            Entity(
                                self.img_orange_left,
                                constants.HALF,
                                x,
                                vx - 3,
                                int(-4 + vy / 2),
                                y=y,
                                half="left",
                            )
                        )
                        self.entity_group.add(
                            Entity(
                                self.img_orange_right,
                                constants.HALF,
                                x,
                                vx + 3,
                                int(-4 + vy / 2),
                                y=y,
                                half="right",
                            )
                        )

                    elif entity.entity_type == constants.BOMB:
                        self.lives -= 1
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
        elif self.state == 3:
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                self.state = 1

    # def _draw(self):
    #     self.screen.fill(constants.BLACK)
    #     # 0 - menu  1 - gra  2 - game over

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

            # pokaż aktualny tryb
            best_text = f"Best Classic: {self.best_score_classic}  |  Best Time: {self.best_score_time}  |  Best Level: {self.best_score_level}"
            best_surf = self.small_font.render(best_text, True, (120, 200, 255))
            best_rect = best_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
            self.screen.blit(best_surf, best_rect)

            mode_text = f"Control: {self.control_mode.upper()}  (M=mouse, H=hand)"
            mode_surf = self.small_font.render(mode_text, True, (200, 200, 0))
            mode_rect = mode_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 540))
            self.screen.blit(mode_surf, mode_rect)

            mode_info = self.small_font.render(
                f"Mode: {self.game_mode} (1=classic, 2=time, 3=levels)",
                True,
                (180, 180, 180),
            )
            mode_info_rect = mode_info.get_rect(
                center=(constants.SCREEN_WIDTH // 2, 580)
            )
            self.screen.blit(mode_info, mode_info_rect)

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

        elif self.state == 2:
            if self.game_mode == self.MODE_TIME_ATTACK and self.times_up:
                self.game_over_surf = self.font.render(
                    f"Time's Up  Score: {self.score}", True, constants.WHITE
                )
                self.game_over_rect = self.game_over_surf.get_rect(
                    center=(constants.SCREEN_WIDTH // 2, 200)
                )
                self.screen.blit(self.game_over_surf, self.game_over_rect)
                if self.best_score_time < self.score:
                    self.best_score_time = self.score

            elif self.game_mode == self.MODE_LEVELS and self.level_end:
                line1 = self.font.render("All levels completed", True, constants.WHITE)
                line2 = self.font.render(f"Score: {self.score}", True, constants.WHITE)
                rect1 = line1.get_rect(center=(constants.SCREEN_WIDTH // 2, 110))
                rect2 = line2.get_rect(center=(constants.SCREEN_WIDTH // 2, 220))
                self.screen.blit(line1, rect1)
                self.screen.blit(line2, rect2)

                if self.best_score_level < self.score:
                    self.best_score_level = self.score

            else:
                self.game_over_surf = self.font.render(
                    f"GAME OVER  Score: {self.score}", True, constants.WHITE
                )
                self.game_over_rect = self.game_over_surf.get_rect(
                    center=(constants.SCREEN_WIDTH // 2, 200)
                )
                self.screen.blit(self.game_over_surf, self.game_over_rect)
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

            # self.restart_surf = self.small_font.render("Press R to restart", True, constants.WHITE)
            # self.restart_rect = self.restart_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 300))
            # self.screen.blit(self.restart_surf, self.restart_rect)

            # self.menu_surf = self.small_font.render("Press N to go to menu", True, constants.WHITE)
            # self.menu_rect = self.menu_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 340))
            # self.screen.blit(self.menu_surf, self.menu_rect)

            self.game_over_surf = self.font.render(
                f"GAME OVER  Score: {self.score}", True, constants.WHITE
            )
            self.game_over_rect = self.game_over_surf.get_rect(
                center=(constants.SCREEN_WIDTH // 2, 210)
            )
            self.screen.blit(self.game_over_surf, self.game_over_rect)

            self.restart_surf = self.small_font.render(
                "Press R to restart", True, constants.WHITE
            )
            self.restart_rect = self.restart_surf.get_rect(
                center=(constants.SCREEN_WIDTH // 2, 500)
            )
            self.screen.blit(self.restart_surf, self.restart_rect)

        elif self.state == 3:
            text = f"NEXT LEVEL"

            surf = self.font.render(text, True, constants.WHITE)
            rect = surf.get_rect(
                center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2)
            )

            self.screen.blit(surf, rect)

            sub = self.small_font.render("Get Ready...", True, (200, 200, 200))
            sub_rect = sub.get_rect(
                center=(constants.SCREEN_WIDTH // 2, constants.SCREEN_HEIGHT // 2 + 80)
            )
            self.screen.blit(sub, sub_rect)

        pygame.display.flip()
