# DEMO
# demo.py
import os
import time
from picamera2 import Picamera2
import cv2
import glob
import board
import neopixel
from gpiozero import Button as GPIOButton 
import colorsys
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from dataclasses import dataclass

from grid_sim import clear_grid, show_grid_bw, set_px, draw_hline, draw_vline
from led_anim import ExpressionAnimator
from led_map import LED_MAP
from led_output import draw_to_led

H, W = 22, 15  #the LED grid: 22 tall 15 wide
SCALE = 28
MODEL_PATH = "face_landmarker.task"


@dataclass
class FaceSettings:
    eye_shape_idx: int = 0
    mouth_shape_idx: int = 0
    face_color_idx: int = 0
    ear_color_idx: int = 0
    ear_anim_idx: int = 0

EYE_SHAPES = ["round", "square", "tired", "angry", "heart"]
MOUTH_SHAPES = ["basic", "pointy_up", "pointy_down"]
FACE_COLORS = [
    (50, 10, 50),
    (50, 0, 10),
    (0, 50, 50),
    (0, 0, 50),
    (50, 10, 35),
]
EAR_COLORS = [
    (50, 10, 50),
    (50, 0, 10),
    (0, 50, 50),
    (0, 0, 50),
    (50, 10, 35),
]
EAR_ANIM = ["solid", "chase", "pulse", "blink", "rainbow"]

LIVE = 0
MENU_EYES = 1
MENU_MOUTH = 2
MENU_FACE_COLOR = 3
MENU_EAR_COLOR = 4
MENU_EAR_ANIM = 5


class UIState:
    def __init__(self):
        self.mode = LIVE
    def in_menu(self):
        return self.mode != LIVE
    def enter_menu(self):
        self.mode = MENU_EYES
    def next_menu(self):
        if self.mode == MENU_EAR_ANIM:
            self.mode = MENU_EYES
        else:
            self.mode += 1
    def save_and_exit(self):
        self.mode = LIVE

def cycle_current_option(settings, ui):
    if ui.mode == MENU_EYES:
        settings.eye_shape_idx = (settings.eye_shape_idx + 1) % len(EYE_SHAPES)
    elif ui.mode == MENU_MOUTH:
        settings.mouth_shape_idx = (settings.mouth_shape_idx + 1) % len(MOUTH_SHAPES)
    elif ui.mode == MENU_FACE_COLOR:
        settings.face_color_idx = (settings.face_color_idx + 1) % len(FACE_COLORS)
    elif ui.mode == MENU_EAR_COLOR:
        settings.ear_color_idx = (settings.ear_color_idx + 1) % len(EAR_COLORS)
    elif ui.mode == MENU_EAR_ANIM:
        settings.ear_anim_idx = (settings.ear_anim_idx + 1) % len(EAR_ANIM)
        
LONG_PRESS_TIME = 0.8

class Button:
    def __init__(self, pin):
        self.btn = GPIOButton(pin, pull_up = True, bounce_time=0.05)
        
        self.last_raw = False
        self.press_time = None
        self.long_fired = False
    
    def update(self):
        short_press = False
        long_press = False
        
        raw = self.btn.is_pressed # true when pressed 
        now = time.monotonic()
        
        #pressed
        if not self.last_raw and raw:
            self.press_time = now
            self.long_fired = False
            
        #held
        if raw and self.press_time is not None and not self.long_fired:
            if now - self.press_time >= LONG_PRESS_TIME:
                long_press = True
                self.long_fired = True
        
        #released
        if self.last_raw and not raw:
            if self.press_time is not None and not self.long_fired:
                short_press = True
            self.press_time = None
            self.long_fired = False
            
        
        self.last_raw = raw
        return short_press, long_press
    

def update_button_events(button1, button2):
    b1_short, b1_long = button1.update()
    b2_short, b2_long = button2.update()
    return b1_short, b1_long, b2_short, b2_long

def blendshapes_to_dict(face_blendshapes):
    """
    face_blendshapes: list of category objects per face
    convert first face to {name: score}
    """
    if not face_blendshapes:
        return {}
    out = {}
    for c in face_blendshapes[0]:
        out[c.category_name] = float(c.score)
    return out

def get_live_sliders(result, anim):
    bs = blendshapes_to_dict(result.face_blendshapes)
#     if result is None:
#         bs = {}
#     else:
#         bs = blendshapes_to_dict(result.face_blendshapes)
#
    sliders = anim.blendshape_sliders(bs)   
    return bs, sliders
    
