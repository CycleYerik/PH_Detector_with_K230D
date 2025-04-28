#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        摄像头 实验
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
from media.sensor import *  #导入sensor模块，使用摄像头相关接口
from media.display import * #导入display模块，使用display相关接口
from media.media import *   #导入media模块，使用meida相关接口


try:
    sensor = Sensor(width=1280, height = 960) #构建摄像头对象
    sensor.reset() #复位和初始化摄像头

    sensor.set_framesize(Sensor.VGA)      #设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.YUV420SP) #设置输出图像格式，默认通道0

    # 将通道0图像绑定到视频输出
    bind_info = sensor.bind_info()
    Display.bind_layer(**bind_info, layer=Display.LAYER_VIDEO1)

    #使用IDE缓冲区输出图像,显示尺寸和sensor配置一致。
    Display.init(Display.ST7701, sensor.width(), sensor.height(), fps=90, to_ide=True)
    MediaManager.init() #初始化media资源管理器
    sensor.run() #启动sensor

    while True:
        os.exitpoint() #检测IDE中断

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
