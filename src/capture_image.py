# Version von FFU funktioniert teilweise nicht

import cv2
import time
import argparse
import subprocess
import sys
import os

def capture_with_gstreamer(device='/dev/video2', width=4032, height=3040, output_path='capture_gst.jpg'):
    """
    Captures a single image using a GStreamer pipeline.

    Parameters:
    - device (str): The video device path (e.g., '/dev/video2').
    - width (int): Image width.
    - height (int): Image height.
    - output_path (str): Path to save the captured image.

    Returns:
    - elapsed_time (float): Time taken in seconds.
    - success (bool): Whether the capture was successful.
    """
    gst_command = [
        'gst-launch-1.0',
        'v4l2src', f'device={device}', 'num-buffers=1',
        '!', 'video/x-raw,width={},height={},format=YUY2'.format(width, height),
        '!', 'jpegenc', 'quality=100',
        '!', f'filesink', f'location={output_path}'
    ]

    print("Executing GStreamer command:")
    print(' '.join(gst_command))

    start_time = time.perf_counter()
    try:
        # Run the GStreamer pipeline
        subprocess.run(gst_command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("Error: GStreamer pipeline failed.")
        print("GStreamer Output:", e.stderr.decode())
        return None, False
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time
    return elapsed_time, True

def capture_with_opencv(device='/dev/video2', width=4032, height=3040, output_path='capture_opencv.jpg'):
    """
    Captures a single image using OpenCV's native VideoCapture.

    Parameters:
    - device (str): The video device path (e.g., '/dev/video2').
    - width (int): Image width.
    - height (int): Image height.
    - output_path (str): Path to save the captured image.

    Returns:
    - elapsed_time (float): Time taken in seconds.
    - success (bool): Whether the capture was successful.
    """
    start_time = time.perf_counter()

    # Define the GStreamer pipeline for OpenCV
    # Note: Using videoconvert to ensure the format is BGR for OpenCV
    gst_pipeline = (
        f"v4l2src device={device} num-buffers=1 ! "
        f"video/x-raw,width={width},height={height},format=YUY2 ! "
        "videoconvert ! video/x-raw,format=BGR ! appsink"
    )

    print("Using OpenCV with the following pipeline:")
    print(gst_pipeline)

    # Initialize VideoCapture with the GStreamer pipeline
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

    if not cap.isOpened():
        print("Error: Unable to open camera with OpenCV.")
        return None, False

    # Read a single frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Failed to capture image with OpenCV.")
        cap.release()
        return None, False

    # Release the VideoCapture object
    cap.release()

    # Save the captured frame as a JPEG file with quality=100
    try:
        success = cv2.imwrite(output_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    except Exception as e:
        print(f"Error: Failed to save image with OpenCV. {e}")
        return None, False

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    if success:
        return elapsed_time, True
    else:
        return elapsed_time, False

def capture_with_native_opencv(device=2, width=4032, height=3040, output_path='capture_native_opencv.jpg'):
    """
    Captures a single image using OpenCV's native VideoCapture without GStreamer.

    Parameters:
    - device (int or str): The video device index or path (e.g., 2 or '/dev/video2').
    - width (int): Image width.
    - height (int): Image height.
    - output_path (str): Path to save the captured image.

    Returns:
    - elapsed_time (float): Time taken in seconds.
    - success (bool): Whether the capture was successful.
    """
    start_time = time.perf_counter()

    print("Using OpenCV's native VideoCapture.")

    # Initialize VideoCapture with the device index or path
    cap = cv2.VideoCapture(device, cv2.CAP_V4L2)

    if not cap.isOpened():
        print(f"Error: Unable to open camera device {device}.")
        return None, False

    # Set the desired resolution
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)

    # Attempt to set the pixel format to YUY2 if supported
    fourcc = cv2.VideoWriter_fourcc(*'YUYV')
    cap.set(cv2.CAP_PROP_FOURCC, fourcc)

    # Allow the camera to adjust
    time.sleep(0.5)  # Wait for the camera to adjust settings

    # Read a single frame
    ret, frame = cap.read()

    if not ret:
        print("Error: Failed to capture image with native OpenCV.")
        cap.release()
        return None, False

    # Release the VideoCapture object
    cap.release()

    # Check the captured frame's dimensions
    captured_height, captured_width = frame.shape[:2]
    print(f"Captured image size: {captured_width}x{captured_height}")

    # If the captured frame size doesn't match the desired size, resize it
    if captured_width != width or captured_height != height:
        print("Warning: Captured image size does not match the desired resolution. Resizing...")
        frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)

    # Save the image as JPEG with quality=100
    try:
        success = cv2.imwrite(output_path, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
    except Exception as e:
        print(f"Error: Failed to save image with native OpenCV. {e}")
        return None, False

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    if success:
        return elapsed_time, True
    else:
        return elapsed_time, False

def main():
    parser = argparse.ArgumentParser(description="Capture images using GStreamer or OpenCV pipelines.")
    parser.add_argument(
        '--method',
        choices=['gstreamer', 'opencv', 'native_opencv'],
        required=True,
        help="Method to use for capturing images: 'gstreamer', 'opencv' (OpenCV with GStreamer), 'native_opencv' (OpenCV without GStreamer)"
    )
    parser.add_argument(
        '--device',
        type=str,
        default='/dev/video2',
        help="Video device path (e.g., '/dev/video2'). For native_opencv, you can also provide device index as integer."
    )
    parser.add_argument(
        '--width',
        type=int,
        default=4032,
        help="Width of the captured image."
    )
    parser.add_argument(
        '--height',
        type=int,
        default=3040,
        help="Height of the captured image."
    )
    parser.add_argument(
        '--output',
        type=str,
        default='capture.jpg',
        help="Output image file path."
    )

    args = parser.parse_args()

    method = args.method
    device = args.device
    width = args.width
    height = args.height
    output_path = args.output

    print(f"Selected method: {method}")
    print(f"Device: {device}")
    print(f"Resolution: {width}x{height}")
    print(f"Output Path: {output_path}\n")

    if method == 'gstreamer':
        elapsed_time, success = capture_with_gstreamer(
            device=device,
            width=width,
            height=height,
            output_path=output_path
        )
    elif method == 'opencv':
        elapsed_time, success = capture_with_opencv(
            device=device,
            width=width,
            height=height,
            output_path=output_path
        )
    elif method == 'native_opencv':
        # If device is a string that can be converted to int, do so
        try:
            device_index = int(device)
        except ValueError:
            device_index = device  # Keep as string if not an integer
        elapsed_time, success = capture_with_native_opencv(
            device=device_index,
            width=width,
            height=height,
            output_path=output_path
        )
    else:
        print("Error: Unsupported method selected.")
        sys.exit(1)

    if elapsed_time is not None:
        print(f"\nTime taken for {method}: {elapsed_time:.4f} seconds.")
    else:
        print(f"\nCapture failed using method: {method}.")

    if success:
        print(f"Image successfully saved to '{output_path}'.")
    else:
        print(f"Failed to save image using method: {method}.")

if __name__ == "__main__":
    main()
