import cv2
import numpy as np
import time
import threading
import os
import sys
import termios
import tty
import select
import gpiod  # Import the libgpiod Python module
import configparser  # For reading the config file


class FrameGrabber(threading.Thread):
    """
    A thread class for continuously grabbing frames from the VideoCapture object.
    The latest frame and FPS are stored in shared variables protected by a lock.
    """
    def __init__(self, capture, shared_data):
        threading.Thread.__init__(self)
        self.capture = capture
        self.shared_data = shared_data
        self.stopped = False
        self.frame_count = 0
        self.start_time = time.time()
        self.current_fps = 0.0

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
                # Update frame count for FPS calculation
                self.frame_count += 1
                elapsed_time = time.time() - self.start_time
                if elapsed_time >= 1.0:
                    self.current_fps = self.frame_count / elapsed_time
                    self.shared_data['fps'] = self.current_fps
                    self.frame_count = 0
                    self.start_time = time.time()

    def stop(self):
        self.stopped = True


class GPIOController:
    """
    A class to manage GPIO lines using libgpiod.
    Maps line names to their offsets and controls them as outputs.
    """

    def __init__(self, chip_name='/dev/gpiochip0', line_name_mapping=None):
        """
        Initialize the GPIO controller.

        :param chip_name: The name or path of the GPIO chip (default: '/dev/gpiochip0')
        :param line_name_mapping: Dictionary mapping logical names to physical line names
        """
        if line_name_mapping is None:
            line_name_mapping = {}

        self.chip_name = chip_name
        self.line_name_mapping = line_name_mapping
        self.lines = {}  # Maps logical names to line offsets
        self.request = None

        self._find_and_request_lines()

    def _find_and_request_lines(self):
        """
        Find GPIO lines based on the mapping and request them as outputs.
        """
        try:
            chip = gpiod.Chip(self.chip_name)
            config = {}
            for logical_name, physical_name in self.line_name_mapping.items():
                try:
                    line_offset = chip.line_offset_from_id(physical_name)
                except KeyError:
                    print(f"Error: GPIO line '{physical_name}' not found in chip '{self.chip_name}'.")
                    chip.close()
                    sys.exit(1)
                self.lines[logical_name] = line_offset
                config[line_offset] = gpiod.LineSettings(
                    direction=gpiod.line.Direction.OUTPUT,
                    output_value=gpiod.line.Value.INACTIVE  # Initialize to LOW
                )
                print(f"Mapped logical '{logical_name}' to physical '{physical_name}' (Line {line_offset}).")
            chip.close()

            # Request lines using the module-level function
            self.request = gpiod.request_lines(
                self.chip_name,
                consumer="GPIOController",
                config=config
            )
            print("Successfully requested GPIO lines:")
            for logical_name, line_offset in self.lines.items():
                print(f"  {logical_name} on line {line_offset}")
        except Exception as e:
            print(f"Error requesting GPIO lines: {e}")
            self.cleanup()
            sys.exit(1)

    def set_pins(self, pins, value):
        """
        Set specified GPIO pins to a given value.

        :param pins: List of logical GPIO names to set
        :param value: Value to set the pins to (0 or 1)
        """
        if not self.request:
            print("Error: GPIO lines have not been requested.")
            return

        for pin in pins:
            line_offset = self.lines.get(pin)
            if line_offset is not None:
                val = gpiod.line.Value.ACTIVE if value else gpiod.line.Value.INACTIVE
                try:
                    self.request.set_value(line_offset, val)
                    state = "HIGH" if value else "LOW"
                    print(f"Set '{pin}' (Line {line_offset}) to {state}.")
                except Exception as e:
                    print(f"Error setting value for '{pin}': {e}")
            else:
                print(f"Warning: GPIO pin '{pin}' not found in configuration.")

    def cleanup(self):
        """
        Release all GPIO lines.
        """
        if self.request:
            try:
                self.request.close()
                print("Released all GPIO lines.")
            except Exception as e:
                print(f"Error releasing GPIO lines: {e}")


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


def capture_image(shared_data, save_folder, image_prefix='img', image_ext='.jpg', black_threshold=10, percentage_threshold=0.95):
    """
    Capture the latest frame and save it as a high-quality JPG.
    If the image is nearly or completely black, do not save and prompt the user.

    :param shared_data: shared data containing the latest frame
    :param save_folder: folder to save images
    :param image_prefix: prefix for image filenames
    :param image_ext: file extension for images
    :param black_threshold: intensity threshold to consider a pixel as black
    :param percentage_threshold: minimum proportion of pixels below the black threshold
    """
    with shared_data['lock']:
        frame = shared_data['frame']
    if frame is not None:

        # Check the proportion of pixels below the black threshold
        num_black_pixels = np.sum(frame < black_threshold)
        total_pixels = frame.size
        black_ratio = num_black_pixels / total_pixels
        print(f'Black ratio: {black_ratio:.4f}')

        if black_ratio >= percentage_threshold:
            print("Captured image is nearly or completely black. Not saving.")
            return

        image_number = get_next_image_number(save_folder, prefix=image_prefix, ext=image_ext)
        filename = os.path.join(save_folder, f"{image_prefix}{image_number}{image_ext}")
        # Save image with full quality
        success = cv2.imwrite(filename, frame, [int(cv2.IMWRITE_JPEG_QUALITY), 100])
        if success:
            print(f"Image saved: {filename}")
        else:
            print(f"Failed to save image: {filename}")
    else:
        print("No frame available to capture.")


