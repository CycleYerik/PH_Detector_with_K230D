import time
import gc
from config import PH_COLOR_THRESHOLDS, CONFIG
from hardware.sensor_manager import SensorManager
from hardware.uart_manager import UARTManager
from hardware.button_handler import ButtonHandler

class PHDetector:
    def __init__(self):
        self.sensor = SensorManager(CONFIG["sensor_resolution"])
        self.uart = UARTManager(CONFIG["uart_port"], CONFIG["uart_baudrate"])
        self.is_detecting = False
        
        # 注册按键回调
        ButtonHandler(CONFIG["button_pin"], self._toggle_detection)
        
    def _toggle_detection(self):
        self.is_detecting = not self.is_detecting
        if self.is_detecting:
            print("Detection STARTED")
        else:
            print("Detection STOPPED")
    
    def _get_dominant_color(self, img):
        # 提取ROI区域并计算平均颜色
        roi = CONFIG["roi"]
        stats = img.get_statistics(roi=roi)
        return (stats.l_mean(), stats.a_mean(), stats.b_mean())
    
    def _match_ph_value(self, lab_color):
        min_distance = float('inf')
        matched_ph = 0.0
        for ph, thresholds in PH_COLOR_THRESHOLDS.items():
            # 计算颜色距离（简化版）
            distance = sum([
                abs(lab_color[0] - (thresholds[0]+thresholds[1]))/2,
                abs(lab_color[1] - (thresholds[2]+thresholds[3]))/2,
                abs(lab_color[2] - (thresholds[4]+thresholds[5]))/2
            ])
            if distance < min_distance:
                min_distance = distance
                matched_ph = ph
        return matched_ph
    
    def run(self):
        try:
            while True:
                if self.is_detecting:
                    img = self.sensor.capture_frame()
                    color = self._get_dominant_color(img)
                    ph_value = self._match_ph_value(color)
                    
                    # 发送到串口屏幕
                    self.uart.send_ph_value(ph_value)
                    
                    # 绘制检测区域（调试用）
                    img.draw_rectangle(CONFIG["roi"], color=(255,0,0))
                
                gc.collect()
                time.sleep_ms(100)
                
        except KeyboardInterrupt:
            pass
        finally:
            self.sensor.release()
            self.uart.release()

if __name__ == "__main__":
    detector = PHDetector()
    detector.run()