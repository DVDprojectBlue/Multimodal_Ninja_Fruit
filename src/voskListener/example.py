import time

from voskListener import VoskListener


def cb_menu() -> None:
    print("[CALLBACK menu]")


def cb_start() -> None:
    print("[CALLBACK start]")


def cb_stop() -> None:
    print("[CALLBACK stop]")

def cb_jeden() -> None:
    print("[CALLBACK jeden]") 


if __name__ == "__main__":
    phrases = [
        (["menu", "options", "settings"], cb_menu),
        (["start", "run", "go", "begin"], cb_start),
        (["stop", "end", "and"], cb_stop),
        (["one", "first"], cb_jeden),
    ]

    listener = VoskListener(
        phrases,
        model_path="model",
        show_log=True,
        language="en",
        default_device=True,
        # === Parametry VAD (Voice Activity Detection) ===
        vad_threshold=6000.0,      # energia RMS do wykrycia mowy (wyżej = mniej czułe na szum)
        silence_seconds=0.1,        # minimalny czas ciszy do zatwierdzenia (szybka odpowiedź)
        pre_roll_seconds=0.1,      # ile audio przed wykryciem mowy zabuforować
        # === Parametry pewności ===
        confidence_threshold=0.6,   # minimalny score aby zatwierdzić komendę (bez grammar mode!)
        grammar_confidence_threshold=0.9,  # minimalny score aby zatwierdzić komendę w grammar mode
        use_grammar=True,          # użyj confidence score zamiast ograniczenia słownika
        # === Parametry wydajności modelu ===
        beam=5.0,                  # szerokość wiązki (wyżej = dokładniej ale wolniej)
        max_active=3000,            # max aktywnych stanów (wyżej = dokładniej ale wolniej)
    )
    listener.start()

    listener_error_reported = False
    try:
        while True:
            time.sleep(0.2)
            if listener.last_error is not None and not listener_error_reported:
                print(f"[App] listener unavailable: {listener.error_message or listener.last_error}")
                print("[App] app keeps running; you can fix audio/model and restart listener")
                listener_error_reported = True
            

    except KeyboardInterrupt:
        listener.stop()
        print("Stopped")
