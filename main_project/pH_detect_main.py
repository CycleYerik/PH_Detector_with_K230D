import time, os, sys
from media.sensor import *
from media.display import *
from media.media import *
from machine import Pin, FPIOA

# pH值对应的LAB颜色阈值
# 格式: (pH值, (L_min, L_max, A_min, A_max, B_min, B_max))
pH_thresholds = [
    (0, (20, 43, -4, 5, 30, 40)),    # pH 0
    (1, (15, 48, 24,36,-27,-17)),    # pH 1
    (2, (20, 80, 19,26, -12, 2)),    # pH 2
    (3, (20, 76, 10,20,-4,10)),     # pH 3
    (4, (20, 100, -1,11,20,38)),     # pH 4
    (5, (5, 100, -15,-5,24,37)),     # pH 5
    (6, (11, 100, -28,-16,39,50)),     # pH 6
    (7, (11, 100, -26,-18,20,30)),    # pH 7
    (8, (21, 100, -24,-16,4,15)),   # pH 8
    (9, (0, 55, -23,-13,-8,6)),   # pH 9
    (10,(0, 36, 3,14,-42,-29)),  # pH 10
    (11, (0, 50,17,26,-46,-40)),  # pH 11
    (12, (0, 46, 26,38,-60,-48)),  # pH 12
    (13,(0, 25, 12,23,-41,-30)),  # pH 13
    (14,(0, 20, 22, 34, -52, -42))   # pH 14
]

# 初始化各种IO引脚
fpioa = FPIOA()
fpioa.set_function(34, FPIOA.GPIO34)  # KEY0
fpioa.set_function(35, FPIOA.GPIO35)  # KEY1
fpioa.set_function(0, FPIOA.GPIO0)    # KEY2
key0 = Pin(34, Pin.IN, pull=Pin.PULL_UP, drive=7)
key1 = Pin(35, Pin.IN, pull=Pin.PULL_UP, drive=7)
key2 = Pin(0, Pin.IN, pull=Pin.PULL_DOWN, drive=7)  # KEY2默认下拉


#! 各种模式的配置

# 运行模式
PREVIEW_MODE = 0  # 实时预览模式
DETECT_MODE = 1   # 单次识别模式

# 显示模式 (此为配置标志变量)
SINGLE_DETECT = 0  # 只显示最大面积的pH值
ALL_DETECT = 1    # 显示所有检测到的pH值

# 显示控制标志
SHOW_BOX = True   # 控制是否显示框选结果






io25 = None  # GPIO25引脚对象，用于LED控制

# ROI检测区域 (x, y, width, height)，图像分辨率为640x480
#global_roi = (160, 0, 480, 480)  # 整个正方形框
global_roi = (320 , 0 , 160, 480)

def set_global_roi(x, y, width, height):
    """设置全局ROI区域"""
    global global_roi
    global_roi = (x, y, width, height)

