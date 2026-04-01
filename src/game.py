import pygame
import src.constants as constants
from src.entities import Entity, Spawner

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
        
        lines = ["Ninja Fruit", "In Progress..."]
        self.line_surfs = [self.font.render(line, True, constants.WHITE) for line in lines]
        
        self.line_rects = []
        current_y = 120
        for surf in self.line_surfs:
            rect = surf.get_rect(center=(constants.SCREEN_WIDTH // 2, current_y))
            self.line_rects.append(rect)
            current_y += surf.get_height()

        # Napisy menu
        self.start_surf = self.small_font.render("Press S to start", True, constants.WHITE)
        self.start_rect = self.start_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 500))
        self.quit_surf = self.small_font.render("Press ESC to quit", True, constants.WHITE)
        self.quit_rect = self.quit_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 540))

        # Utworzenie obiektów do zarządzania owocami i bombami
        self.entity_group = pygame.sprite.Group()
        self.spawner = Spawner(self.entity_group, ['apple','melon','lemon'], 'bomb')
        self.spawner.set_chances(0.4, 0.1)

    def run(self):
        while self.running:
            self._handle_events()

            if self.state == 1:
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
        
        #Kolizja myszki z owocami/bombami

    def _update(self):
        # Tu można robić logikę gry
        self.spawner.update()
        self.entity_group.update()

    def _draw(self):
        self.screen.fill(constants.BLACK)

        if self.state == 0:
            for surf, rect in zip(self.line_surfs, self.line_rects):
                self.screen.blit(surf, rect)
            self.screen.blit(self.quit_surf, self.quit_rect)
            self.screen.blit(self.start_surf, self.start_rect)
        elif self.state == 1:
            self.entity_group.draw(self.screen)

        pygame.display.flip()