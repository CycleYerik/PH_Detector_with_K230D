#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        LCD 实验
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

def display_test():
    img = image.Image(640, 480, image.RGB888)
    Display.init(Display.ST7701, width=640, height=480, to_ide=True)
    MediaManager.init()

    try:
        while True:
            img.clear()
            for i in range(10):
                x = (urandom.getrandbits(11) % img.width())
                y = (urandom.getrandbits(11) % img.height())
                r = (urandom.getrandbits(8))
                g = (urandom.getrandbits(8))
                b = (urandom.getrandbits(8))
                size = (urandom.getrandbits(30) % 64) + 32
                # 在不同位置刷新不同大小、颜色的字符串
                img.draw_string_advanced(x,y,size, "Hello World!，你好世界！！！", color=(r, g, b),)

            # 刷新到显示器上
            Display.show_image(img)

            time.sleep(1)
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

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    display_test()
