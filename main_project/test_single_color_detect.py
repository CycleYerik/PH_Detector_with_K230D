import time, os, sys
from media.sensor import *  # 导入sensor模块，使用摄像头相关接口
from media.display import * # 导入display模块，使用display相关接口
from media.media import *   # 导入media模块，使用meida相关接口
from machine import Pin, FPIOA

# pH值对应的LAB颜色阈值
# 格式: (pH值, (L_min, L_max, A_min, A_max, B_min, B_max))
pH_thresholds = [
    (0, (20, 43, -4, 5, 30, 40)),    # pH 0
    (1, (15, 40, 27,36,-33,-24)),    # pH 1
    (2, (20, 80, 26,35, -33, -23)),    # pH 2
    (3, (20, 76, 16,30,9,20)),     # pH 3
    (4, (20, 100, -3,7,14,26)),     # pH 4
    (5, (5, 100, -14, -4, 32, 43)),     # pH 5
    (6, (11, 100, -22, -12, 33, 43)),     # pH 6
    (7, (11, 100, -28, -18, 14, 26)),    # pH 7
    (8, (21, 100, -20, -11, -2, 10)),   # pH 8
    (9, (35, 55, -13, -4, -27, -16)),   # pH 9
    (10,(25, 26, -8, 1, -29, -14)),  # pH 10
    (11, (35, 50, 3, 15, -52, -42)),  # pH 11
    (12, (19, 26, 13, 20, -51,-37)),  # pH 12
    (13,(0, 60, 22, 32, -56, -45)),  # pH 13
    (14,(13, 20, 22, 30, -51, -40))   # pH 14
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

# 定义全局ROI区域 (x, y, width, height)
# 注意：此处的ROI尺寸应与 sensor.set_framesize() 设置的实际图像分辨率匹配。
# 如果 sensor.set_framesize(Sensor.VGA) (640x480)，则ROI不应超过此范围。
# 调整为VGA分辨率下的一个居中ROI，例如 (160, 120, 320, 240)
global_roi = (160, 0, 480, 480) # 假设使用VGA (640x480) 图像，此为图像中央的ROI

def set_global_roi(x, y, width, height):
    """设置全局ROI区域"""
    global global_roi
    global_roi = (x, y, width, height)

def is_blob_in_roi(blob_rect, roi): # 接收 (x, y, w, h) 元组
    """检查blob_rect是否在ROI区域内"""
    x, y, w, h = blob_rect # 现在解包是有效的
    roi_x, roi_y, roi_w, roi_h = roi
    
    # 检查blob的中心点是否在ROI内
    center_x = x + w // 2
    center_y = y + h // 2
    
    return (roi_x <= center_x <= roi_x + roi_w and 
            roi_y <= center_y <= roi_h + roi_y) # 修正: roi_y + roi_h

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

    # detections 中的元素是 (ph_value, blob_rect)
    # 排序时使用 blob_rect 的面积
    sorted_detections = sorted(detections, key=lambda x: x[1][2] * x[1][3], reverse=True)
    keep = []

    while sorted_detections:
        current = sorted_detections.pop(0) # 取出面积最大的检测框 (ph_value, blob_rect)
        keep.append(current)

        # current[1] 和 det[1] 都是 (x, y, w, h) 元组，可以直接传给 calculate_iou
        sorted_detections = [
            det for det in sorted_detections
            if calculate_iou(current[1], det[1]) < iou_threshold
        ]

    return keep

def detect_all_ph(img):
    """检测并显示多个pH值"""
    detected_ph_list = []
    MAX_AREA = 60000  # 最大面积阈值

    # 遍历所有pH值阈值进行检测
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=20000, merge=True)
        for blob in blobs:
            blob_rect = blob.rect() # 获取 (x, y, w, h) 元组
            # 检查blob_rect是否在ROI区域内且满足面积限制
            if blob_rect[2] * blob_rect[3] <= MAX_AREA and is_blob_in_roi(blob_rect, global_roi):
                detected_ph_list.append((ph_value, blob_rect)) # 存储 pH 值和矩形元组

    # 非极大值抑制，去除重叠的检测框
    final_detections = non_max_suppression(detected_ph_list)

    # 在图像上绘制ROI区域 (在检测模式下也绘制，以示检测范围)
    img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3], 
                      color=(0, 255, 0), thickness=2)

    # 在图像上绘制结果
    for ph_value, blob_rect in final_detections: # 迭代的是 (ph_value, 矩形元组)
        img.draw_rectangle(blob_rect[0], blob_rect[1], blob_rect[2], blob_rect[3], color=(255, 0, 0), thickness=4)
        text_y = max(0, blob_rect[1] - 30)
        img.draw_string(blob_rect[0], text_y, f"{ph_value}", color=(255, 0, 0), scale=2)

    return final_detections, img

