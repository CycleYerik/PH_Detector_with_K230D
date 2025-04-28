#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        多颜色识别实验
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

# 颜色识别阈值(l_lo, l_hi, a_lo, a_hi, b_lo, b_hi)即LAB模型，对应 LAB 色彩空间中的 L、A 和 B 通道的最小和最大值
# 下面的阈值元组是用来识别红、绿、蓝三种颜色，你可以根据使用场景调整提高识别效果。
thresholds = [(0, 80, 20, 127, -10, 30), # 红色
              (0, 80, -120, -10, 0, 30), # 绿色
              (0, 80, 0, 90, -128, -20)] # 蓝色

color = [(255,0,0), (0,255,0), (0,0,255)]

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset()  # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run() # 启动sensor
    clock = time.clock() # 构造clock对象

    while True:
        os.exitpoint() # 检测IDE中断
        clock.tick()   # 记录开始时间（ms）
        img = sensor.snapshot() # 从通道0捕获一张图

        for i in range(3):
            blobs = img.find_blobs([thresholds[i]], pixels_threshold=200) # 0,1,2分别表示红，绿，蓝色。
            for blob in blobs:
                img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=color[i], thickness=4)

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
