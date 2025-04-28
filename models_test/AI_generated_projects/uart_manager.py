class UARTManager:
    def __init__(self, port, baudrate):
        self.uart = UART(port, baudrate)
    
    def send_ph_value(self, ph_value):
        # 发送协议示例: "PH:12.5\n"
        self.uart.write(f"PH:{ph_value:.1f}\n")
    
    def release(self):
        self.uart.deinit()