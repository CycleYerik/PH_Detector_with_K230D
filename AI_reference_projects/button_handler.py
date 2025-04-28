from machine import Pin

class ButtonHandler:
    def __init__(self, pin, callback):
        self.btn = Pin(pin, Pin.IN, Pin.PULL_UP)
        self.btn.irq(trigger=Pin.IRQ_FALLING, handler=self._irq_handler)
        self.callback = callback
        self._last_press = 0
        
    def _irq_handler(self, pin):
        if time.ticks_ms() - self._last_press > 500:  # 防抖处理
            self.callback()
            self._last_press = time.ticks_ms()