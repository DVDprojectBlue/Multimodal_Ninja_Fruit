from __future__ import annotations

from dataclasses import dataclass
import threading
import time

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
		self._state_lock = threading.Lock()
		self._latest_result: TrackerStepResult | None = None
		self._calibrate_requested = False
		self._running = False
		self._worker_thread: threading.Thread | None = None

	@property
	def gestures(self):
		return self._gestures

	def upload_calibration_map(self, calibration_map: np.ndarray) -> None:
		with self._state_lock:
			self._gestures.uploadCalibrationMap(calibration_map, context=self.context)

	def set_calibrate(self, calibrate: bool) -> None:
		with self._state_lock:
			self._calibrate_requested = calibrate

	def get_latest_result(self) -> TrackerStepResult | None:
		with self._state_lock:
			return self._latest_result

	def start_background(self) -> None:
		if self._running:
			return

		self._running = True
		self._worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
		self._worker_thread.start()

	def _worker_loop(self) -> None:
		while self._running:
			with self._state_lock:
				calibrate = self._calibrate_requested

			result = self._step_impl(calibrate)

			if result is not None:
				with self._state_lock:
					self._latest_result = result

			# Small backoff to reduce CPU spinning when camera drops frames.
			if result is None:
				time.sleep(0.001)

	def step(self, calibrate: bool) -> TrackerStepResult | None:
		return self._step_impl(calibrate)

	def _step_impl(self, calibrate: bool) -> TrackerStepResult | None:
		ret, frame = self._capture.read()
		if not ret or frame is None:
			return None

		try:
			frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
		except cv2.error:
			return None
		frame = np.flip(frame, axis=1)

		try:
			with self._state_lock:
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

		with self._state_lock:
			algorithm = self._gestures.whichAlgorithm(context=self.context)

		gaze = GazeSample(
			point=(int(event.point[0]), int(event.point[1])),
			fixation=float(event.fixation),
			saccades=bool(event.saccades),
			algorithm=algorithm,
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
		self._running = False
		if self._worker_thread is not None and self._worker_thread.is_alive():
			self._worker_thread.join(timeout=1.0)
		self._worker_thread = None

		if self._capture is None:
			return

		release_fn = getattr(self._capture, "release", None)
		if callable(release_fn):
			release_fn()
