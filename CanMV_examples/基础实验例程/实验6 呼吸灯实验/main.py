#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        PWM实验
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

from machine import Pin, PWM
from machine import FPIOA
import time

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(35, FPIOA.GPIO35)
fpioa.set_function(59,FPIOA.PWM5)
fpioa.set_function(61,FPIOA.GPIO61)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)
ledr = Pin(61, Pin.OUT, pull=Pin.PULL_NONE, drive=7)

# 构造PWM对象
pwm0 = PWM(5, 200, duty=50, enable=True)
duty = 50
ledr.value(1) # 关闭红色LED灯，防止干扰

while True:
    if key0.value() == 0:
        time.sleep_ms(20)
        if key0.value() == 0:
            duty = duty + 10
            while key0.value() == 0:
                pass
    elif key1.value() == 0:
        time.sleep_ms(20)
        if key1.value() == 0:
            duty = duty - 10
            while key1.value() == 0:
                pass
    if duty == 0:
        duty = 10
    elif duty == 110:
        duty = 100
    # 修改PWM占空比
    if pwm0.duty() != duty:
        pwm0.duty(duty)
    time.sleep_ms(10)
