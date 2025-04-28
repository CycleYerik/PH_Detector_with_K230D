#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        蜂鸣器实验
#    @note      K230D-BOX使用的是无源蜂鸣器，无源蜂鸣器规格书要求震荡频率为 4KHz
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

from machine import PWM
from machine import FPIOA
import time

# 实例化FPIOA
fpioa = FPIOA()

# 设置Pin60为PWM0
fpioa.set_function(60,FPIOA.PWM0)

# 实例化PWM0输出4KHz占空比为50的震荡频率
pwm0 = PWM(0, 4000, duty=50, enable=True)

while True:
    pass
