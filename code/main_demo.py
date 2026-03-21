import os
import time
from picamera2 import Picamera2
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

from grid_sim import clear_grid, show_grid_bw
from led_anim import ExpressionAnimator

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
    
    picam2 = Picamera2()
    picam2.configure(
        picam2.create_video_configuration(
            main={"format": "RGB888", "size": (640, 480)}
        )
    )
    picam2.start()
   
    anim = ExpressionAnimator(h=H, w=W)
    
    last_print = 0.0
    
    prev_t = time.time()
    while True:
        #ok, frame = cap.read()
        #if not ok:
        #    break
        
        
        
        #MediaPipe Tasks expects RGB
        #rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Picamera2 returns an RGB numpy array (H,W,3)
        rgb = picam2.capture_array()
        #run face landmarker
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = landmarker.detect(mp_image)
        
        # blendshapes -> sliders
        bs = blendshapes_to_dict(result.face_blendshapes)
        sliders = anim.blendshape_sliders(bs)
        
        #render grid
        grid = clear_grid(H, W)
        anim.render(grid, sliders)
        
        #show LED grid demo window
        show_grid_bw(grid, scale=SCALE, title= "LED 22x14 (q to quit)")
        show_pixels()
        
        #also show camera
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        cv2.imshow("Camera", bgr) # frame => brg
        
        now = time.time()
        if now - last_print > 1.0:
            if bs:
                print("sliders:", {k: round(v, 2) for k, v in sliders.items()})
            else:
                print("No face detected")
        
        if cv2.waitKey(1)& 0xFF == ord("q"):
            break
        #if key == ord("q"):
        #    break
    #cap.release()
    cv2.destroyAllWindows()
    picam2.stop()
    
if __name__== "__main__":
    main()