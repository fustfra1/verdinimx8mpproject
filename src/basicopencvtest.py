import cv2
import numpy as np
import time

def main():
    original_width, original_height = 4032, 3040
    output_width, output_height = 1920, 1080

    capture_pipeline = (
        f"v4l2src device=/dev/video2 ! "
        f"video/x-raw,format=YUY2,width={output_width},height={output_height},framerate=5/1 ! "
        "imxvideoconvert_g2d ! "
        "appsink"
    )

    display_pipeline = (
        'appsrc ! '
        'videorate ! '
        'video/x-raw,format=BGR,width=1920,height=1080,framerate=5/1 ! '  # Changed framerate to 5/1
        'videoconvert ! '
        'vpuenc_h264 ! rtph264pay config-interval=1 pt=96 ! '
        'udpsink host=192.168.99.96 port=5000'
    )

    cap = cv2.VideoCapture(capture_pipeline, cv2.CAP_GSTREAMER)
    if not cap.isOpened():
        print("Error: Unable to open capture pipeline.")
        return

    out = cv2.VideoWriter(display_pipeline, cv2.CAP_GSTREAMER, 0, 5, (output_width, output_height), True)  # Changed fps to 5
    if not out.isOpened():
        print("Error: Unable to open display pipeline.")
        cap.release()
        return

    print("Streaming started. Press 'q' to stop.")

    # Initialize variables for FPS calculation
    frame_count = 0
    start_time = time.time()
    fps = 0

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error: Failed to read frame from capture pipeline.")
                break

            # Ensure the frame has the correct data type
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)

            # Ensure the frame has 3 channels
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif frame.shape[2] == 4:
                frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)

            # Resize the frame
            resized_frame = cv2.resize(frame, (output_width, output_height))

            # FPS calculation
            frame_count += 1
            elapsed_time = time.time() - start_time
            if elapsed_time >= 1.0:
                fps = frame_count / elapsed_time
                frame_count = 0
                start_time = time.time()

            # Overlay FPS on the frame
            fps_text = f"FPS: {fps:.2f}"
            cv2.putText(
                resized_frame,
                fps_text,
                (10, 30),  # Position (x, y)
                cv2.FONT_HERSHEY_SIMPLEX,
                1,          # Font scale
                (0, 255, 0),# Color (B, G, R)
                2,          # Thickness
                cv2.LINE_AA
            )

            # Write the frame
            out.write(resized_frame)

            # Optional: Display the frame locally
            # cv2.imshow('Streaming Frame', resized_frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                print("Stream stopped by user.")
                break

    except KeyboardInterrupt:
        print("Stream interrupted by user.")

    finally:
        cap.release()
        out.release()
        cv2.destroyAllWindows()
        print("Resources released. Exiting.")

if __name__ == '__main__':
    main()
