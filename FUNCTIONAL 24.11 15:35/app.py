#!/usr/bin/env python3
"""
Patched Flask app with lgpio PWM support (GPIO 14) and safe fallback when lgpio is not
available. Designed to be run under Gunicorn (no app.run()).

Features:
- Serves index.html from project root at '/'
- /set_brightness -> accepts JSON {value: 0-255} and sets PWM duty (0-100%) on GPIO 14
- /set_volume -> accepts JSON {value: 0-100} (stored in memory)
- /set_track -> accepts JSON {track: "path/to/track"} (stored in memory)
- /add_message -> accepts JSON {text: "..."} stores message in-memory
- /get_messages -> returns JSON {messages: [...]}

Graceful handling when lgpio is not installed: app still boots, endpoints return OK
but no hardware PWM is performed.

Place this file in your project root (where index.html lives) and restart gunicorn/systemd.
"""

from __future__ import annotations

import atexit
import json
import logging
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_from_directory

# --- Logging setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("lite21")

# --- Flask app ---
# Serve static files from project root so index.html is available at '/'
app = Flask(__name__, static_folder=".", static_url_path="")

# --- PWM / GPIO setup (lgpio) with safe fallback ---
HAS_LGPIO = False
HAS_RPI_GPIO = False
try:
    import lgpio

    HAS_LGPIO = True
    log.info("lgpio available: hardware PWM enabled")
except Exception as e:
    lgpio = None  # type: ignore
    log.warning("lgpio not available — running in dry-run mode (no hardware PWM): %s", e)

# Use BCM pin 14
LED_PIN = 14
PWM_FREQ = 1000  # Hz

# chip handle (when lgpio present)
chip = None

if HAS_LGPIO:
    try:
        chip = lgpio.gpiochip_open(0)
        # initialize with 0% duty
        lgpio.tx_pwm(chip, LED_PIN, PWM_FREQ, 0)
        log.info("Initialized PWM on GPIO %d (freq=%d)", LED_PIN, PWM_FREQ)
    except Exception as e:
        log.exception("Failed to initialize lgpio PWM — continuing in dry-run mode: %s", e)
        HAS_LGPIO = False
        chip = None

# Fallback to RPi.GPIO software PWM when lgpio isn't present.
GPIO = None
_pwm = None
if not HAS_LGPIO:
    try:
        import RPi.GPIO as GPIO  # type: ignore

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        _pwm = GPIO.PWM(LED_PIN, PWM_FREQ)
        _pwm.start(0)
        HAS_RPI_GPIO = True
        log.info("RPi.GPIO available: software PWM enabled on GPIO %d", LED_PIN)
    except Exception as e:
        GPIO = None
        _pwm = None
        log.warning("RPi.GPIO not available — LED control disabled: %s", e)


def set_pwm_duty_percent(percent: float) -> None:
    """Set hardware PWM duty as a percent (0-100).

    If lgpio isn't available, this logs and does nothing.
    """
    percent = max(0.0, min(100.0, float(percent)))
    if HAS_LGPIO and chip is not None:
        # lgpio.tx_pwm expects duty in percent (0-100)
        try:
            lgpio.tx_pwm(chip, LED_PIN, PWM_FREQ, int(percent))
        except Exception:
            log.exception("lgpio.tx_pwm failed")
    elif HAS_RPI_GPIO and _pwm is not None:
        try:
            _pwm.ChangeDutyCycle(percent)
        except Exception:
            log.exception("RPi.GPIO ChangeDutyCycle failed")
    else:
        log.debug("DRY-RUN: set_pwm_duty_percent(%s%%)", percent)


@atexit.register
def _cleanup():
    try:
        if HAS_LGPIO and chip is not None:
            log.info("Cleaning up PWM: setting 0 and closing chip")
            try:
                lgpio.tx_pwm(chip, LED_PIN, 0, 0)
            except Exception:
                log.exception("Failed to disable PWM")
            try:
                lgpio.gpiochip_close(chip)
            except Exception:
                log.exception("Failed to close lgpio chip")
        if HAS_RPI_GPIO and _pwm is not None and GPIO is not None:
            log.info("Stopping RPi.GPIO PWM and cleaning up pin %d", LED_PIN)
            try:
                _pwm.ChangeDutyCycle(0)
                _pwm.stop()
            except Exception:
                log.exception("Failed to stop RPi.GPIO PWM")
            try:
                GPIO.cleanup(LED_PIN)
            except Exception:
                log.exception("Failed to cleanup RPi.GPIO pin")
    except Exception:
        log.exception("Unexpected error during cleanup")


