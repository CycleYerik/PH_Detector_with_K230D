#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        文件读写 实验
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
import uos

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(35, FPIOA.GPIO35)
fpioa.set_function(0, FPIOA.GPIO0)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)
key2 = Pin(0, Pin.IN, pull=Pin.PULL_DOWN, drive=7)

i = 0
print(uos.listdir("/sdcard/"))

while True:
    # 读取按键状态，并做相应的按键解释
    if key0.value() == 0:
        f = open('/sdcard/test.txt', 'w') #以写的方式打开一个文件，没有该文件就自动新建
        wr_data = "正点原子 K230D BOX + {}".format(i)
        f.write(wr_data) #写入数据
        f.close() #每次操作完记得关闭文件
        print("write success") #读取数据并在终端打印
        time.sleep_ms(50)
    if key1.value() == 0:
        f = open('/sdcard/test.txt', 'r') #以读方式打开一个文件
        text = f.read()
        print(text) #读取数据并在终端打印
        f.close() #每次操作完记得关闭文件
        time.sleep_ms(50)
    if key2.value() == 1:
        print(uos.listdir("/sdcard/"))
        time.sleep_ms(50)
    time.sleep_ms(200)
    i = i + 1

