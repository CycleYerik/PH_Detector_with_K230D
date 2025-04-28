#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        看门狗实验
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

from machine import WDT
from machine import Pin
from machine import FPIOA
import time

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)

# 实例化wdt1，timeout为3s
wdt1 = WDT(1,3)

print("system start-up")

feed_times = 0

while feed_times < 5:
    if key0.value() == 0:
        time.sleep_ms(20)
        if key0.value() == 0:
            # 对WDT喂狗
            wdt1.feed()
            feed_times += 1
            print("Feed WDT1 %d times." % (feed_times))
            while key0.value() == 0:
                pass
    time.sleep_ms(10)
