#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        视频播放器 实验
#   @note       运行后视频自动播放，按下KEY0视频暂停播放，按下KEY1后视频继续播放  注意：当前版本仅支持MP4
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
from media.display import * #导入display模块，使用display相关接口
from media.media import *   #导入media模块，使用meida相关接口
from media.player import *
import os

# 实例化FPIOA
fpioa = FPIOA()

# 为IO分配相应的硬件功能
fpioa.set_function(34, FPIOA.GPIO34)
fpioa.set_function(35, FPIOA.GPIO35)

# 构造GPIO对象
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)

start_play = False
def player_event(event,data):
    global start_play
    if(event == K_PLAYER_EVENT_EOF):
        start_play = False

def play_mp4_test(filename):
    global start_play

    # 使用LCD作为输出显示
    player=Player(Display.ST7701, display_to_ide=True)
    player.load(filename)
    player.set_event_callback(player_event)
    player.start()
    start_play = True

    try:
        while(start_play):
            # 读取按键状态，并做相应的按键解释
            if key0.value() == 0:
                player.pause()
                print("play pause")
            if key1.value() == 0:
                player.resume()
                print("play resume")
            time.sleep(0.1)
            os.exitpoint()
    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        import sys
        sys.print_exception(e)

    player.stop() #停止播放
    print("play over")


if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    play_mp4_test("/data/VIDEO/test.mp4")

