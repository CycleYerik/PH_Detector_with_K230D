#####################################################################################################
# @file         test_single_color_detect.py
# @brief        pH值颜色识别实验
# @license      Copyright (c) 2020-2032, 广州市星翼电子科技有限公司
#####################################################################################################

import time, os, sys
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口
from machine import Pin, FPIOA

# pH值对应的LAB颜色阈值
# 格式: (pH值, (L_min, L_max, A_min, A_max, B_min, B_max))
pH_thresholds = [
    (0, (37, 43, 29, 51, -4, 5)),    # pH 0 - 红色
    (1, (37, 43, 29, 51, -4, 5)),    # pH 1
    (2, (43, 45, 31, 58, -9, 16)),    # pH 2
    (3, (22, 76, 28, 73, 18, 53)),     # pH 3
    (4, (22, 81, 5, 8, 32, 44)),     # pH 4
    (5, (22, 61, -20, -1, 16, 29)),     # pH 5
    (6, (11, 72, 3, 9, 35, 54)),     # pH 6
    (7, (11, 72, -11, -1, 16, 36)),    # pH 7
    (8, (21, 40, -20, -4, 9, 22)),   # pH 8
    (9, (26, 36, -38, -4, 2, 5)),   # pH 9
    (10, (17, 29, -21, -6, -25, 1)),  # pH 10
    (11, (17, 23, -6, -1, -11, -3)),  # pH 11
    (12, (16, 30, 3, 14, -21, -3)),  # pH 12
    (13,  (2, 36, 9, 11, -19, -9)),  # pH 13
    (14, (21, 25, -4, 8, -11, 0))   # pH 14
]

# 初始化FPIOA
fpioa = FPIOA()
# 配置按键引脚
fpioa.set_function(34, FPIOA.GPIO34)  # KEY0
fpioa.set_function(35, FPIOA.GPIO35)  # KEY1
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)

# 定义状态
PREVIEW_MODE = 0  # 实时预览模式
DETECT_MODE = 1   # 单次识别模式

# 定义显示模式
SINGLE_DETECT = 0  # 只显示最大面积的pH值
ALL_DETECT = 1    # 显示所有检测到的pH值

def calculate_iou(box1, box2):
    """计算两个框的IoU（交并比）"""
    # box格式: (x, y, w, h)
    x1 = max(box1[0], box2[0])
    y1 = max(box1[1], box2[1])
    x2 = min(box1[0] + box1[2], box2[0] + box2[2])
    y2 = min(box1[1] + box1[3], box2[1] + box2[3])
    
    # 计算交集面积
    intersection = max(0, x2 - x1) * max(0, y2 - y1)
    
    # 计算并集面积
    box1_area = box1[2] * box1[3]
    box2_area = box2[2] * box2[3]
    union = box1_area + box2_area - intersection
    
    # 计算IoU
    iou = intersection / union if union > 0 else 0
    return iou

def non_max_suppression(detections, iou_threshold=0.5):
    """非极大值抑制，去除重叠的检测框"""
    if not detections:
        return []
    
    # 按置信度（面积）排序
    sorted_detections = sorted(detections, key=lambda x: x[1][2] * x[1][3], reverse=True)
    keep = []
    
    while sorted_detections:
        # 保留置信度最高的检测框
        current = sorted_detections.pop(0)
        keep.append(current)
        
        # 移除与当前框重叠度高的其他框
        sorted_detections = [
            det for det in sorted_detections
            if calculate_iou(current[1], det[1]) < iou_threshold
        ]
    
    return keep

def detect_all_ph(img):
    """检测并显示所有pH值，使用NMS去重"""
    detected_ph_list = []
    
    # 遍历所有pH值进行检测
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=200)
        for blob in blobs:
            detected_ph_list.append((ph_value, blob))
    
    # 使用NMS去重
    filtered_detections = non_max_suppression(detected_ph_list)
    
    # 在图像上绘制结果
    for ph_value, blob in filtered_detections:
        # 在图像上绘制矩形框和pH值
        img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=(255, 0, 0), thickness=4)
        img.draw_string(blob[0], blob[1] - 30, f"{ph_value}", color=(255, 0, 0), scale=2)
    
    
    
    return filtered_detections, img

