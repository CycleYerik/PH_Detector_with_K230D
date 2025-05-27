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
    (0, (20, 43, 29, 45, -6, 1)),    # pH 0 - 红色
    (1, (15, 40, 24,35,-17,-7)),    # pH 1
    (2, (20, 41, 19,34, -15, 0)),    # pH 2
    (3, (20, 76, 15,22,15,25)),     # pH 3
    (4, (20, 80, 4,10,15,30)),     # pH 4
    (5, (5, 77, -9, 2, 32, 42)),     # pH 5
    (6, (11, 72, -15, -5, 31, 43)),     # pH 6
    (7, (11, 72, -24, -12, 14, 28)),    # pH 7
    (8, (21, 40, -24, -12, 5, 17)),   # pH 8
    (9, (7, 40, -13, -6, -21, -7)),   # pH 9
    (10,(5, 36, -7, 2, -28, -16)),  # pH 10
    (11, (5, 35, -3, 6, -33, -25)),  # pH 11
    (12, (7, 30, 8, 18, -41, -32)),  # pH 12
    (13,(0, 31, 20, 30, -46, -40)),  # pH 13
    (14,(9, 30, 15, 30, -42, -33))   # pH 14
]

# 初始化FPIOA
fpioa = FPIOA()
# 配置按键引脚
fpioa.set_function(34, FPIOA.GPIO34)  # KEY0
fpioa.set_function(35, FPIOA.GPIO35)  # KEY1
fpioa.set_function(0, FPIOA.GPIO0)    # KEY2
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)
key2 = Pin(0, Pin.IN, pull=Pin.PULL_DOWN, drive=7)  # KEY2默认下拉

# 定义运行模式
PREVIEW_MODE = 0  # 实时预览模式
DETECT_MODE = 1   # 单次识别模式

# 定义显示模式 (此为配置标志变量)
SINGLE_DETECT = 0  # 只显示最大面积的pH值
ALL_DETECT = 1    # 显示所有检测到的pH值

# 全局变量及配置
io25 = None  # GPIO25引脚对象，用于LED控制
detect_mode = ALL_DETECT  # 默认使用多值检测模式 (SINGLE_DETECT, ALL_DETECT)

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

def non_max_suppression(detections, iou_threshold=0.1):
    """非极大值抑制，去除重叠的检测框"""
    if not detections:
        return []
    
    # 按置信度（面积）排序
    # detections 格式: (ph_value, blob_tuple)
    # blob_tuple 格式: (x, y, w, h)
    sorted_detections = sorted(detections, key=lambda x: x[1][2] * x[1][3], reverse=True)
    keep = []
    
    while sorted_detections:
        current = sorted_detections.pop(0)
        keep.append(current)
        
        # 移除与当前框重叠度高的其他框
        # 注意：这里会移除所有与当前框重叠度高于 iou_threshold 的框，无论其 pH 值是否相同
        # 如果需要保留不同 pH 值但有重叠的框，需要更复杂的逻辑
        sorted_detections = [
            det for det in sorted_detections
            if calculate_iou(current[1], det[1]) < iou_threshold
        ]
    
    return keep


def detect_all_ph(img):
    """检测并显示所有pH值"""
    
    detected_ph_list = []
    
    # 遍历所有pH值进行检测
    for ph_value, threshold in pH_thresholds:
        # pixels_threshold 调整为适用于多个小色块的检测，避免太多噪声
        blobs = img.find_blobs([threshold], pixels_threshold=200, merge=True) 
        for blob in blobs:
            detected_ph_list.append((ph_value, blob))
    
    # 使用NMS去重，保留最大且不重叠的色块
    # 这里的NMS会优先保留面积大的色块，如果不同pH值的色块严重重叠，可能会只保留其中一个
    final_detections = non_max_suppression(detected_ph_list)
    
    # 在图像上绘制结果
    for ph_value, blob in final_detections:
        img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=(255, 0, 0), thickness=4)
        # 确保文本不会超出图片上方边界
        text_y = max(0, blob[1] - 30) 
        img.draw_string(blob[0], text_y, f"{ph_value}", color=(255, 0, 0), scale=2)
    
    return final_detections, img