def is_blob_in_roi(blob_rect, roi): # 接收 (x, y, w, h) 元组
    """检查blob_rect是否在ROI区域内"""
    x, y, w, h = blob_rect
    roi_x, roi_y, roi_w, roi_h = roi

    # 检查blob的中心点是否在ROI内
    center_x = x + w // 2
    center_y = y + h // 2

    return (roi_x <= center_x <= roi_x + roi_w and
            roi_y <= center_y <= roi_h + roi_y)

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
    MAX_AREA = 60000  # 单个色块最大像素面积阈值

    # 遍历所有pH值阈值进行检测
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=1000, merge=True)
        for blob in blobs:
            blob_rect = blob.rect()
            if blob_rect[2] * blob_rect[3] <= MAX_AREA and is_blob_in_roi(blob_rect, global_roi):
                detected_ph_list.append((ph_value, blob_rect))

    # 非极大值抑制，去除重叠的检测框
    final_detections = non_max_suppression(detected_ph_list)

    # 绘制ROI区域，以示检测范围
    img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3],
                          color=(0, 255, 0), thickness=2)

    # 在图像上绘制结果
    if SHOW_BOX:
        for ph_value, blob_rect in final_detections:
            img.draw_rectangle(blob_rect[0], blob_rect[1], blob_rect[2], blob_rect[3], color=(255, 0, 0), thickness=4)
            text_y = max(0, blob_rect[1] - 30)
            img.draw_string(blob_rect[0], text_y, f"{ph_value}", color=(255, 0, 0), scale=2)

    # 将识别的结果显示在左侧
    text_display_x = 10
    text_display_y_base = img.height() // 4
    # 模式显示
    mode_display_y = text_display_y_base - 45
    img.draw_string(text_display_x, mode_display_y, "All", color=(255, 255, 255), scale=3)
    img.draw_string(text_display_x, text_display_y_base, "pH", color=(255, 255, 255), scale=4)
    value_display_y = text_display_y_base + 50
    if final_detections:
        unique_ph_values = sorted(set(ph for ph, _ in final_detections))
        value_str = ",".join(str(ph) for ph in unique_ph_values)
    else:
        value_str = "NO"
    img.draw_string(text_display_x, value_display_y, value_str, color=(255, 0, 0), scale=4)

    return final_detections, img

def detect_single_ph(img):
    """检测并显示单pH值"""
    detected_ph = None
    max_blob_size = 0
    max_blob_rect = None
    MAX_AREA = 60000  # 最大面积阈值

    # 遍历所有pH值，找到面积最大的色块
    for ph_value, threshold in pH_thresholds:
        blobs = img.find_blobs([threshold], pixels_threshold=1000, merge=True)
        for blob in blobs:
            blob_rect = blob.rect()
            current_size = blob_rect[2] * blob_rect[3]
            if current_size <= MAX_AREA and is_blob_in_roi(blob_rect, global_roi):
                if current_size > max_blob_size:
                    max_blob_size = current_size
                    detected_ph = ph_value
                    max_blob_rect = blob_rect

    # 绘制ROI区域，以示检测范围
    img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3],
                          color=(0, 255, 0), thickness=2)

    # 如果找到了有效的色块，则绘制最大的
    if max_blob_rect is not None and SHOW_BOX:
        img.draw_rectangle(max_blob_rect[0], max_blob_rect[1], max_blob_rect[2], max_blob_rect[3], color=(255, 0, 0), thickness=4)
        text_y = max(0, max_blob_rect[1] - 30)
        img.draw_string(max_blob_rect[0], text_y, f"pH:{detected_ph}", color=(255, 0, 0), scale=2)

    # 将识别的结果显示在左侧
    text_display_x = 10
    text_display_y_base = img.height() // 4
    # 模式显示
    mode_display_y = text_display_y_base - 45
    img.draw_string(text_display_x, mode_display_y, "Single", color=(255, 255, 255), scale=3)
    img.draw_string(text_display_x, text_display_y_base, "pH", color=(255, 255, 255), scale=4)
    value_display_y = text_display_y_base + 50
    if detected_ph is not None:
        value_str = f"{detected_ph}"
    else:
        value_str = "NO"
    img.draw_string(text_display_x, value_display_y, value_str, color=(255, 0, 0), scale=4)

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

        # 配置IO25为输出并置为低电平
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
        detect_mode = ALL_DETECT

        # 主循环，实现状态机
        while True:
            os.exitpoint()


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

                # 绘制ROI区域
                img.draw_rectangle(global_roi[0], global_roi[1], global_roi[2], global_roi[3],
                                  color=(0, 255, 0), thickness=2)
                # 在左上角显示 'live'
                text_display_x = 10
                text_display_y_base = img.height() // 4
                img.draw_string(text_display_x, text_display_y_base, "live", color=(255, 255, 255), scale=5)

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
                    io25.value(1) # 切换回预览模式时，确保补光灯关闭
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
