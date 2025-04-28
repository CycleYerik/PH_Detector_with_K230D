# PH颜色阈值配置（LAB颜色空间）
PH_COLOR_THRESHOLDS = {
    # PH值: (L_min, L_max, A_min, A_max, B_min, B_max)
    1: (0, 30,  -128, -10,  -50, 30),
    2: (20, 60, -50,  30,   10,  70),
    # ... 其他PH值阈值
    14: (60, 100, 50,  127,  80,  127)
}

# 硬件参数
CONFIG = {
    "sensor_resolution": (640, 480),
    "roi": (200, 150, 240, 180),  # 检测区域(x, y, w, h)
    "uart_port": "uart:/dev/ttyS1",
    "uart_baudrate": 115200,
    "button_pin": "GPIO1"  # 按键连接的GPIO引脚
}