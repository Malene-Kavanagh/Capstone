import math
import numpy as np
from dataclasses import dataclass
from led_map import LED_MAP

from grid_sim import set_px, draw_hline, draw_vline, draw_line

def clamp01(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x

@dataclass
class SmoothValue:
    v: float = 0.0
    alpha: float = 0.25 #higher = snappier, lower = smoother
    
    def update(self, x: float) -> float:
        x = float(x)
        self.v = (1.0 - self.alpha) * self.v + self.alpha *x
        return self.v

class ExpressionAnimator:
    """
    renders a simple face on a 15x22 grid:
        - eyebrows furrow
        - eyes blink and look around
        - mouth smiles
        - jaw open opens the mouth
    """
    
    def __init__(self, h: int =15, w: int = 22):
        self.h, self.w = h, w
        
        #smoothing for jitter lower = smoother
        self.smile = SmoothValue(alpha=0.15) #25
        self.frown = SmoothValue(alpha=0.15) #25
        self.jaw = SmoothValue(alpha=0.30)   #25
        self.blinkL = SmoothValue(alpha=0.35)
        self.blinkR = SmoothValue(alpha=0.35)
        self.look_in_R = SmoothValue(alpha=0.15) #20
        self.look_in_L = SmoothValue(alpha=0.15) #20
        self.look_out_R = SmoothValue(alpha=0.15) #20
        self.look_out_L = SmoothValue(alpha=0.15) #20
        self.look_up = SmoothValue(alpha=0.12) # 25
        self.look_down = SmoothValue(alpha=0.12) #25
        self.eyebrow_down_L = SmoothValue(alpha=0.10)
        self.eyebrow_down_R = SmoothValue(alpha=0.10)
        
        
    def _get(self, bs: dict, key: str, default: float = 0.0) -> float:
        return float(bs.get(key, default))
    
    def blendshape_sliders(self, bs: dict) -> dict:
        """
        Map mediaPipe blendshape names -> sliders [0...1]
        """
        #smile
        smile_raw = 0.5 * (
            self._get(bs, "mouthSmileLeft") + self._get(bs, "mouthSmileRight")
        )
        
        frown_raw = 0.5 *(
            self._get(bs, "mouthFrownLeft") + self._get(bs,"mouthFrownRight")
            )
        #jaw open
        jaw_raw = self._get(bs, "jawOpen")
        
        #Blink (higher = more closed)
        blinkL_raw = self._get(bs, "eyeBlinkLeft")
        blinkR_raw = self._get(bs, "eyeBlinkRight")
        look_in_R_raw = self._get(bs, "eyeLookInRight")
        look_in_L_raw = self._get(bs, "eyeLookInLeft")
        look_out_R_raw = self._get(bs, "eyeLookOutRight")
        look_out_L_raw = self._get(bs, "eyeLookOutLeft")
        look_up_raw = self._get(bs, "eyeLookUpLeft")
        look_down_raw = self._get(bs, "eyeLookDownLeft")
        eyebrow_down_L_raw = self._get(bs, "browDownLeft")
        eyebrow_down_R_raw = self._get(bs, "browDownRight")
        
        return {
            "smile": clamp01(self.smile.update(smile_raw)),
            "frown": clamp01(self.frown.update(frown_raw)),
            "jaw":clamp01(self.jaw.update(jaw_raw)),
            "blinkL": clamp01(self.blinkL.update(blinkL_raw)),
            "blinkR": clamp01(self.blinkR.update(blinkR_raw)),
            "look_in_R": clamp01(self.look_in_R.update(look_in_R_raw)),
            "look_in_L": clamp01(self.look_in_L.update(look_in_L_raw)),
            "look_out_R": clamp01(self.look_out_R.update(look_out_R_raw)),
            "look_out_L": clamp01(self.look_out_L.update(look_out_L_raw)),
            "look_up": clamp01(self.look_up.update(look_up_raw)),
            "look_down": clamp01(self.look_down.update(look_down_raw)),
            "eyebrow_down_L": clamp01(self.eyebrow_down_L.update(eyebrow_down_L_raw)),
            "eyebrow_down_R": clamp01(self.eyebrow_down_R.update(eyebrow_down_R_raw)),
            
        }
    
    def draw_eye_by_name(self, grid, x, y, blink, name, side="left"):
        if name == "round":
            self.draw_eye_O(grid, x, y, blink)
        elif name == "square":
            self.draw_eye_square(grid, x, y, blink)
#         elif name == "diamond":
#             self.draw_eye_diamond(grid, x, y, blink)
        elif name == "tired":
            self.draw_eye_sleepy(grid, x, y, blink)
        elif name == "angry":
            self.draw_eye_angry(grid, x, y, blink, side=side)
        elif name == "heart":
            self.draw_eye_heart(grid, x, y, blink)
        else:
            self.draw_eye_O(grid, x, y, blink)

    def draw_mouth_by_name(self, grid, cx, mouth_y, smile, frown, jaw, name):
        if name == "basic":
            self.draw_mouth(grid, cx, mouth_y, smile, frown, jaw)
        elif name == "pointy_up":
            self.draw_mouth_pointy_up(grid, cx, mouth_y, smile, frown, jaw)
        elif name == "pointy_down":
            self.draw_mouth_pointy_down(grid, cx, mouth_y, smile, frown, jaw)
#         elif name == "meh":
#             self.draw_mouth(grid, cx, mouth_y, 0.0, max(frown, 0.4), jaw)
        else:
            self.draw_mouth(grid, cx, mouth_y, smile, frown, jaw)
    
    def blink(self, grid, x, y):
        set_px(grid, x-1, y, True)
        set_px(grid, x, y, True)
        set_px(grid, x+1, y, True)
    
    def draw_eye_O(self, grid, x, y, blink):
        if blink > 0.03:
            #eye closed line
            self.blink(grid, x, y)
        else:
            set_px(grid, x - 1, y, True)
            set_px(grid, x + 1, y, True)
            set_px(grid, x - 1, y +1, True)
            set_px(grid, x + 1, y +1, True)
            set_px(grid, x, y - 1, True) #bottom
            set_px(grid, x, y + 2, True) #top
    
    def draw_eye_square(self, grid, x, y, blink):
        if blink > 0.03:
            #eye closed line
            self.blink(grid, x, y) 
        else:
            draw_hline(grid, x-1, x+1, y-1)
            draw_hline(grid, x-1, x+1, y+1)
            draw_vline(grid, x-1, y-1, y+1)
            draw_vline(grid, x+1, y-1, y+1)
    
    def draw_eye_sleepy(self, grid, x, y, blink):
        set_px(grid, x, y, True)
        if blink > 0.03:
            #eye closed line
            self.blink(grid, x, y)
        else:
            draw_hline(grid, x-2, x+2, y)
            set_px(grid, x-1, y+1, True)
            set_px(grid, x+1, y+1, True)
            
    def draw_eye_angry(self, grid, x, y, blink, side="left"):
        if blink > 0.03:
            self.blink(grid, x, y)
        else:
            draw_hline(grid, x-1, x+1, y+1)
            if side == "left":
                set_px(grid, x-1, y-1, True)
                set_px(grid, x,   y,   True)
                set_px(grid, x+1, y+1, True)
            else:
                set_px(grid, x+1, y-1, True)
                set_px(grid, x,   y,   True)
                set_px(grid, x-1, y+1, True)
    
    def draw_eye_heart(self, grid, x, y, blink):
        if blink > 0.03:
            self.blink(grid, x, y)
        else:
            set_px(grid, x-1, y-1, True)
            set_px(grid, x+1, y-1, True)
            set_px(grid, x-2, y,   True)
            set_px(grid, x,   y,   True)
            set_px(grid, x+2, y,   True)
            set_px(grid, x-1, y+1, True)
            set_px(grid, x+1, y+1, True)
            set_px(grid, x,   y+2, True)
 
    def draw_mouth(self, grid, cx, mouth_y, smile, frown, jaw):
        h, w = self.h, self.w
        #mouth width and curve based on smile
        # 2 + 2
        mouth_half = int(2 + 1.5 * max(smile, frown)) #Fwidth grows with smile
        x0 = cx - mouth_half
        x1 = cx + mouth_half
        
        curve = smile - frown
        
        
        mid_y = mouth_y +int(round(2 * (1.0 - abs(curve)))) # flatter when smiling
      
        # Corner y (same both sides)
        #mouth curve: corners lift as smile increases
        # y_offset is negative when smiling (lift corners)
        if curve >= 0:
            lift = int(round(3 * abs(curve)))
            corner_y = mid_y - lift
        elif curve <= 0:
            lift = int(round(3 * abs(curve)))
            corner_y = mid_y + lift
        
        
        
        # How far the "ramps" go inward from each corner (keep small for 14-wide)
        ramp = min(2, mouth_half)              # 1..2

        # Left ramp: from (x0, corner_y) down/up to (x0+ramp, mid_y)
        for i in range(ramp + 1):
            # linear interpolation, rounded, symmetric by construction
            y = int(round(corner_y + (mid_y - corner_y) * (i / ramp))) if ramp > 0 else mid_y
            set_px(grid, x0 + i, y, True)

        # Right ramp: mirror of left ramp
        for i in range(ramp + 1):
            y = int(round(corner_y + (mid_y - corner_y) * (i / ramp))) if ramp > 0 else mid_y
            set_px(grid, x1 - i, y, True)

        # Middle segment: flat line between ramps
        draw_hline(grid, x0 + ramp, x1 - ramp, mid_y,LED_MAP)
        
        #jaw open: open a vertical gap in the middle
        if jaw > 0.04:
            if smile > 0.2:
                draw_hline(grid, x0, x1, corner_y-1, LED_MAP)
            elif frown > 0.2:
                draw_hline(grid, x0, x1, corner_y+1,LED_MAP)
            else:
                open_amt = int(round(1 + 3 * jaw))
                y_top = mid_y + 1
                y_bot = min(h - 2, mid_y + open_amt)
                
                draw_vline(grid, cx - 3, y_top, y_bot-1,LED_MAP)
                draw_vline(grid, cx + 3, y_top, y_bot-1, LED_MAP)
                draw_hline(grid, cx- 2, cx+ 2, y_bot, LED_MAP)
    
    
    def draw_mouth_pointy_up(self, grid, cx, mouth_y, smile, frown, jaw):
        h, w = self.h, self.w
        
        #how wide mouth is
        mouth_half = int(round(2 + 2 *smile + 1 * frown))
        mouth_half = max(2, min(4, mouth_half))
        
        x0 = cx - mouth_half
        x1 = cx + mouth_half
        
        #certer of pointy mouth V
        center_y = mouth_y + 2
        
        #corners of mouth rise
        corner_lift = int(round(1 + 2 * smile - 1 * frown))
        corner_lift = max(0, min(3,corner_lift))
        
        corner_y = center_y - corner_lift
        open_y = min(h - 1, center_y + int(round(1 + 2 * jaw)))
        #draw left and right sides
        draw_line(grid, x0, corner_y, cx, center_y)
        draw_line(grid, cx, center_y, x1, corner_y)
        
        if jaw > 0.08:
            top_y = max(0, corner_y -1)
            draw_hline(grid, x0, x1, top_y)
            
            #mouth opening wider
            
            if jaw > 0.12: #0.18
                draw_line(grid, x0, top_y, x0+1, corner_y)
                draw_line(grid, cx-1, top_y, cx+1, open_y)
            
            if jaw > 0.16: #0.28
                open_y = min(h-1, center_y +int(round(1+2 * jaw)))
                draw_hline(grid, cx-1, cx +1, open_y)
                
    def draw_mouth_pointy_down(self, grid, cx, mouth_y, smile, frown, jaw):
        h, w = self.h, self.w
        
        #how wide mouth is
        mouth_half = int(round(2 + 2 *smile + 1 * frown))
        mouth_half = max(2, min(4, mouth_half))
        
        x0 = cx - mouth_half
        x1 = cx + mouth_half
        
        #certer of pointy mouth V
        center_y = mouth_y
        
        #corners of mouth rise
        corner_drop = int(round(1 + 2 * smile - 1 * frown))
        corner_drop = max(0, min(3,corner_drop))
        
        corner_y = center_y + corner_drop
        open_y = min(h - 1, center_y + int(round(1 + 2 * jaw)))
        #draw left and right sides
        draw_line(grid, x0, corner_y, cx, center_y)
        draw_line(grid, cx, center_y, x1, corner_y)
        
        if jaw > 0.08:
            bottom_y = max(0, corner_y +2)
            draw_hline(grid, x0, x1, bottom_y)
            
            #mouth opening wider
            
            if jaw > 0.12: #0.18
#                 draw_line(grid, x0, bottom_y, x0+1, corner_y)
                draw_line(grid, cx-1, bottom_y, cx+1, open_y)
            
            if jaw > 0.16: #0.28
                open_y = min(h-1, center_y +int(round(1+2 * jaw)))
                draw_hline(grid, cx-1, cx +1, open_y)
        
   
        
    
    def render(self, grid: np.ndarray, sliders: dict, eye_shape = "round", mouth_shape="basic"):
        """
        Draw into grid (uint8 hxw).
        """
        
        h, w = self.h, self.w
        
        smile = sliders["smile"]
        frown = sliders["frown"]
        jaw = sliders["jaw"]
        blinkL = sliders["blinkL"]
        blinkR = sliders["blinkR"]
        look_in_R = sliders["look_in_R"]
        look_in_L = sliders["look_in_L"]
        look_out_R = sliders["look_out_R"]
        look_out_L = sliders["look_out_L"]
        look_up = sliders["look_up"]
        look_down = sliders["look_down"]
        eyebrow_down_L = sliders["eyebrow_down_L"]
        eyebrow_down_R = sliders["eyebrow_down_R"]
        
        
        #face layout anchors (tuned for 22x14
        cx = w // 2
        eye_y = int(h * 0.25)
        mouth_y = int(h * 0.55)
        
        left_eye_x = cx - 4
        right_eye_x = cx + 4
        
        # X-AXIS EYE MOVEMENT
        eye_range = 2.0
        
        right_sig =  look_in_R - look_out_R
        left_sig = look_out_L - look_in_L
        
        right_eye_x_target =(right_eye_x) + right_sig * eye_range
        left_eye_x_target = (left_eye_x) + left_sig * eye_range
        
#         alpha = 1.5 #2.0
#         right_eye_x += (right_eye_x - right_eye_x_target) * alpha
#         left_eye_x += (left_eye_x - left_eye_x_target) * alpha
        alpha = 1.1   # between 0 and 1
        right_eye_x += (right_eye_x_target - right_eye_x) * alpha
        left_eye_x += (left_eye_x_target - left_eye_x) * alpha
        
        
        # Y-AXIS EYE MOVEMENT
        
        up_down_sig = look_down - look_up
        eye_y_target = eye_y +up_down_sig * 1.6
        
        #eye: open = 6 pixels with hole, blink = horizontal line / nothing
        if eyebrow_down_L > 0.01:
            bd_left = left_eye_x + 2
            bd_right = left_eye_x - 2
            draw_hline(grid, int(round(bd_left)), int(round(bd_right)),int(round(eye_y_target - 1)), LED_MAP)
        
        if eyebrow_down_R > 0.01:
            bd_left = right_eye_x - 2
            bd_right = right_eye_x + 2
            draw_hline(grid, int(round(bd_left)), int(round(bd_right)),int(round(eye_y_target - 1)), LED_MAP)
#             
#         self.draw_eye_O(grid, int(round(left_eye_x)), int(round(eye_y_target)), blinkL)
#         self.draw_eye_O(grid, int(round(right_eye_x)), int(round(eye_y_target)), blinkR)
#         
#         self.draw_mouth(grid, cx, mouth_y, smile, frown, jaw)
#
        self.draw_eye_by_name(
            grid,
            int(round(left_eye_x)),
            int(round(eye_y_target)),
            blinkL,
            eye_shape,
            side="left"
        )

        self.draw_eye_by_name(
            grid,
            int(round(right_eye_x)),
            int(round(eye_y_target)),
            blinkR,
            eye_shape,
            side="right"
        )

        self.draw_mouth_by_name(
            grid,
            cx,
            mouth_y,
            smile,
            frown,
            jaw,
            mouth_shape
        )
        
        
                    