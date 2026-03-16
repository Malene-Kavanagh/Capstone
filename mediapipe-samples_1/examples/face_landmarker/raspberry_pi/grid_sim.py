# grid_sim.py
# black and white LED simulator

import numpy as np
import cv2

def show_grid_bw(grid: np.ndarray, scale: int = 25, title: str = "LED 14x22"):
    """
    grid: uint8 image shape (h,w), values 0 or 255
    """
    h, w = grid.shape[:2]
    img = cv2.resize(grid, (w*scale, h*scale), interpolation=cv2.INTER_NEAREST)
    cv2.imshow(title, img)
    
def clear_grid(h: int, w: int) -> np.ndarray:
    return np.zeros((h,w), dtype=np.uint8)

def set_px(grid: np.ndarray, x: int, y: int, on: bool = True):
    h, w = grid.shape
    if 0 <= x < w and 0 <= y < h:
        grid[y, x] = 255 if on else 0
        
def draw_hline(grid: np.ndarray, x0: int, x1: int, y:int):
    if x0 > x1:
        x0, x1 = x1, x0
    for x in range(x0, x1 + 1):
        set_px(grid, x, y, True)

def draw_vline(grid: np.ndarray, x: int, y0: int, y1: int):
    if y0 > y1:
        y0, y1 = y1, y0
    for y in range(y0, y1 + 1):
        set_px(grid, x, y, True)
        
def draw_line(grid, x0, y0, x1, y1):
    """Bresenham line for integer grid."""
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        if 0 <= y0 < grid.shape[0] and 0 <= x0 < grid.shape[1]:
            grid[y0, x0] = 255
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy

def draw_rect_outline(grid: np.ndarray, x0: int, y0: int, x1: int, y1: int):
    draw_hline(grid, x0, x1, y0)
    draw_hline(grid, x0, x1, y1)
    draw_vline(grid, x0, y0, y1)
    draw_vline(grid, x1, y0, y1)