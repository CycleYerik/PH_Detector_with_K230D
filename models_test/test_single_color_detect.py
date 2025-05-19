#####################################################################################################
# @file         test_single_color_detect.py
# @brief        pH值颜色识别实验
# @license      Copyright (c) 2020-2032, 广州市星翼电子科技有限公司
#####################################################################################################

import time, os, sys
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口
from machine import Pin, FPIOA

# pH值对应的LAB颜色阈值
# 格式: (pH值, (L_min, L_max, A_min, A_max, B_min, B_max))
pH_thresholds = [
    (0, (0, 80, 20, 127, -10, 30)),    # pH 0 - 红色
    (1, (0, 80, 15, 120, -15, 25)),    # pH 1
    (2, (0, 80, 10, 115, -20, 20)),    # pH 2
    (3, (0, 80, 5, 110, -25, 15)),     # pH 3
    (4, (0, 80, 0, 105, -30, 10)),     # pH 4
    (5, (0, 80, -5, 100, -35, 5)),     # pH 5
    (6, (0, 80, -10, 95, -40, 0)),     # pH 6
    (7, (0, 80, -15, 90, -45, -5)),    # pH 7
    (8, (0, 80, -20, 85, -50, -10)),   # pH 8
    (9, (0, 80, -25, 80, -55, -15)),   # pH 9
    (10, (0, 80, -30, 75, -60, -20)),  # pH 10
    (11, (0, 80, -35, 70, -65, -25)),  # pH 11
    (12, (0, 80, -40, 65, -70, -30)),  # pH 12
    (13, (0, 80, -45, 60, -75, -35)),  # pH 13
    (14, (0, 80, -50, 55, -80, -40))   # pH 14
]

# 初始化FPIOA
fpioa = FPIOA()
# 配置按键引脚
fpioa.set_function(34, FPIOA.GPIO34)  # KEY0
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)

def detect_ph_color(img):
    """检测图像中的pH值颜色"""
    detected_ph = None
    max_blob_size = 0
    
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=200)
        for blob in blobs:
            # 如果找到更大的色块，更新检测结果
            if blob[2] * blob[3] > max_blob_size:
                max_blob_size = blob[2] * blob[3]
                detected_ph = ph_value
                # 在图像上绘制矩形框和pH值
                img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=(255, 0, 0), thickness=4)
                img.draw_string(blob[0], blob[1] - 20, f"pH: {ph_value}", color=(255, 0, 0), scale=2)
    
    return detected_ph

def main():
    try:
        # 初始化摄像头
        sensor = Sensor(width=1280, height=960)
        sensor.reset()
        sensor.set_framesize(Sensor.VGA)
        sensor.set_pixformat(Sensor.RGB565)
        
        # 初始化显示
        Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
        MediaManager.init()
        sensor.run()
        
        print("pH值颜色识别程序已启动")
        print("按下KEY0进行单次识别")
        
        while True:
            os.exitpoint()
            
            # 检测按键按下
            if key0.value() == 0:
                time.sleep_ms(20)  # 消抖
                if key0.value() == 0:
                    # 捕获图像
                    img = sensor.snapshot()
                    
                    # 进行pH值颜色识别
                    detected_ph = detect_ph_color(img)
                    
                    if detected_ph is not None:
                        print(f"检测到pH值: {detected_ph}")
                    else:
                        print("未检测到有效的pH值颜色")
                    
                    # 显示图像
                    Display.show_image(img)
                    
                    # 等待按键释放
                    while key0.value() == 0:
                        time.sleep_ms(10)
            
            time.sleep_ms(10)  # 降低CPU使用率

    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        print(f"Exception {e}")
    finally:
        # 释放资源
        if isinstance(sensor, Sensor):
            sensor.stop()
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    main() 