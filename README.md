# picam2-streaming

This repository contains code to set up a camera streaming service using Flask and interfaces with both a Pi camera and a webcam.

## Files Overview:

- `camera_manager.py`: Contains the core classes and functions for managing and interfacing with the cameras.
- `app.py`: A Flask application that serves the camera feed on different endpoints, providing routes to preview and stream camera feeds, as well as control camera operations.

## Features:

1. **StreamingOutput**: An IO wrapper that assists in real-time streaming of video frames from the camera.

2. **CameraManager**: Handles camera operations such as setting up the camera, streaming, adding timestamps to frames, and even sending frames to Kafka.

3. **Flask Application**:

   A web service that provides routes for:

   - Previewing camera frames in low resolution.
   - Streaming high resolution frame and its corresponding timestamp.
   - Starting, stopping, and rebooting the camera.

## Setup:

1. Ensure you have all the necessary libraries installed, including Flask, picamera2, and others referenced in the files.
   ```sh
   pip install -r requirements.txt
   ```


2. Set up the necessary configurations for the cameras and any other services like Kafka.

3. Run the Flask application using the command:

   ```sh
   python app.py
   ```

## Access:

Once the Flask application is running:

- Access the main page at `http://<your-ip-address>:8080/`.
- Preview the Pi camera feed at `http://<your-ip-address>:8080/preview`.
- Stream the Pi camera feed at `http://<your-ip-address>:8080/video_feed`.
- Preview the webcam feed at `http://<your-ip-address>:8080/preview_webcam`.

## Routes:

- `/` : Main template page.
- `/preview` : Preview a single frame from the Pi camera.
- `/video_feed` : Stream video feed from the Pi camera.
- `/preview_webcam` : Preview a single frame from the webcam.
- `/start` : Start the Pi camera.
- `/stop` : Stop the Pi camera.
- `/reboot` : Reboot the Pi camera.

------

