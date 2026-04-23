from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pygame
import src.constants as constants
from src.eye_tracking.tracker import EyeTracker


@dataclass(frozen=True)
class CalibrationRenderData:
    point: tuple[int, int] | None
    acceptance_radius: int
    progress: int
    total: int
    is_complete: bool


class EyeTrackingGameMode:
    """Standalone eye tracking adapter for the existing NinjaFruitGame loop."""

    CALIBRATION_GRID_STEP = 0.2

    def __init__(self, screen_width, screen_height):
        config = self._load_config()
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.eye_tracker = None
        self._started = False
        self._error_message = ""

        self.camera_source = config["camera_source"]
        self.context = config["eye_context"]
        self.fixation_threshold = config["fixation_threshold"]
        self.calibration_points = config["calibration_points"]

        self.last_tracker_result = None
        self.last_calibration_render = CalibrationRenderData(
            point=None,
            acceptance_radius=0,
            progress=0,
            total=0,
            is_complete=False,
        )
        self._fps_font = pygame.font.Font(None, 28)
        self._fps_value = 0.0
        self._fps_frame_count = 0
        self._fps_last_sample_ms = pygame.time.get_ticks()
        self._calibration_progress = 0
        self._calibration_total = 0
        self._previous_calibration_point = (-1, -1)

        self.calibration_active = False

    def start(self) -> bool:
        if self._started:
            return True

        try:
            self.eye_tracker = EyeTracker(
                camera_source=self.camera_source,
                screen_width=self.screen_width,
                screen_height=self.screen_height,
                context=self.context,
                fixation_threshold=self.fixation_threshold,
            )
            self.eye_tracker.start_background()
            self._start_calibration()
            self._error_message = ""
            self._started = True
            return True
        except Exception as exc:
            self._error_message = str(exc)
            if self.eye_tracker is not None:
                self.eye_tracker.close()
            self.eye_tracker = None
            self._started = False
            return False

    def get_error(self) -> str:
        return self._error_message

    def is_calibrating(self) -> bool:
        return self._started and self.calibration_active

    def _load_config(self) -> dict:
        config_path = Path(__file__).with_name("config.yaml")
        if not config_path.exists():
            raise RuntimeError(f"Missing eye tracking config file: {config_path}")

        data: dict[str, str] = {}
        for line in config_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()

        required = ["camera_source", "eye_context", "fixation_threshold", "calibration_points"]
        missing = [key for key in required if key not in data]
        if missing:
            raise RuntimeError(f"Missing eye tracking config keys: {', '.join(missing)}")

        return {
            "camera_source": data["camera_source"],
            "eye_context": data["eye_context"],
            "fixation_threshold": float(data["fixation_threshold"]),
            "calibration_points": int(data["calibration_points"]),
        }

    def _start_calibration(self):
        if self.eye_tracker is None:
            return

        calibration_map = self._build_calibration_map()
        np.random.shuffle(calibration_map)
        if 0 < self.calibration_points < len(calibration_map):
            calibration_map = calibration_map[: self.calibration_points]

        self.eye_tracker.upload_calibration_map(calibration_map)

        self._calibration_progress = 0
        self._calibration_total = len(calibration_map)
        self._previous_calibration_point = (-1, -1)
        self.last_calibration_render = CalibrationRenderData(
            point=None,
            acceptance_radius=0,
            progress=0,
            total=self._calibration_total,
            is_complete=False,
        )
        self.calibration_active = self._calibration_total > 0
        self.eye_tracker.set_calibrate(self.calibration_active)

    def _build_calibration_map(self) -> np.ndarray:
        x = np.arange(0, 1.0 + self.CALIBRATION_GRID_STEP, self.CALIBRATION_GRID_STEP)
        y = np.arange(0, 1.0 + self.CALIBRATION_GRID_STEP, self.CALIBRATION_GRID_STEP)
        xx, yy = np.meshgrid(x, y)
        return np.column_stack([xx.ravel(), yy.ravel()])

    def reset_session(self):
        if self._started and self.eye_tracker is not None:
            self._start_calibration()

    def get_control_position(self):
        if not self._started:
            return None

        if self.calibration_active:
            return None

        if self.last_tracker_result and self.last_tracker_result.gaze:
            return self.last_tracker_result.gaze.point

        return None

    def update(self):
        if not self._started or self.eye_tracker is None:
            return

        self.eye_tracker.set_calibrate(self.calibration_active)
        tracker_result = self.eye_tracker.get_latest_result()
        if tracker_result is None:
            return

        if self.calibration_active:
            self.last_tracker_result = tracker_result

            if tracker_result.calibration:
                calibration_point = tracker_result.calibration.point
                if calibration_point != self._previous_calibration_point:
                    self._calibration_progress += 1
                    self._previous_calibration_point = calibration_point

                calibration_complete = self._calibration_progress >= self._calibration_total
                self.last_calibration_render = CalibrationRenderData(
                    point=calibration_point,
                    acceptance_radius=tracker_result.calibration.acceptance_radius,
                    progress=self._calibration_progress,
                    total=self._calibration_total,
                    is_complete=calibration_complete,
                )

                if calibration_complete:
                    self.calibration_active = False
                    self.eye_tracker.set_calibrate(False)
            return

        self.last_tracker_result = tracker_result

    def draw_overlay(self, screen):
        if not self._started:
            return

        if self.calibration_active:
            self._draw_calibration_state(screen)

        self._draw_gaze_cursor(screen)
        self._draw_fps_counter(screen)

    def _draw_fps_counter(self, screen):
        self._fps_frame_count += 1
        now_ms = pygame.time.get_ticks()
        elapsed_ms = now_ms - self._fps_last_sample_ms

        if elapsed_ms >= 250:
            self._fps_value = (self._fps_frame_count * 1000.0) / elapsed_ms
            self._fps_frame_count = 0
            self._fps_last_sample_ms = now_ms

        fps_text = self._fps_font.render(f"FPS: {self._fps_value:.1f}", True, constants.WHITE)
        screen.blit(fps_text, (12, 10))

    def _draw_gaze_cursor(self, screen):
        if self.last_tracker_result and self.last_tracker_result.gaze:
            gaze_point = self.last_tracker_result.gaze.point
            pygame.draw.circle(screen, (0, 255, 0), gaze_point, 12, 2)

    def _draw_calibration_state(self, screen):
        if self.last_calibration_render.point:
            # Filled acceptance circle.
            pygame.draw.circle(
                screen,
                (100, 0, 255),
                self.last_calibration_render.point,
                self.last_calibration_render.acceptance_radius,
            )
            # Marker in the center so the user has a precise fixation target.
            pygame.draw.circle(
                screen,
                constants.WHITE,
                self.last_calibration_render.point,
                5,
            )
            pygame.draw.circle(
                screen,
                constants.BLACK,
                self.last_calibration_render.point,
                2,
            )

        font = pygame.font.Font(None, 36)
        progress_text = font.render(
            f"Calibrating: {self.last_calibration_render.progress}/{self.last_calibration_render.total}",
            True,
            constants.WHITE,
        )
        progress_rect = progress_text.get_rect(center=(self.screen_width // 2, 60))
        screen.blit(progress_text, progress_rect)

    def shutdown(self):
        if self.eye_tracker is not None:
            self.eye_tracker.close()
        self.eye_tracker = None
        self._started = False
