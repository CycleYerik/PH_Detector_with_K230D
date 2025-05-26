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

# 定义状态
PREVIEW_MODE = 0  # 实时预览模式
DETECT_MODE = 1   # 单次识别模式

# 定义显示模式
SINGLE_DETECT = 0  # 只显示最大面积的pH值
ALL_DETECT = 1    # 显示所有检测到的pH值

# 定义检测方案
OLD_DETECT = 0    # 使用旧的基于阈值的检测方案
NEW_DETECT = 1    # 使用新的基于矩形检测和颜色分析的方案

# RGB到LAB转换的常量
PARAM_13 = 1.0 / 3.0
PARAM_16116 = 16.0 / 116.0
XN = 0.950456
YN = 1.0
ZN = 1.088754

# 全局变量
io25 = None  # GPIO25引脚对象
detect_method = OLD_DETECT  # 默认使用新方案

def gamma(x):
    """Gamma校正函数"""
    return pow((x + 0.055) / 1.055, 2.4) if x > 0.04045 else x / 12.92

def rgb_to_xyz(r, g, b):
    """RGB转XYZ颜色空间"""
    # 归一化RGB值
    r = r / 255.0
    g = g / 255.0
    b = b / 255.0
    
    # Gamma校正
    r = gamma(r)
    g = gamma(g)
    b = gamma(b)
    
    # RGB到XYZ的转换矩阵
    x = 0.4124564 * r + 0.3575761 * g + 0.1804375 * b
    y = 0.2126729 * r + 0.7151522 * g + 0.0721750 * b
    z = 0.0193339 * r + 0.1191920 * g + 0.9503041 * b
    
    return x, y, z

def xyz_to_lab(x, y, z):
    """XYZ转LAB颜色空间"""
    # 归一化
    x /= XN
    y /= YN
    z /= ZN
    
    # 计算f函数
    def f(t):
        return pow(t, PARAM_13) if t > 0.008856 else 7.787 * t + PARAM_16116
    
    fx = f(x)
    fy = f(y)
    fz = f(z)
    
    # 计算LAB值
    l = 116.0 * fy - 16.0
    l = max(0.0, l)  # 确保L值非负
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    
    return l, a, b

def rgb_to_lab(r, g, b):
    """RGB转LAB颜色空间"""
    x, y, z = rgb_to_xyz(r, g, b)
    return xyz_to_lab(x, y, z)

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

def non_max_suppression(detections, iou_threshold=0.1): # iou越大，重叠度越高
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

def calculate_lab_distance(lab1, lab2):
    """计算两个LAB颜色值之间的欧氏距离"""
    return ((lab1[0] - lab2[0])**2 + (lab1[1] - lab2[1])**2 + (lab1[2] - lab2[2])**2)**0.5

def find_closest_ph(lab_value):
    """有问题，暂无法运行。根据LAB颜色值找到最接近的pH值"""
    min_distance = float('inf')
    closest_ph = None
    
    for ph, (l_min, l_max, a_min, a_max, b_min, b_max) in pH_thresholds:
        # 计算LAB范围的中心点
        lab_center = (
            (l_min + l_max) / 2,
            (a_min + a_max) / 2,
            (b_min + b_max) / 2
        )
        # 计算与当前pH值的LAB中心点的距离
        distance = calculate_lab_distance(lab_value, lab_center)
        if distance < min_distance:
            min_distance = distance
            closest_ph = ph
    
    return closest_ph

def detect_all_ph_new(img):
    """有问题，暂无法运行。使用新方案检测并显示所有pH值"""
    detected_ph_list = []
    
    # 首先进行矩形检测
    for r in img.find_rects(threshold=8000):
        # 获取矩形区域
        x, y, w, h = r.rect()
        # 提取矩形区域内的图像
        roi = img.copy(x, y, w, h)
        
        # 计算ROI区域的平均LAB值
        l_sum = a_sum = b_sum = 0
        pixel_count = 0
        
        for py in range(h):
            for px in range(w):
                pixel = roi.get_pixel(px, py)
                # 将RGB转换为LAB
                r, g, b = pixel  # 假设pixel返回(R,G,B)元组
                l, a, b = rgb_to_lab(r, g, b)
                l_sum += l
                a_sum += a
                b_sum += b
                pixel_count += 1
        
        if pixel_count > 0:
            avg_l = l_sum / pixel_count
            avg_a = a_sum / pixel_count
            avg_b = b_sum / pixel_count
            
            # 找到最接近的pH值
            ph_value = find_closest_ph((avg_l, avg_a, avg_b))
            if ph_value is not None:
                detected_ph_list.append((ph_value, (x, y, w, h)))
    
    # 使用NMS去重
    filtered_detections = non_max_suppression(detected_ph_list)
    
    # 在图像上绘制结果
    for ph_value, rect in filtered_detections:
        img.draw_rectangle(rect[0], rect[1], rect[2], rect[3], color=(255, 0, 0), thickness=4)
        img.draw_string(rect[0], rect[1] - 30, f"{ph_value}", color=(255, 0, 0), scale=2)
    
    return filtered_detections, img

