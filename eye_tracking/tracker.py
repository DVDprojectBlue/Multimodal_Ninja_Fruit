from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

try:
	from eyeGestures import EyeGestures_v3
	from eyeGestures.utils import VideoCapture
except ImportError:  # pragma: no cover - handled at runtime
	EyeGestures_v3 = None
	VideoCapture = None


@dataclass(frozen=True)
class GazeSample:
	point: tuple[int, int]
	fixation: float
	saccades: bool
	algorithm: str


@dataclass(frozen=True)
class CalibrationSample:
	point: tuple[int, int]
	acceptance_radius: int


@dataclass(frozen=True)
class TrackerStepResult:
	gaze: GazeSample | None
	calibration: CalibrationSample | None
	debug_frame: np.ndarray | None


class EyeTracker:
	"""High-level reusable eye tracking service for pygame/game loops."""

	def __init__(
		self,
		camera_source: str,
		screen_width: int,
		screen_height: int,
		context: str = "game_context",
		fixation_threshold: float = 1.0,
	) -> None:
		if EyeGestures_v3 is None or VideoCapture is None:
			raise RuntimeError(
				"eyeGestures is not available. Install dependencies from requirements.txt"
			)

		self.camera_source = camera_source
		self.screen_width = screen_width
		self.screen_height = screen_height
		self.context = context

		self._gestures = EyeGestures_v3()
		self._gestures.setFixation(fixation_threshold)
		self._capture = VideoCapture(camera_source)

	@property
	def gestures(self):
		return self._gestures

	def step(self, calibrate: bool) -> TrackerStepResult | None:
		ret, frame = self._capture.read()
		if not ret or frame is None:
			return None

		try:
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		except cv2.error:
			return None
		frame = np.flip(frame, axis=1)

		try:
			event, calibration = self._gestures.step(
				frame,
				calibrate,
				self.screen_width,
				self.screen_height,
				context=self.context,
			)
		except (TypeError, IndexError, AttributeError, ValueError):
			# eyeGestures can fail on individual frames when landmarks are not detected.
			return None

		if event is None:
			return TrackerStepResult(gaze=None, calibration=None, debug_frame=None)

		gaze = GazeSample(
			point=(int(event.point[0]), int(event.point[1])),
			fixation=float(event.fixation),
			saccades=bool(event.saccades),
			algorithm=self._gestures.whichAlgorithm(context=self.context),
		)

		calibration_sample = None
		if calibration is not None:
			calibration_sample = CalibrationSample(
				point=(int(calibration.point[0]), int(calibration.point[1])),
				acceptance_radius=int(calibration.acceptance_radius),
			)

		return TrackerStepResult(
			gaze=gaze,
			calibration=calibration_sample,
			debug_frame=event.sub_frame,
		)

	def close(self) -> None:
		if self._capture is None:
			return

		release_fn = getattr(self._capture, "release", None)
		if callable(release_fn):
			release_fn()
