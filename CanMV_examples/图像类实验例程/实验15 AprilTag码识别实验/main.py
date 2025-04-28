#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        AprilTag码实验
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

import time, math, os, gc
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口

# AprilTag代码支持多达6个标签族，可以同时处理。
# 返回的标记对象将具有其标记族和标记族中的ID。
tag_families = 0
tag_families |= image.TAG16H5 # 注释掉，禁用此家族
tag_families |= image.TAG25H7 # 注释掉，禁用此家族
tag_families |= image.TAG25H9 # 注释掉，禁用此家族
tag_families |= image.TAG36H10 # 注释掉，禁用此家族
tag_families |= image.TAG36H11 # 注释掉，禁用此家族 (默认家族)
tag_families |= image.ARTOOLKIT # 注释掉，禁用此家族
# 标签系列有什么区别？例如，TAG16H5家族实际上是一个4x4方形标签。
# 所以，这意味着可以看到它比6x6的TAG36H11标签有更长的距离。
# 然而，较低的H值（H5对H11），意味着4x4标签的假阳性率远高于6x6标签。
# 所以，除非你有特殊需求需要使用其他标签系列，否则使用默认族TAG36H11。

def family_name(tag):
    if(tag.family() == image.TAG16H5):
        return "TAG16H5"
    if(tag.family() == image.TAG25H7):
        return "TAG25H7"
    if(tag.family() == image.TAG25H9):
        return "TAG25H9"
    if(tag.family() == image.TAG36H10):
        return "TAG36H10"
    if(tag.family() == image.TAG36H11):
        return "TAG36H11"
    if(tag.family() == image.ARTOOLKIT):
        return "ARTOOLKIT"

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头
    sensor.set_framesize(Sensor.QVGA)   # 设置帧大小QVGA(320x240)，默认通道0
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

        for tag in img.find_apriltags(families=tag_families):
            img.draw_rectangle([v for v in tag.rect()], color=(255, 0, 0), thickness=4)
            img.draw_cross(tag.cx(), tag.cy(), color=(0, 255, 0), thickness=2)
            #打印AprilTag码信息
            print_args = (family_name(tag), tag.id(), (180 * tag.rotation()) / math.pi)
            print("Tag Family %s, Tag ID %d, rotation %f (degrees)" % print_args)

        # 显示图片
        Display.show_image(img, x=round((640-sensor.width())/2), y=round((480-sensor.height())/2))
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
