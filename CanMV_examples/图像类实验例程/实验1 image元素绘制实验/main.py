#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        image元素绘制实验
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

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.RGB565) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run() # 启动sensor

    while True:
        os.exitpoint() # 检测IDE中断
        img = sensor.snapshot() # 从通道0捕获一张图

        # 绘制线段
        img.draw_line(10, 30, 70, 30, color=(255, 0, 0), thickness=2)
        # 绘制矩形
        img.draw_rectangle(10, 70, 60, 60, color=(0, 255, 0), thickness=2, fill=False)
        # 绘制圆形
        img.draw_circle(40, 170, 30, color=(0, 0, 255), thickness=2, fill=True)
        # 绘制椭圆形
        img.draw_ellipse(40, 240, 30, 15, 45, color=(255, 0, 0), thickness=2)
        # 绘制十字线
        img.draw_cross(40, 310, color=(0, 255, 0), size=30, thickness=2)
        # 绘制箭头
        img.draw_arrow(10, 380, 70, 380, color=(0, 0, 255), thickness=2)
        # 绘制字符，支持中文
        img.draw_string_advanced(150, 20, 60, "正点原子", color = (255, 0, 0))
        # 绘制字符串
        img.draw_string(150, 100, "Hello\r\nK230D BOX", color=(255, 0, 0), scale=6)
        # 显示图片
        Display.show_image(img, x=round((640 - sensor.width()) / 2), y=round((480 - sensor.height()) / 2))

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
