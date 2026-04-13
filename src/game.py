import pygame
import src.constants as constants

from src.entities import Spawner, Entity
from src.voskListener import VoskListener

class NinjaFruitGame:
    def __init__(self, title="Multimodal Ninja Fruit"):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = 0 # 0 - menu, 1 -gra
        self.voice_listener = None
        
        self._prepare_assets()
        self._setup_voice_control()

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
        self.prev_mouse_pos = None
        self.current_mouse_pos = None

    def _setup_voice_control(self):
        phrases = [
            (["start", "run", "go", "begin"], self._start_game),
            (["menu", "back"], self._go_to_menu),
            (["restart", "retry", "play again"], self._restart_game),
            (["quit", "exit", "stop"], self._quit_game),
        ]

        self.voice_listener = VoskListener(
            phrases=phrases,
            use_grammar=True,
            grammar_confidence_threshold=0.7
        )
        self.voice_listener.start()

    def _start_game(self):
        if self.state == 0:
            self.state = 1

    def _go_to_menu(self):
        self.state = 0

    def _restart_game(self):
        if self.state == 2:
            self.score = 0
            self.lives = 3
            self.state = 1

    def _quit_game(self):
        self.running = False

    def run(self):
        while self.running:
            self._handle_events()
            self._update()
            self._draw()
            self.clock.tick(constants.FPS)

        if self.voice_listener is not None:
            self.voice_listener.stop()
        pygame.quit()

    def _handle_events(self):
        # Obsługa eventów
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._quit_game()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self._quit_game()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_s and self.state == 0:
                self._start_game()
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_r and self.state == 2:
                self._restart_game()

    def _update(self):
        # Tu można robić logikę gry
        if self.state == 1:
            self.spawner.update()
            self.entity_group.update()

            self.prev_mouse_pos = self.current_mouse_pos
            self.current_mouse_pos = pygame.mouse.get_pos()

            for entity in self.entity_group:
                if entity.check_slice(self.prev_mouse_pos, self.current_mouse_pos):
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
            self.game_over_rect = self.game_over_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 200))
            self.screen.blit(self.game_over_surf, self.game_over_rect)

            self.restart_surf = self.small_font.render("Press R to restart", True, constants.WHITE)
            self.restart_rect = self.restart_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 300))
            self.screen.blit(self.restart_surf, self.restart_rect)

        pygame.display.flip()