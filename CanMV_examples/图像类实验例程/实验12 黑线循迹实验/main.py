#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        黑色灰度循线 实验
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

# 跟踪一条黑线。使用[(128,255)]来跟踪白线。
GRAYSCALE_THRESHOLD = [(0, 64)]

# 下面是roi【区域】元组列表。每个roi用(x, y, w, h)表示的矩形。线检测算法将尝试在每个roi中找到最大blob的质心。
# 然后，质心的x位置将使用不同的权重进行平均，其中最大的权重分配给图像底部附近的roi，而较少的权重分配给下一个roi，以此类推。
# 采样图像QQVGA 160*120
#ROIS = [ # [ROI, weight]
#        (0, 100, 160, 20, 0.7), # 可以根据机器人的实际情况调整权重值。
#        (0,  50, 160, 20, 0.3),
#        (0,   0, 160, 20, 0.1)
#       ]

# 采样图像QVGA 320*240
#ROIS = [ # [ROI, weight]
#        (0, 200, 320, 40, 0.7), # 可以根据机器人的实际情况调整权重值。
#        (0,  100, 320, 40, 0.3),
#        (0,   0, 320, 40, 0.1)
#       ]

# 采样图像VGA 640*480
ROIS = [ # [ROI, weight]
        (0, 400, 640, 80, 0.7), # 可以根据机器人的实际情况调整权重值。
        (0, 200, 640, 80, 0.3),
        (0,   0, 640, 80, 0.1)
       ]

# 计算权重值（weight）的和 (结果不一定为1).
weight_sum = 0
for r in ROIS: weight_sum += r[4] # r[4] 是矩形权重值.

try:
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    sensor.reset() # 复位和初始化摄像头
    sensor.set_framesize(Sensor.VGA)    # 设置帧大小VGA(640x480)，默认通道0
    sensor.set_pixformat(Sensor.GRAYSCALE) # 设置输出图像格式，默认通道0

    # 初始化LCD显示器，同时IDE缓冲区输出图像,显示的数据来自于sensor通道0。
    Display.init(Display.ST7701, width=640, height=480, fps=90, to_ide=True)
    MediaManager.init() # 初始化media资源管理器
    sensor.run() # 启动sensor
    clock = time.clock() # 构造clock对象

    while True:
        os.exitpoint() # 检测IDE中断
        clock.tick()   # 记录开始时间（ms）
        img = sensor.snapshot() # 从通道0捕获一张图

        centroid_sum = 0
        for r in ROIS:
            # 在灰度图中寻找黑线
            blobs = img.find_blobs(GRAYSCALE_THRESHOLD, roi=r[0:4], merge=True) # r[0:4] 是上面定义的roi元组.

            if blobs:
                # 寻找矩形中最多像素的区域.
                largest_blob = max(blobs, key=lambda b: b.pixels())

                # 对该区域进行标记.
                img.draw_rectangle([v for v in largest_blob.rect()])
                img.draw_cross(largest_blob.cx(), largest_blob.cy())
                centroid_sum += largest_blob.cx() * r[4] # r[4] 是矩形的权重值.

        center_pos = (centroid_sum / weight_sum) # 确定直线的中心。

        # 将直线中心位置转换成角度.
        # 我们用的是非线性运算所以我们离线越远响应就越强.
        deflection_angle = 0

        # 使用反正切函数计算直线中心偏离角度.
        # 角度输出到-45到45左右.（权重X坐标落在图像左半部分记作正偏，落在右边部分记为负偏）

#        deflection_angle = -math.atan((center_pos - 80) / 60) # 采用图像为QQVGA 160*120时候使用
#        deflection_angle = -math.atan((center_pos - 160) / 120) # 采用图像为QVGA 320*240时候使用
        deflection_angle = -math.atan((center_pos - 320) / 240) # 采用图像为VGA 640*480时候使用

        # 将角度x从弧度转换为度数。
        deflection_angle = math.degrees(deflection_angle)

        # 可以将偏离角度发送给机器人进行处理
#        print("Turn Angle: %f" % deflection_angle)

        # LCD显示偏移角度
        img.draw_string_advanced(0, 0, 24, str('%.1f' % deflection_angle), color=(255,255,255), thickness=4)

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
