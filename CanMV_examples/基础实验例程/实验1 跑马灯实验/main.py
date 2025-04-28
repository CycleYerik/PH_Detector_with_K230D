#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        跑马灯实验
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

from machine import Pin
from machine import FPIOA
import time

# 实例化FPIOA
fpioa = FPIOA()

# 设置Pin59为GPIO59，Pin61为GPIO61
fpioa.set_function(59, FPIOA.GPIO59)
fpioa.set_function(61, FPIOA.GPIO61)

# 实例化蓝色LED灯和红色LED灯引脚为输出
ledr = Pin(61, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
ledb = Pin(59, Pin.OUT, pull=Pin.PULL_NONE, drive=7)

# 设置输出为高
ledb.value(1)
# pin.on()
# pin.high()
# 设置输出为低
ledb.value(0)
# pin.off()
# pin.low()

while True:
    # 设置LED对应的GPIO对象输出对应的高低电平
    ledb.value(1)
    ledr.value(0)
    time.sleep_ms(200)
    ledb.value(0)
    ledr.value(1)
    time.sleep_ms(200)
