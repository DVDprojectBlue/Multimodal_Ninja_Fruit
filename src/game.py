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

    def __init__(self, title="Multimodal Ninja Fruit"):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 0 # 0 - menu, 1 - gra
        self.voice_listener = None
        self.hand_detector = None
        self.control_mode = self.CONTROL_MOUSE

        self.pointer_trail = deque(maxlen=25) # bufor do rysowania śladu ruchu

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
        
        lines = ["Ninja Fruit", "In Progress..."]
        self.line_surfs = [self.font.render(line, True, constants.WHITE) for line in lines]
        
        self.line_rects = []
        current_y = 120
        for surf in self.line_surfs:
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH // 2, current_y))
            self.line_rects.append(rect)
            current_y += surf.get_height()

        # Napisy menu
        self.start_surf = self.small_font.render("Press S or say START", True, constants.WHITE)
        self.start_rect = self.start_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
        self.quit_surf = self.small_font.render("Press ESC or say QUIT", True, constants.WHITE)
        self.quit_rect = self.quit_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 540))

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()
        self.spawner = Spawner(self.entity_group, ['apple','melon','lemon'], 'bomb')
        self.spawner.set_chances(0.4, 0.1)

        # Cięcie owoców/bomb
        self.lives = 3
        self.score = 0
        self.prev_pos = None
        self.current_pos = None

    def _setup_voice_control(self):
        phrases = [
            (["start", "run", "go", "begin"], self._start_game),
            (["menu", "back"], self._go_to_menu),
            (["restart", "retry", "play again"], self._restart_game),
            (["quit", "exit", "stop"], self._quit_game),
            (["mouse", "mouse control"], self._set_mouse_control), # sterowanie myszką
            (["hand", "hand control"], self._set_hand_control), # sterowanie ręką
            # TODO: sterowanie wzrokiem i inne
        ]

        self.voice_listener = VoskListener(
            phrases=phrases,
            use_grammar=True,
            grammar_confidence_threshold=0.7
        )
        self.voice_listener.start()

    def _setup_motion_control(self):
        self.hand_detector = HandsDetector(cam_url=constants.CAM_URL, smoothing=0.7, debug=True)

    def _start_game(self):
        if self.state == 0:
            self.state = 1

    def _go_to_menu(self):
        self.state = 0

    def _restart_game(self):
        if self.state == 2:
            self.score = 0
            self.lives = 3
            self.entity_group.empty()
            self.prev_pos = None
            self.current_pos = None
            self.state = 1

    def _quit_game(self):
        self.running = False

    def _set_mouse_control(self):
        self.set_control_mode(self.CONTROL_MOUSE)

    def _set_hand_control(self):
        self.set_control_mode(self.CONTROL_HAND)

    def _get_pointer_position(self):

        #Zwraca (x, y) w pikselach gry

        if self.control_mode == self.CONTROL_MOUSE:
            return pygame.mouse.get_pos()

        if self.control_mode == self.CONTROL_HAND:
            return self.hand_detector.get_screen_position(constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT)

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
                elif event.key == pygame.K_m:
                    self._set_mouse_control()
                elif event.key == pygame.K_h:
                    self._set_hand_control()
                # TODO: inne skróty klawiszowe do sterowania itp.

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

            for entity in self.entity_group:
                if entity.check_slice(self.prev_pos, self.current_pos):
                    if entity.entity_type == constants.FRUIT:
                        self.score += 1
                        x, y, vx, vy = entity.get_state()
                        entity.kill()

                        self.entity_group.add(Entity(None, constants.HALF, x, vx-3, int(-4+vy/2), y=y, half='left'))
                        self.entity_group.add(Entity(None, constants.HALF, x, vx+3, int(-4+vy/2), y=y, half='right'))

                    elif entity.entity_type == constants.BOMB:
                        self.lives -= 1
                        entity.kill()
                if self.lives <= 0:
                    self.state = 2

    def _draw(self):
        self.screen.fill(constants.BLACK)
        # 0 - menu  1 - gra  2 - game over

        if self.state == 0:
            for surf, rect in zip(self.line_surfs, self.line_rects):
                self.screen.blit(surf, rect)
            self.screen.blit(self.quit_surf, self.quit_rect)
            self.screen.blit(self.start_surf, self.start_rect)

            # pokaż aktualny tryb
            mode_text = f"Control: {self.control_mode.upper()}  (M=mouse, H=hand)"
            mode_surf = self.small_font.render(mode_text, True, (200, 200, 0))
            mode_rect = mode_surf.get_rect(
                center=(constants.SCREEN_WIDTH // 2, 580)
            )
            self.screen.blit(mode_surf, mode_rect)

        elif self.state == 1:
            self.entity_group.draw(self.screen)
            # if self.prev_pos and self.current_pos:
            #     pygame.draw.line(self.screen, (255, 255, 255), self.prev_pos, self.current_pos, 3)

            # rysowanie śladu ruchu
            if len(self.pointer_trail) >= 2:
                points = list(self.pointer_trail)
                for i in range(1, len(points)):
                    p1 = points[i - 1]
                    p2 = points[i]

                    intensity = int(255 * (i / len(points)))   # starsze ciemniejsze, nowsze jaśniejsze
                    width = max(1, int(6 * (i / len(points)))) # nowsze grubsze

                    color = (intensity, intensity, intensity)
                    pygame.draw.line(self.screen, color, p1, p2, width)

            self.score_surf = self.small_font.render(f"Score: {self.score}", True, constants.WHITE)
            self.score_rect = self.score_surf.get_rect(topright=(constants.SCREEN_WIDTH - 20, 20))
            self.screen.blit(self.score_surf, self.score_rect)

            self.lives_surf = self.small_font.render(f"Lives: {self.lives}", True, constants.WHITE)
            self.lives_rect = self.lives_surf.get_rect(topright=(constants.SCREEN_WIDTH - 20, 50))
            self.screen.blit(self.lives_surf, self.lives_rect)

            # tryb sterowania w rogu
            ctrl_surf = self.small_font.render(
                f"[{self.control_mode.upper()}]", True, (150, 150, 150)
            )
            self.screen.blit(ctrl_surf, (10, 10))
        
        elif self.state == 2:
            self.game_over_surf = self.font.render(f"GAME OVER  Score: {self.score}", True, constants.WHITE)
            self.game_over_rect = self.game_over_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 200))
            self.screen.blit(self.game_over_surf, self.game_over_rect)

            self.restart_surf = self.small_font.render("Press R to restart", True, constants.WHITE)
            self.restart_rect = self.restart_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 300))
            self.screen.blit(self.restart_surf, self.restart_rect)

        pygame.display.flip()