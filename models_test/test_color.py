#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.2
# @date         2025-04-30
# @brief        PH值单次识别实验
# @license      Copyright (c) 2020-2032, 广州市星翼电子科技有限公司
#####################################################################################################
# @attention
#
# 实验平台:正点原子 K230D BOX开发板
# 在线视频:www.yuanzige.com
# 技术论坛:www.openedv.com
# 公司网址:www.alientek.com
# 购买地址:openedv.taobao.com
#
#####################################################################################################

import time, os, sys
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口
import math
from maix import gpio

# 配置GPIO中断引脚 (请根据实际连接修改)
BUTTON_PIN = 34
button_pressed = False

# PH值对应的颜色范围 (l_lo, l_hi, a_lo, a_hi, b_lo, b_hi)
ph_thresholds = [
    (30, 70, 10, 50, 20, 60),   # PH 1 (示例值，需要根据实际颜色调整)
    (30, 70, 5, 45, 15, 55),    # PH 2 (示例值，需要根据实际颜色调整)
    (30, 70, 0, 40, 10, 50),    # PH 3 (示例值，需要根据实际颜色调整)
    (30, 70, -5, 35, 5, 45),   # PH 4 (示例值，需要根据实际颜色调整)
    (30, 70, -10, 30, 0, 40),  # PH 5 (示例值，需要根据实际颜色调整)
    (40, 80, -15, 25, -5, 35),  # PH 6 (示例值，需要根据实际颜色调整)
    (50, 90, -20, 20, -10, 30),  # PH 7 (示例值，需要根据实际颜色调整)
    (50, 90, -25, 15, -15, 25),  # PH 8 (示例值，需要根据实际颜色调整)
    (40, 80, -30, 10, -20, 20),  # PH 9 (示例值，需要根据实际颜色调整)
    (30, 70, -35, 5, -25, 15),  # PH 10 (示例值，需要根据实际颜色调整)
    (30, 70, -40, 0, -30, 10),  # PH 11 (示例值，需要根据实际颜色调整)
    (30, 70, -45, -5, -35, 5),  # PH 12 (示例值，需要根据实际颜色调整)
    (30, 70, -50, -10, -40, 0), # PH 13 (示例值，需要根据实际颜色调整)
    (30, 70, -55, -15, -45, -5)  # PH 14 (示例值，需要根据实际颜色调整)
]

ph_values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14]
min_blob_pixels = 200  # 最小颜色区域像素数量阈值

def on_button_press(pin):
    global button_pressed
    button_pressed = True
    print("按钮被按下，开始识别...")

try:
    # 初始化GPIO
    button = gpio.GPIO(BUTTON_PIN, gpio.IN, gpio.PULL_UP) # 使用上拉电阻
    button.irq(on_button_press, gpio.IRQ_FALLING, gpio.WAKEUP_LOW) # 下降沿触发中断

    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset()  # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run() # 启动sensor
    clock = time.clock() # 构造clock对象

    while True:
        os.exitpoint() # 检测IDE中断
        clock.tick()   # 记录开始时间（ms）
        img = sensor.snapshot() # 从通道0捕获一张图
        Display.show_image(img) # 持续显示视频流
        print(f"FPS: {clock.fps():.2f}", end='\r') # 打印FPS

        if button_pressed:
            button_pressed = False
            closest_ph = None
            min_difference = float('inf')
            best_blob = None

            for i, threshold in enumerate(ph_thresholds):
                blobs = img.find_blobs([threshold], pixels_threshold=min_blob_pixels)
                for blob in blobs:
                    # 计算颜色区域的平均LAB值 (简单地取边界框中心的像素值作为代表)
                    center_x = int(blob[0] + blob[2] / 2)
                    center_y = int(blob[1] + blob[3] / 2)
                    if 0 <= center_x < img.width() and 0 <= center_y < img.height():
                        lab = img.get_pixel(center_x, center_y, get_lab=True)
                        if lab:
                            l_diff = (threshold[0] + threshold[1]) / 2 - lab[0]
                            a_diff = (threshold[2] + threshold[3]) / 2 - lab[1]
                            b_diff = (threshold[4] + threshold[5]) / 2 - lab[2]
                            difference = math.sqrt(l_diff**2 + a_diff**2 + b_diff**2) # 计算欧氏距离

                            if difference < min_difference:
                                min_difference = difference
                                closest_ph = ph_values[i]
                                best_blob = blob

            if closest_ph is not None and best_blob is not None:
                print(f"\n识别结果: 最接近的PH值为 {closest_ph}")
                # 在图像上框出识别到的颜色区域并标注PH值
                img.draw_rectangle(best_blob[0], best_blob[1], best_blob[2], best_blob[3], color=(0, 255, 0), thickness=4)
                text_x = best_blob[0]
                text_y = best_blob[1] - 20 if best_blob[1] > 20 else best_blob[1] + best_blob[3] + 10
                img.draw_string(text_x, text_y, f"PH: {closest_ph}", color=(255, 0, 0), scale=2)
                Display.show_image(img) # 显示标注后的结果图像
                sensor.stop() # 停止视频流
                while True: # 保持显示结果，等待下一次按键
                    time.sleep(0.1)
                    if button_pressed:
                        button_pressed = False
                        sensor.run() # 重新启动视频流
                        break
            else:
                print("\n未识别到符合条件的颜色")
                Display.show_image(img) # 仍然显示当前的帧
                time.sleep(1) # 避免频繁触发

# IDE中断释放资源代码
except KeyboardInterrupt as e:
    print("user stop: ", e)
except BaseException as e:
    print(f"Exception {e}")
finally:
    # sensor stop run
    if isinstance(sensor, Sensor):
        sensor.stop()
    # deinit display
    Display.deinit()
    # deinit gpio
    if 'button' in locals():
        button.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # release media buffer
    MediaManager.deinit()