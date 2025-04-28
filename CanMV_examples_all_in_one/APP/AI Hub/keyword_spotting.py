#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        关键词唤醒实验
#   @note       关键词为：小楠小楠，K230D-BOX默认无扬声器，可以通过显示器唤醒查看现象
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

from libs.PipeLine import ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
from media.pyaudio import *                     # 音频模块
from media.media import *
from media.display import *                     # 导入display模块，使用display相关接口
from media.sensor import *                      # 软件抽象模块，主要封装媒体数据链路以及媒体缓冲区
from machine import Pin
from machine import FPIOA
import media.wave as wave                       # wav音频处理模块
import nncase_runtime as nn                     # nncase运行模块，封装了kpu（kmodel推理）和ai2d（图片预处理加速）操作
import ulab.numpy as np                         # 类似python numpy操作，但也会有一些接口不同
import aidemo                                   # aidemo模块，封装ai demo相关前处理、后处理等操作
import time                                     # 时间统计
import struct                                   # 字节字符转换模块
import gc                                       # 垃圾回收模块
import os,sys                                   # 操作系统接口模块
import machine
from machine import Pin
from machine import FPIOA

class Button():
    def __init__(self, fpioa, pinx, valid=0):
        fpioa.set_function(pinx, fpioa.GPIO0 + pinx)

        pull = Pin.PULL_UP if valid == 0 else Pin.PULL_DOWN
        self.pin = Pin(pinx, Pin.IN, pull=pull, drive=7)
        self.valid = valid

    def is_pressing(self):
        return True if self.pin.value() == self.valid else False

DISPLAY_WIDTH = ALIGN_UP(640, 16)
DISPLAY_HEIGHT = 480

# 自定义关键词唤醒类，继承自AIBase基类
class KWSApp(AIBase):
    def __init__(self, kmodel_path, threshold, debug_mode=0):
        super().__init__(kmodel_path)  # 调用基类的构造函数
        self.kmodel_path = kmodel_path  # 模型文件路径
        self.threshold=threshold
        self.debug_mode = debug_mode  # 是否开启调试模式
        self.cache_np = np.zeros((1, 256, 105), dtype=np.float)

    # 自定义预处理，返回模型输入tensor列表
    def preprocess(self,pcm_data):
        pcm_data_list=[]
        # 获取音频流数据
        for i in range(0, len(pcm_data), 2):
            # 每两个字节组织成一个有符号整数，然后将其转换为浮点数，即为一次采样的数据，加入到当前一帧（0.3s）的数据列表中
            int_pcm_data = struct.unpack("<h", pcm_data[i:i+2])[0]
            float_pcm_data = float(int_pcm_data)
            pcm_data_list.append(float_pcm_data)
        # 将pcm数据处理为模型输入的特征向量
        mp_feats = aidemo.kws_preprocess(fp, pcm_data_list)[0]
        mp_feats_np = np.array(mp_feats).reshape((1, 30, 40))
        audio_input_tensor = nn.from_numpy(mp_feats_np)
        cache_input_tensor = nn.from_numpy(self.cache_np)
        return [audio_input_tensor,cache_input_tensor]

    # 自定义当前任务的后处理，results是模型输出array列表
    def postprocess(self, results):
        with ScopedTiming("postprocess", self.debug_mode > 0):
            logits_np = results[0]
            self.cache_np= results[1]
            max_logits = np.max(logits_np, axis=1)[0]
            max_p = np.max(max_logits)
            idx = np.argmax(max_logits)
            # 如果分数大于阈值，且idx==1(即包含唤醒词)，播放回复音频
            if max_p > self.threshold and idx == 1:
                return 1
            else:
                return 0


if __name__ == "__main__":
    fpioa = FPIOA()
    button0 = Button(fpioa, 34, 0)

    # 实例化FPIOA
    fpioa = FPIOA()
    # 设置Pin63为GPIO63
    fpioa.set_function(63, FPIOA.GPIO63)
    # 实例化功放控制引脚
    spk_sd = Pin(63, Pin.OUT, pull=Pin.PULL_NONE, drive=7)
    # 拉低使能
    spk_sd.value(0)

    os.exitpoint(os.EXITPOINT_ENABLE)
    nn.shrink_memory_pool()
    # 设置模型路径和其他参数
    kmodel_path = "/sdcard/examples/kmodel/kws.kmodel"
    # 其它参数
    THRESH = 0.5                # 检测阈值
    SAMPLE_RATE = 16000         # 采样率16000Hz,即每秒采样16000次
    CHANNELS = 1                # 通道数 1为单声道，2为立体声
    FORMAT = paInt16            # 音频输入输出格式 paInt16
    CHUNK = int(0.3 * 16000)    # 每次读取音频数据的帧数，设置为0.3s的帧数16000*0.3=4800
    reply_wav_file = "/sdcard/examples/utils/wozai.wav"         # kws唤醒词回复音频路径

    img = image.Image(DISPLAY_WIDTH, DISPLAY_HEIGHT, image.RGB888)
    # 初始化LCD
    Display.init(Display.ST7701, width = DISPLAY_WIDTH, height = DISPLAY_HEIGHT, to_ide = True)
    # 初始化音频预处理接口
    fp = aidemo.kws_fp_create()
    # 初始化音频流
    p = PyAudio()
    p.initialize(CHUNK)
    MediaManager.init()    #vb buffer初始化
    # 用于采集实时音频数据
    input_stream = p.open(format=FORMAT,channels=CHANNELS,rate=SAMPLE_RATE,input=True,frames_per_buffer=CHUNK)
    # 用于播放回复音频，K230D BOX无扬声器，需要外接扬声器
    output_stream = p.open(format=FORMAT,channels=CHANNELS,rate=SAMPLE_RATE,output=True,frames_per_buffer=CHUNK)
    # 初始化自定义关键词唤醒实例
    kws = KWSApp(kmodel_path,threshold=THRESH,debug_mode=0)

    try:
        while True:
            os.exitpoint()                      # 检查是否有退出信号
            with ScopedTiming("total",1):
                pcm_data=input_stream.read()
                res=kws.run(pcm_data)
                if res:
                    print("====Detected XiaonanXiaonan!====")
                    wf = wave.open(reply_wav_file, "rb")
                    wav_data = wf.read_frames(CHUNK)
                    while wav_data:
                        output_stream.write(wav_data)
                        wav_data = wf.read_frames(CHUNK)
                    time.sleep(1) # 时间缓冲，用于播放回复声音
                    wf.close()
                    img.clear()
                    time.sleep_ms(100)
                    img.draw_string(0, 20, "Hello K230D-BOX\r\n", color=(255, 0, 0), scale=4)
                    Display.show_image(img)
                else:
                    print("Deactivated!")
                gc.collect()                    # 垃圾回收
            if button0.is_pressing():
                try:
                    with open("/sdcard/main.py", "rb") as f:
                        os.remove("/sdcard/main.py")
                except Exception as e:
                    pass
                with open("/sdcard/CanMV Sample/main.py", "rb") as f:
                    code_src = f.read()
                with open("/sdcard/main.py", "wb") as f:
                    f.write(code_src)
                machine.reset()
    except Exception as e:
        sys.print_exception(e)                  # 打印异常信息
    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        print(f"Exception {e}")

    finally:
        input_stream.stop_stream()
        output_stream.stop_stream()
        input_stream.close()
        output_stream.close()
        p.terminate()
        # deinit display
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        MediaManager.deinit()              #释放vb buffer
        aidemo.kws_fp_destroy(fp)
        kws.deinit()                       # 反初始化


