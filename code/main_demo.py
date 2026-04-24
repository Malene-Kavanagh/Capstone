import os
import time
from picamera2 import Picamera2
import cv2
import glob
import board
import neopixel
import colorsys
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from grid_sim import clear_grid, show_grid_bw
from led_anim import ExpressionAnimator
from led_map import LED_MAP
from led_output import draw_to_led

#main_demo.py

H, W = 22, 15  #the LED grid: 14 tall 22 wide
SCALE = 28

MODEL_PATH = "face_landmarker.task"

def blendshapes_to_dict(face_blendshapes):
    """
    face_blendshapes: list of category objects per face
    convert first face to {name: score}
    """
    if not face_blendshapes:
        return {}
    # face_blendshapes [0] is a list[category]
    out = {}
    for c in face_blendshapes[0]:
        out[c.category_name] = float(c.score)
    return out

def fuse_face_views(top_img, bot_img):
    # Make bottom match top size
    bot_resized = cv2.resize(bot_img, (top_img.shape[1], top_img.shape[0]))
    
    merged = np.vstack(( top_img, bot_resized))
#     y0 = 120
#     y1 = 840
#     x0 = 40
#     x1 = 600
#     cropped = merged[y0:y1,x0,x1]
    
    seam = top_img.shape[0]
    band = 40

    y0 = max(0, seam - band // 2)
    y1 = min(merged.shape[0], seam + band // 2)

    merged[y0:y1, :] = cv2.GaussianBlur(merged[y0:y1, :], (31, 31), 0)

    #merged = cv2.resize(merged, (640, 480))
    return merged

def main():
    # --- face landmarker setup ---
    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(f"Model not found: {MODEL_PATH}")
    
    base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
    options = vision.FaceLandmarkerOptions(
        base_options=base_options,
        output_face_blendshapes=True, #important for expression sliders
        output_facial_transformation_matrixes=False,
        num_faces=1
    )
    landmarker = vision.FaceLandmarker.create_from_options(options)
    
    #cap = cv2.VideoCapture(0)
    #if not cap.isOpened():
    #    raise RuntimeError("Could not open camera")
    
    #SINGLE CAMERA 
    #picam2 = Picamera2()
    #picam2.configure(
    #    picam2.create_video_configuration(
    #        main={"format": "RGB888", "size": (640, 480)}
    #    )
    #)
    #picam2.start()
    
    # DOUBLE CAMERA SYSTEM#
    top_cam = Picamera2(0)
    bot_cam = Picamera2(1)
    
    """
    Camera capture sizes
    (640, 480)  fast but cropped
    (1280,720) larger but still fast
    (1920, 1080) sider, more detail medium speed
    (2304, 1296) near full sensor but slower
    can use lores to have faster processing speeds
    
    
    bot_cam.configure(
        bot_cam.create_video_configuration(
            main={"format": "RGB888", "size": (1280, 720)}
        )
    )
    """
    top_cam.configure(
        top_cam.create_video_configuration(
            main={"format": "RGB888", "size": (1280, 720)},
            lores={"format": "RGB888", "size": (320, 240)}
        )
    )

    bot_cam.configure(
        bot_cam.create_video_configuration(
            main={"format": "RGB888", "size": (1280,1080)},
            lores={"format": "RGB888", "size": (320, 240)}
        )
    )
    
    top_cam.start()
    bot_cam.start()
    time.sleep(1.0)
    
    LED_COUNT = 330
    LED_PIN = board.D4
    
    
    pixels = neopixel.NeoPixel(
        LED_PIN,
        LED_COUNT,
        brightness=0.05,
        auto_write=False
    )
    
    
    anim = ExpressionAnimator(h=H, w=W)
    
    last_print = 0.0
    
    prev_t = time.time()
    while True:
        #ok, frame = cap.read()
        #if not ok:
        #    break
        
        
        
        #MediaPipe Tasks expects RGB
        #rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        #ONE CAMERA SYSTEM
        ## Picamera2 returns an RGB numpy array (H,W,3)
        #rgb = picam2.capture_array()
        #
        ##run face landmarker
        #mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        #result = landmarker.detect(mp_image)
        #
        ## blendshapes -> sliders
        #bs = blendshapes_to_dict(result.face_blendshapes)
        #sliders = anim.blendshape_sliders(bs)
        #
        
        #TWO CAMERA SYSTEM
        top_img = top_cam.capture_array("main")
        top_lores = top_cam.capture_array("lores")
        
        bot_img = bot_cam.capture_array("main")
        bot_lores = bot_cam.capture_array("lores")
        
        top_img = cv2.flip(top_img,-1)
        top_lores = cv2.flip(top_lores,-1)
        #top_img = cv2.flip(top_img, 1)
        #top_lores = cv2.flip(top_lores, 1)
        #bot_img = cv2.rotate(bot_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        #blend
        merged = fuse_face_views(top_img, bot_img)
        merged_lores = fuse_face_views(top_lores, bot_lores)
        # then feed into mediapipe
        media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=merged_lores)
        result = landmarker.detect(media_image)
        bs = blendshapes_to_dict(result.face_blendshapes)
        
        sliders = anim.blendshape_sliders(bs)
        
        
        #render grid
        grid = clear_grid(H, W)
        anim.render(grid, sliders)
        
        draw_to_led(grid, pixels, LED_MAP)
        
        
        #show LED grid demo window
        show_grid_bw(grid, scale=SCALE, title= "LED 22x14 (q to quit)")
        #show_pixels()
        
        # SINGLE CAMERA SYSTEM
        ##also show camera
        #bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        #cv2.imshow("Camera", bgr) # frame => brg
        
        # TWO CAMERA SYSTEM
        cv2.imshow("Top", cv2.cvtColor(top_img, cv2.COLOR_RGB2BGR))
        cv2.imshow("Bottom", cv2.cvtColor(bot_img, cv2.COLOR_RGB2BGR))
        cv2.imshow("Merged", cv2.cvtColor(merged, cv2.COLOR_RGB2BGR))
        cv2.imshow("Lores", cv2.cvtColor(merged_lores, cv2.COLOR_RGB2BGR))
        now = time.time()
        if now - last_print > 1.0:
            if bs:
                print("sliders:", {k: round(v, 2) for k, v in sliders.items()})
            else:
                print("No face detected")
        
        if cv2.waitKey(1)& 0xFF == ord("q"):
            pixels.fill((0,0,0))
            pixels.show()
            break
        #if key == ord("q"):
        #    break
    #cap.release()
    cv2.destroyAllWindows()
    # ONE CAMERA SYSTEM
    #picam2.stop()
    
    # TWO CAMERA SYSTEM
    top_cam.stop()
    bot_cam.stop()
    
if __name__== "__main__":
    main()