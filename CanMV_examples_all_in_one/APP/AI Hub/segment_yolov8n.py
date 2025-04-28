#####################################################################################################
# @file         main.py
# @author       正点原子团队(ALIENTEK)
# @version      V1.0
# @date         2024-09-12
# @brief        物体分割实验
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

from libs.PipeLine import PipeLine, ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import os
import ujson
from media.media import *
from media.sensor import *
from time import *
import nncase_runtime as nn
import ulab.numpy as np
import time
import utime
import image
import random
import gc
import sys
import aidemo
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

# 自定义YOLOv8分割类
class SegmentationApp(AIBase):
    def __init__(self,kmodel_path,labels,model_input_size,confidence_threshold=0.2,nms_threshold=0.5,mask_threshold=0.5,rgb888p_size=[224,224],display_size=[1920,1080],debug_mode=0):
        super().__init__(kmodel_path,model_input_size,rgb888p_size,debug_mode)
        # 模型路径
        self.kmodel_path=kmodel_path
        # 分割类别标签
        self.labels=labels
        # 模型输入分辨率
        self.model_input_size=model_input_size
        # 置信度阈值
        self.confidence_threshold=confidence_threshold
        # nms阈值
        self.nms_threshold=nms_threshold
        # mask阈值
        self.mask_threshold=mask_threshold
        # sensor给到AI的图像分辨率
        self.rgb888p_size=[ALIGN_UP(rgb888p_size[0],16),rgb888p_size[1]]
        # 显示分辨率
        self.display_size=[ALIGN_UP(display_size[0],16),display_size[1]]
        self.debug_mode=debug_mode
        # 检测框预置颜色值
        self.color_four=[(255, 220, 20, 60), (255, 119, 11, 32), (255, 0, 0, 142), (255, 0, 0, 230),
                         (255, 106, 0, 228), (255, 0, 60, 100), (255, 0, 80, 100), (255, 0, 0, 70),
                         (255, 0, 0, 192), (255, 250, 170, 30), (255, 100, 170, 30), (255, 220, 220, 0),
                         (255, 175, 116, 175), (255, 250, 0, 30), (255, 165, 42, 42), (255, 255, 77, 255),
                         (255, 0, 226, 252), (255, 182, 182, 255), (255, 0, 82, 0), (255, 120, 166, 157)]
        # 分割结果的numpy.array，用于给到aidemo后处理接口
        self.masks=np.zeros((1,self.display_size[1],self.display_size[0],4))
        # Ai2d实例，用于实现模型预处理
        self.ai2d=Ai2d(debug_mode)
        # 设置Ai2d的输入输出格式和类型
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT,nn.ai2d_format.NCHW_FMT,np.uint8, np.uint8)

    # 配置预处理操作，这里使用了pad和resize，Ai2d支持crop/shift/pad/resize/affine，具体代码请打开/sdcard/app/libs/AI2D.py查看
    def config_preprocess(self,input_image_size=None):
        with ScopedTiming("set preprocess config",self.debug_mode > 0):
            # 初始化ai2d预处理配置，默认为sensor给到AI的尺寸，您可以通过设置input_image_size自行修改输入尺寸
            ai2d_input_size=input_image_size if input_image_size else self.rgb888p_size
            top,bottom,left,right=self.get_padding_param()
            self.ai2d.pad([0,0,0,0,top,bottom,left,right], 0, [114,114,114])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1,3,ai2d_input_size[1],ai2d_input_size[0]],[1,3,self.model_input_size[1],self.model_input_size[0]])

    # 自定义当前任务的后处理
    def postprocess(self,results):
        with ScopedTiming("postprocess",self.debug_mode > 0):
            # 这里使用了aidemo的segment_postprocess接口
            seg_res = aidemo.segment_postprocess(results,[self.rgb888p_size[1],self.rgb888p_size[0]],self.model_input_size,[self.display_size[1],self.display_size[0]],self.confidence_threshold,self.nms_threshold,self.mask_threshold,self.masks)
            return seg_res

    # 绘制结果
    def draw_result(self,pl,seg_res):
        with ScopedTiming("display_draw",self.debug_mode >0):
            if seg_res[0]:
                pl.osd_img.clear()
                mask_img=image.Image(self.display_size[0], self.display_size[1], image.ARGB8888,alloc=image.ALLOC_REF,data=self.masks)
                pl.osd_img.copy_from(mask_img)
                dets,ids,scores = seg_res[0],seg_res[1],seg_res[2]
                for i, det in enumerate(dets):
                    x1, y1, w, h = map(lambda x: int(round(x, 0)), det)
                    pl.osd_img.draw_string_advanced(x1,y1-50,32, " " + self.labels[int(ids[i])] + " " + str(round(scores[i],2)) , color=self.get_color(int(ids[i])))
            else:
                pl.osd_img.clear()

    # 计算padding参数
    def get_padding_param(self):
        dst_w = self.model_input_size[0]
        dst_h = self.model_input_size[1]
        ratio_w = float(dst_w) / self.rgb888p_size[0]
        ratio_h = float(dst_h) / self.rgb888p_size[1]
        if ratio_w < ratio_h:
            ratio = ratio_w
        else:
            ratio = ratio_h
        new_w = (int)(ratio * self.rgb888p_size[0])
        new_h = (int)(ratio * self.rgb888p_size[1])
        dw = (dst_w - new_w) / 2
        dh = (dst_h - new_h) / 2
        top = (int)(round(dh - 0.1))
        bottom = (int)(round(dh + 0.1))
        left = (int)(round(dw - 0.1))
        right = (int)(round(dw + 0.1))
        return  top, bottom, left, right

    # 根据当前类别索引获取框的颜色
    def get_color(self, x):
        idx=x%len(self.color_four)
        return self.color_four[idx]


if __name__=="__main__":
    fpioa = FPIOA()
    button0 = Button(fpioa, 34, 0)

    # 显示模式，默认"hdmi",可以选择"hdmi"和"lcd"
    display_mode="lcd"
    if display_mode=="hdmi":
        display_size=[1920,1080]
    else:
        display_size=[640,480]
    # 模型路径
    kmodel_path="/sdcard/examples/kmodel/yolov8n_seg_320.kmodel"
    labels = ["person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch", "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]
    #其它参数设置
    confidence_threshold = 0.2
    nms_threshold = 0.5
    mask_threshold=0.5
    rgb888p_size=[320,320]

    # 初始化PipeLine
    sensor = Sensor(width=1280, height=960) # 构建摄像头对象
    pl = PipeLine(rgb888p_size=rgb888p_size, display_size=display_size, display_mode=display_mode)
    pl.create(sensor=sensor)  # 创建PipeLine实例
    # 初始化自定义YOLOV8分割示例
    seg=SegmentationApp(kmodel_path,labels=labels,model_input_size=[320,320],confidence_threshold=confidence_threshold,nms_threshold=nms_threshold,mask_threshold=mask_threshold,rgb888p_size=rgb888p_size,display_size=display_size,debug_mode=0)
    seg.config_preprocess()
    try:
        while True:
            os.exitpoint()
            with ScopedTiming("total",1):
                # 获取当前帧数据
                img=pl.get_frame()
                # 推理当前帧
                seg_res=seg.run(img)
                # 打印结果
#                print(seg_res)
                # 绘制结果到PipeLine的osd图像
                seg.draw_result(pl,seg_res)
                # 显示当前的绘制结果
                pl.show_image()
                gc.collect()
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
        sys.print_exception(e)
    finally:
        seg.deinit()
        pl.destroy()