def detect_single_ph(img):
    """只检测并显示最大面积的pH值"""
    detected_ph = None
    max_blob_size = 0
    max_blob = None
    
    # 首先遍历所有pH值，找到最大的色块
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=200)
        for blob in blobs:
            current_size = blob[2] * blob[3]  # 计算当前色块大小
            if current_size > max_blob_size:
                max_blob_size = current_size
                detected_ph = ph_value
                max_blob = blob
    
    # 如果找到了有效的色块，则只绘制最大的那个
    if max_blob is not None:
        # 在图像上绘制矩形框和pH值
        img.draw_rectangle(max_blob[0], max_blob[1], max_blob[2], max_blob[3], color=(255, 0, 0), thickness=4)
        img.draw_string(max_blob[0], max_blob[1] - 30, f"pH:{detected_ph}", color=(255, 0, 0), scale=2)
    
    # 在图像下方固定位置显示检测结果
    if detected_ph is not None:
        img.draw_string(img.width() - 420, img.height() - 100, f"pH:{detected_ph}", color=(255, 0, 0), scale=5)
    else:
        img.draw_string(img.width() - 600, img.height() - 100, "No pH detected", color=(255, 0, 0), scale=5)
    
    return detected_ph, img

def check_key_press(key):
    """检查按键是否按下（带消抖）"""
    if key.value() == 0:
        time.sleep_ms(20)  # 消抖
        if key.value() == 0:
            return True
    return False

def main():
    try:
        # 初始化摄像头
        sensor = Sensor(width=1280, height=960)
        sensor.reset()
        sensor.set_framesize(Sensor.VGA)
        sensor.set_pixformat(Sensor.RGB565)        
        # 初始化显示
        Display.init(Display.ST7701, width=sensor.width(), height=sensor.height(),to_ide=True)
        MediaManager.init()
        sensor.run()
        
        print("pH值颜色识别程序已启动")
        print("KEY0: 切换到实时预览模式")
        print("KEY1: 进行单次pH值识别")
        print("KEY2: 切换显示模式（单值/多值）")
        
        current_state = PREVIEW_MODE
        last_detected_ph = None
        last_detected_img = None
        is_start_detect = False
        detect_mode = ALL_DETECT  # 默认使用多值检测模式
        
        while True:
            os.exitpoint()
            
            # 状态机处理
            if current_state == PREVIEW_MODE:
                # 实时预览模式
                img = sensor.snapshot()
                Display.show_image(img)
                
                # 检查是否进行识别
                if check_key_press(key1):
                    current_state = DETECT_MODE
                    print("切换到单次识别模式")
                    is_start_detect = True
                    # 等待按键释放
                    while key1.value() == 0:
                        time.sleep_ms(10)
                
            elif current_state == DETECT_MODE:
                # 单次识别模式，显示最后一次识别结果
                if last_detected_img is not None:
                    Display.show_image(last_detected_img)
                
                # 检查是否进行新的识别
                if check_key_press(key1) or is_start_detect:
                    # 捕获当前图像并进行识别
                    is_start_detect = False
                    img = sensor.snapshot()
                    
                    # 根据当前检测模式选择检测函数
                    if detect_mode == SINGLE_DETECT:
                        detected_ph, processed_img = detect_single_ph(img)
                        if detected_ph is not None:
                            last_detected_ph = detected_ph
                            last_detected_img = processed_img
                            print(f"检测到pH值: {detected_ph}")
                        else:
                            print("未检测到有效的pH值颜色")
                    else:
                        detected_ph_list, processed_img = detect_all_ph(img)
                        if detected_ph_list:
                            last_detected_img = processed_img
                            ph_values = [str(ph) for ph, _ in detected_ph_list]
                            print(f"检测到pH值: {','.join(ph_values)}")
                        else:
                            print("未检测到有效的pH值颜色")
                    
                    # 等待按键释放
                    while key1.value() == 0:
                        time.sleep_ms(10)
                
                # 检查是否切换回预览模式
                if check_key_press(key0):
                    current_state = PREVIEW_MODE
                    print("切换到实时预览模式")
                    # 等待按键释放
                    while key0.value() == 0:
                        time.sleep_ms(10)
            
            time.sleep_ms(100)  # 降低CPU使用率

    except KeyboardInterrupt as e:
        print("user stop: ", e)
    except BaseException as e:
        print(f"Exception {e}")
    finally:
        # 释放资源
        if isinstance(sensor, Sensor):
            sensor.stop()
        Display.deinit()
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    main() 