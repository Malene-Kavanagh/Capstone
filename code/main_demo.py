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
CHECKERBOARD = (3,5)

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

def fuse_face_views2(top_img, bot_img):
    merged = np.vstack(( top_img, bot_img))
    seam = top_img.shape[0]
    band = 40

    y0 = max(0, seam - band // 2)
    y1 = min(merged.shape[0], seam + band // 2)

    merged[y0:y1, :] = cv2.GaussianBlur(merged[y0:y1, :], (31, 31), 0)

    #merged = cv2.resize(merged, (640, 480))
    return merged

def build_fisheye_maps(K, D, size, balance=0.3):
    w, h = size
    K_new = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
        K, D, (w, h), np.eye(3), balance=balance
    )
    map1, map2 = cv2.fisheye.initUndistortRectifyMap(
        K, D, np.eye(3), K_new, (w, h), cv2.CV_16SC2
    )
    return map1, map2
def undistort_fisheye(img, map1, map2):
    return cv2.remap(img, map1, map2, interpolation=cv2.INTER_LINEAR)

def pinch_warp(img, strength=0.3):
    h, w = img.shape[:2]
    cx = w // 2

    mapx = np.zeros((h, w), np.float32)
    mapy = np.zeros((h, w), np.float32)

    for y in range(h):
        for x in range(w):
            dx = (x - cx) / cx
            factor = 1 - strength * (1 - dx*dx)  # strongest at center

            mapx[y, x] = cx + (x - cx) * factor
            mapy[y, x] = y

    return cv2.remap(img, mapx, mapy, cv2.INTER_LINEAR)

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
    
    """SINGLE CAMERA SYSTEM"""
    #picam2 = Picamera2()
    #picam2.configure(
    #    picam2.create_video_configuration(
    #        main={"format": "RGB888", "size": (640, 480)}
    #    )
    #)
    #picam2.start()
    """
    cam = Picamera2(0)
    cam.configure(
        cam.create_video_configuration(
            main={"format": "RGB888", "size": (1280, 720)},
            lores={"format": "RGB888", "size": (320, 240)}
        )
    )
    
    cam.start()
    """
    
    
    """DOUBLE CAMERA SYSTEM """
    
#     top_cam = Picamera2(0)
    bot_cam = Picamera2(1)
    
    """
    Camera capture sizes
    (320, 240)
    (480, 360)
    (640, 480)  fast but cropped
    (1280,720) larger but still fast
    (1920, 1080) sider, more detail medium speed
    (2304, 1296) near full sensor but slower
    can use lores to have faster processing speeds
    
   """
    
    
#     top_cam.configure(
#         top_cam.create_video_configuration(
#             main={"format": "RGB888", "size": (1920, 1080)},
#             lores={"format": "RGB888", "size": (320, 240)}
#         )
#     )

    bot_cam.configure(
        bot_cam.create_video_configuration(
            main={"format": "RGB888", "size": (2304, 1296)},
            lores={"format": "RGB888", "size": (480, 360)}
        )
    )
    
#     top_cam.start()
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
    
#     K_top = np.load("K_top.npy")
#     D_top = np.load("D_top.npy")
    
#     top_map1, top_map2 = build_fisheye_maps(K_top, D_top, (320, 240))
    
    
    K_bot = np.load("K_bot.npy")
    D_bot = np.load("D_bot.npy")
    
    bot_map1, bot_map2 = build_fisheye_maps(K_bot, D_bot, (320, 240))
    
    
#     K = np.load("K.npy")
#     D = np.load("D.npy")
    
#     top_map1i, top_map2i = build_fisheye_maps(K, D, (1280,720))
    
    K2 = np.load("K2.npy")
    D2 = np.load("D2.npy")
    
    bot_map1i, bot_map2i = build_fisheye_maps(K2, D2, (1280,720))
    
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
        """
        cam_main = cam.capture_array("main")
        cam_lores = cam.capture_array("lores")
        cam_un = undistort_fisheye(cam_main, map1, map2)
        """
        
        #TWO CAMERA SYSTEM
#         top_img = top_cam.capture_array("main")
#         top_lores = top_cam.capture_array("lores")
        
#         bot_img = bot_cam.capture_array("main")
        bot_lores = bot_cam.capture_array("lores")
        
        """ UNDISTORTING IMAGES """
        
#         top_un_lores = undistort_fisheye(top_lores, top_map1, top_map2)
#         bot_un_lores = undistort_fisheye(bot_lores, bot_map1, bot_map2)
        
#         top_un_img = undistort_fisheye(top_img, top_map1i, top_map2i)
#         bot_un_img = undistort_fisheye(bot_img, bot_map1i, bot_map2i)
        
        
        """ ROTATE IMAGE"""
        
        #top_un = cv2.flip(top_un, -1)
        
#         top_img = cv2.flip(top_img,-1)
#         top_lores = cv2.flip(top_lores,-1)
#         top_un_img = cv2.flip(top_un_img,-1)
#         top_un_lores = cv2.flip(top_un_lores,-1)
        #top_img = cv2.flip(top_img, 1)
        #top_lores = cv2.flip(top_lores, 1)
#         cam_un = cv2.rotate(cam_un, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         cam_lores = cv2.rotate(cam_lores, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         cam_main = cv2.rotate(cam_main, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         bot_img = cv2.rotate(bot_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
        bot_lores = cv2.rotate(bot_lores, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         bot_un_img = cv2.rotate(bot_un_img, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         bot_un_lores = cv2.rotate(bot_un_lores, cv2.ROTATE_90_COUNTERCLOCKWISE)
#         bot_pinch_I = pinch_warp(bot_img, 0.3)
#         bot_pinch_L = pinch_warp(bot_lores, 0.3)
        """MERGING IMAGE"""
        
        #blend
#         merged_img = fuse_face_views(top_img, bot_img)
#         merged_lores = fuse_face_views(top_lores, bot_lores)
#         merged_un_img = fuse_face_views(top_un_img, bot_un_img)
#         merged_un_lores = fuse_face_views(top_un_lores, bot_un_lores)
        # then feed into mediapipe
        media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=bot_lores)
#         media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cam_un)
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
        
#         cv2.imshow("cam_un", cv2.cvtColor(cam_un, cv2.COLOR_RGB2BGR))
#         cv2.imshow("cam_lores", cv2.cvtColor(cam_lores, cv2.COLOR_RGB2BGR))
#         cv2.imshow("cam_main", cv2.cvtColor(cam_main, cv2.COLOR_RGB2BGR))
        
        # TWO CAMERA SYSTEM
#         cv2.imshow("Top lores", cv2.cvtColor(top_lores, cv2.COLOR_RGB2BGR))
        cv2.imshow("Bottom lores", cv2.cvtColor(bot_lores, cv2.COLOR_RGB2BGR))
        
#         cv2.imshow("Bottom_pinch_Img", cv2.cvtColor(bot_pinch_I, cv2.COLOR_RGB2BGR))
#         cv2.imshow("Bottom_Pinch_lores", cv2.cvtColor(bot_pinch_L, cv2.COLOR_RGB2BGR))
        
#         cv2.imshow("Top main", cv2.cvtColor(top_img, cv2.COLOR_RGB2BGR))
#         cv2.imshow("Bottom main", cv2.cvtColor(bot_img, cv2.COLOR_RGB2BGR))
        
#         cv2.imshow("Top_Undis_main", cv2.cvtColor(top_un_img, cv2.COLOR_RGB2BGR))
#         cv2.imshow("Bottom_Undis_loRes", cv2.cvtColor(bot_un_lores, cv2.COLOR_RGB2BGR))
        
#         cv2.imshow("Merged_img", cv2.cvtColor(merged_img, cv2.COLOR_RGB2BGR))
#         cv2.imshow("mergedLores", cv2.cvtColor(merged_lores, cv2.COLOR_RGB2BGR))
#         cv2.imshow("merged_un_lores", cv2.cvtColor(merged_un_lores, cv2.COLOR_RGB2BGR))
#         cv2.imshow("merged_un_img", cv2.cvtColor(merged_un_img, cv2.COLOR_RGB2BGR))
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
#     top_cam.stop()
    bot_cam.stop()
    #cam.stop()
    
if __name__== "__main__":
    main()