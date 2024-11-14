import cv2
import numpy
import time
cv2.setNumThreads(8)

def main():
    # Define your GStreamer pipeline
    # Modify the pipeline according to your camera's specifications
    # gst_pipeline = (
    #     "v4l2src device=/dev/video2 ! "
    #     "video/x-raw,format=YUY2,width=4032,height=3040,framerate=5/1 ! "
    #     "videoconvert ! "
    #     "appsink"
    # )
    # gst_pipeline = "v4l2src device=/dev/video2 ! video/x-raw,format=YUY2,width=4032,height=3040,framerate=5/1 ! videoconvert ! appsink"
    # gst_pipeline = "v4l2src device=/dev/video2 ! video/x-raw,format=YUY2,width=4032,height=3040,framerate=5/1 ! videoconvert ! video/x-raw,format=BGR ! appsink max-buffers=2 drop=1 sync=1"
    gst_pipeline = "v4l2src device=/dev/video2 ! video/x-raw,format=YUY2,width=4032,height=3040,framerate=5/1 ! imxvideoconvert_g2d ! appsink"
    # Initialize VideoCapture with GStreamer pipeline
    cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER) # 0.53 fps
    # cap = cv2.VideoCapture(2) # 0.81 fps

    if not cap.isOpened():
        print("Error: Unable to open GStreamer pipeline.")
        return

    print("GStreamer pipeline opened successfully.")
    print("Press 'q' to quit.")

    frame_count = 0
    start_time = time.time()
    fps = 0

    try:
        while True:
            ret = cap.grab()
            print('used threads:',cv2.getNumThreads())
            if not ret:
                print("Error: Failed to read frame from GStreamer pipeline.")
                break

            frame_count += 1

            # Calculate FPS every second
            elapsed_time = time.time() - start_time
            if elapsed_time >= 1.0:
                fps = frame_count / elapsed_time
                print(f"FPS: {fps:.2f}")
                frame_count = 0
                start_time = time.time()

            # (Optional) Display the frame in a window
            # Uncomment the following lines if you want to see the video
            # cv2.imshow('GStreamer OpenCV Feed', frame)
            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     print("Quitting...")
            #     break

    except KeyboardInterrupt:
        print("\nInterrupted by user.")

    finally:
        # Release resources
        cap.release()
        cv2.destroyAllWindows()
        print("Resources released.")

if __name__ == "__main__":
    main()
