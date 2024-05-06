import io, sys
from threading import Condition
from picamera2 import MappedArray, Picamera2
from picamera2.encoders import MJPEGEncoder
from picamera2.outputs import FileOutput
import cv2
import time
import logging

logging.basicConfig(level=logging.DEBUG)

# Enable the following if you want to use Kafka
# from producer_config import config, delivery_report
# from confluent_kafka import Producer


class StreamingOutput(io.BufferedIOBase):
    """
    This class represents a streaming output buffer that can handle
    data streams such as video frames. It provides mechanisms for
    synchronized write and read operations.
    """

    def __init__(self):
        """
        Initialize the buffer, the timestamp, and the threading condition.
        """
        self.frame = None
        self.ts = None
        self.condition = Condition()

    def write(self, buf, ts=None):
        """
        Write a buffer to the frame buffer with thread synchronization.

        Args:
        - buf: The buffer data to write.
        - ts: Optional timestamp for the buffer data.
        """
        with self.condition:
            self.frame = buf
            self.ts = int(time.time() * 1000) if ts is None else ts
            self.condition.notify_all()

    def save(self, data):
        """
        Mimic a file write operation by saving data to the streaming buffer.

        Args:
        - data: The data to save.
        """
        self.write(data)


class CameraManager:
    """
    This class manages operations for both PiCamera and a generic webcam.
    It can set up, start, and stop cameras, as well as capture frames and
    send them to Kafka.
    """

    def __init__(
            self,
            name=None,
            pi_source=None,
            web_source=None,
            enable_webcam=False,
            enable_kafka=False,
            producer_config=None
    ):
        """
        Initialize the CameraManager with various configurations.

        Args:
        - name: The name identifier for the camera.
        - pi_source: Source for the PiCamera (default 0).
        - web_source: Source for the webcam (default 1).
        - enable_webcam: Flag to enable webcam.
        - enable_kafka: Flag to enable Kafka producer.
        - producer_config: Configuration for Kafka producer.
        """
        self.picam2 = None
        self.webcam = None
        self.output_high = StreamingOutput()
        self.output_low = StreamingOutput()
        self.webcam_review = io.BytesIO()

        self.name = name if name else None
        self.start_time = time.time()
        self.webcam_start_time = time.time()
        self.frame_count = 0
        self.web_frame_count = 0
        self.fps = 0
        self.webcam_fps = 0

        self.enable_kafka = enable_kafka
        self.producer = Producer(producer_config) if enable_kafka else None
        self.enable_webcam = enable_webcam

        self.pi_source = pi_source if pi_source else 0
        self.web_source = web_source if web_source else 1
        
        self.picam2_running = False
        self.webcam_running = False
        self.picam2_rebooting = False

    def setup_camera(self, resolution=(640, 360)):
        """
        Setup and start the PiCamera with main and lores configurations.(Two streams)
        The main configuration is for high resolution and the lores is for
        low resolution.

        Args:
        - resolution: Tuple representing the resolution for the camera.
        """
        if not self.picam2_running:
            self.picam2 = Picamera2(0)
            config = self.picam2.create_video_configuration(main={"size": (1920, 1080), "format": "RGB888"},
                                                            lores={"size": resolution, "format": "YUV420"},
                                                            controls={"FrameDurationLimits": (33333, 33333)}
                                                            )
            self.picam2.configure(config)
            self.picam2.start_recording(MJPEGEncoder(), FileOutput(self.output_high))
            self.picam2.start_recording(MJPEGEncoder(), FileOutput(self.output_low), name="lores")
            self.picam2.pre_callback = self.apply_timestamp
            self.picam2.set_controls({"FrameDurationLimits": (33333, 33333)})
            self.picam2_running =True


    def setup_webcam(self):
        """Setup and start the webcam."""
        if self.enable_webcam and not self.webcam:
            self.webcam = Picamera2(1)
            # config = self.webcam.create_video_configuration(main={"size": resolution, "format": "MJPEG"})
            config = self.webcam.create_video_configuration(main={"size": (1080, 720), "format": "MJPEG"})
            self.webcam.configure(config)
            self.webcam.start()
            self.webcam_running = True

    def stop(self):
        """Stop recording and close both PiCamera and webcam."""
        logging.debug("Stopping cameras.")
        if self.picam2 and self.picam2_running:
            try:
                self.picam2.stop_recording()
                self.picam2.close()
                self.picam2_running = False
                logging.debug("PiCamera stopped and closed.")
            except Exception as e:
                logging.error(f"Failed to stop PiCamera: {e}")
        if self.enable_webcam and self.webcam and self.webcam_running:
            try:
                self.webcam.stop_recording()
                self.webcam.close()
                self.webcam_running = False
                logging.debug("Webcam stopped and closed.")
            except Exception as e:
                logging.error(f"Failed to stop webcam: {e}")


    def reboot(self):
        """Reboot the PiCamera and webcam."""
        logging.debug("Rebooting cameras.")
        if self.picam2_running:
            self.stop()
        self.picam2_running = False
        self.picam2_rebooting = True
        time.sleep(1)
        try:
            self.setup_camera()
            logging.debug("PiCamera setup completed or not being used.")
        except Exception as e:
            logging.error(f"Error setting up PiCamera: {e}")
        
        try:
            self.setup_webcam()
            logging.debug("Webcam setup completed.")
        except Exception as e:
            logging.error(f"Error setting up webcam: {e}")
        self.picam2_rebooting = False
        
    def preview(self):
        """Preview the PiCamera. using the lores stream."""
        with self.output_low.condition:
            self.output_low.condition.wait()
            frame = self.output_low.frame

            return frame

    def get_frame(self):
        """Sending the high resolution video jpeg frame and its timestamp, optionally to Kafka."""

        with self.output_high.condition:
            self.output_high.condition.wait()
            frame = self.output_high.frame
            ts = self.output_high.ts

            if self.enable_kafka:
                self.send_frame_to_kafka(frame, ts)

            return frame, ts

    def get_webcam_frame(self):
        """Sending the webcam video jpeg frame and its timestamp"""
        curr_time = time.time()
        if curr_time - self.webcam_start_time >= 1:
            self.webcam_fps = self.web_frame_count
            self.web_frame_count = 0
            self.webcam_start_time = curr_time

        else:
            self.web_frame_count += 1
        self.webcam.capture_file(self.webcam_review, format='jpeg')
        self.webcam_review.seek(0)
        cur = self.webcam_review.read()
        self.webcam_review.seek(0)
        self.webcam_review.truncate()
        return cur, int(time.time() * 1000)

    def fps(self, fps):
        """Set the framerate for the PiCamera."""
        self.picam2.framerate = fps

    def apply_timestamp(self, request):
        """
        Apply timestamp and fps overlays to the video frame.

        Args:
        - request: The picamera2 request object.
        """
        timestamp = time.strftime("%Y-%m-%d %X")
        curr_time = time.time()
        if curr_time - self.start_time >= 1:
            self.fps = self.frame_count
            self.frame_count = 0
            self.start_time = curr_time
        else:
            self.frame_count += 1
        with MappedArray(request, "main") as m:
            cv2.putText(m.array, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(m.array, f"FPS: {self.fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
                        cv2.LINE_AA)
        with MappedArray(request, "lores") as m:
            cv2.putText(m.array, timestamp, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(m.array, f"FPS: {self.fps:.2f}", (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2,
                        cv2.LINE_AA)

    def send_frame_to_kafka(self, frame, ts):
        """
        Send video frame to Kafka topic "frames".

        Args:
        - frame: The video frame to send.
        - ts: Timestamp for the video frame.
        """
        self.producer.produce(
            topic="frames",
            key=str.encode(self.name) if self.name else None,
            value=frame,
            on_delivery=delivery_report,
            timestamp=ts,
        )
        self.producer.poll(0)