def render_live_mode(grid, anim, sliders, settings):
    eye_shape = EYE_SHAPES[settings.eye_shape_idx]
    mouth_shape = MOUTH_SHAPES[settings.mouth_shape_idx]

    anim.render(grid, sliders, eye_shape=eye_shape, mouth_shape=mouth_shape)
    
def colorwheel(pos):
    pos = pos % 256

    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    else:
        pos -= 170
        return (pos * 3, 0, 255 - pos * 3)
    
def render_menu_preview( grid, anim, ui_mode, settings):
        h, w = grid.shape
        cx = w // 2
        eye_y = int(h * 0.25)
        mouth_y = int(h * 0.55)
        
        left_eye_x = cx - 4
        right_eye_x = cx + 4
        
        render_menu_ears(grid, ui_mode)
        
        # eye preview
        eye_shape = EYE_SHAPES[settings.eye_shape_idx]
        if eye_shape == "round":
            anim.draw_eye_O(grid, left_eye_x, eye_y, 0.0)
            anim.draw_eye_O(grid, right_eye_x, eye_y, 0.0)
        elif eye_shape == "square":
            anim.draw_eye_square(grid, left_eye_x, eye_y, 0.0)
            anim.draw_eye_square(grid, right_eye_x, eye_y, 0.0)
        elif eye_shape == "tired":
            anim.draw_eye_sleepy(grid, left_eye_x, eye_y, 0.0)
            anim.draw_eye_sleepy(grid, right_eye_x, eye_y, 0.0)
#         elif eye_shape == "diamond":
#             anim.draw_eye_diamond(grid, left_eye_x, eye_y, 0.0)
#             anim.draw_eye_diamond(grid, right_eye_x, eye_y, 0.0)
        elif eye_shape == "angry":
            anim.draw_eye_angry(grid, left_eye_x, eye_y, 0.0)
            anim.draw_eye_angry(grid, right_eye_x, eye_y, 0.0)
        elif eye_shape == "heart":
            anim.draw_eye_heart(grid, left_eye_x, eye_y, 0.0)
            anim.draw_eye_heart(grid, right_eye_x, eye_y, 0.0)
        
        # mouth preview
        smile = 0.4
        frown = 0.0
        jaw = 0.0
        mouth_shape = MOUTH_SHAPES[settings.mouth_shape_idx]
        if mouth_shape == "basic":
            anim.draw_mouth(grid, cx, mouth_y, smile, frown, jaw)
        elif mouth_shape == "pointy_up":
            anim.draw_mouth_pointy_up(grid, cx, mouth_y, smile, frown, jaw)
        elif mouth_shape == "pointy_down":
            anim.draw_mouth_pointy_down(grid, cx, mouth_y, smile, frown, jaw)
#         elif mouth_shape == "meh":
        
        
        if ui_mode == MENU_EYES:
            draw_hline(grid, left_eye_x -2, right_eye_x + 2, eye_y - 3)
        elif ui_mode == MENU_MOUTH:
            draw_hline(grid, cx -4, cx +4, mouth_y -2)
        elif ui_mode == MENU_FACE_COLOR:
            draw_vline(grid, 0, 8, 14)
        elif ui_mode == MENU_EAR_COLOR:
            draw_vline(grid, w-1, 8, 14)
        elif ui_mode == MENU_EAR_ANIM:
            draw_hline(grid, 0, w-1, h-1)

def render_menu_ears(grid, menu_state):
    #left
        set_px(grid, 0, 2, True)
        set_px(grid, 1, 1, True)
        set_px(grid, 1, 2, True)
        set_px(grid, 2, 0, True)
        set_px(grid, 2, 1, True)
        set_px(grid, 2, 2, True)
       #right 
        w = grid.shape[1]
        set_px(grid, w-1, 2, True)
        set_px(grid, w-2, 1, True)
        set_px(grid, w-2, 2, True)
        set_px(grid, w-3, 0, True)
        set_px(grid, w-3, 1, True)
        set_px(grid, w-3, 2, True)
        
        #extra menu indicator
        if menu_state == MENU_EAR_COLOR:
            draw_vline(grid, 0, 6, 12)
            draw_vline(grid, w - 1, 6, 12)
        elif menu_state == MENU_EAR_ANIM:
            draw_hline(grid, 0, w - 1, grid.shape[0] - 1)

def apply_led_output(grid, pixels, settings):
    face_color = FACE_COLORS[settings.face_color_idx]
    draw_to_led(grid, pixels, LED_MAP, on_color=face_color)

