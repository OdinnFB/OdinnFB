from flask import Flask, request, jsonify, send_file

app = Flask(__name__, static_folder='.', static_url_path='')

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

if __name__ == '__main__':
    # Run on 0.0.0.0 so it's accessible from other devices on the network
    app.run(host='0.0.0.0', port=5000, debug=False)