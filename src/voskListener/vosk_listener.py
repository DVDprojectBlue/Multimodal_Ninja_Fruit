import json
import math
import queue
import sys
import threading
from array import array
from collections import deque
from pathlib import Path
from typing import Dict, Callable, Iterable, List, Optional, Tuple, Union
from urllib.error import URLError
from urllib.request import urlretrieve
import zipfile

import vosk

MODEL_CONFIG = {
    "pl": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip",
        "dirname": "vosk-model-small-pl-0.22",
    },
    "en": {
        "url": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
        "dirname": "vosk-model-small-en-us-0.15",
    },
}
DEFAULT_LANGUAGE = "en"

try:
    import sounddevice as sd
    _sounddevice_import_error = None
except Exception:  # pragma: no cover - graceful fallback if sounddevice missing
    sd = None
    _sounddevice_import_error = "failed to import sounddevice (install package and system audio backend, e.g. portaudio)"


class VoskListener:
    def __init__(
        self,
        phrases: Union[
            Dict[str, Callable[[], None]],
            Iterable[
                Union[
                    str,
                    Tuple[str, Callable[[], None]],
                    Tuple[Iterable[str], Callable[[], None]],
                ]
            ],
        ],
        callback: Callable[[], None] = None,
        model_path: str = "model",
        samplerate: Optional[int] = None,
        device: Optional[int] = None,
        default_device: bool = True,
        use_grammar: bool = True,
        confidence_threshold: float = 0.8,
        grammar_confidence_threshold: Optional[float] = 0.8,
        vad_threshold: float = 6000.0,
        pre_roll_seconds: float = 0.1,
        silence_seconds: float = 0.1,
        chunk_size: int = 1024,
        beam: float = 5.0,
        max_active: int = 3000,
        show_log: bool = True,
        language: str = DEFAULT_LANGUAGE,
    ):
        self.callbacks = self._build_callbacks(phrases, callback)
        self.model_path = self._resolve_model_path(model_path)
        self.samplerate = samplerate
        self.device = device
        self.default_device = default_device
        self.use_grammar = use_grammar
        self.confidence_threshold = confidence_threshold
        self.grammar_confidence_threshold = grammar_confidence_threshold
        self.vad_threshold = vad_threshold
        self.pre_roll_seconds = pre_roll_seconds
        self.silence_seconds = silence_seconds
        self.chunk_size = chunk_size
        self.beam = beam
        self.max_active = max_active
        self.show_log = show_log
        self.language = language.lower()

        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.last_error: Optional[Exception] = None
        self.error_message: Optional[str] = None

    @staticmethod
    def _resolve_model_path(model_path: str) -> str:
        path = Path(model_path)
        if path.is_absolute():
            return str(path)

        # Relative paths are always stored under this package directory.
        package_candidate = (Path(__file__).resolve().parent / path).resolve()
        return str(package_candidate)

    @staticmethod
    def _build_callbacks(
        phrases: Union[
            Dict[str, Callable[[], None]],
            Iterable[
                Union[
                    str,
                    Tuple[str, Callable[[], None]],
                    Tuple[Iterable[str], Callable[[], None]],
                ]
            ],
        ],
        callback: Callable[[], None] = None,
    ) -> Dict[str, Callable[[], None]]:
        if isinstance(phrases, dict):
            callbacks = phrases
        else:
            callbacks = {}
            for item in phrases:
                if isinstance(item, tuple):
                    phrase_or_phrases, cb = item
                    if isinstance(phrase_or_phrases, str):
                        callbacks[phrase_or_phrases] = cb
                    else:
                        for phrase in phrase_or_phrases:
                            if not isinstance(phrase, str):
                                raise TypeError("Phrase groups must contain only strings")
                            callbacks[phrase] = cb
                elif isinstance(item, str):
                    if callback is None:
                        raise ValueError("If `phrases` is an iterable of strings, you must provide a `callback` function")
                    callbacks[item] = callback
                else:
                    raise TypeError(
                        "Each item in `phrases` must be either a string, a (phrase, callback) tuple, or a ([phrase1, phrase2], callback) tuple"
                    )

        return {k.lower(): v for k, v in callbacks.items()}

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self.last_error = None
        self.error_message = None
        self._stop_event.clear()
        self._log("starting listener...")
        self._thread = threading.Thread(target=self.worker, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self._log("listener stopped")

    def worker(self) -> None:
        try:
            if sd is None:
                raise RuntimeError(f"sounddevice is required for microphone input: {_sounddevice_import_error}")

            # Always suppress verbose Vosk C++ API logs
            vosk.SetLogLevel(-1)

            self._log("starting: preparing speech model (first run may take longer)...")

            model_path = ensure_vosk_model(
                self.model_path,
                language=self.language,
                beam=self.beam,
                max_active=self.max_active,
                verbose=self.show_log,
            )
            self.model_path = model_path
            self._log(f"model ready: {self.model_path}")

            input_device = self._select_input_device(self.device, self.default_device)

            device_info = sd.query_devices(input_device)
            self._log(
                f"input device selected: id={input_device} | name={device_info.get('name', 'unknown')}"
            )

            if self.samplerate is None:
                effective_samplerate = int(device_info["default_samplerate"])
            else:
                effective_samplerate = int(self.samplerate)
            self._log(f"sample rate: {effective_samplerate} Hz")

            model = vosk.Model(model_path)
            rec = self._create_recognizer(model, effective_samplerate)
            audio_queue: "queue.Queue[bytes]" = queue.Queue()
            pre_roll_chunks = max(1, int((effective_samplerate * self.pre_roll_seconds) / self.chunk_size))
            silence_limit_chunks = max(1, int((effective_samplerate * self.silence_seconds) / self.chunk_size))
            pre_buffer: deque[bytes] = deque(maxlen=pre_roll_chunks)
            speech_active = False
            silence_chunks = 0
            active_chunks = 0

            def _audio_callback(indata, _frames, _time, status) -> None:
                if status:
                    # Keep going even if PortAudio reports transient status.
                    pass
                audio_queue.put(bytes(indata))

            with sd.RawInputStream(
                device=input_device,
                samplerate=effective_samplerate,
                blocksize=self.chunk_size,
                dtype="int16",
                channels=1,
                callback=_audio_callback,
            ) as stream:
                while not self._stop_event.is_set():
                    try:
                        data = audio_queue.get(timeout=0.2)
                    except queue.Empty:
                        continue

                    if not data:
                        continue

                    chunk_energy = self._rms_level(data)
                    voice_detected = chunk_energy >= self.vad_threshold

                    if not speech_active:
                        pre_buffer.append(data)
                        if not voice_detected:
                            continue

                        speech_active = True
                        silence_chunks = 0
                        active_chunks = 0
                        if self.show_log:
                            self._log(f"speech detected (energy: {chunk_energy:.0f})")

                        rec = self._create_recognizer(model, effective_samplerate)
                        for buffered_chunk in pre_buffer:
                            rec.AcceptWaveform(buffered_chunk)
                        pre_buffer.clear()

                    else:
                        is_kaldi_final = rec.AcceptWaveform(data)
                        if is_kaldi_final:
                            result_json = rec.Result()
                            self._handle_result(result_json, is_final=True)
                            speech_active = False
                            silence_chunks = 0
                            pre_buffer.clear()
                            rec = self._create_recognizer(model, effective_samplerate)
                            continue
                        else:
                            # handle partial results to show log if enabled
                            self._handle_result(rec.PartialResult(), is_final=False)

                    if speech_active:
                        active_chunks += 1
                        if self.show_log and active_chunks % (int((effective_samplerate * 10.0) / self.chunk_size)) == 0:
                            self._log(f"warning: speech active for 10s (energy: {chunk_energy:.0f}). Consider increasing vad_threshold > {self.vad_threshold:.0f}")

                    if voice_detected:
                        silence_chunks = 0
                    else:
                        silence_chunks += 1

                    if speech_active and silence_chunks >= silence_limit_chunks:
                        result_json = rec.FinalResult()
                        self._handle_result(result_json, is_final=True)
                        speech_active = False
                        silence_chunks = 0
                        pre_buffer.clear()
                        rec = self._create_recognizer(model, effective_samplerate)

                if speech_active:
                    result_json = rec.FinalResult()
                    self._handle_result(result_json, is_final=True)
        except Exception as exc:
            self.last_error = exc
            self.error_message = self._friendly_error_message(exc)
            self._log(self.error_message, is_error=True)

    def _log(self, message: str, is_error: bool = False) -> None:
        prefix = "[VoskListener][ERROR]" if is_error else "[VoskListener]"
        print(f"{prefix} {message}")

    @staticmethod
    def _friendly_error_message(exc: Exception) -> str:
        if isinstance(exc, ValueError) and "Unsupported language" in str(exc):
            return str(exc)
        if isinstance(exc, RuntimeError) and "No input audio device found" in str(exc):
            return "No microphone input device found. Connect/select a microphone and try again."
        if isinstance(exc, RuntimeError) and "sounddevice is required" in str(exc):
            return "Audio backend is not ready. Install `sounddevice` and PortAudio for your system."
        if isinstance(exc, URLError):
            return "Model download failed (network issue). Check internet connection and retry."
        if isinstance(exc, FileNotFoundError):
            return str(exc)
        return f"Listener failed: {exc}"

    def _create_recognizer(self, model: vosk.Model, sample_rate: int) -> vosk.KaldiRecognizer:
        grammar = self._build_grammar() if self.use_grammar else None
        if grammar:
            rec = vosk.KaldiRecognizer(model, float(sample_rate), json.dumps(grammar))
        else:
            rec = vosk.KaldiRecognizer(model, float(sample_rate))

        # Ask Vosk to include per-word details (including confidence when available).
        rec.SetWords(True)
        return rec

    def _build_grammar(self) -> List[str]:
        grammar = sorted({phrase.strip().lower() for phrase in self.callbacks.keys() if phrase.strip()})
        if not grammar:
            grammar = []
        grammar.append("[unk]")
        return grammar

    def _handle_result(self, result_json: str, is_final: bool) -> None:
        res = json.loads(result_json)
        text = (res.get("text") if is_final else res.get("partial", ""))
        text = (text or "").lower().strip()

        if self.show_log and text:
            if is_final:
                print(f"[VoskListener][Final] {text}")
            else:
                print(f"[VoskListener][Partial] {text}")

        if not is_final or not text:
            return

        words = res.get("result") or []

        # In grammar mode, accept only exact command text to avoid forcing
        # arbitrary speech into the nearest configured command.
        if self.use_grammar:
            cb = self.callbacks.get(text)
            if cb is None:
                if self.show_log:
                    self._log(f"ignored non-command utterance: '{text}'")
                return

            phrase_conf = self._phrase_confidence(words, text)
            if phrase_conf is None:
                phrase_conf = self._result_confidence(res, text)

            if self.grammar_confidence_threshold is not None:
                if phrase_conf is not None and phrase_conf < self.grammar_confidence_threshold:
                    if self.show_log:
                        self._log(
                            f"ignored '{text}' conf={phrase_conf:.3f} < {self.grammar_confidence_threshold:.2f}"
                        )
                    return

                if phrase_conf is None and self.show_log:
                    self._log(
                        f"no confidence for '{text}', accepting exact command without threshold"
                    )

            if self.show_log and (phrase_conf is None or phrase_conf <= 0.0):
                self._log(f"accepting exact command '{text}' conf=None/0.0 (grammar mode)")
            elif self.show_log:
                self._log(f"accepting exact command '{text}' conf={phrase_conf:.3f}")

            try:
                cb()
            except Exception as exc:
                self._log(f"callback for '{text}' failed: {exc}", is_error=True)
            return

        matches = self._collect_matches(text, words)
        if not matches:
            if self.show_log and text:
                self._log(f"no recognized commands in: '{text}'")
            return

        phrase, phrase_conf, cb = self._select_best_match(matches)

        # W grammar mode: zaakceptuj wynik nawet z conf=0.0 (Vosk zwraca 0.0 dla poprawnie rozpoznanych słów z gramatyki)
        # W non-grammar mode: wymagaj pewności powyżej threshold
        if not self.use_grammar and phrase_conf is not None and phrase_conf > 0.0 and phrase_conf < self.confidence_threshold:
            if self.show_log:
                self._log(f"ignored '{phrase}' conf={phrase_conf:.3f} < {self.confidence_threshold:.2f}")
            return

        if self.show_log and (phrase_conf is None or phrase_conf <= 0.0):
            self._log(f"accepting '{phrase}' conf=None/0.0 (grammar mode)")
        elif self.show_log:
            self._log(f"accepting '{phrase}' conf={phrase_conf:.3f}")

        try:
            cb()
        except Exception as exc:
            self._log(f"callback for '{phrase}' failed: {exc}", is_error=True)

    @staticmethod
    def _phrase_confidence(words: List[Dict[str, Union[str, float]]], phrase: str) -> Optional[float]:
        phrase_words = [part for part in phrase.lower().split() if part]
        if not phrase_words:
            return None

        if not words:
            return None

        recognized_words = [str(item.get("word", "")).lower() for item in words]
        confidences: List[Optional[float]] = []
        for item in words:
            conf_value = item.get("conf")
            confidences.append(float(conf_value) if conf_value is not None else None)

        span_length = len(phrase_words)
        for start in range(0, len(recognized_words) - span_length + 1):
            window = recognized_words[start : start + span_length]
            if window == phrase_words:
                span_confidences = confidences[start : start + span_length]
                available_confidences = [value for value in span_confidences if value is not None]
                if not available_confidences:
                    return None
                return sum(available_confidences) / len(available_confidences)

        if span_length == 1:
            for idx, word in enumerate(recognized_words):
                if word == phrase_words[0]:
                    return confidences[idx]

        return None

    def _collect_matches(
        self,
        text: str,
        words: List[Dict[str, Union[str, float]]],
    ) -> List[Tuple[str, Optional[float], Callable[[], None]]]:
        recognized_words = [str(item.get("word", "")).lower() for item in words if item.get("word")]
        if not recognized_words:
            recognized_words = [part for part in text.split() if part]

        matches: List[Tuple[str, Optional[float], Callable[[], None]]] = []
        for phrase, cb in self.callbacks.items():
            phrase_words = [part for part in phrase.split() if part]
            if not phrase_words:
                continue

            if not self._contains_phrase(recognized_words, phrase_words):
                continue

            matches.append((phrase, self._phrase_confidence(words, phrase), cb))

        return matches

    @staticmethod
    def _contains_phrase(recognized_words: List[str], phrase_words: List[str]) -> bool:
        span_length = len(phrase_words)
        if span_length == 0 or len(recognized_words) < span_length:
            return False

        for start in range(0, len(recognized_words) - span_length + 1):
            if recognized_words[start : start + span_length] == phrase_words:
                return True
        return False

    def _select_best_match(
        self,
        matches: List[Tuple[str, Optional[float], Callable[[], None]]],
    ) -> Tuple[str, Optional[float], Callable[[], None]]:
        def score(item: Tuple[str, Optional[float], Callable[[], None]]) -> Tuple[float, int]:
            phrase, conf, _cb = item
            confidence_score = float(conf) if conf is not None and conf > 0.0 else -1.0
            return (confidence_score, len(phrase.split()))

        return max(matches, key=score)

    @staticmethod
    def _result_confidence(res: Dict[str, object], text: str) -> Optional[float]:
        alternatives = res.get("alternatives")
        if not isinstance(alternatives, list):
            return None

        normalized_text = text.strip().lower()
        for alt in alternatives:
            if not isinstance(alt, dict):
                continue

            alt_text = str(alt.get("text", "")).strip().lower()
            if alt_text != normalized_text:
                continue

            conf = alt.get("confidence")
            if conf is None:
                conf = alt.get("conf")
            if conf is None:
                continue

            try:
                return float(conf)
            except (TypeError, ValueError):
                continue

        return None

    @staticmethod
    def _rms_level(audio_bytes: bytes) -> float:
        samples = array("h")
        samples.frombytes(audio_bytes)
        if not samples:
            return 0.0
        mean_square = sum(float(s) * float(s) for s in samples) / len(samples)
        return math.sqrt(mean_square)

    def _log_available_input_devices(self) -> None:
        try:
            devices = self.list_input_devices()
        except Exception as exc:
            self._log(f"could not list input devices: {exc}", is_error=True)
            return

        self._log("available input devices:")
        if not devices:
            self._log("  - none")
            return

        for dev in devices:
            self._log(
                f"  - id={dev['index']} | name={dev['name']} | in={dev['max_input_channels']} | sr={int(dev['default_samplerate'])}"
            )

    @staticmethod
    def _select_input_device(requested_device: Optional[int], default_device: bool = True) -> int:
        if requested_device is not None:
            return requested_device

        if not default_device:
            return VoskListener._prompt_for_input_device()

        try:
            default_input, _ = sd.default.device
            if default_input is not None and int(default_input) >= 0:
                info = sd.query_devices(int(default_input))
                if int(info.get("max_input_channels", 0)) > 0:
                    return int(default_input)
        except Exception:
            pass

        devices = sd.query_devices()
        for idx, info in enumerate(devices):
            if int(info.get("max_input_channels", 0)) > 0:
                return idx

        raise RuntimeError("No input audio device found. Connect a microphone or set `device=<index>`.")

    @staticmethod
    def _prompt_for_input_device() -> int:
        devices = VoskListener.list_input_devices()
        if not devices:
            raise RuntimeError("No input audio device found. Connect a microphone and try again.")

        if not sys.stdin.isatty():
            raise RuntimeError("default_device=False requires interactive terminal. Pass `device=<index>` or set default_device=True.")

        print("[VoskListener] available input devices:")
        for dev in devices:
            print(
                f"[VoskListener]   - id={dev['index']} | name={dev['name']} | in={dev['max_input_channels']} | sr={int(dev['default_samplerate'])}"
            )

        valid_indexes = {int(dev["index"]) for dev in devices}
        while True:
            selected = input("[VoskListener] choose input device id: ").strip()
            if not selected:
                print("[VoskListener] please enter a device id")
                continue
            try:
                selected_idx = int(selected)
            except ValueError:
                print("[VoskListener] invalid value, enter numeric device id")
                continue
            if selected_idx not in valid_indexes:
                print("[VoskListener] id not in available list, try again")
                continue
            return selected_idx

    @staticmethod
    def list_input_devices() -> List[Dict[str, Union[int, str, float]]]:
        if sd is None:
            raise RuntimeError(f"sounddevice is required for microphone input: {_sounddevice_import_error}")

        result: List[Dict[str, Union[int, str, float]]] = []
        for idx, info in enumerate(sd.query_devices()):
            if int(info.get("max_input_channels", 0)) > 0:
                result.append(
                    {
                        "index": idx,
                        "name": str(info.get("name", "unknown")),
                        "max_input_channels": int(info.get("max_input_channels", 0)),
                        "default_samplerate": float(info.get("default_samplerate", 0.0)),
                    }
                )
        return result

    @staticmethod
    def microphone_signal_level(duration_seconds: float = 1.0, device: Optional[int] = None) -> float:
        if sd is None:
            raise RuntimeError(f"sounddevice is required for microphone input: {_sounddevice_import_error}")

        input_device = VoskListener._select_input_device(device, True)
        device_info = sd.query_devices(input_device)
        samplerate = int(device_info["default_samplerate"])
        frames = max(1, int(samplerate * duration_seconds))

        with sd.RawInputStream(
            device=input_device,
            samplerate=samplerate,
            blocksize=frames,
            dtype="int16",
            channels=1,
        ) as stream:
            data, overflow = stream.read(frames)
            if overflow:
                raise RuntimeError("Audio buffer overflow during microphone test")

        samples = array("h")
        samples.frombytes(bytes(data))
        if not samples:
            return 0.0

        mean_square = sum(float(s) * float(s) for s in samples) / len(samples)
        return mean_square ** 0.5


def _zip_top_level_folder(zip_path: Path) -> Optional[str]:
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        for member in zip_ref.infolist():
            name = member.filename.strip("/")
            if not name:
                continue
            top = name.split("/", 1)[0]
            if top and top != "__MACOSX":
                return top
    return None


def ensure_vosk_model(
    model_path: str,
    language: str = DEFAULT_LANGUAGE,
    beam: float = 13.0,
    max_active: int = 3000,
    verbose: bool = False,
) -> str:
    language = language.lower()
    if language not in MODEL_CONFIG:
        raise ValueError(f"Unsupported language: {language}. Supported: {', '.join(MODEL_CONFIG.keys())}")
    
    config = MODEL_CONFIG[language]
    model_url = config["url"]
    model_dirname = config["dirname"]
    
    target_path = Path(model_path).resolve()
    if target_path.exists():
        return str(target_path)

    base_dir = target_path.parent
    base_dir.mkdir(parents=True, exist_ok=True)

    archive_name = f"{model_dirname}.zip"
    archive_path = base_dir / archive_name
    if not archive_path.exists():
        if verbose:
            print(f"[VoskListener] Model not found at {target_path}. Downloading {language.upper()} model from {model_url}...")
        urlretrieve(model_url, archive_path)
        if verbose:
            print(f"[VoskListener] Downloaded model archive to {archive_path}")
    elif verbose:
        print(f"[VoskListener] Using existing model archive: {archive_path}")

    extracted_dir = base_dir / model_dirname
    if not extracted_dir.exists():
        if verbose:
            print(f"[VoskListener] Extracting model archive to {base_dir}...")
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            zip_ref.extractall(base_dir)

    if not extracted_dir.exists():
        top_folder = _zip_top_level_folder(archive_path)
        if top_folder is not None:
            candidate = base_dir / top_folder
            if candidate.exists():
                extracted_dir = candidate

    if not extracted_dir.exists():
        raise FileNotFoundError(
            f"Model extraction finished, but no model folder was found. Expected: {extracted_dir}"
        )

    _write_model_config(extracted_dir, beam=beam, max_active=max_active)

    if verbose:
        print(f"[VoskListener] Using model directory: {extracted_dir}")
    return str(extracted_dir)


def _write_model_config(model_dir: Path, beam: float, max_active: int) -> None:
    conf_dir = model_dir / "conf"
    conf_dir.mkdir(parents=True, exist_ok=True)
    conf_path = conf_dir / "model.conf"

    lines: List[str] = []
    if conf_path.exists():
        lines = conf_path.read_text(encoding="utf-8").splitlines()

    def _replace_or_add(prefix: str, value: str) -> None:
        nonlocal lines
        for index, line in enumerate(lines):
            if line.startswith(prefix):
                lines[index] = f"{prefix}{value}"
                return
        lines.append(f"{prefix}{value}")

    _replace_or_add("--beam=", str(beam))
    _replace_or_add("--max-active=", str(max_active))
    conf_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

