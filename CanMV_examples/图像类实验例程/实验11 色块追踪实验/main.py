#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        色块追踪实验
# @license      Copyright (c) 2020-2032, 广州市星翼电子科技有限公司
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
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口
from machine import Pin
from machine import FPIOA

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run() # 启动sensor
    clock = time.clock() # 构造clock对象

    frame_count = 0
    threshold_flag = 0  # 捕获颜色LAB值的标记
    threshold = [50, 50, 0, 0, 0, 0] # 中间的 L, A, B 值.
    # 捕捉图像中心的颜色阈值。
    r = [(640//2) - (50//2), (480//2) - (50//2), 50, 50] # 50x50 center of QVGA.

    while True:
        os.exitpoint() # 检测IDE中断
        clock.tick()  # 记录开始时间（ms）
        img = sensor.snapshot() # 从通道0捕获一张图

        if key0.value() == 0:
            frame_count = 0
            threshold_flag = 1
        if frame_count < 60 & threshold_flag == 1:
            if frame_count == 0:
                print("Letting auto algorithms run. Don't put anything in front of the camera!")
                print("Auto algorithms done. Hold the object you want to track in front of the camera in the box.")
                print("MAKE SURE THE COLOR OF THE OBJECT YOU WANT TO TRACK IS FULLY ENCLOSED BY THE BOX!")
            img.draw_rectangle([v for v in r])
            frame_count = frame_count + 1
        elif (frame_count < 120) & threshold_flag == 1:
            if frame_count == 60:
                print("Learning thresholds...")
            elif frame_count == 119:
                print("Thresholds learned...")
                print("Tracking colors...")
                threshold_flag = 0 # 解除标记
            hist = img.get_histogram(roi=r)
            lo = hist.get_percentile(0.01) # Get the CDF of the histogram at the 1% range (ADJUST AS NECESSARY)!
            hi = hist.get_percentile(0.99) # Get the CDF of the histogram at the 99% range (ADJUST AS NECESSARY)!
            # 取平均值
            threshold[0] = (threshold[0] + lo.l_value()) // 2
            threshold[1] = (threshold[1] + hi.l_value()) // 2
            threshold[2] = (threshold[2] + lo.a_value()) // 2
            threshold[3] = (threshold[3] + hi.a_value()) // 2
            threshold[4] = (threshold[4] + lo.b_value()) // 2
            threshold[5] = (threshold[5] + hi.b_value()) // 2
            for blob in img.find_blobs([threshold], pixels_threshold=100, area_threshold=100, merge=True, margin=10):
                img.draw_rectangle([v for v in blob.rect()])
                img.draw_cross(blob.cx(), blob.cy())
                img.draw_rectangle([v for v in r])
            frame_count = frame_count + 1
            del hist
        else:
            for blob in img.find_blobs([threshold], pixels_threshold=100, area_threshold=100, merge=True, margin=10):
                img.draw_rectangle([v for v in blob.rect()])
                img.draw_cross(blob.cx(), blob.cy())
        # 显示图片
        Display.show_image(img)
        print(clock.fps()) # 打印FPS

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
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # release media buffer
    MediaManager.deinit()