def detect_single_ph_new(img):
    """有问题，暂无法运行。使用新方案只检测并显示最大面积的pH值"""
    detected_ph = None
    max_rect_size = 0
    max_rect = None
    
    # 进行矩形检测
    for r in img.find_rects(threshold=8000):
        x, y, w, h = r.rect()
        current_size = w * h
        
        if current_size > max_rect_size:
            # 提取矩形区域内的图像
            roi = img.copy(x, y, w, h)
            
            # 计算ROI区域的平均LAB值
            l_sum = a_sum = b_sum = 0
            pixel_count = 0
            
            for py in range(h):
                for px in range(w):
                    pixel = roi.get_pixel(px, py)
                    # 将RGB转换为LAB
                    r, g, b = pixel  # 假设pixel返回(R,G,B)元组
                    l, a, b = rgb_to_lab(r, g, b)
                    l_sum += l
                    a_sum += a
                    b_sum += b
                    pixel_count += 1
            
            if pixel_count > 0:
                avg_l = l_sum / pixel_count
                avg_a = a_sum / pixel_count
                avg_b = b_sum / pixel_count
                
                # 找到最接近的pH值
                ph_value = find_closest_ph((avg_l, avg_a, avg_b))
                if ph_value is not None:
                    max_rect_size = current_size
                    detected_ph = ph_value
                    max_rect = (x, y, w, h)
    
    # 如果找到了有效的矩形，则绘制结果
    if max_rect is not None:
        img.draw_rectangle(max_rect[0], max_rect[1], max_rect[2], max_rect[3], color=(255, 0, 0), thickness=4)
        img.draw_string(max_rect[0], max_rect[1] - 30, f"pH:{detected_ph}", color=(255, 0, 0), scale=2)
    
    # 在图像下方固定位置显示检测结果
    if detected_ph is not None:
        img.draw_string(img.width() - 420, img.height() - 100, f"pH:{detected_ph}", color=(255, 0, 0), scale=5)
    else:
        img.draw_string(img.width() - 600, img.height() - 100, "No pH detected", color=(255, 0, 0), scale=5)
    
    return detected_ph, img

def detect_all_ph(img):
    """检测并显示所有pH值，根据标志位选择检测方案"""
    if detect_method == NEW_DETECT:
        return detect_all_ph_new(img)
    else:
        detected_ph_list = []
        
        # 遍历所有pH值进行检测
        for ph_value, threshold in pH_thresholds:
            blobs = img.find_blobs([threshold], pixels_threshold=200)
            for blob in blobs:
                detected_ph_list.append((ph_value, blob))
        
        # 使用NMS去重
        filtered_detections = non_max_suppression(detected_ph_list)
        
        # 过滤不同pH值但重合度高的检测框
        final_detections = []
        for i, (ph_value, blob) in enumerate(filtered_detections):
            skip = False
            for j, (other_ph, other_blob) in enumerate(final_detections):
                if ph_value != other_ph and calculate_iou(blob, other_blob) > 0.1:
                    # 如果重合度高，保留面积较大的那个
                    if blob[2] * blob[3] > other_blob[2] * other_blob[3]:
                        final_detections[j] = (ph_value, blob)
                    skip = True
                    break
            if not skip:
                final_detections.append((ph_value, blob))
        
        # 在图像上绘制结果
        for ph_value, blob in final_detections:
            img.draw_rectangle(blob[0], blob[1], blob[2], blob[3], color=(255, 0, 0), thickness=4)
            img.draw_string(blob[0], blob[1] - 30, f"{ph_value}", color=(255, 0, 0), scale=2)
        
        return final_detections, img

def detect_single_ph(img):
    """只检测并显示最大面积的pH值，根据标志位选择检测方案"""
    if detect_method == NEW_DETECT:
        return detect_single_ph_new(img)
    else:
        detected_ph = None
        max_blob_size = 0
        max_blob = None
        
        # 定义面积阈值（像素数）
        MIN_AREA = 100  # 最小面积阈值
        MAX_AREA = 200000  # 最大面积阈值
        
        # 首先遍历所有pH值，找到最大的色块
        for ph_value, threshold in pH_thresholds:
            blobs = img.find_blobs([threshold],pixels_threshold = 1500,merge = True)
            for blob in blobs:
                current_size = blob[2] * blob[3]  # 计算当前色块大小
                # 只考虑在面积范围内的色块
                if MIN_AREA <= current_size <= MAX_AREA:
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
        global io25, detect_method
        # 配置IO25为输出并置为高电平
        fpioa.set_function(25, FPIOA.GPIO25)
        io25 = Pin(25, Pin.OUT)
        io25.value(1)  # 初始状态设为低电平
        
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
        # print("KEY2: 切换检测方案（旧方案/新方案）") # 暂未加入
        
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
                    # # 打开LED灯
                    # io25.value(1)
                    # # 等待2秒
                    # time.sleep_ms(1000)
                    # # 关闭LED灯
                    # io25.value(0)
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
                    # 打开LED灯
                    # io25.value(1)
                    # # 等待2秒
                    # time.sleep_ms(1000)
                    # # 关闭LED灯
                    # io25.value(0)
                    
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