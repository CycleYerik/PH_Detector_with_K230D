#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        触摸屏 实验
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

import time, os, urandom, sys
from media.display import *
from media.media import *
from machine import TOUCH

# 实例化TOUCH设备0
tp = TOUCH(0)

def load_draw_dialog():
    img.clear()
    img.draw_string_advanced(640 - 52, 0, 30, "RST", color = (255, 0, 0))


"""
 * @brief       画粗线
 * @param       x1,y1: 起点坐标
 * @param       x2,y2: 终点坐标
 * @param       size : 线条粗细程度
 * @param       color: 线的颜色
 * @retval      无
"""
def lcd_draw_bline(x1,y1,x2,y2,size,color):

    t = 0
    xerr = 0
    yerr = 0
    delta_x = 0
    delta_y = 0
    distance = 0
    incx = 0
    incy = 0
    row = 0
    col = 0

    delta_x = x2 - x1                       # 计算坐标增量
    delta_y = y2 - y1
    row = x1
    col = y1

    if delta_x > 0:
        incx = 1                            # 置单步方向
    elif delta_x == 0:
        incx = 0                            #垂直线
    else:
        incx = -1
        delta_x = -delta_x

    if delta_y > 0:
        incy = 1
    elif delta_y == 0:
        incy = 0                            # 水平线
    else:
        incy = -1
        delta_y = -delta_y

    if delta_x > delta_y:
        distance = delta_x;                 # 选取基本增量坐标轴
    else:
        distance = delta_y

    for t in range(0,distance + 1):         # 画线输出
        img.draw_circle(row, col, size, color)   # 画点
        xerr += delta_x
        yerr += delta_y

        if xerr > distance:
            xerr -= distance
            row += incx

        if yerr > distance:
            yerr -= distance
            col += incy

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    img = image.Image(640, 480, image.RGB888)
    Display.init(Display.ST7701, width=640, height=480, to_ide=True)
    MediaManager.init()

    lastpos = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]    #最后一次的数据
    # 清空屏幕并在右上角显示"RST"
    load_draw_dialog()
    Display.show_image(img, 640, 480)
    try:
        while True:
            # 获取TOUCH数据
            p = tp.read(5)

            if p == ():  # 发生触摸事件
                lastpos = [[0, 0], [0, 0], [0, 0], [0, 0], [0, 0]]  # 重新清空所有点

            for i in range(len(p)): # 打印每个点坐标信息，最大5点。
                if (p[i].x < 640 and p[i].y < 480):

                    if lastpos[i][0] == 0x0 and lastpos[i][1] == 0x0:

                        lastpos[i][0] = p[i].x
                        lastpos[i][1] = p[i].y

                    lcd_draw_bline(lastpos[i][0], lastpos[i][1], p[i].x, p[i].y, 2, color=(255, 0, 0));
                    lastpos[i][0] = p[i].x
                    lastpos[i][1] = p[i].y

                    if (p[i].x > (640 - 50) and p[i].y < 30):

                        load_draw_dialog()
                        lastpos[i][0] = 0
                        lastpos[i][1] = 0
                else:
                    lastpos[i][0] = 0x0
                    lastpos[i][1] = 0x0

            # 刷新到显示器上
            Display.show_image(img)
            time.sleep_ms(5)
            os.exitpoint()

    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        print(f"Exception {e}")

    # deinit display
    Display.deinit()
    os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
    time.sleep_ms(100)
    # release media buffer
    MediaManager.deinit()
