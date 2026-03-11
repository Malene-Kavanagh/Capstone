import cv2
from picamera2 import Picamera2

picam2 = Picamera2()
picam2.configure(
    picam2.create_preview_configuration(
        main={"format": "RGB888", "size": (1280, 720)}
    )
)
picam2.start()

try:
    while True:
        frame_rgb = picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        
        cv2.imshow("Pi Camera", frame_bgr)
        
        if cv2.waitKey(1) & 0xFF == 27:
            break
finally:
    picam2.stop()
    cv2.destroyAllWindows()