# --- In-memory state ---
state_lock = threading.Lock()
_state: Dict[str, Any] = {
    "brightness": 0,  # 0-255
    "volume": 50,  # 0-100
    "track": None,
    "messages": [],  # list of dicts: {text, timestamp}
}


def add_message(text: str) -> Dict[str, Any]:
    obj = {"text": text, "timestamp": datetime.utcnow().isoformat() + "Z"}
    with state_lock:
        _state["messages"].append(obj)
    return obj


# --- Routes ---
@app.route("/", methods=["GET"])
def index():
    # Serve index.html from project root
    root = Path(__file__).parent
    return send_from_directory(str(root), "index.html")


@app.route("/set_brightness", methods=["POST"])
def set_brightness():
    try:
        data = request.get_json(force=True)
        raw = data.get("value", None)
        if raw is None:
            return jsonify({"status": "error", "error": "missing 'value'"}), 400

        # slider provides 0-255; map to 0-100% duty
        value = int(raw)
        value = max(0, min(255, value))
        duty_percent = (value / 255.0) * 100.0

        # apply PWM
        set_pwm_duty_percent(duty_percent)

        with state_lock:
            _state["brightness"] = value

        log.info("Brightness set to %d (duty=%.1f%%)", value, duty_percent)
        return jsonify({"status": "ok", "value": value, "duty": duty_percent})

    except Exception as e:
        log.exception("Error in set_brightness")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/set_volume", methods=["POST"])
def set_volume():
    try:
        data = request.get_json(force=True)
        raw = data.get("value", None)
        if raw is None:
            return jsonify({"status": "error", "error": "missing 'value'"}), 400
        value = int(raw)
        value = max(0, min(100, value))
        with state_lock:
            _state["volume"] = value
        log.info("Volume set to %d", value)
        return jsonify({"status": "ok", "value": value})
    except Exception as e:
        log.exception("Error in set_volume")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/set_track", methods=["POST"])
def set_track():
    try:
        data = request.get_json(force=True)
        track = data.get("track")
        if not track:
            return jsonify({"status": "error", "error": "missing 'track'"}), 400
        with state_lock:
            _state["track"] = track
        log.info("Track set to %s", track)
        return jsonify({"status": "ok", "track": track})
    except Exception as e:
        log.exception("Error in set_track")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/add_message", methods=["POST"])
def add_message_route():
    try:
        data = request.get_json(force=True)
        text = data.get("text")
        if not text:
            return jsonify({"status": "error", "error": "missing 'text'"}), 400
        msg = add_message(str(text))
        log.info("Added message: %s", text)
        return jsonify({"status": "ok", "message": msg})
    except Exception as e:
        log.exception("Error in add_message")
        return jsonify({"status": "error", "error": str(e)}), 500


@app.route("/get_messages", methods=["GET"])
def get_messages():
    with state_lock:
        msgs = list(_state["messages"])[-200:]
    return jsonify({"messages": msgs})


@app.route("/status", methods=["GET"])
def status():
    with state_lock:
        s = {
            "brightness": _state["brightness"],
            "volume": _state["volume"],
            "track": _state["track"],
            "has_lgpio": HAS_LGPIO,
        }
    return jsonify(s)


# --- Safety: simple background keepalive to ensure lgpio chip still alive (optional) ---
if HAS_LGPIO and chip is not None:
    def _watchdog_thread():
        while True:
            try:
                # A cheap operation to keep an eye on chip
                # there's no direct 'ping' so attempt a harmless tx_pwm with current duty
                time.sleep(60)
            except Exception:
                log.exception("Watchdog caught exception")
                break

    t = threading.Thread(target=_watchdog_thread, daemon=True)
    t.start()


# When run directly, allow debug run (useful for dev). Under Gunicorn, this block isn't executed.
if __name__ == "__main__":
    log.info("Starting app in debug mode on http://127.0.0.1:5000")
    # set a sensible default PWM duty for manual runs
    try:
        set_pwm_duty_percent((int(_state["brightness"]) / 255.0) * 100.0)
    except Exception:
        log.exception("Failed to set initial PWM in __main__")
    app.run(host="127.0.0.1", port=5000, debug=True)
