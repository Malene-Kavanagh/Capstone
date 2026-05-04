from gpiozero import Button as GPIOButton
import time

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

"""
while True:
    if button1.is_pressed and button2.is_pressed:
        print("both buttons ARE pressed")
        exit(0)
    elif button2.is_pressed:
        print("Button 2 pressed")
    elif button1.is_pressed:
        print("Button 1 pressed")
    else:
        print("no button is pressed")
    sleep(0.2) # small delay
    """
button1 = Button(5) #supposidly setting GPIO pin
button2 = Button(6)
while True:
    b1_short, b1_long = button1.update()
    b2_short, b2_long = button2.update()

    if b1_short:
        print("B1 short")
    if b1_long:
        print("B1 long")

    if b2_short:
        print("B2 short")
    if b2_long:
        print("B2 long")

    time.sleep(0.01)