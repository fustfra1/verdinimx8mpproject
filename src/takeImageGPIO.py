import cv2
import numpy as np
import time
import threading
import os
import subprocess
import sys
import termios
import tty
import select


# FFU:
#  Das umbauen und zuerst gpiod per pip installieren, ist viel schneller!

class FrameGrabber(threading.Thread):
    """
    A thread class for continuously grabbing frames from the VideoCapture object.
    The latest frame is stored in a shared variable protected by a lock.
    """
    def __init__(self, capture, shared_data):
        threading.Thread.__init__(self)
        self.capture = capture
        self.shared_data = shared_data
        self.stopped = False

    def run(self):
        while not self.stopped:
            ret, frame = self.capture.read()
            if not ret:
                print("Error: Failed to read frame from capture pipeline.")
                self.stop()
                break
            with self.shared_data['lock']:
                # Update the latest frame
                self.shared_data['frame'] = frame.copy()

    def stop(self):
        self.stopped = True

def set_gpio_pins(pins, value):
    """
    Set GPIO pins to a specific value using gpioset.

    :param pins: list of GPIO pin numbers to set
    :param value: value to set the pins to (0 or 1)
    """
    for pin in pins:
        subprocess.run(['gpioset', '0', f'{pin}={value}'])

def get_next_image_number(folder, prefix='img', ext='.jpg'):
    """
    Get the next image number based on existing files in the folder.

    :param folder: directory to look for existing images
    :param prefix: prefix of image filenames
    :param ext: extension of image files
    :return: next image number (int)
    """
    existing_files = [f for f in os.listdir(folder) if f.startswith(prefix) and f.endswith(ext)]
    numbers = []
    for f in existing_files:
        num_str = f[len(prefix):-len(ext)]
        if num_str.isdigit():
            numbers.append(int(num_str))
    if numbers:
        next_num = max(numbers) + 1
    else:
        next_num = 1
    return next_num

def capture_image(shared_data, save_folder, image_prefix='img', image_ext='.jpg'):
    """
    Capture the latest frame and save it as a high-quality JPG.

    :param shared_data: shared data containing the latest frame
    :param save_folder: folder to save images
    :param image_prefix: prefix for image filenames
    :param image_ext: file extension for images
    """
    with shared_data['lock']:
        frame = shared_data['frame']
    if frame is not None:
        image_number = get_next_image_number(save_folder, prefix=image_prefix, ext=image_ext)
        filename = os.path.join(save_folder, f"{image_prefix}{image_number}.jpg")
        # Save image with full quality
        success = cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        if success:
            print(f"Image saved: {filename}")
        else:
            print(f"Failed to save image: {filename}")
    else:
        print("No frame available to capture.")

def main():
    # Original resolution
    original_width, original_height = 4032, 3040

    # GStreamer pipeline for capturing frames
    capture_pipeline = (
        f'v4l2src device=/dev/video2 ! '
        f'video/x-raw,format=YUY2,width={original_width},height={original_height} ! '
        'videoconvert ! '
        'appsink'
    )

    # OpenCV VideoCapture for capturing frames
    cap = cv2.VideoCapture(capture_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Error: Unable to open capture pipeline.")
        return

    # Shared data structure with a lock
    shared_data = {
        'frame': None,
        'lock': threading.Lock(),
    }

    # Initialize and start the frame grabbing thread
    grabber = FrameGrabber(cap, shared_data)
    grabber.start()

    # Set up image save folder
    save_folder = 'images'
    os.makedirs(save_folder, exist_ok=True)

    # Set terminal to cbreak mode
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        print("Press 'p' to capture with white LED, 'u' for UV light, 'q' to quit.")

        while True:
            # Check if a key has been pressed
            dr, dw, de = select.select([sys.stdin], [], [], 0.1)
            if dr:
                ch = sys.stdin.read(1)
                if ch == 'p':
                    print("Capturing image with white LED...")
                    # Set GPIO pins 5 and 6 to 1
                    set_gpio_pins([5, 6], 1)
                    # Wait 0.5 seconds
                    time.sleep(2.5)
                    # Capture image
                    capture_image(shared_data, save_folder)
                    time.sleep(1)
                    # Set GPIO pins 5 and 6 to 0
                    set_gpio_pins([5, 6], 0)
                elif ch == 'u':
                    print("Capturing image with UV light...")
                    # Set GPIO pin 0 to 1
                    set_gpio_pins([0], 1)
                    # Wait 0.5 seconds
                    time.sleep(2.5)
                    # Capture image
                    capture_image(shared_data, save_folder)
                    time.sleep(1)
                    # Set GPIO pin 0 to 0
                    set_gpio_pins([0], 0)
                elif ch == 'q':
                    print("Quitting...")
                    break
            # Sleep briefly to reduce CPU usage
            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\nInterrupted by user.")
    finally:
        # Restore terminal settings
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        # Stop frame grabbing thread
        grabber.stop()
        grabber.join()
        # Release camera
        cap.release()
        print("Resources released.")

if __name__ == '__main__':
    main()