def detect_single_ph(img):
    """只检测并显示最大面积的pH值"""
    
    detected_ph = None
    max_blob_size = 0
    max_blob = None
    
    # 定义面积阈值（像素数）
    MIN_AREA = 100  # 最小面积阈值
    MAX_AREA = 200000  # 最大面积阈值
    
    # 首先遍历所有pH值，找到最大的色块
    for ph_value, threshold in pH_thresholds:
        # pixels_threshold 和 merge 参数针对单次检测进行了调整，以找到较大且合并的区域
        blobs = img.find_blobs([threshold], pixels_threshold=1500, merge=True)
        for blob in blobs:
            current_size = blob[2] * blob[3]  # 计算当前色块大小
            # 只考虑在面积范围内的色块
            if MIN_AREA <= current_size <= MAX_AREA:
                if current_size > max_blob_size:
                    max_blob_size = current_size
                    detected_ph = ph_value
                    max_blob = blob
    
    # 如果找到了有效的色块，则绘制最大的那个
    if max_blob is not None:
        # 在图像上绘制矩形框和pH值
        img.draw_rectangle(max_blob[0], max_blob[1], max_blob[2], max_blob[3], color=(255, 0, 0), thickness=4)
        text_y = max(0, max_blob[1] - 30) # 确保文本不越界
        img.draw_string(max_blob[0], text_y, f"pH:{detected_ph}", color=(255, 0, 0), scale=2)
    
    # 在图像下方固定位置显示检测结果 (使用相对位置)
    bottom_text_y = img.height() - 100 # 距离底部100像素
    if detected_ph is not None:
        text_str = f"pH:{detected_ph}"
        # 估算文本宽度并居中
        # 假设scale=5时，每个字符宽度大约是15-20像素，这里取个估计值
        text_width = len(text_str) * 25 
        text_x = (img.width() - text_width) // 2
        img.draw_string(text_x, bottom_text_y, text_str, color=(255, 0, 0), scale=5)
    else:
        text_str = "No pH detected"
        text_width = len(text_str) * 25
        text_x = (img.width() - text_width) // 2
        img.draw_string(text_x, bottom_text_y, text_str, color=(255, 0, 0), scale=5)
    
    return detected_ph, img

def check_key_press(key):
    """检查按键是否按下（带消抖）"""
    if key.value() == 0:
        time.sleep_ms(20)  # 消抖
        if key.value() == 0:
            return True
    return False

def flash_led(duration_ms=1000):
    """LED闪烁函数"""
    if io25:
        io25.value(1) # 打开LED
        time.sleep_ms(duration_ms)
        io25.value(0) # 关闭LED

def main():
    try:
        global io25 # 声明io25为全局变量，因为在这里进行赋值操作
        
        # 配置IO25为输出并置为低电平（初始关闭）
        fpioa.set_function(25, FPIOA.GPIO25)
        io25 = Pin(25, Pin.OUT)
        io25.value(0) # 初始状态设为低电平（LED关闭）
        
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
        
        current_state = PREVIEW_MODE
        last_detected_ph = None
        last_detected_img = None
        is_start_detect = False
        
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
                    is_start_detect = False
                    
                    # 闪烁LED提示正在检测
                    flash_led(500) # 闪烁0.5秒
                    
                    img = sensor.snapshot()
                    # 根据当前检测模式选择检测函数
                    if detect_mode == SINGLE_DETECT:
                        detected_ph, processed_img = detect_single_ph(img)
                        if detected_ph is not None:
                            last_detected_ph = detected_ph
                            last_detected_img = processed_img
                            print(f"检测到pH值: {detected_ph}")
                        else:
                            last_detected_ph = None # 清除上次检测结果
                            last_detected_img = processed_img # 即使没检测到也更新图像，显示“No pH detected”
                            print("未检测到有效的pH值颜色")
                    else: # detect_mode == ALL_DETECT
                        detected_ph_list, processed_img = detect_all_ph(img)
                        if detected_ph_list:
                            last_detected_img = processed_img
                            ph_values = [str(ph) for ph, _ in detected_ph_list]
                            print(f"检测到pH值: {','.join(ph_values)}")
                        else:
                            last_detected_img = processed_img # 即使没检测到也更新图像
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
        # 确保LED在程序结束时关闭
        if io25:
            io25.value(0) 
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(100)
        MediaManager.deinit()

if __name__ == "__main__":
    os.exitpoint(os.EXITPOINT_ENABLE)
    main()