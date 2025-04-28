#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        按键输入实验
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

from machine import Pin,PWM
from machine import FPIOA
import time

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(59, FPIOA.GPIO59)
fpioa.set_function(61, FPIOA.GPIO61)
fpioa.set_function(60, FPIOA.PWM0)
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(35, FPIOA.GPIO35)
fpioa.set_function(0, FPIOA.GPIO0)

# 构造GPIO对象
ledb = Pin(59, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
ledr = Pin(61, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
beep = PWM(0, 4000, duty=50, enable=False)
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)
key2 = Pin(0, Pin.IN, pull=Pin.PULL_DOWN, drive=7)

while True:
    # 读取按键状态，并做相应的按键解释
    if key0.value() == 0:
        ledr.value(0)
    else:
        ledr.value(1)
    if key1.value() == 0:
        ledb.value(0)
    else:
        ledb.value(1)
    if key2.value() == 1:
        beep.enable(True)
    else:
        beep.enable(False)
