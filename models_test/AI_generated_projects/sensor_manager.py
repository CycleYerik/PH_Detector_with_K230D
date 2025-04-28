from media.sensor import Sensor
from media.media import MediaManager

class SensorManager:
    def __init__(self, resolution):
        self.sensor = Sensor(resolution[0], resolution[1])
        self._setup_sensor()
        
    def _setup_sensor(self):
        self.sensor.reset()
        self.sensor.set_pixformat(Sensor.RGB565)
        self.sensor.set_framesize(self.sensor.width, self.sensor.height)
        MediaManager.init()
        self.sensor.run()
    
    def capture_frame(self):
        return self.sensor.snapshot()
    
    def release(self):
        self.sensor.stop()
        MediaManager.deinit()