from flask import Flask, request, jsonify, send_file
import json
import os
from datetime import datetime
import RPi.GPIO as GPIO

# --- GPIO SETUP ---
LED_PIN = 18

GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

# PWM at 1000 Hz
pwm = GPIO.PWM(LED_PIN, 1000)
pwm.start(0)   # Start with LED off

app = Flask(__name__, static_folder='.', static_url_path='')

# Store messages.json next to this script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MESSAGES_FILE = os.path.join(BASE_DIR, 'messages.json')

def load_messages():
    """Load messages from file."""
    if os.path.exists(MESSAGES_FILE):
        try:
            with open(MESSAGES_FILE, 'r') as f:
                data = json.load(f)
                return data.get('messages', [])
        except:
            return []
    return []

def save_messages(messages):
    """Save messages to file."""
    try:
        with open(MESSAGES_FILE, 'w') as f:
            json.dump({'messages': messages}, f)
        return True
    except Exception as e:
        print(f"Error saving messages: {e}")
        return False

@app.route('/')
def serve_index():
    """Serve the main HTML page."""
    response = send_file('index.html')
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/set_brightness', methods=['POST'])
def set_brightness():
    """Handle brightness control."""
    data = request.json
    value = int(data.get('value', 0))

    # Convert 0–255 slider → 0–100 PWM duty cycle
    duty = max(0, min(100, (value / 255) * 100))

    pwm.ChangeDutyCycle(duty)

    print(f"Brightness set to {value} (duty {duty:.1f}%)")

    return jsonify({'status': 'ok'})

@app.route('/set_volume', methods=['POST'])
def set_volume():
    """Handle volume control."""
    data = request.json
    volume = data.get('value')
    print(f"Volume set to: {volume}")
    # TODO: Add your audio volume control here
    return jsonify({'status': 'ok'})

@app.route('/set_track', methods=['POST'])
def set_track():
    """Handle track selection."""
    data = request.json
    track = data.get('track')
    print(f"Track set to: {track}")
    # TODO: Add your audio playback control here
    return jsonify({'status': 'ok'})

@app.route('/get_messages', methods=['GET'])
def get_messages():
    """Retrieve all stored messages."""
    messages = load_messages()
    return jsonify({'messages': messages})

@app.route('/add_message', methods=['POST'])
def add_message():
    """Add a new message and store it."""
    data = request.json
    text = data.get('text', '').strip()
    
    if not text or len(text) > 100:
        return jsonify({'status': 'error', 'message': 'Invalid message'}), 400
    
    messages = load_messages()
    msg = {
        'text': text,
        'timestamp': datetime.now().isoformat()
    }
    messages.append(msg)
    ok = save_messages(messages)
    if not ok:
        return jsonify({'status': 'error', 'message': 'Failed to save'}), 500
    
    return jsonify({'status': 'ok', 'message': msg})

if __name__ == '__main__':
    # Ensure messages file exists
    if not os.path.exists(MESSAGES_FILE):
        save_messages([])
        print(f"Created messages file at {MESSAGES_FILE}")
    
    app.run(host='0.0.0.0', port=5000, debug=False)

import atexit

@atexit.register
def cleanup():
    pwm.stop()
    GPIO.cleanup()