def load_config(config_file='config.ini'):
    """
    Load configuration parameters from the specified INI file.

    :param config_file: path to the configuration file
    :return: dictionary containing configuration parameters
    """
    config = configparser.ConfigParser()
    if not os.path.exists(config_file):
        print(f"Configuration file '{config_file}' not found. Using default settings.")
        return {}
    config.read(config_file)
    return config['DEFAULT']


def main():
    # Load configuration
    config = load_config()

    # Black detection parameters
    BLACK_THRESHOLD = config.getfloat('black_threshold', 10.0)
    PERCENTAGE_THRESHOLD = config.getfloat('percentage_threshold', 0.95)

    # LED control timings in seconds
    CAPTURE_DELAY_BEFORE_DEFAULT = config.getfloat('capture_delay_before', 0.1)
    CAPTURE_DELAY_AFTER = config.getfloat('capture_delay_after', 0.0)

    # GPIO configuration
    CHIP_NAME = config.get('chip_name', '/dev/gpiochip0')
    line_name_mapping = {
        'uv_light': config.get('uv_light_line', 'SODIMM_206'),
        'white_led_1': config.get('white_led_1_line', 'SODIMM_210'),
        'white_led_2': config.get('white_led_2_line', 'SODIMM_212')
    }

    # Image capture parameters
    IMAGE_PREFIX = config.get('image_prefix', 'img')
    IMAGE_EXT = config.get('image_ext', '.jpg')
    SAVE_FOLDER = config.get('save_folder', 'images')

    # Camera configuration
    VIDEO_DEVICE = config.get('video_device', '/dev/video2')
    VIDEO_FORMAT = config.get('video_format', 'YUY2')
    VIDEO_WIDTH = config.getint('video_width', 4032)
    VIDEO_HEIGHT = config.getint('video_height', 3040)

    # GStreamer pipeline for capturing frames
    capture_pipeline = (
        f'v4l2src device={VIDEO_DEVICE} ! '
        f'video/x-raw,format={VIDEO_FORMAT},width={VIDEO_WIDTH},height={VIDEO_HEIGHT} ! '
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
        'fps': 0.0,
        'lock': threading.Lock(),
    }

    # Initialize and start the frame grabbing thread
    grabber = FrameGrabber(cap, shared_data)
    grabber.start()

    # Set up image save folder
    os.makedirs(SAVE_FOLDER, exist_ok=True)

    # Initialize GPIO controller with correct chip name and mapping
    gpio = GPIOController(chip_name=CHIP_NAME, line_name_mapping=line_name_mapping)

    # Set terminal to cbreak mode
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        print("Press 'p' to capture with white LED, 'u' for UV light, 'q' to quit.")

        last_fps_display_time = time.time()
        while True:
            current_time = time.time()

            # Display FPS every second
            if current_time - last_fps_display_time >= 1.0:
                with shared_data['lock']:
                    current_fps = shared_data['fps']
                print(f"Current FPS: {current_fps:.2f}")
                last_fps_display_time = current_time

            # Check if a key has been pressed
            dr, dw, de = select.select([sys.stdin], [], [], 0.1)
            if dr:
                ch = sys.stdin.read(1)
                if ch == 'p':
                    print("Capturing image with white LED...")
                    # Calculate dynamic delay based on FPS
                    with shared_data['lock']:
                        current_fps = shared_data['fps']
                    if current_fps > 0:
                        dynamic_delay_before = 1.0 / current_fps * 1.2  # Half the frame time
                    else:
                        dynamic_delay_before = CAPTURE_DELAY_BEFORE_DEFAULT
                    print(f"Dynamic capture_delay_before set to {dynamic_delay_before:.4f} seconds.")

                    # Set GPIO pins 'white_led_1' and 'white_led_2' to 1 (HIGH)
                    gpio.set_pins(['white_led_1', 'white_led_2'], 1)
                    # Wait before capturing
                    time.sleep(dynamic_delay_before)
                    # Capture image
                    capture_image(shared_data, SAVE_FOLDER, IMAGE_PREFIX, IMAGE_EXT, BLACK_THRESHOLD, PERCENTAGE_THRESHOLD)
                    # Wait after capturing (if needed)
                    if CAPTURE_DELAY_AFTER > 0:
                        time.sleep(CAPTURE_DELAY_AFTER)
                    # Set GPIO pins 'white_led_1' and 'white_led_2' to 0 (LOW)
                    gpio.set_pins(['white_led_1', 'white_led_2'], 0)
                elif ch == 'u':
                    print("Capturing image with UV light...")
                    # Calculate dynamic delay based on FPS
                    with shared_data['lock']:
                        current_fps = shared_data['fps']
                    if current_fps > 0:
                        dynamic_delay_before = 1.0 / current_fps * 1.2  # Half the frame time
                    else:
                        dynamic_delay_before = CAPTURE_DELAY_BEFORE_DEFAULT
                    print(f"Dynamic capture_delay_before set to {dynamic_delay_before:.4f} seconds.")

                    # Set GPIO pin 'uv_light' to 1 (HIGH)
                    gpio.set_pins(['uv_light'], 1)
                    # Wait before capturing
                    time.sleep(dynamic_delay_before)
                    # Capture image
                    capture_image(shared_data, SAVE_FOLDER, IMAGE_PREFIX, IMAGE_EXT, BLACK_THRESHOLD, PERCENTAGE_THRESHOLD)
                    # Wait after capturing (if needed)
                    if CAPTURE_DELAY_AFTER > 0:
                        time.sleep(CAPTURE_DELAY_AFTER)
                    # Set GPIO pin 'uv_light' to 0 (LOW)
                    gpio.set_pins(['uv_light'], 0)
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
        # Cleanup GPIO
        gpio.cleanup()
        print("Resources released.")


if __name__ == '__main__':
    main()
