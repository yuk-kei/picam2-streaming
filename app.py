from flask import Flask, render_template, Response
from camera_manager import CameraManager

app = Flask(__name__)
camera_pi = CameraManager()
camera_pi.setup_camera()
camera_pi.setup_webcam()


# from webcam_pi2 import Camera

@app.route('/')
def index():
    return render_template('index.html')


def preview_frame(camera):
    while True:
        frame = camera.preview()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def preview_webcam_frame(camera):
    while True:
        frame, ts = camera.get_webcam_frame()
        timestamp_bytes = str(ts).encode('utf-8')
        delimiter = b'---timestamp---'
        # yield 'timestamp: ' + str(ts) + '\r\n'
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + delimiter + timestamp_bytes + b'\r\n--frame\r\n'


def generate_frame(camera):
    while True:
        frame, ts = camera.get_frame()
        # frame, ts= camera.get_webcam_frame()
        timestamp_bytes = str(ts).encode('utf-8')
        delimiter = b'---timestamp---'
        # yield 'timestamp: ' + str(ts) + '\r\n'
        yield b'Content-Type: image/jpeg\r\n\r\n' + frame + delimiter + timestamp_bytes + b'\r\n--frame\r\n'


@app.route('/preview')
def preview():
    return Response(preview_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/video_feed')
def video_feed():
    # return Response(generate_frame(camera_pi))
    return Response(generate_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/preview_webcam')
def preview_webcam():
    """Video streaming route. Put this in the src attribute of an img tag."""
    return Response(preview_webcam_frame(camera_pi),
                    mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/start')
def start():
    camera_pi.setup_camera()
    return "Camera started"


@app.route('/stop')
def stop():
    camera_pi.stop()
    return "Camera stopped"


@app.route('/reboot')
def reboot():
    camera_pi.reboot()
    return "Camera rebooted"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, threaded=True)