def detect_single_ph(img):
    """检测并显示单pH值"""
    detected_ph = None
    max_blob_size = 0
    max_blob_rect = None # 存储面积最大的色块的矩形元组
    MAX_AREA = 60000  # 最大面积阈值

    # 首先遍历所有pH值，找到面积最大的色块
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=500, merge=True)
        for blob in blobs:
            blob_rect = blob.rect() # 获取 (x, y, w, h) 元组
            current_size = blob_rect[2] * blob_rect[3] # 使用元组的宽高计算面积
            # 检查blob_rect是否在ROI区域内且满足面积限制
            if current_size <= MAX_AREA and is_blob_in_roi(blob_rect, global_roi):
                if current_size > max_blob_size:
                    max_blob_size = current_size
                    detected_ph = ph_value
                    max_blob_rect = blob_rect # 存储矩形元组

    # 在图像上绘制ROI区域 (在检测模式下也绘制，以示检测范围)
    img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3], 
                      color=(0, 255, 0), thickness=2)

    # 如果找到了有效的色块，则绘制最大的
    if max_blob_rect is not None:
        # 在图像上绘制矩形框和pH值
        img.draw_rectangle(max_blob_rect[0], max_blob_rect[1], max_blob_rect[2], max_blob_rect[3], color=(255, 0, 0), thickness=4)
        text_y = max(0, max_blob_rect[1] - 30)
        img.draw_string(max_blob_rect[0], text_y, f"pH:{detected_ph}", color=(255, 0, 0), scale=2)

    # ====== START: 修改的显示逻辑 ======
    # 定义文本显示的起始X坐标（靠近左侧）
    text_display_x = 10
    # 定义文本显示的起始Y坐标（中上部）
    # img.height() // 4 大约是总高的四分之一处
    text_display_y_base = img.height() // 4 

    # 绘制 "pH" 标签
    # 使用白色，比例为4，使其足够大且清晰
    img.draw_string(text_display_x, text_display_y_base, "pH", color=(255, 255, 255), scale=4)

    # 计算pH值或"NO"的Y坐标，使其在"pH"标签的下一行
    # 假设 scale=4 的文本高度大约是40-50像素，这里使用50作为偏移量
    value_display_y = text_display_y_base + 50 

    # 根据是否检测到pH值来确定显示内容
    if detected_ph is not None:
        value_str = f"{detected_ph}"
    else:
        value_str = "NO"
    
    # 绘制pH值或"NO"
    # 使用红色，比例为4
    img.draw_string(text_display_x, value_display_y, value_str, color=(255, 0, 0), scale=4)
    # ====== END: 修改的显示逻辑 ======

    return detected_ph, img

def check_key_press(key):
    """按键KEY0、1响应函数"""
    if key.value() == 0:
        time.sleep_ms(20)  # 消抖
        if key.value() == 0:
            return True
    return False

def check_key_press_k2(key):
    """按键KEY2响应函数"""
    if key.value() == 1:
        time.sleep_ms(20)  # 消抖
        if key.value() == 1:
            return True
    return False

def flash_led(duration_ms=1000):
    """补光灯的开闭"""
    if io25:
        io25.value(1) # 打开LED
        time.sleep_ms(duration_ms)
        io25.value(0) # 关闭LED

def main():
    try:
        global io25

        # 配置IO25为输出并置为低电平（初始关闭）
        fpioa.set_function(25, FPIOA.GPIO25)
        io25 = Pin(25, Pin.OUT)
        io25.value(1) # 初始状态设为低电平（LED补光灯关闭）

        # 初始化摄像头
        sensor = Sensor(width=1280, height=960)
        sensor.reset()
        sensor.set_framesize(Sensor.VGA) # 设置VGA分辨率 (640x480)
        sensor.set_pixformat(Sensor.RGB565)

        # 初始化显示
        # 显示器分辨率应与摄像头输出分辨率一致，或根据需要进行缩放
        Display.init(Display.ST7701, width=sensor.width(), height=sensor.height(),to_ide=True)
        MediaManager.init()
        sensor.run()

        print("pH值颜色识别程序已启动")
        print("KEY0: 切换到实时预览模式")
        print("KEY1: 进行单次pH值识别")
        print("KEY2: 切换识别模式 (单次检测/所有检测)")

        current_state = PREVIEW_MODE
        last_detected_ph = None
        last_detected_img = None
        is_start_detect = False
        detect_mode = ALL_DETECT # 保持 detect_mode 初始值不变

        # 主循环，实现状态机
        while True:
            os.exitpoint()

            # 状态机处理

            # 切换检测功能
            if check_key_press_k2(key2):
                if detect_mode == SINGLE_DETECT:
                    detect_mode = ALL_DETECT
                    print("切换到检测所有pH值模式")
                else:
                    detect_mode = SINGLE_DETECT
                    print("切换到单次检测pH值模式")
                # 等待按键释放
                while key2.value() == 1:
                    time.sleep_ms(10)

            # 实时预览模式
            if current_state == PREVIEW_MODE:
                img = sensor.snapshot()
                
                # 在实时预览中绘制ROI区域
                # 使用绿色边框，厚度为2
                img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3], 
                                  color=(0, 255, 0), thickness=2)
                
                Display.show_image(img)

                # 是否按下按键进行识别
                if check_key_press(key1):
                    current_state = DETECT_MODE
                    print("切换到单次识别模式")
                    is_start_detect = True
                    # 等待按键释放
                    while key1.value() == 0:
                        time.sleep_ms(10)

            # 单次识别模式
            elif current_state == DETECT_MODE:
                # 默认显示已有的检测结果
                if last_detected_img is not None :
                    Display.show_image(last_detected_img)

                # 检查是否进行新的识别
                if check_key_press(key1) or is_start_detect:
                    is_start_detect = False

                    # 打开补光灯，提示正在检测
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
                            last_detected_img = processed_img
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
                    io25.value(1) # 切换回预览模式时，确保补光灯关闭（或根据需求调整）
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