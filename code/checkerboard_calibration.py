#FROM OPENCV camera calibration
import cv2
from picamera2 import Picamera2
import os

CHECKERBOARD = (5, 8) #inner corners whole checkerboard is 4, 5
SAVE_DIR = "calbrate_cam2"
#SAVE_DIR = "calibrate_top"
#SAVE_DIR = "calibrate_bot"

os.makedirs(SAVE_DIR, exist_ok=True)

cam = Picamera2(1)

#top_cam = Picamera2(0)
#bot_cam = Picamera2(1)

cam.configure(
    cam.create_video_configuration(
        lores={"format": "RGB888", "size": (1280, 720)}
    )
)

"""
top_cam.configure(
    top_cam.create_video_configuration(
        lores={"format": "RGB888", "size": (320, 240)}
    )
)
"""
"""
bot_cam.configure(
    bot_cam.create_video_configuration(
        lores={"format": "RGB888", "size": (320, 240)}
    )
)
"""
cam.start()
#top_cam.start()
#bot_cam.start()

count = 0

while True:
    frame = cam.capture_array()
    #frame = top_cam.capture_array()
    #frame = bot_cam.capture_array()
    brg = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(brg, cv2.COLOR_BGR2GRAY)
    
    found, corners = cv2.findChessboardCorners(gray, CHECKERBOARD, None)
    
    preview = brg.copy()
    
    if found: cv2.drawChessboardCorners(preview, CHECKERBOARD, corners, found)
    
    cv2.imshow("calibration", preview)
    
    key = cv2.waitKey(1)& 0xFF
    if key == ord("s") and found:
        path = os.path.join(SAVE_DIR, f"img_{count:02d}.jpg")
        cv2.imwrite(path, brg)
        print("saved", path)
        count += 1
    elif key == ord("q"):
        break
cam.stop()
#top_cam.stop()
#bot_cam.stop()
cv2.destroyAllWindows()