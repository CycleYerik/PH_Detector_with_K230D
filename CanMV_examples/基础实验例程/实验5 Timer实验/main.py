#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        Timer实验
# @license      Copyright (c) 2020-2032, 广州市星翼电子科技有限公司
#####################################################################################################
# @attention
#
# 实验平台:正点原子 DNK230开发板
# 在线视频:www.yuanzige.com
# 技术论坛:www.openedv.com
# 公司网址:www.alientek.com
# 购买地址:openedv.taobao.com
#
#####################################################################################################

from machine import Pin
from machine import FPIOA
from machine import Timer
import time

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(61, FPIOA.GPIO61)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
ledr = Pin(61, Pin.OUT, pull=Pin.PULL_NONE, drive=7)

count = 0

# Timer超时回调函数
def timer_timeout_cb(timer):
    global count
    count = count + 1
    ledr.value(count % 2)

# 实例化一个软定时器
tim = Timer(-1)
tim.init(period = 1000, mode = Timer.PERIODIC, callback = timer_timeout_cb)

while True:
    if key0.value() == 0:
        time.sleep_ms(20)
        if key0.value() == 0:
            # 释放Timer资源
            tim.deinit()
            while key0.value() == 0:
                pass
    time.sleep_ms(10)
