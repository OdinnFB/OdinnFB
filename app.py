from flask import Flask, request, jsonify, send_file
from datetime import datetime

app = Flask(__name__, static_folder='.', static_url_path='')

# In-memory storage for messages
# This list will be cleared when the server restarts
MESSAGES = []

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
    return jsonify({'messages': MESSAGES})

@app.route('/add_message', methods=['POST'])
def add_message():
    """Add a new message and store it in memory."""
    data = request.json
    text = data.get('text', '').strip()
    
    if not text or len(text) > 100:
        return jsonify({'status': 'error', 'message': 'Invalid message'}), 400
    
    msg = {
        'text': text,
        'timestamp': datetime.now().isoformat()
    }
    MESSAGES.append(msg)
    
    return jsonify({'status': 'ok', 'message': msg, 'message_count': len(MESSAGES)})

@app.route('/clear_messages', methods=['POST'])
def clear_messages():
    """Clear all messages (optional admin endpoint)."""
    global MESSAGES
    MESSAGES = []
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=False)
