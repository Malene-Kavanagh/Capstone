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
    renders a simple face on a 14x22 grid:
        - eyes blink
        - mouth smiles
        - jaw open opens the mouth
    """
    
    def __init__(self, h: int =14, w: int = 22):
        self.h, self.w = h, w
        
        #smoothing for jitter
        self.smile = SmoothValue(alpha=0.20)
        self.jaw = SmoothValue(alpha=0.25)
        self.blinkL = SmoothValue(alpha=0.35)
        self.blinkR = SmoothValue(alpha=0.35)
        
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
        
        return {
            "smile": clamp01(self.smile.update(smile_raw)),
            "jaw":clamp01(self.jaw.update(jaw_raw)),
            "blinkL": clamp01(self.blinkL.update(blinkL_raw)),
            "blinkR": clamp01(self.blinkR.update(blinkR_raw)),
        }
    
    def render(self, grid: np.ndarray, sliders: dict):
        """
        Draw into grid (uint8 hxw).
        """
        
        h, w = self.h, self.w
        
        smile = sliders["smile"]
        jaw = sliders["jaw"]
        blinkL = sliders["blinkL"]
        blinkR = sliders["blinkR"]
        
        #face layout anchors (tuned for 22x14
        cx = w // 2
        eye_y = int(h * 0.30)
        mouth_y = int(h * 0.65)
        
        left_eye_x = cx - 3
        right_eye_x = cx + 3
        
        #eye: open = 2 pixels, blink = horizontal line / nothing
        def draw_eye(x, y, blink):
            if blink > 0.4:
                #eye closed line
                set_px(grid, x-1, y, True)
                set_px(grid, x, y, True)
                set_px(grid, x+1, y, True)
            else:
                # open "round" eye
                set_px(grid, x, y+1, True)
                set_px(grid, x, y, True)
                set_px(grid, x, y+1, True)
        draw_eye(left_eye_x, eye_y, blinkL)
        draw_eye(right_eye_x, eye_y, blinkR)
        
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
            open_amt = int(round(2 + 3 * jaw)) #1...4 pixels
            y_top = mid_y +1
            y_bot = min(h-2, mid_y + open_amt) #using h -2 so bottom doesn't clip
            
            #carve a "mouth opening" by drawing vertical lines down from mid
            draw_vline(grid, cx - 1, y_top, y_bot)
            draw_vline(grid, cx + 1, y_top, y_bot)
            
            draw_hline(grid, cx -1, cx+1, y_bot)