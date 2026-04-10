import pygame
import src.constants as constants
from src.base_game_mode import BaseGameMode
from eye_tracking.eye_tracking_game_mode import EyeTrackingGameMode


class NinjaFruitGame:
    MENU_STATE = 0
    MODE_STATE = 1

    def __init__(self, title="Multimodal Ninja Fruit"):
        pygame.init()
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.running = True
        self.state = self.MENU_STATE

        self.mode = None
        self.menu_notice = ""

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

        self.start_surf = self.small_font.render("Press S for base mode", True, constants.WHITE)
        self.start_rect = self.start_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 470))
        self.eye_start_surf = self.small_font.render("Press E for eye tracking mode", True, constants.WHITE)
        self.eye_start_rect = self.eye_start_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 510))
        self.menu_mode_surf = self.small_font.render("Press M to return to menu", True, constants.WHITE)
        self.quit_surf = self.small_font.render("Press ESC to quit", True, constants.WHITE)
        self.quit_rect = self.quit_surf.get_rect(center=(constants.SCREEN_WIDTH // 2, 590))

    def run(self):
        while self.running:
            self._handle_events()

            if self.state == self.MODE_STATE and self.mode:
                self.mode.update()

            self._draw()
            self.clock.tick(constants.FPS)

        self._shutdown_mode()
        pygame.quit()

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
            elif self.state == self.MENU_STATE:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_s:
                    BaseGameMode.start(self)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_e:
                    EyeTrackingGameMode.start(self)
            elif self.mode:
                action = self.mode.handle_event(event)
                if action == "menu":
                    self._shutdown_mode()
                    self._set_windowed()
                    self.state = self.MENU_STATE

    def _shutdown_mode(self):
        if self.mode:
            self.mode.shutdown()
            self.mode = None

    def _set_windowed(self):
        self.screen = pygame.display.set_mode((constants.SCREEN_WIDTH, constants.SCREEN_HEIGHT))

    def _set_fullscreen(self):
        self.screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

    def _draw(self):
        self.screen.fill(constants.BLACK)

        if self.state == self.MENU_STATE:
            for surf, rect in zip(self.line_surfs, self.line_rects):
                self.screen.blit(surf, rect)
            self.screen.blit(self.eye_start_surf, self.eye_start_rect)
            self.screen.blit(self.quit_surf, self.quit_rect)
            self.screen.blit(self.start_surf, self.start_rect)

            if self.menu_notice:
                notice = self.small_font.render(self.menu_notice, True, (255, 120, 120))
                notice_rect = notice.get_rect(center=(constants.SCREEN_WIDTH // 2, 420))
                self.screen.blit(notice, notice_rect)
        elif self.state == self.MODE_STATE and self.mode:
            self.mode.draw(self.screen)
            menu_mode_rect = self.menu_mode_surf.get_rect(
                center=(self.screen.get_width() // 2, self.screen.get_height() - 40)
            )
            self.screen.blit(self.menu_mode_surf, menu_mode_rect)

        pygame.display.flip()