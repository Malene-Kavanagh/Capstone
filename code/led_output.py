def draw_to_led(grid, pixels, led_map, on_color =(255,255,255), off_color=(0,0,0)):
    """
    grid where in a 2d array 0 = off and int > 0 = on
    pixels: Neopixel object
    led_map: 2d array mapped to the proper led num location
    on_color: RGB tuple for lit pixels
    off_collor: RGB tuple for unlit pixels
    """
    
    h = len(led_map)
    w = len(led_map[0])
    
    for y in range(h):
        for x in range(w):
            led_idx = led_map[y][x]
            
            if grid[y, x] > 0:
                pixels[led_idx] = on_color
            else:
                pixels[led_idx] = off_color
    
    pixels.show()