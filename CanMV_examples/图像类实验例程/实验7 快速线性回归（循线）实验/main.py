#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        快速线性回归实验
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

THRESHOLD = (0, 100)  # 黑白图像的灰度阈值
BINARY_VISIBLE = True # 使用二值化图像你可以看到什么是线性回归。
                      # 这可能降低帧率

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.GRAYSCALE) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run()        # 启动sensor
    clock = time.clock() # 构造clock对象

    while True:
        os.exitpoint() # 检测IDE中断
        clock.tick()   # 记录开始时间（ms）
        img = sensor.snapshot() # 从通道0捕获一张图
        img = img.binary([THRESHOLD]) if BINARY_VISIBLE else img
        # 返回一个类似于find_lines()和find_line_segments()方法返回的对象.
        # 有以下方法：x1(), y1(), x2(), y2(), length(),
        # theta() (rotation in degrees), rho(), 和 magnitude().
        #
        # magnitude() 表示线性回归的效果。范围是(0， INF]
        # 其中，0表示一个圆。INF值越大，表示线性回归效果越好。
        line = img.get_regression([(255,255) if BINARY_VISIBLE else THRESHOLD])
        if (line):
            img.draw_line(line.line(), color=127, thickness=5)
            # LCD显示theta角度
            img.draw_string_advanced(0, 0, 24, str('%.1f' % line.theta()), color=(255,255,255), thickness=4)
            print(line) # 打印结果
#        print("FPS %f, mag = %s" % (clock.fps(), str(line.magnitude()) if (line) else "N/A"))
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
