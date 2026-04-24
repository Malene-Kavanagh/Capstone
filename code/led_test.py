import time
import board
import neopixel
import colorsys

#LED strip  config
LED_COUNT     = 30           # num of LED pixels
LED_PIN       = board.D18     # GPIO pin 18
LED_PIN2      = board.D17

pixels1 = neopixel.NeoPixel(
    LED_PIN,
    LED_COUNT,
    brightness=0.05,
    auto_write=False
    )

pixels2 = neopixel.NeoPixel(
    LED_PIN2,
    LED_COUNT,
    brightness=0.05,
    auto_write=False
    )
def led_on():
    pixels1.fill((50,10,50))
    pixels2.fill((50,10,50))
    pixels1.show()
    pixels2.show()

def blink():
    for i in range(LED_COUNT):
        #(GREEN,RED,BLUE)
        pixels1[i] = (50, 10, 50)
        pixels2[i] = (50, 10, 50)
    pixels1.show()
    pixels2.show()
    time.sleep(1)
    
    pixels1.fill((0,0,0))
    pixels2.fill((0,0,0))
    pixels1.show()
    pixels2.show()
    time.sleep(1)
    
def colorwheel(pos):
    """
    Generate an RGB color from a position on the color wheel (0-255).
    The colours are a transition r -> g -> b -> r.
    """
    if pos < 0 or pos > 255:
        return (0, 0, 0)
    if pos < 85:
        return (255 - pos * 3, pos * 3, 0)
    if pos < 170:
        pos -= 85
        return (0, 255 - pos * 3, pos * 3)
    pos -= 170
    return (pos * 3, 0, 255 - pos * 3)

# Function using colorsys for smoother gradient (requires colorsys library)
def colorsys_colorwheel(hue_value):
    """
    Generate RGB color using the colorsys library.
    Hue value should be between 0 and 255.
    """
    hue = hue_value / 255.0  # colorsys uses 0.0 to 1.0 for hue
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    # Convert float values to 0-255 integers
    return (int(r * 255), int(g * 255), int(b * 255))


def rainbow_cycle(pixels1, pixels2, num_pixels, speed=0.01):
    for i in range(255):  # Cycle through all hues
        for j in range(num_pixels):
            # Calculate the color for each pixel based on its position and current hue
            pixel_index = (i + j) % 255
            color = colorsys_colorwheel(pixel_index) # or colorwheel(pixel_index)
            pixels1[j] = color
            pixels2[j] = color
        pixels1.show() # Update the physical LEDs
        pixels2.show()
        time.sleep(speed)

while True:
    #rainbow_cycle(pixels, LED_COUNT)
    led_on()
#    blink()
    rainbow_cycle(pixels1, pixels2, LED_COUNT, 0.04)