def apply_ear_output(ear1, ear2, settings, frame_count):
    color = EAR_COLORS[settings.ear_color_idx]
    anim = EAR_ANIM[settings.ear_anim_idx]

    n1 = len(ear1)
    n2 = len(ear2)
    n = min(n1, n2)

    # clear first
    for i in range(n1):
        ear1[i] = (0, 0, 0)
    for i in range(n2):
        ear2[i] = (0, 0, 0)

    if anim == "solid":
        for i in range(n):
            ear1[i] = color
            ear2[i] = color

    elif anim == "blink":
        on = ((frame_count // 10) % 2) == 0
        c = color if on else (0, 0, 0)
        for i in range(n):
            ear1[i] = c
            ear2[i] = c

    elif anim == "chase":
        idx = (frame_count // 2) % n
        ear1[idx] = color
        ear2[idx] = color

    elif anim == "pulse":
        level = 0.25 + 0.75 * abs(np.sin(frame_count * 0.12))
        c = tuple(int(v * level) for v in color)
        for i in range(n):
            ear1[i] = c
            ear2[i] = c

    elif anim == "rainbow":
        for i in range(n):
            c = colorwheel((frame_count * 4 + i * 256 // max(1, n)) % 256)
            ear1[i] = c
            ear2[i] = c

    ear1.show()
    ear2.show()

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
    cam = Picamera2(0)
    cam.configure(
        cam.create_video_configuration(
            main={"format": "RGB888", "size": (2304, 1296)},
            lores={"format": "RGB888", "size": (480, 360)}
        )
    )
    
    cam.start()
    time.sleep(1.0)
    
    LED_COUNT = 330
    LED_PIN = board.D4
    EAR_COUNT = 30
    LED_EAR1 = board.D27 #left ear
    LED_EAR2 = board.D17 #right ear
    
    pixels = neopixel.NeoPixel(
        LED_PIN,
        LED_COUNT,
        brightness=0.05,
        auto_write=False)
    
    ear1 = neopixel.NeoPixel(
        LED_EAR1,
        EAR_COUNT,
        brightness=0.05,
        auto_write=False)
    
    ear2 = neopixel.NeoPixel(
        LED_EAR2,
        EAR_COUNT,
        brightness=0.05,
        auto_write=False)
    
    anim = ExpressionAnimator(h=H, w=W)
    
    last_print = 0.0
    
    prev_t = time.time()

    settings = FaceSettings()
    ui=UIState()
    
    button1 = Button(5)
    button2 = Button(6)
    frame_count = 0
    #the loop for camera and output
    while True:
        b1_short, b1_long, b2_short, b2_long = update_button_events(button1, button2)
    
        if ui.mode == LIVE:
            if b1_long and b2_long:
                pixels.fill((0,0,0))
                ear1.fill((0,0,0))
                ear2.fill((0,0,0))
                pixels.show()
                ear1.show()
                ear2.show()
                break
            if b1_long:
                ui.enter_menu()
        else:
            if b1_long:
                ui.save_and_exit()
            elif b1_short:
                ui.next_menu()
            elif b2_short:
                cycle_current_option(settings, ui)
        
        cam_lores = cam. capture_array("lores")
        cam_lores = cv2.rotate(cam_lores, cv2.ROTATE_90_COUNTERCLOCKWISE)
        
        media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cam_lores)
        results = landmarker.detect(media_image)
#         last_results = None
# 
#         if frame_count % 2 == 0:
#             media_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=cam_lores)
#             last_results = landmarker.detect(media_image)
# 
#         results = last_results
        
        #render grid
        grid = clear_grid(H, W)
        
                #Menu / Live
        if ui.mode == LIVE:
            bs, sliders = get_live_sliders(results, anim)
            render_live_mode(grid, anim, sliders, settings)
        else:
            render_menu_preview(grid, anim, ui.mode, settings)
        
        #setting the leds
        apply_led_output(grid, pixels, settings)
        apply_ear_output(ear1, ear2, settings, frame_count)
        frame_count += 1
        #show LED grid demo window
        show_grid_bw(grid, scale=SCALE, title= "LED 22x14 (q to quit)")
        cv2.imshow("Camera Low Resolution", cv2.cvtColor(cam_lores, cv2.COLOR_RGB2BGR))
        
        #other exit case
        if cv2.waitKey(1)& 0xFF == ord("q"):
            pixels.fill((0,0,0))
            ear1.fill((0,0,0))
            ear2.fill((0,0,0))
            pixels.show()
            ear1.show()
            ear2.show()
            break
    cv2.destroyAllWindows()
    cam.stop()   
        
if __name__== "__main__":
    main()    