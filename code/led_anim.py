import math
import numpy as np
from dataclasses import dataclass

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
        - eyes blink
        - mouth smiles
        - jaw open opens the mouth
    """
    
    def __init__(self, h: int =15, w: int = 22):
        self.h, self.w = h, w
        
        #smoothing for jitter
        self.smile = SmoothValue(alpha=0.20)
        self.jaw = SmoothValue(alpha=0.25)
        self.blinkL = SmoothValue(alpha=0.35)
        self.blinkR = SmoothValue(alpha=0.35)
        self.look_in_R = SmoothValue(alpha=0.20)
        self.look_in_L = SmoothValue(alpha=0.20)
        self.look_out_R = SmoothValue(alpha=0.20)
        self.look_out_L = SmoothValue(alpha=0.20)
        
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
        
        #jaw open
        jaw_raw = self._get(bs, "jawOpen")
        
        #Blink (higher = more closed)
        blinkL_raw = self._get(bs, "eyeBlinkLeft")
        blinkR_raw = self._get(bs, "eyeBlinkRight")
        look_in_R_raw = self._get(bs, "eyeLookInRight")
        look_in_L_raw = self._get(bs, "eyeLookInLeft")
        look_out_R_raw = self._get(bs, "eyeLookOutRight")
        look_out_L_raw = self._get(bs, "eyeLookOutLeft")
        
        return {
            "smile": clamp01(self.smile.update(smile_raw)),
            "jaw":clamp01(self.jaw.update(jaw_raw)),
            "blinkL": clamp01(self.blinkL.update(blinkL_raw)),
            "blinkR": clamp01(self.blinkR.update(blinkR_raw)),
            "look_in_R": clamp01(self.look_in_R.update(look_in_R_raw)),
            "look_in_L": clamp01(self.look_in_L.update(look_in_L_raw)),
            "look_out_R": clamp01(self.look_out_R.update(look_out_R_raw)),
            "look_out_L": clamp01(self.look_out_L.update(look_out_L_raw)),
            
        }
    def draw_eye_O(self, grid, x, y, blink):
        if blink > 0.4:
            #eye closed line
            set_px(grid, x-1, y, True)
            set_px(grid, x, y, True)
            set_px(grid, x+1, y, True)
        else:
            set_px(grid, x - 1, y, True)
            set_px(grid, x + 1, y, True)
            set_px(grid, x - 1, y +1, True)
            set_px(grid, x + 1, y +1, True)
            set_px(grid, x, y - 1, True)
            set_px(grid, x, y + 2, True)
            
    def draw_mouth(self, grid, cx, mouth_y, smile, jaw):
        h, w = self.h, self.w
        #mouth width and curve based on smile
        mouth_half = int(2 + 2 * smile) #Fwidth grows with smile
        x0 = cx - mouth_half
        x1 = cx + mouth_half
        
        #mouth curve: corners lift as smile increases
        # y_offset is negative when smiling (lift corners)
        lift = int(round(2 * smile))
        mid_y = mouth_y +int(round(2 * (1.0 - smile))) # flatter when smiling
      
        # Corner y (same both sides)
        corner_y = mid_y - lift

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
        draw_hline(grid, x0 + ramp, x1 - ramp, mid_y)
        
        #jaw open: open a vertical gap in the middle
        if jaw > 0.15:
            if smile > 0.2:
                draw_hline(grid, x0, x1, corner_y-1)
            else:
                open_amt = int(round(1 + 3 * jaw))
                y_top = mid_y + 1
                y_bot = min(h - 2, mid_y + open_amt)
                
                draw_vline(grid, cx - 2, y_top, y_bot-1)
                draw_vline(grid, cx + 2, y_top, y_bot-1)
                #draw_vline(grid, x0, y , mouth_y)
                #draw_vline(grid, x1, y , mouth_y)
                draw_hline(grid, cx- 1, cx+ 1, y_bot)
    
    def render(self, grid: np.ndarray, sliders: dict):
        """
        Draw into grid (uint8 hxw).
        """
        
        h, w = self.h, self.w
        
        smile = sliders["smile"]
        jaw = sliders["jaw"]
        blinkL = sliders["blinkL"]
        blinkR = sliders["blinkR"]
        look_in_R = sliders["look_in_R"]
        look_in_L = sliders["look_in_L"]
        look_out_R = sliders["look_out_R"]
        look_out_L = sliders["look_out_L"]
        
        
        #face layout anchors (tuned for 22x14
        cx = w // 2
        eye_y = int(h * 0.30)
        mouth_y = int(h * 0.55)
        
        left_eye_x = cx - 4
        right_eye_x = cx + 4
        
        #if look_in_R > 0.2 and look_in_R > look_out_R:
        #    right_eye_x = cx + 2
        #elif look_out_R > 0.2 and look_out_R > look_in_R:
        #    right_eye_x = cx + 6
        
        
        #if look_in_L > 0.2 and look_in_L > look_out_L:
        #    left_eye_x = cx - 2
        #elif look_out_L > 0.2 and look_out_L > look_in_L:
        #    left_eye_x = cx - 6
        
        #SMOOTH TEST
        eye_range = 2.0
        
        right_sig = look_out_R - look_in_R
        left_sig = look_in_L - look_out_L
        
        right_eye_x_target =(right_eye_x) + right_sig * eye_range
        left_eye_x_target = (left_eye_x) + left_sig * eye_range
        
        alpha = 2.0
        right_eye_x += (right_eye_x_target - right_eye_x) * alpha
        left_eye_x += (left_eye_x_target - left_eye_x) * alpha
        
        
        #eye: open = 6 pixels with hole, blink = horizontal line / nothing
        self.draw_eye_O(grid, int(round(left_eye_x)), eye_y, blinkL)
        self.draw_eye_O(grid, int(round(right_eye_x)), eye_y, blinkR)
        
        self.draw_mouth(grid, cx, mouth_y, smile, jaw)
        
        
        
                