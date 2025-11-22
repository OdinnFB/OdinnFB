from flask import Flask, request, jsonify, send_file
import json
import os
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')

MESSAGES_FILE = 'messages.json'

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
    with open(MESSAGES_FILE, 'w') as f:
        json.dump({'messages': messages}, f)

@app.route('/')
def serve_index():
    """Serve the main HTML page."""
    return send_file('index.html')

@app.route('/set_brightness', methods=['POST'])
def set_brightness():
    """Handle brightness control."""
    data = request.json
    brightness = data.get('value')
    print(f"Brightness set to: {brightness}")
    # TODO: Add your GPIO/hardware control here
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
    messages.append({
        'text': text,
        'timestamp': datetime.now().isoformat()
    })
    save_messages(messages)
    
    return jsonify({'status': 'ok', 'message_count': len(messages)})

@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """Clear all messages (optional admin endpoint)."""
    save_messages([])
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=False)
