from flask import Flask, render_template, Response, jsonify
from camera_manager import CameraManager

app = Flask(__name__)

camera_pi = CameraManager()
camera_pi.setup_camera()
camera_pi.setup_webcam()


@app.route('/')
def index():
    """Serve the main HTML template page."""
    return render_template('index.html')


def preview_frame(camera):
    """
    Generate a preview frame from the camera.

    Args:
    - camera: The camera instance to fetch the frame from.

    Yields:
    - JPEG formatted frame.
    """
    while True:
        frame = camera.preview()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def preview_webcam_frame(camera):
    """
    Generate a preview frame from the webcam with timestamp.

    Args:
    - camera: The camera instance to fetch the frame and timestamp from.

    Yields:
    - JPEG formatted frame followed by its timestamp.
    """
    while True:
        frame, ts = camera.get_webcam_frame()
        timestamp_bytes = str(ts).encode('utf-8')
        delimiter = b'---timestamp---'
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + delimiter + timestamp_bytes + b'\r\n--frame\r\n'


def generate_frame(camera):
    """
    Generate a video frame from the camera with timestamp.

    Args:
    - camera: The camera instance to fetch the frame and timestamp from.

    Yields:
    - JPEG formatted frame followed by its timestamp.
    """
    while True:
        frame, ts = camera.get_frame()
        timestamp_bytes = str(ts).encode('utf-8')
        delimiter = b'---timestamp---'
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + delimiter + timestamp_bytes + b'\r\n--frame\r\n'


@app.route('/preview')
def preview():
    """Video preview route returning a single frame."""
    return Response(preview_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed')
def video_feed():
    """Video streaming route to provide live video feed."""
    return Response(generate_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/preview_webcam')
def preview_webcam():
    """
    Video streaming route for the webcam.
    This should be placed in the src attribute of an img tag.
    """
    if not camera_pi.enable_webcam:
        return Response("Webcam not enabled", status=404)

    return Response(preview_webcam_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start')
def start():
    """Route to start the camera."""
    if camera_pi.picam2_running:
        return jsonify({"message": "Camera already running"})
    camera_pi.setup_camera()
    return jsonify({"message": "Camera started"})


@app.route('/stop')
def stop():
    """Route to stop the camera."""
    if not camera_pi.picam2_running:
        return jsonify({"message": "Camera already stopped"})
    camera_pi.stop()
    return jsonify({"message": "Camera stopped"})


@app.route('/reboot')
def reboot():
    """Route to reboot the camera."""
    if camera_pi.picam2_rebooting:
        return jsonify({"message": "Camera is currently rebooting"})
    camera_pi.reboot()
    return jsonify({"message": "Camera rebooted"})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)

