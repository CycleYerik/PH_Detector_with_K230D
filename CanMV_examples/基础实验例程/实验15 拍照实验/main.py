#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        拍照 实验
#   @note       按下KEY0拍摄JPG格式的照片，按下KEY1拍摄BMP格式的照片
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
from machine import Pin
from machine import FPIOA
from media.sensor import *  #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import *   #导入media模块，使用meida相关接口
import image                #导入Image模块，使用Image相关接口

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(35, FPIOA.GPIO35)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)

try:
    try:
        os.mkdir("/data/PHOTO")
    except Exception:
        pass
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头

    sensor.set_framesize(Sensor.VGA)      # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.YUV420SP) # 设置输出图像格式，默认通道0

    # 将通道0图像绑定到视频输出
    bind_info = sensor.bind_info()
    Display.bind_layer(**bind_info, layer=Display.LAYER_VIDEO1)

    # 设置通道1输出格式，用于图像保存
    sensor.set_framesize(Sensor.SXGAM, chn=CAM_CHN_ID_1)  # 输出帧大小SXGAM(1280x960)
    sensor.set_pixformat(Sensor.RGB565, chn=CAM_CHN_ID_1) # 设置输出图像格式，选择通道1

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width = 640, height = 480, to_ide = False)
    MediaManager.init()  # 初始化media资源管理器

    sensor.run()  # 启动sensor

    while True:
        os.exitpoint() # 检测IDE中断
        # 读取按键状态，并做相应的按键解释
        if key0.value() == 0:
            img = sensor.snapshot(chn=CAM_CHN_ID_1) # 从通道1捕获一张图
            img.save("/data/PHOTO/photo.jpg")
            print("snapshot success") # 提示照片保存成功
            time.sleep_ms(50)
        if key1.value() == 0:
            img = sensor.snapshot(chn=CAM_CHN_ID_1) # 从通道1捕获一张图
            img.save("/data/PHOTO/photo.bmp")
            print("snapshot success") # 提示照片保存成功
            time.sleep_ms(50)
        time.sleep_ms(10)
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
