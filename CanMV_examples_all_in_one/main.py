from media.display import *
from media.media import *
import machine
from machine import TOUCH
from machine import Pin
from machine import FPIOA
from machine import RTC
from machine import PWM
import os
import gc
import time
import lvgl as lv
import math

DISPLAY_WIDTH = 640
DISPLAY_HEIGHT = 480

RESOURCES_PATH = "/sdcard/CanMV Sample/"

class LCD():
    def __init__(self, width=640, height=480, to_ide=False, fpioa=None, bl_pinx=5, bl_valid=1):
        self.display = Display()
        self.display.init(Display.ST7701, width, height, to_ide=to_ide, quality=100)
        MediaManager.init()

        fpioa.set_function(bl_pinx, fpioa.GPIO0 + bl_pinx)
        pull = Pin.PULL_UP if bl_valid == 0 else Pin.PULL_DOWN
        self.bl = Pin(bl_pinx, Pin.OUT, pull=pull, drive=7)
        self.bl_valid = bl_valid
        self.on()

    def __del__(self):
        del self.bl
        os.exitpoint(os.EXITPOINT_ENABLE_SLEEP)
        time.sleep_ms(50)
        self.display.deinit()
        MediaManager.deinit()

    def on(self):
        self.bl.value(self.bl_valid)

    def off(self):
        self.bl.value(1 - self.bl_valid)

    def lvgl_flush_cb(self, disp, area, px_map):
        if disp.flush_is_last() == True:
            if self.draw_buf_1.virtaddr() == uctypes.addressof(px_map.__dereference__()):
                self.display.show_image(self.draw_buf_1)
            else:
                self.display.show_image(self.draw_buf_2)

        disp.flush_ready()

    def lvgl_init(self, width, height):
        self.draw_buf_1 = image.Image(width, height, image.BGRA8888)
        self.draw_buf_2 = image.Image(width, height, image.BGRA8888)

        self.disp = lv.disp_create(width, height)
        self.disp.set_flush_cb(self.lvgl_flush_cb)
        self.disp.set_draw_buffers(self.draw_buf_1.bytearray(), self.draw_buf_2.bytearray(), self.draw_buf_1.size(), lv.DISP_RENDER_MODE.DIRECT)

    def lvgl_deinit(self):
        del self.disp
        del self.draw_buf_1
        del self.draw_buf_2

class Touch():
    def __init__(self):
        self.touch = TOUCH(0)

    def __del__(self):
        del self.touch

    def lvgl_read_cb(self, indev, data):
        x, y, state = 0, 0, lv.INDEV_STATE.RELEASED
        tp = self.touch.read(1)
        if len(tp):
            x, y, event = tp[0].x, tp[0].y, tp[0].event
            if event == TOUCH.EVENT_DOWN or event == TOUCH.EVENT_MOVE:
                state = lv.INDEV_STATE.PRESSED
        data.point = lv.point_t({'x': x, 'y': y})
        data.state = state

    def lvgl_init(self):
        self.indev = lv.indev_create()
        self.indev.set_type(lv.INDEV_TYPE.POINTER)
        self.indev.set_read_cb(self.lvgl_read_cb)

    def lvgl_deinit(self):
        del self.indev

class LED():
    def __init__(self, fpioa, pinx, valid=0, pwm_ch=-1):
        self.is_pwm = False
        self.valid = valid
        if pwm_ch != -1:
            self.is_pwm = True
            duty = 100 if self.valid == 0 else 0
            fpioa.set_function(pinx, fpioa.PWM0 + pwm_ch)
            self.pwm = PWM(pwm_ch, 1000, duty, enable=True)
        else:
            pull = Pin.PULL_UP if self.valid == 0 else Pin.PULL_DOWN
            value = 1 if self.valid == 0 else 0
            fpioa.set_function(pinx, FPIOA.GPIO0 + pinx)
            self.pin = Pin(pinx, Pin.OUT, pull=pull, drive=7)
            self.pin.value(value)

    def off(self):
        if self.is_pwm != False:
            self.pwm.duty(100 if self.valid == 0 else 0)
        else:
            self.pin.value(1 if self.valid == 0 else 0)

    def on(self):
        if self.is_pwm != False:
            self.pwm.duty(0 if self.valid == 0 else 100)
        else:
            self.pin.value(0 if self.valid == 0 else 1)

    def set_brightness(self, brightness):
        if self.is_pwm != False:
            brightness = 0 if brightness < 0 else 100 if brightness > 100 else brightness
            self.pwm.duty(100 - brightness if self.valid == 0 else brightness)

class Button():
    def __init__(self, fpioa, pinx, valid=0):
        fpioa.set_function(pinx, fpioa.GPIO0 + pinx)

        pull = Pin.PULL_UP if valid == 0 else Pin.PULL_DOWN
        self.pin = Pin(pinx, Pin.IN, pull=pull, drive=7)
        self.valid = valid

    def is_pressing(self):
        return True if self.pin.value() == self.valid else False

class Buzzer():
    def __init__(self, fpioa, pinx, valid=0, pwm_ch=-1):
        self.valid = valid
        duty = 100 if self.valid == 0 else 0
        fpioa.set_function(pinx, fpioa.PWM0 + pwm_ch)
        self.pwm = PWM(pwm_ch, 4000, duty, enable=True)

    def off(self):
        self.pwm.duty(100 if self.valid == 0 else 0)

    def on(self):
        self.pwm.duty(0 if self.valid == 0 else 100)

    def set_loudness(self, loudness):
        loudness = 0 if loudness < 0 else 100 if loudness > 100 else loudness
        self.pwm.duty(100 - loudness if self.valid == 0 else loudness)

    def set_frequency(self, frequency):
        self.pwm.freq(frequency)

class ClockManager():
    def __init__(self, year, month, day, hour, minute, second, microsecond):
        self.rtc = RTC()
        self.set_time(year, month, day, hour, minute, second, microsecond)

    def __del__(self):
        del self.rtc

    def set_time(self, year, month, day, hour, minute, second, microsecond):
        self.rtc.init((year, month, day, 0, hour, minute, second, microsecond))

    def get_time(self):
        return self.rtc.datetime()

def lvgl_init(lcd, touch):
    lv.init()
    lcd.lvgl_init(DISPLAY_WIDTH, DISPLAY_HEIGHT)
    touch.lvgl_init()

def lvgl_deinit(lcd, touch):
    lcd.lvgl_deinit()
    touch.lvgl_deinit()
    lv.deinit()

class GUI():
    class LockScreen():
        class HomeBar():
            def __init__(self, screen, bar_color):
                self.home_bar = lv.obj(screen)
                self.home_bar.set_size(lv.pct(50), 12)
                self.home_bar.align(lv.ALIGN.BOTTOM_MID, 0, -10)
                self.home_bar.set_style_pad_all(0, 0)
                self.home_bar.set_style_border_width(0, 0)
                self.home_bar.set_style_bg_color(bar_color, 0)
                self.home_bar.clear_flag(lv.obj.FLAG.SCROLLABLE)

                self.lv_font_lock_screen_home_bar_label = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_lock_screen_home_bar_label_size30_bpp4.bin")

                self.bar_label = lv.label(screen)
                self.bar_label.set_style_text_font(self.lv_font_lock_screen_home_bar_label, 0)
                self.bar_label.set_text("Swipe up to open")
                self.bar_label.align(lv.ALIGN.BOTTOM_MID, 0, -25)
                self.bar_label.set_style_text_color(bar_color, 0)

                self.bar_handle_start_y = None
                self.bar_handle = lv.obj(screen)
                self.bar_handle.set_size(lv.pct(100), 80)
                self.bar_handle.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                self.bar_handle.set_style_pad_all(0, 0)
                self.bar_handle.set_style_border_width(0, 0)
                self.bar_handle.set_style_radius(0, 0)
                self.bar_handle.set_style_opa(0, 0)
                self.bar_handle.move_foreground()
                self.bar_handle.set_user_data(screen)
                self.bar_handle.add_event(self.bar_handle_all_event_cb, lv.EVENT.ALL, None)

                self.home_bar_y_anim = lv.anim_t()
                self.home_bar_y_anim.init()
                self.home_bar_y_anim.set_var(self.home_bar)
                self.home_bar_y_anim.set_values(-10, -25)
                self.home_bar_y_anim.set_time(1000)
                self.home_bar_y_anim.set_playback_delay(500)
                self.home_bar_y_anim.set_playback_time(800)
                self.home_bar_y_anim.set_repeat_delay(2000)
                self.home_bar_y_anim.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
                self.home_bar_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.home_bar_y_anim.set_custom_exec_cb(lambda anim, val: self.home_bar_y_anim_cb(self.home_bar, val))
                lv.anim_t.start(self.home_bar_y_anim)

                self.bar_label_y_anim = lv.anim_t()
                self.bar_label_y_anim.init()
                self.bar_label_y_anim.set_var(self.bar_label)
                self.bar_label_y_anim.set_values(-25, -40)
                self.bar_label_y_anim.set_time(1000)
                self.bar_label_y_anim.set_playback_delay(0)
                self.bar_label_y_anim.set_playback_time(0)
                self.bar_label_y_anim.set_repeat_delay(3300)
                self.bar_label_y_anim.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
                self.bar_label_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.bar_label_y_anim.set_custom_exec_cb(lambda anim, val: self.bar_label_y_anim_cb(self.bar_label, val))
                lv.anim_t.start(self.bar_label_y_anim)

                self.bar_label_opa_anim = lv.anim_t()
                self.bar_label_opa_anim.init()
                self.bar_label_opa_anim.set_var(self.bar_label)
                self.bar_label_opa_anim.set_values(0, 255)
                self.bar_label_opa_anim.set_time(1000)
                self.bar_label_opa_anim.set_playback_delay(500)
                self.bar_label_opa_anim.set_playback_time(800)
                self.bar_label_opa_anim.set_repeat_delay(2000)
                self.bar_label_opa_anim.set_repeat_count(lv.ANIM_REPEAT_INFINITE)
                self.bar_label_opa_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.bar_label_opa_anim.set_custom_exec_cb(lambda anim, val: self.bar_label_opa_anim_cb(self.bar_label, val))
                lv.anim_t.start(self.bar_label_opa_anim)

                self.screen_y_anim = lv.anim_t()
                self.screen_y_anim.init()
                self.screen_y_anim.set_var(screen)
                self.screen_y_anim.set_time(300)
                self.screen_y_anim.set_repeat_count(1)
                self.screen_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.screen_y_anim.set_custom_exec_cb(lambda anim, val: self.screen_y_anim_cb(screen, val))

            def home_bar_y_anim_cb(self, home_bar, y):
                home_bar.set_y(y)

            def bar_label_y_anim_cb(self, bar_label, y):
                bar_label.set_y(y)

            def bar_label_opa_anim_cb(self, bar_label, opa):
                bar_label.set_style_opa(opa, 0)

            def screen_y_anim_cb(self, screen, y):
                screen.set_y(y)

            def bar_handle_all_event_cb(self, event):
                code = event.get_code()
                bar_handle = lv.obj.__cast__(event.get_target())
                screen = lv.obj.__cast__(bar_handle.get_user_data())

                if code == lv.EVENT.PRESSING:
                    point = lv.point_t()
                    indev = lv.indev_get_act()
                    indev.get_point(point)

                    if self.bar_handle_start_y is None:
                        self.bar_handle_start_y = point.y
                    else:
                        delta_y = point.y - self.bar_handle_start_y
                        screen_y = screen.get_y()
                        screen_y_dest = screen_y + delta_y
                        if screen_y_dest <= 0:
                            screen.set_y(screen_y_dest)
                        self.bar_handle_start_y = point.y
                elif code == lv.EVENT.RELEASED:
                    self.bar_handle_start_y = None
                    screen_y = screen.get_y()
                    screen_height = screen.get_height()
                    if screen_y < -(screen_height // 3):
                        self.screen_y_anim.set_values(screen_y, -520)
                    else:
                        self.screen_y_anim.set_values(screen_y, 0)
                    lv.anim_t.start(self.screen_y_anim)

        class ClockTime():
            def __init__(self, screen, hour, minute):
                self.lv_font_lock_screen_clock_time = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_lock_screen_clock_time_size150_bpp4.bin")

                self.clock_time = lv.label(screen)
                self.clock_time.set_style_text_font(self.lv_font_lock_screen_clock_time, 0)
                self.clock_time.set_text(f"{hour:02d}" + ":" + f"{minute:02d}")
                self.clock_time.align(lv.ALIGN.TOP_MID, 0, 100)
                self.clock_time.set_style_text_color(lv.color_hex(0x000000), 0)

            def set_time(self, hour, minute):
                self.clock_time.set_text(f"{hour:02d}" + ":" + f"{minute:02d}")

        class Wallpaper():
            def __init__(self, screen, path):
                with open(path, 'rb') as f:
                    wallpaper_data = f.read()
                wallpaper_dsc = lv.img_dsc_t({
                    'data_size': len(wallpaper_data),
                    'data': wallpaper_data
                })
                wallpaper = lv.img(screen)
                wallpaper.set_src(wallpaper_dsc)
                wallpaper.center()
                wallpaper.move_background()

        def __init__(self, screen):
            self.conv = lv.obj(screen)
            self.conv.set_size(lv.pct(100), lv.pct(100))
            self.conv.center()
            self.conv.set_style_pad_all(0, 0)
            self.conv.set_style_border_width(0, 0)
            self.conv.set_style_radius(0, 0)
            self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
            self.conv.set_style_bg_grad_color(lv.color_hex(0x000000), 0)
            self.conv.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
            self.conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
            self.conv.add_event(self.conv_all_event_cb, lv.EVENT.ALL, None)

            self.home_bar = self.HomeBar(self.conv, lv.color_hex(0xFFFFFF))
            self.clock_time = self.ClockTime(self.conv, 0, 0)
#            self.wallpaper = self.Wallpaper(self.conv, RESOURCES_PATH + "Wallpapers/lock_screen_wallpaper.png")

        def hide(self):
            self.conv.add_flag(lv.obj.FLAG.HIDDEN)

        def show(self):
            if self.conv.has_flag(lv.obj.FLAG.HIDDEN):
                self.conv.set_y(-480)
                self.conv.clear_flag(lv.obj.FLAG.HIDDEN)

                self.conv_y_anim = lv.anim_t()
                self.conv_y_anim.init()
                self.conv_y_anim.set_var(self.conv)
                self.conv_y_anim.set_values(-480, 0)
                self.conv_y_anim.set_time(300)
                self.conv_y_anim.set_repeat_count(1)
                self.conv_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.conv_y_anim.set_custom_exec_cb(lambda anim, val: self.conv_y_anim_cb(self.conv, val))
                lv.anim_t.start(self.conv_y_anim)

        def conv_y_anim_cb(self, conv, y):
            conv.set_y(y)

        def conv_all_event_cb(self, event):
            code = event.get_code()
            conv = lv.obj.__cast__(event.get_target())
            if code == lv.EVENT.STYLE_CHANGED:
                if (conv.get_y() <= -481):
                    self.hide()

    class HomeScreen():
        class AppManager():
            class AppBase():
                class HomeBar():
                    def __init__(self, icon_area, masker, screen, app_close_func):
                        self.icon_area = icon_area
                        self.app_close_func = app_close_func
                        self.app_need_close = False

                        self.home_bar = lv.obj(screen)
                        self.home_bar.set_size(lv.pct(50), 12)
                        self.home_bar.align(lv.ALIGN.BOTTOM_MID, 0, -10)
                        self.home_bar.set_style_pad_all(0, 0)
                        self.home_bar.set_style_border_width(0, 0)
                        self.home_bar.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.home_bar.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.home_bar_y_anim = lv.anim_t()
                        self.home_bar_y_anim.init()
                        self.home_bar_y_anim.set_var(self.home_bar)
                        self.home_bar_y_anim.set_time(300)
                        self.home_bar_y_anim.set_repeat_count(1)
                        self.home_bar_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.home_bar_y_anim.set_custom_exec_cb(lambda anim, val: self.home_bar_y_anim_cb(self.home_bar, val))

                        self.bar_handle_start_x = None
                        self.bar_handle_prev_y = None
                        self.bar_handle = lv.obj(screen)
                        self.bar_handle.set_size(lv.pct(50), 22)
                        self.bar_handle.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                        self.bar_handle.set_style_pad_all(0, 0)
                        self.bar_handle.set_style_border_width(0, 0)
                        self.bar_handle.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.bar_handle.set_style_radius(0, 0)
                        self.bar_handle.set_style_opa(0, 0)
                        self.bar_handle.move_foreground()
                        self.bar_handle.set_user_data(masker)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.PRESSING, None)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.RELEASED, None)

                        self.masker_width_anim = lv.anim_t()
                        self.masker_width_anim.init()
                        self.masker_width_anim.set_var(masker)
                        self.masker_width_anim.set_repeat_count(1)
                        self.masker_width_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.masker_width_anim.set_custom_exec_cb(lambda anim, val: self.masker_width_anim_cb(masker, val))
                        self.masker_width_anim.set_ready_cb(self.masker_width_anim_ready_cb)

                        self.masker_height_anim = lv.anim_t()
                        self.masker_height_anim.init()
                        self.masker_height_anim.set_var(masker)
                        self.masker_height_anim.set_repeat_count(1)
                        self.masker_height_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.masker_height_anim.set_custom_exec_cb(lambda anim, val: self.masker_height_anim_cb(masker, val))

                        self.masker_x_anim = lv.anim_t()
                        self.masker_x_anim.init()
                        self.masker_x_anim.set_var(masker)
                        self.masker_x_anim.set_repeat_count(1)
                        self.masker_x_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.masker_x_anim.set_custom_exec_cb(lambda anim, val: self.masker_x_anim_cb(masker, val))

                        self.masker_y_anim = lv.anim_t()
                        self.masker_y_anim.init()
                        self.masker_y_anim.set_var(masker)
                        self.masker_y_anim.set_repeat_count(1)
                        self.masker_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.masker_y_anim.set_custom_exec_cb(lambda anim, val: self.masker_y_anim_cb(masker, val))

                        self.masker_opa_anim = lv.anim_t()
                        self.masker_opa_anim.init()
                        self.masker_opa_anim.set_var(masker)
                        self.masker_opa_anim.set_repeat_count(1)
                        self.masker_opa_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                        self.masker_opa_anim.set_custom_exec_cb(lambda anim, val: self.masker_opa_anim_cb(masker, val))

                    def enter_full_screen(self):
                        self.home_bar_y_anim.set_values(-10, 12)
                        lv.anim_t.start(self.home_bar_y_anim)

                    def exit_full_screen(self):
                        self.home_bar_y_anim.set_values(12, -10)
                        lv.anim_t.start(self.home_bar_y_anim)

                    def home_bar_y_anim_cb(self, home_bar, y):
                        home_bar.set_y(y)

                    def masker_width_anim_ready_cb(self, anim):
                        if self.app_need_close == True:
                            self.app_close_func()

                    def masker_width_anim_cb(self, masker, width):
                        masker.set_width(width)

                    def masker_height_anim_cb(self, masker, height):
                        masker.set_height(height)

                    def masker_x_anim_cb(self, masker, x):
                        masker.set_x(x)

                    def masker_y_anim_cb(self, masker, y):
                        masker.set_y(y)

                    def masker_opa_anim_cb(self, masker, opa):
                        masker.set_style_opa(opa, 0)

                    def bar_handle_event_cb(self, event):
                        code = event.get_code()
                        bar_handle = lv.obj.__cast__(event.get_target())
                        masker = lv.obj.__cast__(bar_handle.get_user_data())

                        if code == lv.EVENT.PRESSING:
                            point = lv.point_t()
                            indev = lv.indev_get_act()
                            indev.get_point(point)

                            if self.bar_handle_start_x is None:
                                self.bar_handle_start_x = point.x
                                self.bar_handle_prev_y = point.y
                            else:
                                screen_width = masker.get_parent().get_width()
                                screen_height = masker.get_parent().get_height()
                                size_pct = 1 - (screen_height - point.y) / screen_height
                                if size_pct < 0.5:
                                    size_pct = 0.5
                                masker_width_dect = int(screen_width * size_pct)
                                masker_height_dect = int(screen_height * size_pct)
                                masker_x_dect = (screen_width - masker_width_dect) // 2 + point.x - self.bar_handle_start_x
                                masker_y_dect = point.y - self.bar_handle_prev_y + masker.get_y() + masker.get_height() - masker_height_dect
                                masker.set_width(masker_width_dect)
                                masker.set_height(masker_height_dect)
                                masker.set_x(masker_x_dect)
                                masker.set_y(masker_y_dect)
#                                masker.set_style_opa(int(size_pct * 255), 0)

                                self.bar_handle_prev_y = point.y
                        elif code == lv.EVENT.RELEASED:
                            screen = masker.get_parent()
                            screen_width = screen.get_width()
                            screen_height = screen.get_height()
                            masker_width = masker.get_width()
                            masker_height = masker.get_height()
                            masker_x = masker.get_x()
                            masker_y = masker.get_y()
                            masker_opa = masker.get_style_opa(0)

                            if self.bar_handle_prev_y > (screen_height * 0.75):
                                self.app_need_close = False
                                anim_time = 100
                                masker_width_dest = screen_width
                                masker_height_dest = screen_height
                                masker_x_dest = 1
                                masker_y_dest = 1
                                masker_opa_dest = 255
                            else:
                                self.app_need_close = True
                                anim_time = 200
                                masker_width_dest = self.icon_area.x2 - self.icon_area.x1
                                masker_height_dest = self.icon_area.y2 - self.icon_area.y1
                                masker_x_dest = self.icon_area.x1
                                masker_y_dest = self.icon_area.y1
                                masker_opa_dest = 0

                            self.masker_width_anim.set_time(anim_time)
                            self.masker_height_anim.set_time(anim_time)
                            self.masker_x_anim.set_time(anim_time)
                            self.masker_y_anim.set_time(anim_time)
                            self.masker_opa_anim.set_time(anim_time)
                            self.masker_width_anim.set_values(masker_width, masker_width_dest)
                            self.masker_height_anim.set_values(masker_height, masker_height_dest)
                            self.masker_x_anim.set_values(masker_x, masker_x_dest)
                            self.masker_y_anim.set_values(masker_y, masker_y_dest)
                            self.masker_opa_anim.set_values(masker_opa, masker_opa_dest)
                            lv.anim_t.start(self.masker_width_anim)
                            lv.anim_t.start(self.masker_height_anim)
                            lv.anim_t.start(self.masker_x_anim)
                            lv.anim_t.start(self.masker_y_anim)
#                            lv.anim_t.start(self.masker_opa_anim)

                            self.bar_handle_start_x = None
                            self.bar_handle_prev_y = None

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources, close_cb=None):
                    self.icon_area = icon_area
                    self.masker = masker
                    self.status_bar = status_bar
                    self.hw_resources = hw_resources
                    self.close_cb = close_cb
                    self.is_full_screen = False
                    self.timer_list = []

                    self.conv = lv.obj(masker)
                    self.conv.set_size(screen.get_width(), screen.get_height())
                    self.conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                    self.conv.set_style_pad_all(0, 0)
                    self.conv.set_style_border_width(0, 0)
                    self.conv.set_style_radius(0, 0)
                    self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.home_bar = self.HomeBar(self.icon_area, self.masker, self.conv, self.close_base)

                def close_base(self):
                    self.masker.move_background()
                    self.masker.add_flag(lv.obj.FLAG.HIDDEN)
                    if self.close_cb is not None:
                        self.close_cb()
                    for i in range(self.home_bar.bar_handle.get_event_count()):
                        self.home_bar.bar_handle.remove_event(i)
                    del self.home_bar
                    if len(self.timer_list) != 0:
                        for i in range(len(self.timer_list)):
                            self.timer_list[i].pause()
                            self.timer_list[i]._del()
                    self.conv.delete()
                    self.status_bar.light_mode()
                    if self.is_full_screen == True:
                        self.is_full_screen = False
                        self.status_bar.exit_full_screen()

                def set_home_bar_color(self, bar_color):
                    self.home_bar.home_bar.set_style_bg_color(bar_color, 0)

                def set_home_bar_top(self):
                    self.home_bar.home_bar.move_foreground()
                    self.home_bar.bar_handle.move_foreground()

                def enter_full_screen(self):
                    if self.is_full_screen == False:
                        self.is_full_screen = True
                        self.status_bar.enter_full_screen()
                        self.home_bar.enter_full_screen()

                def exit_full_screen(self):
                    if self.is_full_screen == True:
                        self.is_full_screen = False
                        self.status_bar.exit_full_screen()
                        self.home_bar.exit_full_screen()

            class AppTemplate(AppBase):
                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)

                    self.btn = lv.btn(self.conv)
                    self.btn.set_size(200, 100)
                    self.btn.center()

                    self.set_home_bar_color(lv.color_hex(0x000000))
                    self.set_home_bar_top()

            class AppAIHub(AppBase):
                class RebootConfirmer():
                    class DemoScriptRunner():
                        def __init__(self):
                            pass

                        def run(self, demo_script_path):
                            print(demo_script_path)
                            try:
                                with open("/sdcard/main.py", "rb") as f:
                                    os.remove("/sdcard/main.py")
                            except Exception as e:
                                pass
                            with open(demo_script_path, "rb") as f:
                                code_src = f.read()
                            with open("/sdcard/main.py", "wb") as f:
                                f.write(code_src)
                            machine.reset()

                    def __init__(self, screen):
                        self.lv_font_normal_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size25_bpp4.bin")
                        self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                        self.demo_script_runner = self.DemoScriptRunner()

                        self.masker = lv.obj(screen)
                        self.masker.set_size(lv.pct(100), lv.pct(100))
                        self.masker.center()
                        self.masker.set_style_pad_all(0, 0)
                        self.masker.set_style_border_width(0, 0)
                        self.masker.set_style_radius(0, 0)
                        self.masker.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.masker.set_style_bg_opa(50, 0)
                        self.masker.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.conv = lv.obj(self.masker)
                        self.conv.set_size(lv.pct(55), lv.pct(55))
                        self.conv.center()
                        self.conv.set_style_pad_all(0, 0)
                        self.conv.set_style_border_width(0, 0)
                        self.conv.set_style_radius(20, 0)
                        self.conv.set_style_clip_corner(True, 0)
                        self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.msg = lv.label(self.conv)
                        self.msg.set_style_text_font(self.lv_font_normal_size20, 0)
                        self.msg.set_width(lv.pct(90))
                        self.msg.set_text("Confirm to restart the device to run the Demo?\n\nPress and hold key0 to return.")
                        self.msg.align(lv.ALIGN.TOP_MID, 20, 30)
                        self.msg.set_style_text_color(lv.color_hex(0x000000), 0)

                        self.cancel_btn = lv.btn(self.conv)
                        self.cancel_btn.set_size(lv.pct(40), lv.pct(30))
                        self.cancel_btn.align(lv.ALIGN.BOTTOM_LEFT, 20, -20)
                        self.cancel_btn.set_style_radius(20, 0)
                        self.cancel_btn.set_style_bg_color(lv.color_hex(0x2196F3), 0)
                        self.cancel_btn.add_event(self.btn_event_cb, lv.EVENT.CLICKED, None)

                        self.btn_label = lv.label(self.cancel_btn)
                        self.btn_label.set_style_text_font(self.lv_font_normal_size25, 0)
                        self.btn_label.set_text("Cancel")
                        self.btn_label.center()
                        self.btn_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                        self.confirm_btn = lv.btn(self.conv)
                        self.confirm_btn.set_size(lv.pct(40), lv.pct(30))
                        self.confirm_btn.align(lv.ALIGN.BOTTOM_RIGHT, -20, -20)
                        self.confirm_btn.set_style_radius(20, 0)
                        self.confirm_btn.set_style_bg_color(lv.color_hex(0xF44336), 0)
                        self.confirm_btn.add_event(self.btn_event_cb, lv.EVENT.CLICKED, None)

                        self.btn_label = lv.label(self.confirm_btn)
                        self.btn_label.set_style_text_font(self.lv_font_normal_size25, 0)
                        self.btn_label.set_text("Confirm")
                        self.btn_label.center()
                        self.btn_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                        self.hide()

                        self.demo_script_path = None

                    def show(self, demo_script_path):
                        self.demo_script_path = demo_script_path
                        self.masker.move_foreground()
                        self.masker.clear_flag(lv.obj.FLAG.HIDDEN)

                    def hide(self):
                        self.masker.add_flag(lv.obj.FLAG.HIDDEN)

                    def btn_event_cb(self, event):
                        code = event.get_code()
                        btn = lv.btn.__cast__(event.get_target())

                        if code == lv.EVENT.CLICKED:
                            if btn == self.cancel_btn:
                                self.hide()
                            elif btn == self.confirm_btn:
                                self.demo_script_runner.run(self.demo_script_path)

                class DemoManager():
                    def __init__(self, side_bar, demo_show_func):
                        self.demo_show_func = demo_show_func

                        self.lv_font_normal_bold_size40 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_bold_size40_bpp4.bin")
                        self.lv_font_normal_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size25_bpp4.bin")
                        self.lv_font_app_ai_hub_demo_commit_bold_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_ai_hub_demo_commit_bold_size20_bpp4.bin")

                        self.list_title = lv.label(side_bar)
                        self.list_title.set_style_text_font(self.lv_font_normal_bold_size40, 0)
                        self.list_title.align(lv.ALIGN.TOP_LEFT, 20, 50)
                        self.list_title.set_text("AI Demo")
                        self.list_title.set_style_text_color(lv.color_hex(0x000000), 0)

                        self.list_conv = lv.obj(side_bar)
                        self.list_conv.set_size(lv.pct(100), lv.pct(80))
                        self.list_conv.align(lv.ALIGN.BOTTOM_LEFT, 0, 0)
                        self.list_conv.set_style_pad_all(0, 0)
                        self.list_conv.set_style_border_width(0, 0)
                        self.list_conv.set_style_radius(0, 0)
                        self.list_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.list_conv.set_style_bg_opa(0, 0)
                        self.list_conv.add_flag(lv.obj.FLAG.SCROLLABLE)
                        self.list_conv.set_scroll_dir(lv.DIR.VER)
                        self.list_conv.set_scroll_snap_y(lv.SCROLL_SNAP.NONE)
                        self.list_conv.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

                        self.demo_slot_list = []
                        self.demo_name_list = []
                        self.demo_commit_list = []
                        self.demo_show_path_list = []
                        self.demo_script_path_list = []

                    def add(self, icon_path, demo_name, demo_commit, demo_show_path, demo_script_path):
                        self.demo_name_list.append(demo_name)
                        self.demo_commit_list.append(demo_commit)
                        self.demo_show_path_list.append(demo_show_path)
                        self.demo_script_path_list.append(demo_script_path)

                        slot = lv.obj(self.list_conv)
                        slot.set_size(lv.pct(100), 100)
                        if len(self.demo_slot_list) == 0:
                            slot.align(lv.ALIGN.TOP_MID, 0, 0)
                        else:
                            slot_prev = self.demo_slot_list[-1]
                            slot.align_to(slot_prev, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                        slot.set_style_pad_all(0, 0)
                        slot.set_style_border_width(0, 0)
                        slot.set_style_radius(0, 0)
                        slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                        slot.set_style_bg_opa(0, 0)
                        slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        item_conv = lv.obj(slot)
                        item_conv.set_size(lv.pct(95), lv.pct(90))
                        item_conv.align(lv.ALIGN.TOP_MID, 0, 0)
                        item_conv.set_style_pad_all(0, 0)
                        item_conv.set_style_border_width(0, 0)
                        item_conv.set_style_radius(20, 0)
                        item_conv.set_style_clip_corner(True, 0)
                        item_conv.set_style_bg_color(lv.color_hex(0x007CFB), 0)
                        item_conv.set_style_bg_opa(0, 0)
                        item_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        if len(self.demo_slot_list) != 0:
                            slot_prev = self.demo_slot_list[-1]
                            blank = lv.obj(slot_prev)
                            blank.set_size(lv.pct(95), lv.pct(6))
                            blank.align(lv.ALIGN.BOTTOM_MID, 0, -2)
                            blank.set_style_pad_all(0, 0)
                            blank.set_style_border_width(0, 0)
                            blank.set_style_radius(20, 0)
                            blank.set_style_bg_color(lv.color_hex(0xF1F1F1), 0)
                            blank.set_style_bg_opa(255, 0)
                            blank.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        with open(icon_path, 'rb') as f:
                            icon_data = f.read()
                        icon_dsc = lv.img_dsc_t({
                            'data_size': len(icon_data),
                            'data': icon_data
                        })
                        icon = lv.img(item_conv)
                        icon.set_src(icon_dsc)
                        icon.align(lv.ALIGN.LEFT_MID, 5, 0)

                        label = lv.label(item_conv)
                        label.set_style_text_font(self.lv_font_normal_size25, 0)
                        label.set_text(demo_name)
                        label.set_width(180)
                        label.set_long_mode(lv.label.LONG.SCROLL)
                        label.set_style_anim_speed(15, 0)
                        label.align_to(icon, lv.ALIGN.OUT_RIGHT_TOP, 10, 10)
                        label.set_style_text_color(lv.color_hex(0x000000), 0)

                        commit = lv.label(item_conv)
                        commit.set_style_text_font(self.lv_font_app_ai_hub_demo_commit_bold_size20, 0)
                        commit.set_text(demo_commit)
                        commit.set_width(180)
                        commit.set_long_mode(lv.label.LONG.SCROLL)
                        commit.set_style_anim_speed(15, 0)
                        commit.align_to(icon, lv.ALIGN.OUT_RIGHT_BOTTOM, 10, -10)
                        commit.set_style_text_color(lv.color_hex(0x7F7F7F), 0)

                        handle = lv.obj(item_conv)
                        handle.set_size(lv.pct(100), lv.pct(100))
                        handle.center()
                        handle.set_style_pad_all(0, 0)
                        handle.set_style_border_width(0, 0)
                        handle.set_style_radius(0, 0)
                        handle.set_style_bg_opa(0, 0)
                        handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        handle.move_foreground()
                        handle.add_event(self.handle_event_cb, lv.EVENT.CLICKED, None)

                        self.demo_slot_list.append(slot)

                    def handle_event_cb(self, event):
                        code = event.get_code()
                        handle = lv.obj.__cast__(event.get_target())
                        item_conv = lv.obj.__cast__(handle.get_parent())
                        slot = lv.obj.__cast__(item_conv.get_parent())

                        if code == lv.EVENT.CLICKED:
                            if slot in self.demo_slot_list:
                                for slot_index in self.demo_slot_list:
                                    item_conv = slot_index.get_child(0)
                                    label = item_conv.get_child(1)
                                    commit = item_conv.get_child(2)

                                    if slot_index == slot:
                                        item_conv.set_style_bg_opa(255, 0)
                                        label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
                                        commit.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
                                    else:
                                        item_conv.set_style_bg_opa(0, 0)
                                        label.set_style_text_color(lv.color_hex(0x000000), 0)
                                        commit.set_style_text_color(lv.color_hex(0x7F7F7F), 0)

                                index = self.demo_slot_list.index(slot)
                                self.demo_show_func(self.demo_name_list[index], self.demo_commit_list[index], self.demo_show_path_list[index], self.demo_script_path_list[index])

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)
                    self.conv.set_style_bg_color(lv.color_hex(0xF3F2F7), 0)

                    self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")
                    self.lv_font_app_ai_hub_demo_commit_bold_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_ai_hub_demo_commit_bold_size20_bpp4.bin")
                    self.lv_font_normal_bold_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_bold_size25_bpp4.bin")

                    self.side_bar = lv.obj(self.conv)
                    self.side_bar.set_size(lv.pct(45), lv.pct(100))
                    self.side_bar.align(lv.ALIGN.LEFT_MID, 0, 0)
                    self.side_bar.set_style_pad_all(0, 0)
                    self.side_bar.set_style_border_width(0, 0)
                    self.side_bar.set_style_radius(0, 0)
                    self.side_bar.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.side_bar.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.demo_conv = lv.obj(self.conv)
                    self.demo_conv.set_size(lv.pct(55), lv.pct(100))
                    self.demo_conv.align(lv.ALIGN.RIGHT_MID, 0, 0)
                    self.demo_conv.set_style_pad_all(0, 0)
                    self.demo_conv.set_style_border_width(0, 0)
                    self.demo_conv.set_style_radius(0, 0)
                    self.demo_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.demo_conv.set_style_bg_opa(0, 0)
                    self.demo_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.reboot_confirmer = self.RebootConfirmer(screen)
                    self.demo_manager = self.DemoManager(self.side_bar, self.demo_show_func)

                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Face Detection",
                        "人脸检测",
                        RESOURCES_PATH + "APP/AI Hub/face_detection_show.png",
                        RESOURCES_PATH + "APP/AI Hub/face_detection.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Face Landmark",
                        "人体关键点检测",
                        RESOURCES_PATH + "APP/AI Hub/face_landmark_show.png",
                        RESOURCES_PATH + "APP/AI Hub/face_landmark.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Face Pose",
                        "人脸姿态检测",
                        RESOURCES_PATH + "APP/AI Hub/face_pose_show.png",
                        RESOURCES_PATH + "APP/AI Hub/face_pose.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Person Detection",
                        "人体检测",
                        RESOURCES_PATH + "APP/AI Hub/person_detection_show.png",
                        RESOURCES_PATH + "APP/AI Hub/person_detection.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Person Keypoint Detect",
                        "人体关键点检测",
                        RESOURCES_PATH + "APP/AI Hub/person_keypoint_detect_show.png",
                        RESOURCES_PATH + "APP/AI Hub/person_keypoint_detect.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Falldown Detect",
                        "跌倒检测",
                        RESOURCES_PATH + "APP/AI Hub/falldown_detect_show.png",
                        RESOURCES_PATH + "APP/AI Hub/falldown_detect.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Hand Detection",
                        "手掌检测",
                        RESOURCES_PATH + "APP/AI Hub/hand_detection_show.png",
                        RESOURCES_PATH + "APP/AI Hub/hand_detection.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Hand Recognition",
                        "手势识别",
                        RESOURCES_PATH + "APP/AI Hub/hand_recognition_show.png",
                        RESOURCES_PATH + "APP/AI Hub/hand_recognition.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Hand Keypoint Detection",
                        "手掌关键点检测",
                        RESOURCES_PATH + "APP/AI Hub/hand_keypoint_detection_show.png",
                        RESOURCES_PATH + "APP/AI Hub/hand_keypoint_detection.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Hand Keypoint Class",
                        "手掌关键点分类",
                        RESOURCES_PATH + "APP/AI Hub/hand_keypoint_class_show.png",
                        RESOURCES_PATH + "APP/AI Hub/hand_keypoint_class.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Dynamic Gesture",
                        "动态手势识别",
                        RESOURCES_PATH + "APP/AI Hub/dynamic_gesture_show.png",
                        RESOURCES_PATH + "APP/AI Hub/dynamic_gesture.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Space Resize",
                        "局部放大器",
                        RESOURCES_PATH + "APP/AI Hub/space_resize_show.png",
                        RESOURCES_PATH + "APP/AI Hub/space_resize.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Finger Guessing",
                        "猜拳游戏",
                        RESOURCES_PATH + "APP/AI Hub/finger_guessing_show.png",
                        RESOURCES_PATH + "APP/AI Hub/finger_guessing.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Object Detect",
                        "物体检测",
                        RESOURCES_PATH + "APP/AI Hub/object_detect_yolov8n_show.png",
                        RESOURCES_PATH + "APP/AI Hub/object_detect_yolov8n.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Segmentation",
                        "物体分割",
                        RESOURCES_PATH + "APP/AI Hub/segmentation_show.png",
                        RESOURCES_PATH + "APP/AI Hub/segmentation.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Licence Det",
                        "车牌检测",
                        RESOURCES_PATH + "APP/AI Hub/licence_det_show.png",
                        RESOURCES_PATH + "APP/AI Hub/licence_det.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Licence Det Rec",
                        "车牌号识别",
                        RESOURCES_PATH + "APP/AI Hub/licence_det_rec_show.png",
                        RESOURCES_PATH + "APP/AI Hub/licence_det_rec.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Keyword Spotting",
                        "关键词唤醒",
                        RESOURCES_PATH + "APP/AI Hub/keyword_spotting_show.png",
                        RESOURCES_PATH + "APP/AI Hub/keyword_spotting.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "Self Learning",
                        "自学习分类",
                        RESOURCES_PATH + "APP/AI Hub/self_learning_show.png",
                        RESOURCES_PATH + "APP/AI Hub/self_learning.py",
                    )
                    self.demo_manager.add(
                        RESOURCES_PATH + "APP/AI Hub/app_icon_72x72_intelligence.png",
                        "More",
                        "更多请见配套的CanMV例程……",
                        None,
                        None,
                    )

                    self.set_home_bar_color(lv.color_hex(0x000000))
                    self.set_home_bar_top()

                def demo_show_func(self, demo_name, demo_commit, demo_show_path, demo_script_path):
                    self.demo_script_path = demo_script_path

                    self.demo_conv.clean()

                    conv = lv.obj(self.demo_conv)
                    conv.set_size(lv.pct(90), lv.pct(88))
                    conv.align(lv.ALIGN.CENTER, 0, 0)
                    conv.set_style_pad_all(0, 0)
                    conv.set_style_border_width(0, 0)
                    conv.set_style_radius(20, 0)
                    conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    demo_show_conv = lv.obj(conv)
                    demo_show_conv.set_size(288, 216)
                    demo_show_conv.align(lv.ALIGN.TOP_MID, 0, 10)
                    demo_show_conv.set_style_pad_all(0, 0)
                    demo_show_conv.set_style_border_width(0, 0)
                    demo_show_conv.set_style_radius(20, 0)
                    demo_show_conv.set_style_clip_corner(True, 0)
                    demo_show_conv.set_style_bg_color(lv.color_hex(0xAFAFAF), 0)
                    demo_show_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    if demo_show_path != None:
                        with open(demo_show_path, 'rb') as f:
                            demo_show_data = f.read()
                        demo_show_dsc = lv.img_dsc_t({
                            'data_size': len(demo_show_data),
                            'data': demo_show_data
                        })
                        demo_show = lv.img(demo_show_conv)
                        demo_show.set_src(demo_show_dsc)
                        demo_show.center()

                    title = lv.label(conv)
                    title.set_style_text_font(self.lv_font_normal_bold_size25, 0)
                    title.set_text(demo_name)
                    title.align_to(demo_show_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
                    title.set_style_text_color(lv.color_hex(0x000000), 0)

                    commit = lv.label(conv)
                    commit.set_style_text_font(self.lv_font_app_ai_hub_demo_commit_bold_size20, 0)
                    commit.set_text(demo_commit)
                    commit.set_width(lv.pct(85))
                    commit.align_to(demo_show_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 45)
                    commit.set_style_text_color(lv.color_hex(0x5F5F5F), 0)

                    btn = lv.btn(conv)
                    btn.set_size(200, 60)
                    btn.align(lv.ALIGN.BOTTOM_MID, 0, -10)
                    btn.set_style_radius(20, 0)
                    btn.add_event(self.btn_event_cb, lv.EVENT.CLICKED, None)
                    if self.demo_script_path is None:
                        btn.set_style_bg_color(lv.color_hex(0x5F5F5F), 0)
                        btn.clear_flag(lv.obj.FLAG.CLICKABLE)

                    btn_label = lv.label(btn)
                    btn_label.set_style_text_font(self.lv_font_normal_size20, 0)
                    btn_label.set_text("Reboot to Run")
                    btn_label.center()
                    btn_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                def btn_event_cb(self, event):
                    if self.demo_script_path is not None:
                        self.reboot_confirmer.show(self.demo_script_path)

            class AppCalculator(AppBase):
                class Keyboard():
                    def __init__(self, conv, show_conv):
                        self.show_label = show_conv.get_child(0)
                        self.history_label = show_conv.get_child(1)

                        self.lv_font_app_calculator_keyboard = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_calculator_keyboard_size30_bpp4.bin")

                        btn_bg_color_list = [0x211924, 0x211924, 0x211924, 0x584B5E, 0xF99429,
                                             0x211924, 0x211924, 0x211924, 0x584B5E, 0xF99429,
                                             0x211924, 0x211924, 0x211924, 0x584B5E, 0xF99429,
                                             0x211924, 0x211924, 0x211924, 0xF99429, 0xF99429]
                        btn_label_list = ["7", "8", "9", "AC", "÷",
                                          "4", "5", "6", "+/-", "×",
                                          "1", "2", "3", "%", "-",
                                          "", "0", ".", "=", "+"]

                        for row in range(4):
                            for col in range(5):
                                btn = lv.obj(conv)
                                btn.set_grid_cell(lv.GRID_ALIGN.STRETCH, col, 1, lv.GRID_ALIGN.STRETCH, row, 1)
                                btn.set_style_pad_all(0, 0)
                                btn.set_style_border_width(0, 0)
                                btn.set_style_radius(50, 0)
                                btn.set_style_clip_corner(True, 0)
                                btn.set_style_bg_color(lv.color_hex(btn_bg_color_list[row * 5 + col]), 0)

                                label = lv.label(btn)
                                label.set_style_text_font(self.lv_font_app_calculator_keyboard, 0)
                                label.set_text(btn_label_list[row * 5 + col])
                                label.center()
                                label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                                btn_handle = lv.obj(btn)
                                btn_handle.set_size(lv.pct(100), lv.pct(100))
                                btn_handle.center()
                                btn_handle.set_style_pad_all(0, 0)
                                btn_handle.set_style_border_width(0, 0)
                                btn_handle.set_style_radius(0, 0)
                                btn_handle.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                                btn_handle.set_style_bg_opa(0, 0)
                                btn_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                                btn_handle.add_event(self.btn_handle_event_cb, lv.EVENT.PRESSED, None)
                                btn_handle.add_event(self.btn_handle_event_cb, lv.EVENT.RELEASED, None)
                                btn_handle.add_event(self.btn_handle_event_cb, lv.EVENT.CLICKED, None)

                                self.btn_handle_opa_anim = lv.anim_t()
                                self.btn_handle_opa_anim.init()
                                self.btn_handle_opa_anim.set_time(100)
                                self.btn_handle_opa_anim.set_repeat_count(1)
                                self.btn_handle_opa_anim.set_path_cb(lv.anim_t.path_ease_in_out)

                        self.btn_handle_prev_process = None
                        self.show_label_text_pointed = False
                        self.show_label_text_calculated = False
                        self.got_result = False

                    def btn_handle_event_cb(self, event):
                        code = event.get_code()
                        btn_handle = lv.obj.__cast__(event.get_target())

                        if code == lv.EVENT.PRESSED or code == lv.EVENT.RELEASED:
                            current_opa = btn_handle.get_style_bg_opa(0)
                            self.btn_handle_opa_anim.set_var(btn_handle)
                            self.btn_handle_opa_anim.set_custom_exec_cb(lambda anim, val: self.btn_handle_opa_anim_cb(btn_handle, val))
                            if code == lv.EVENT.PRESSED:
                                self.btn_handle_opa_anim.set_values(current_opa, 100)
                            elif code == lv.EVENT.RELEASED:
                                self.btn_handle_opa_anim.set_values(current_opa, 0)

                            if self.btn_handle_prev_process is not None:
                                self.btn_handle_prev_process.set_style_bg_opa(0, 0)
                            self.btn_handle_prev_process = btn_handle

                            lv.anim_t.start(self.btn_handle_opa_anim)

                        if code == lv.EVENT.CLICKED:
                            displayable_text_list = ["0", "1", "2", "3",
                                                "4", "5", "6", "7",
                                                "8", "9", ".", "+",
                                                "-", "×", "÷"]
                            calculate_text_list = ["+", "-", "×", "÷"]
                            label = btn_handle.get_parent().get_child(0)
                            label_text = label.get_text()
                            if label_text == "AC":
                                self.show_label.set_text("0")
                                self.history_label.set_text("")
                                self.show_label_text_pointed = False
                                self.show_label_text_calculated = False
                            elif label_text == "=":
                                show_label_text = self.show_label.get_text()
                                if show_label_text[-1] in calculate_text_list or show_label_text[-1] == ".":
                                    show_label_text = show_label_text[:-1]

                                self.history_label.set_text(show_label_text)

                                calculate_text = ""
                                calculate_index = -1
                                if show_label_text[0] != "-":
                                    for calculate_text in calculate_text_list:
                                        calculate_index = show_label_text.find(calculate_text)
                                        if calculate_index != -1:
                                            break
                                else:
                                    for calculate_text in calculate_text_list:
                                        calculate_index = show_label_text[1:].find(calculate_text)
                                        if calculate_index != -1:
                                            calculate_index = calculate_index + 1
                                            break

                                if calculate_index != -1:
                                    number1_text = show_label_text[:calculate_index]
                                    number2_text = show_label_text[calculate_index + 1:]

                                    index = number1_text.find(".")
                                    if index == -1:
                                        number1 = float(number1_text)
                                    else:
                                        while number1_text[-1] == "0":
                                            number1_text = number1_text[:-1]
                                        number1 = float(number1_text[:index]) + (float(number1_text[index + 1:]) / (10 ** len(number1_text[index + 1:])))

                                    index = number2_text.find(".")
                                    if index == -1:
                                        number2 = float(number2_text)
                                    else:
                                        while number2_text[-1] == "0":
                                            number2_text = number2_text[:-1]
                                        number2 = float(number2_text[:index]) + (float(number2_text[index + 1:]) / (10 ** len(number2_text[index + 1:])))

                                    if show_label_text[calculate_index] == "+":
                                        result = number1 + number2
                                    elif show_label_text[calculate_index] == "-":
                                        result = number1 - number2
                                    elif show_label_text[calculate_index] == "×":
                                        result = number1 * number2
                                    elif show_label_text[calculate_index] == "÷":
                                        if number2 != 0:
                                            result = number1 / number2
                                        else:
                                            result = "×"
                                    else:
                                        result = 0

                                    self.show_label.set_text(str(result).rstrip('0').rstrip('.'))
                                    self.got_result = True
                            elif label_text in displayable_text_list:
                                if self.got_result == True:
                                    self.got_result = False
                                    self.history_label.set_text("")
                                    self.show_label_text_pointed = False
                                    self.show_label_text_calculated = False
                                    if label_text not in calculate_text_list or self.show_label.get_text() == "×":
                                        self.show_label.set_text("0")

                                if self.show_label_text_pointed == True and label_text == ".":
                                    label_text = ""
                                if label_text == ".":
                                    self.show_label_text_pointed = True

                                if self.show_label_text_calculated == True and label_text in calculate_text_list:
                                    label_text = ""
                                if label_text in calculate_text_list:
                                    self.show_label_text_calculated = True
                                    self.show_label_text_pointed = False

                                show_label_text = self.show_label.get_text()
                                if show_label_text == "0" and label_text != "." and (label_text not in calculate_text_list or label_text == "-"):
                                    show_label_text = ""

                                if label_text == ".":
                                    if show_label_text == "":
                                        show_label_text = "0"
                                    elif show_label_text[-1] in calculate_text_list:
                                        show_label_text = show_label_text + "0"

                                if label_text in calculate_text_list:
                                    if show_label_text == "":
                                        if label_text == "-":
                                            show_label_text = ""
                                            self.show_label_text_calculated = False
                                        else:
                                            show_label_text = "0"
                                    elif show_label_text == "-":
                                        show_label_text = ""
                                        self.show_label_text_calculated = False
                                    elif show_label_text[-1] == ".":
                                        show_label_text = show_label_text[:-1]

                                show_label_text = show_label_text + label_text

                                self.show_label.set_text(show_label_text)

                    def btn_handle_opa_anim_cb(self, btn_handle, opa):
                        btn_handle.set_style_bg_opa(opa, 0)

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)
                    self.conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.status_bar.dark_mode()

                    self.lv_font_app_calculator_show_main = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_calculator_show_main_size60_bpp4.bin")
                    self.lv_font_app_calculator_show_history = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_calculator_show_history_size30_bpp4.bin")

                    self.show_conv = lv.obj(self.conv)
                    self.show_conv.set_size(lv.pct(95), lv.pct(25))
                    self.show_conv.align(lv.ALIGN.TOP_MID, 0, 40)
                    self.show_conv.set_style_pad_all(0, 0)
                    self.show_conv.set_style_border_width(0, 0)
                    self.show_conv.set_style_radius(0, 0)
                    self.show_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.show_conv.set_style_bg_opa(0, 0)
                    self.show_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.show_label = lv.label(self.show_conv)
                    self.show_label.set_style_text_font(self.lv_font_app_calculator_show_main, 0)
                    self.show_label.set_text("0")
                    self.show_label.align(lv.ALIGN.BOTTOM_RIGHT, -10, -10)
                    self.show_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                    self.history_label = lv.label(self.show_conv)
                    self.history_label.set_style_text_font(self.lv_font_app_calculator_show_history, 0)
                    self.history_label.set_text("")
                    self.history_label.align(lv.ALIGN.BOTTOM_RIGHT, -10, -80)
                    self.history_label.set_style_text_color(lv.color_hex(0x7F7F7F), 0)

                    self.keyboard_conv = lv.obj(self.conv)
                    self.keyboard_conv.set_size(lv.pct(95), lv.pct(60))
                    self.keyboard_conv.align_to(self.show_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                    self.keyboard_conv.set_style_pad_all(0, 0)
                    self.keyboard_conv.set_style_border_width(0, 0)
                    self.keyboard_conv.set_style_radius(0, 0)
                    self.keyboard_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.keyboard_conv.set_style_bg_opa(0, 0)
                    self.keyboard_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
                    self.keyboard_conv.set_style_grid_column_dsc_array([lv.grid_fr(1), lv.grid_fr(1), lv.grid_fr(1), lv.grid_fr(1), lv.grid_fr(1), lv.GRID_TEMPLATE_LAST], 0)
                    self.keyboard_conv.set_style_grid_row_dsc_array([lv.grid_fr(1), lv.grid_fr(1), lv.grid_fr(1), lv.grid_fr(1), lv.GRID_TEMPLATE_LAST], 0)
                    self.keyboard_conv.set_layout(lv.LAYOUT_GRID.value)
                    self.keyboard_conv.set_style_pad_column(10, 0)
                    self.keyboard_conv.set_style_pad_row(10, 0)

                    self.keyboard = self.Keyboard(self.keyboard_conv, self.show_conv)

                    self.set_home_bar_color(lv.color_hex(0xFFFFFF))
                    self.set_home_bar_top()

            class AppPhotos(AppBase):
#                class PhotoList():
#                    def __init__(self, conv):
#                        self.is_full_screen = False

#                        self.list_conv = lv.obj(conv)
#                        self.list_conv.set_size(lv.pct(30), lv.pct(85))
#                        self.list_conv.align(lv.ALIGN.LEFT_MID, 20, 0)
#                        self.list_conv.set_style_pad_all(0, 0)
#                        self.list_conv.set_style_border_width(0, 0)
#                        self.list_conv.set_style_radius(20, 0)
#                        self.list_conv.set_style_clip_corner(True, 0)
#                        self.list_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
#                        self.list_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

#                        self.slot_conv = lv.obj(self.list_conv)
#                        self.slot_conv.set_size(176, 392)
#                        self.slot_conv.center()
#                        self.slot_conv.set_style_pad_all(0, 0)
#                        self.slot_conv.set_style_border_width(0, 0)
#                        self.slot_conv.set_style_radius(20, 0)
#                        self.slot_conv.set_style_clip_corner(True, 0)
#                        self.slot_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
#                        self.slot_conv.set_style_bg_opa(0, 0)
#                        self.slot_conv.add_flag(lv.obj.FLAG.SCROLLABLE)
#                        self.slot_conv.set_scroll_dir(lv.DIR.VER)
#                        self.slot_conv.set_scroll_snap_y(lv.SCROLL_SNAP.NONE)
#                        self.slot_conv.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

#                        self.list_conv_x_anim = lv.anim_t()
#                        self.list_conv_x_anim.init()
#                        self.list_conv_x_anim.set_var(self.list_conv)
#                        self.list_conv_x_anim.set_time(300)
#                        self.list_conv_x_anim.set_repeat_count(1)
#                        self.list_conv_x_anim.set_path_cb(lv.anim_t.path_ease_in_out)
#                        self.list_conv_x_anim.set_custom_exec_cb(lambda anim, val: self.list_conv_x_anim_cb(self.list_conv, val))

#                        self.img_slot_list = []

#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")
#                        self.add("/data/photos/pexels-stywo-1054218.png")

#                    def add(self, img_path):
#                        slot = lv.obj(self.slot_conv)
#                        slot.set_size(lv.pct(100), 132)
#                        if len(self.img_slot_list) == 0:
#                            slot.align(lv.ALIGN.TOP_MID, 0, 0)
#                        else:
#                            slot_prev = self.img_slot_list[-1]
#                            slot.align_to(slot_prev, lv.ALIGN.OUT_BOTTOM_MID, 0, 8)
#                        slot.set_style_pad_all(0, 0)
#                        slot.set_style_border_width(0, 0)
#                        slot.set_style_radius(20, 0)
#                        slot.set_style_clip_corner(True, 0)
#                        slot.set_style_bg_color(lv.color_hex(0x000000), 0)
#                        slot.set_style_bg_opa(50, 0)
#                        slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

#                        with open(img_path, 'rb') as f:
#                            img_data = f.read()
#                        img_dsc = lv.img_dsc_t({
#                            'data_size': len(img_data),
#                            'data': img_data
#                        })
#                        img = lv.img(slot)
#                        img.set_src(img_dsc)
#                        img.center()
#                        img.set_zoom(70)

#                        self.img_slot_list.append(slot)

#                    def list_conv_x_anim_cb(self, list_conv, x):
#                        list_conv.set_x(x)

#                    def enter_full_screen(self):
#                        if self.is_full_screen == False:
#                            self.is_full_screen = True
#                            self.list_conv_x_anim.set_values(20, -192)
#                            lv.anim_t.start(self.list_conv_x_anim)

#                    def exit_full_screen(self):
#                        if self.is_full_screen == True:
#                            self.is_full_screen = False
#                            self.list_conv_x_anim.set_values(-192, 20)
#                            lv.anim_t.start(self.list_conv_x_anim)

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)
                    self.conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.status_bar.dark_mode()

                    self.photos_path = RESOURCES_PATH + "Photos/"

                    self.photos_files = [
                        item for item in os.listdir(self.photos_path)
                        if not os.stat(self.photos_path + item)[0] & 0x4000 and item.endswith(".png")
                    ]
                    self.photo_show_index = 0

                    self.img_conv = lv.obj(self.conv)
                    self.img_conv.set_size(lv.pct(100), lv.pct(100))
                    self.img_conv.center()
                    self.img_conv.set_style_pad_all(0, 0)
                    self.img_conv.set_style_border_width(0, 0)
                    self.img_conv.set_style_radius(0, 0)
                    self.img_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.img_conv.set_style_bg_opa(0, 0)
                    self.img_conv.add_flag(lv.obj.FLAG.SCROLLABLE)
                    self.img_conv.add_flag(lv.obj.FLAG.SCROLL_ONE)
                    self.img_conv.set_scroll_dir(lv.DIR.VER)
                    self.img_conv.set_scroll_snap_y(lv.SCROLL_SNAP.CENTER)
                    self.img_conv.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)
                    self.img_conv.add_event(self.img_conv_event_cb, lv.EVENT.SCROLL_END, None)
                    self.is_img_conv_scroll_auto = True

#                    self.img_conv_color_anim = lv.anim_t()
#                    self.img_conv_color_anim.init()
#                    self.img_conv_color_anim.set_var(self.img_conv)
#                    self.img_conv_color_anim.set_time(300)
#                    self.img_conv_color_anim.set_repeat_count(1)
#                    self.img_conv_color_anim.set_path_cb(lv.anim_t.path_ease_in_out)
#                    self.img_conv_color_anim.set_custom_exec_cb(lambda anim, val: self.img_conv_color_anim_cb(self.img_conv, val))

                    self.img_show_conv_list = []
                    self.img_show_conv_pressing_point = lv.point_t()

                    for i in range(3):
                        img_show_conv = lv.obj(self.img_conv)
                        img_show_conv.set_size(lv.pct(100), lv.pct(100))
                        img_show_conv.set_style_pad_all(0, 0)
                        img_show_conv.set_style_border_width(0, 0)
                        img_show_conv.set_style_radius(0, 0)
                        img_show_conv.set_style_bg_opa(0, 0)
                        img_show_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        img_show_conv.add_flag(lv.obj.FLAG.CLICKABLE)
                        img_show_conv.add_event(self.img_show_conv_event_cb, lv.EVENT.PRESSED, None)
                        img_show_conv.add_event(self.img_show_conv_event_cb, lv.EVENT.RELEASED, None)

                        if i == 0:
                            img_show_conv.center()
                            img_show_conv.set_style_bg_color(lv.color_hex(0xFF0000), 0)
                        elif i == 1:
                            img_show_conv.align_to(self.img_show_conv_list[0], lv.ALIGN.OUT_TOP_MID, 0, 0)
                            img_show_conv.set_style_bg_color(lv.color_hex(0x00FF00), 0)
                        elif i == 2:
                            img_show_conv.align_to(self.img_show_conv_list[0], lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                            img_show_conv.set_style_bg_color(lv.color_hex(0x0000FF), 0)

                        img = lv.img(img_show_conv)
                        img.align(lv.ALIGN.CENTER, -1, -1)

                        self.img_show_conv_list.append(img_show_conv)

                    self.show_img(0)

#                    self.photo_list = self.PhotoList(self.conv)

                    self.set_home_bar_color(lv.color_hex(0xFFFFFF))
                    self.set_home_bar_top()

                def show_img(self, index_inc):
                    self.photo_show_index = self.photo_show_index + index_inc

                    if index_inc == 0:
                        with open(self.photos_path + self.photos_files[self.photo_show_index], 'rb') as f:
                            img_data = f.read()
                        img_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })
                        self.img_show_conv_list[0].get_child(0).set_src(img_dsc)

                    if (index_inc == 0 or index_inc == -1) and self.photo_show_index != 0:
                        with open(self.photos_path + self.photos_files[self.photo_show_index - 1], 'rb') as f:
                            img_data = f.read()
                        img_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })
                        self.img_show_conv_list[1].get_child(0).set_src(img_dsc)

                    if (index_inc == 0 or index_inc == 1) and self.photo_show_index != len(self.photos_files) - 1:
                        with open(self.photos_path + self.photos_files[self.photo_show_index + 1], 'rb') as f:
                            img_data = f.read()
                        img_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })
                        self.img_show_conv_list[2].get_child(0).set_src(img_dsc)

                    if self.photo_show_index == 0:
                        self.img_conv.set_scroll_dir(lv.DIR.BOTTOM)
                    elif self.photo_show_index == len(self.photos_files) - 1:
                        self.img_conv.set_scroll_dir(lv.DIR.TOP)
                    else:
                        self.img_conv.set_scroll_dir(lv.DIR.VER)

#                def img_conv_color_anim_cb(self, img_conv, color):
#                    img_conv.set_style_bg_color(lv.color_hex((color << 0) | (color << 8) | (color << 16)), 0)

                def img_conv_event_cb(self, event):
                    code = event.get_code()
                    img_conv = lv.obj.__cast__(event.get_target())

                    if code == lv.EVENT.SCROLL_END:
                        if self.is_img_conv_scroll_auto == True:
                            self.is_img_conv_scroll_auto = False
                        elif self.is_img_conv_scroll_auto == False:
                            self.is_img_conv_scroll_auto = True
                            if img_conv.get_scroll_y() != 0:
                                if img_conv.get_scroll_y() > 0:
                                    self.img_show_conv_list[0], self.img_show_conv_list[1], self.img_show_conv_list[2] = self.img_show_conv_list[2], self.img_show_conv_list[0], self.img_show_conv_list[1]
                                    photo_show_index_inc = 1
                                if img_conv.get_scroll_y() < 0:
                                    self.img_show_conv_list[0], self.img_show_conv_list[1], self.img_show_conv_list[2] = self.img_show_conv_list[1], self.img_show_conv_list[2], self.img_show_conv_list[0]
                                    photo_show_index_inc = -1
                                self.img_show_conv_list[0].center()
                                self.img_show_conv_list[1].align_to(self.img_show_conv_list[0], lv.ALIGN.OUT_TOP_MID, 0, 0)
                                self.img_show_conv_list[2].align_to(self.img_show_conv_list[0], lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                                self.show_img(photo_show_index_inc)
                                self.is_img_conv_scroll_auto = False
                                img_conv.scroll_to_y(0, 0)

                def img_show_conv_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.PRESSED:
                        indev = lv.indev_get_act()
                        indev.get_point(self.img_show_conv_pressing_point)
                    elif code == lv.EVENT.RELEASED:
                        released_point = lv.point_t()
                        indev = lv.indev_get_act()
                        indev.get_point(released_point)
                        if released_point.x == self.img_show_conv_pressing_point.x and released_point.y == self.img_show_conv_pressing_point.y:
                            if self.is_full_screen == False:
                                self.enter_full_screen()
#                                self.photo_list.enter_full_screen()
#                                self.img_conv_color_anim.set_values(255, 0)
#                                lv.anim_t.start(self.img_conv_color_anim)
                            else:
                                self.exit_full_screen()
#                                self.photo_list.exit_full_screen()
#                                self.img_conv_color_anim.set_values(0, 255)
#                                lv.anim_t.start(self.img_conv_color_anim)

            class AppSettings(AppBase):
                class SideBar():
                    class Profile():
                        def __init__(self, conv):
                            self.lv_font_username_bold_size30 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_username_bold_size30_bpp4.bin")
                            self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                            with open(RESOURCES_PATH + "APP/Settings/settings_icon_72x72_profile.png", 'rb') as f:
                                icon_data = f.read()
                            icon_dsc = lv.img_dsc_t({
                                'data_size': len(icon_data),
                                'data': icon_data
                            })
                            self.icon = lv.img(conv)
                            self.icon.set_src(icon_dsc)
                            self.icon.align(lv.ALIGN.LEFT_MID, 10, 0)

                            self.label = lv.label(conv)
                            self.label.set_style_text_font(self.lv_font_username_bold_size30, 0)
                            self.label.set_text("正点原子")
                            self.label.align_to(self.icon, lv.ALIGN.OUT_RIGHT_MID, 20, -12)
                            self.label.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.commit = lv.label(conv)
                            self.commit.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.commit.set_text("ALIENTEK")
                            self.commit.align_to(self.label, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 8)
                            self.commit.set_style_text_color(lv.color_hex(0x7F7F7F), 0)

                    class System():
                        def __init__(self, conv, item_conv, hw_resources, timer_list):
                            self.item_conv = item_conv
                            self.hw_resources = hw_resources
                            self.timer_list = timer_list

                            self.lv_font_normal_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size25_bpp4.bin")
                            self.lv_font_normal_bold_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_bold_size25_bpp4.bin")

                            with open(RESOURCES_PATH + "APP/Settings/settings_icon_44x44_date_and_time.png", 'rb') as f:
                                icon_data = f.read()
                            icon_dsc = lv.img_dsc_t({
                                'data_size': len(icon_data),
                                'data': icon_data
                            })
                            self.icon = lv.img(conv)
                            self.icon.set_src(icon_dsc)
                            self.icon.align(lv.ALIGN.LEFT_MID, 10, 0)
                            self.icon.set_style_radius(12, 0)
                            self.icon.set_style_clip_corner(True, 0)

                            self.label = lv.label(conv)
                            self.label.set_style_text_font(self.lv_font_normal_size25, 0)
                            self.label.set_text("Date & Time")
                            self.label.align_to(self.icon, lv.ALIGN.OUT_RIGHT_MID, 12, 0)
                            self.label.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.handle = lv.obj(conv)
                            self.handle.set_size(lv.pct(100), lv.pct(100))
                            self.handle.center()
                            self.handle.set_style_pad_all(0, 0)
                            self.handle.set_style_border_width(0, 0)
                            self.handle.set_style_radius(0, 0)
                            self.handle.set_style_bg_color(lv.color_hex(0x000000), 0)
                            self.handle.set_style_bg_opa(0, 0)
                            self.handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                            self.handle.add_flag(lv.obj.FLAG.CLICKABLE)
                            self.handle.add_event(self.handle_event_cb, lv.EVENT.CLICKED, None)

                        def handle_event_cb(self, event):
                            code = event.get_code()
                            handle = lv.obj.__cast__(event.get_target())

                            if code == lv.EVENT.CLICKED:
                                handle.set_style_bg_opa(50, 0)
                                self.load_item_conv()

                        def load_item_conv(self):
                            self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")
                            self.lv_font_normal_bold_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_bold_size25_bpp4.bin")

                            self.item_conv.clean()

                            self.is_in_setting = False

                            date_conv = lv.obj(self.item_conv)
                            date_conv.set_size(lv.pct(90), 200)
                            date_conv.align(lv.ALIGN.TOP_MID, 0, 40)
                            date_conv.set_style_pad_all(0, 0)
                            date_conv.set_style_border_width(0, 0)
                            date_conv.set_style_radius(12, 0)
                            date_conv.set_style_clip_corner(True, 0)
                            date_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                            date_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                            date_title = lv.label(date_conv)
                            date_title.set_style_text_font(self.lv_font_normal_bold_size25, 0)
                            date_title.set_text("Date Settings")
                            date_title.align(lv.ALIGN.TOP_LEFT, 10, 10)
                            date_title.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.year_roller = lv.roller(date_conv)
                            self.year_roller.set_options("\n".join(str(year) for year in range(2010, 2039 + 1)), lv.roller.MODE.NORMAL)
                            self.year_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.year_roller.set_width((92))
                            self.year_roller.set_visible_row_count(3)
                            self.year_roller.align(lv.ALIGN.BOTTOM_LEFT, 10, -10)
                            self.year_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.year_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            self.month_roller = lv.roller(date_conv)
                            self.month_roller.set_options("\n".join(str(month) for month in range(1, 12 + 1)), lv.roller.MODE.NORMAL)
                            self.month_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.month_roller.set_width((92))
                            self.month_roller.set_visible_row_count(3)
                            self.month_roller.align_to(self.year_roller, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
                            self.month_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.month_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            self.day_roller = lv.roller(date_conv)
                            self.day_roller.set_options("\n".join(str(day) for day in range(1, 31 + 1)), lv.roller.MODE.NORMAL)
                            self.day_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.day_roller.set_width((92))
                            self.day_roller.set_visible_row_count(3)
                            self.day_roller.align_to(self.month_roller, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
                            self.day_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.day_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            year_label = lv.label(date_conv)
                            year_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            year_label.set_text("Year")
                            year_label.align_to(self.year_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            year_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            month_label = lv.label(date_conv)
                            month_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            month_label.set_text("Month")
                            month_label.align_to(self.month_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            month_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            day_label = lv.label(date_conv)
                            day_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            day_label.set_text("Date")
                            day_label.align_to(self.day_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            day_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            time_conv = lv.obj(self.item_conv)
                            time_conv.set_size(lv.pct(90), 200)
                            time_conv.align_to(date_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
                            time_conv.set_style_pad_all(0, 0)
                            time_conv.set_style_border_width(0, 0)
                            time_conv.set_style_radius(12, 0)
                            time_conv.set_style_clip_corner(True, 0)
                            time_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                            time_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                            time_title = lv.label(time_conv)
                            time_title.set_style_text_font(self.lv_font_normal_bold_size25, 0)
                            time_title.set_text("Time Settings")
                            time_title.align(lv.ALIGN.TOP_LEFT, 10, 10)
                            time_title.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.hour_roller = lv.roller(time_conv)
                            self.hour_roller.set_options("\n".join(str(hour) for hour in range(0, 23 + 1)), lv.roller.MODE.NORMAL)
                            self.hour_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.hour_roller.set_width(92)
                            self.hour_roller.set_visible_row_count(3)
                            self.hour_roller.align(lv.ALIGN.BOTTOM_LEFT, 10, -10)
                            self.hour_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.hour_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            self.minute_roller = lv.roller(time_conv)
                            self.minute_roller.set_options("\n".join(str(minute) for minute in range(0, 59 + 1)), lv.roller.MODE.NORMAL)
                            self.minute_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.minute_roller.set_width(92)
                            self.minute_roller.set_visible_row_count(3)
                            self.minute_roller.align_to(self.hour_roller, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
                            self.minute_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.minute_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            self.second_roller = lv.roller(time_conv)
                            self.second_roller.set_options("\n".join(str(second) for second in range(0, 59 + 1)), lv.roller.MODE.NORMAL)
                            self.second_roller.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.second_roller.set_width(92)
                            self.second_roller.set_visible_row_count(3)
                            self.second_roller.align_to(self.minute_roller, lv.ALIGN.OUT_RIGHT_MID, 10, 0)
                            self.second_roller.add_event(self.roller_event_cb, lv.EVENT.VALUE_CHANGED, None)
                            self.second_roller.add_event(self.roller_event_cb, lv.EVENT.PRESSING, None)

                            hour_label = lv.label(time_conv)
                            hour_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            hour_label.set_text("Hour")
                            hour_label.align_to(self.hour_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            hour_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            minute_label = lv.label(time_conv)
                            minute_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            minute_label.set_text("Minute")
                            minute_label.align_to(self.minute_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            minute_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            second_label = lv.label(time_conv)
                            second_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            second_label.set_text("Second")
                            second_label.align_to(self.second_roller, lv.ALIGN.OUT_TOP_MID, 0, 0)
                            second_label.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.update_item_conv()

                            self.time_updater = lv.timer_create(self.time_updater_cb, 1000, None)
                            self.timer_list.append(self.time_updater)

                        def roller_event_cb(self, event):
                            code = event.get_code()

                            if code == lv.EVENT.VALUE_CHANGED:
                                year = self.year_roller.get_selected() + 2010
                                month = self.month_roller.get_selected() + 1
                                day = self.day_roller.get_selected() + 1
                                hour = self.hour_roller.get_selected() + 0
                                minute = self.minute_roller.get_selected() + 0
                                second = self.second_roller.get_selected() + 0
                                clock_manager = self.hw_resources.get("ClockManager")
                                clock_manager.set_time(year, month, day, hour, minute, second, 0)
                                self.is_in_setting = False
                            elif code == lv.EVENT.PRESSING:
                                self.is_in_setting = True

                        def update_item_conv(self):
                            if self.is_in_setting == False:
                                clock_manager = self.hw_resources.get("ClockManager")
                                time = clock_manager.get_time()
                                self.year_roller.set_selected(time[0] - 2010, lv.ANIM.ON)
                                self.month_roller.set_selected(time[1] - 1, lv.ANIM.ON)
                                self.day_roller.set_selected(time[2] - 1, lv.ANIM.ON)
                                self.hour_roller.set_selected(time[4] - 0, lv.ANIM.ON)
                                self.minute_roller.set_selected(time[5] - 0, lv.ANIM.ON)
                                self.second_roller.set_selected(time[6] - 0, lv.ANIM.ON)

                        def time_updater_cb(self, timer):
                            self.update_item_conv()

                    def __init__(self, conv, item_conv, hw_resources, timer_list):
                        self.lv_font_normal_bold_size40 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_bold_size40_bpp4.bin")

                        self.title = lv.label(conv)
                        self.title.set_style_text_font(self.lv_font_normal_bold_size40, 0)
                        self.title.align(lv.ALIGN.TOP_LEFT, 20, 50)
                        self.title.set_text("Settings")
                        self.title.set_style_text_color(lv.color_hex(0x000000), 0)

                        self.scroll_conv = lv.obj(conv)
                        self.scroll_conv.set_size(lv.pct(90), 380)
                        self.scroll_conv.align(lv.ALIGN.TOP_MID, 0, 100)
                        self.scroll_conv.set_style_pad_all(0, 0)
                        self.scroll_conv.set_style_border_width(0, 0)
                        self.scroll_conv.set_style_radius(0, 0)
                        self.scroll_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.scroll_conv.set_style_bg_opa(0, 0)
                        self.scroll_conv.add_flag(lv.obj.FLAG.SCROLLABLE)
                        self.scroll_conv.set_scroll_dir(lv.DIR.VER)
                        self.scroll_conv.set_scroll_snap_y(lv.SCROLL_SNAP.NONE)
                        self.scroll_conv.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

                        self.profile_conv = lv.obj(self.scroll_conv)
                        self.profile_conv.set_size(lv.pct(100), 92)
                        self.profile_conv.align(lv.ALIGN.TOP_MID, 0, 0)
                        self.profile_conv.set_style_pad_all(0, 0)
                        self.profile_conv.set_style_border_width(0, 0)
                        self.profile_conv.set_style_radius(12, 0)
                        self.profile_conv.set_style_clip_corner(True, 0)
                        self.profile_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.profile_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.system_conv = lv.obj(self.scroll_conv)
                        self.system_conv.set_size(lv.pct(100), 1 * 64)
                        self.system_conv.align_to(self.profile_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
                        self.system_conv.set_style_pad_all(0, 0)
                        self.system_conv.set_style_border_width(0, 0)
                        self.system_conv.set_style_radius(12, 0)
                        self.system_conv.set_style_clip_corner(True, 0)
                        self.system_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.system_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.holder = lv.obj(self.scroll_conv)
                        self.holder.set_size(lv.pct(100), 30)
                        self.holder.align_to(self.system_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                        self.holder.set_style_pad_all(0, 0)
                        self.holder.set_style_border_width(0, 0)
                        self.holder.set_style_bg_opa(0, 0)
                        self.holder.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.profile = self.Profile(self.profile_conv)
                        self.system = self.System(self.system_conv, item_conv, hw_resources, timer_list)

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)
                    self.conv.set_style_bg_color(lv.color_hex(0xF3F2F7), 0)

                    self.side_bar_conv = lv.obj(self.conv)
                    self.side_bar_conv.set_size(lv.pct(44), lv.pct(100))
                    self.side_bar_conv.align(lv.ALIGN.LEFT_MID, 0, 0)
                    self.side_bar_conv.set_style_pad_all(0, 0)
                    self.side_bar_conv.set_style_border_width(0, 0)
                    self.side_bar_conv.set_style_radius(0, 0)
                    self.side_bar_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.side_bar_conv.set_style_bg_opa(0, 0)
                    self.side_bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.split_line = lv.obj(self.conv)
                    self.split_line.set_size(2, lv.pct(100))
                    self.split_line.align_to(self.side_bar_conv, lv.ALIGN.OUT_RIGHT_MID, 0, 0)
                    self.split_line.set_style_pad_all(0, 0)
                    self.split_line.set_style_border_width(0, 0)
                    self.split_line.set_style_radius(0, 0)
                    self.split_line.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.split_line.set_style_bg_opa(50, 0)
                    self.split_line.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.item_conv = lv.obj(self.conv)
                    self.item_conv.set_size(lv.pct(55), lv.pct(100))
                    self.item_conv.align(lv.ALIGN.RIGHT_MID, 0, 0)
                    self.item_conv.set_style_pad_all(0, 0)
                    self.item_conv.set_style_border_width(0, 0)
                    self.item_conv.set_style_radius(0, 0)
                    self.item_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.item_conv.set_style_bg_opa(0, 0)
                    self.item_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.side_bar = self.SideBar(self.side_bar_conv, self.item_conv, self.hw_resources, self.timer_list)

                    self.set_home_bar_color(lv.color_hex(0x000000))
                    self.set_home_bar_top()

            class AppClock(AppBase):
                class TopBar():
                    class LocalClock():
                        class DialHand():
                            def __init__(self, conv):
                                self.dial_center = lv.obj(conv)
                                self.dial_center.set_size(12, 12)
                                self.dial_center.align(lv.ALIGN.CENTER, 0, 0)
                                self.dial_center.set_style_pad_all(0, 0)
                                self.dial_center.set_style_border_width(0, 0)
                                self.dial_center.set_style_radius(6, 0)
                                self.dial_center.set_style_bg_color(lv.color_hex(0x000000), 0)
                                self.dial_center.clear_flag(lv.obj.FLAG.SCROLLABLE)

                                self.center_x = conv.get_width() // 2
                                self.center_y = conv.get_height() // 2

                                self.hour_length = 20

                                self.hour_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.hour = lv.line(conv)
                                self.hour.set_style_line_width(4, 0)
                                self.hour.set_style_line_color(lv.color_hex(0x000000), 0)

                                self.hour_main_offset = 12
                                self.hour_main_length = 60
                                self.hour_main_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.hour_main = lv.line(conv)
                                self.hour_main.set_style_line_width(8, 0)
                                self.hour_main.set_style_line_color(lv.color_hex(0x000000), 0)

                                self.minute_length = 50
                                self.minute_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.minute = lv.line(conv)
                                self.minute.set_style_line_width(4, 0)
                                self.minute.set_style_line_color(lv.color_hex(0x000000), 0)

                                self.minute_main_offset = 16
                                self.minute_main_length = 100
                                self.minute_main_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.minute_main = lv.line(conv)
                                self.minute_main.set_style_line_width(8, 0)
                                self.minute_main.set_style_line_color(lv.color_hex(0x000000), 0)

                                self.second_center = lv.obj(conv)
                                self.second_center.set_size(8, 8)
                                self.second_center.align(lv.ALIGN.CENTER, 0, 0)
                                self.second_center.set_style_pad_all(0, 0)
                                self.second_center.set_style_border_width(0, 0)
                                self.second_center.set_style_radius(3, 0)
                                self.second_center.set_style_bg_color(lv.color_hex(0xEF8732), 0)
                                self.second_center.clear_flag(lv.obj.FLAG.SCROLLABLE)

                                self.second_length = 16
                                self.second_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.second = lv.line(conv)
                                self.second.set_style_line_width(4, 0)
                                self.second.set_style_line_color(lv.color_hex(0xEF8732), 0)

                                self.second_main_length = 110
                                self.second_main_points = [lv.point_t({'x': self.center_x, 'y': self.center_y}), lv.point_t({'x': self.center_x, 'y': self.center_y})]

                                self.second_main = lv.line(conv)
                                self.second_main.set_style_line_width(4, 0)
                                self.second_main.set_style_line_color(lv.color_hex(0xEF8732), 0)

                            def set(self, hour_angle, minute_angle, second_angle):
                                hour_angle = 360 - (hour_angle - 90)
                                minute_angle = 360 - (minute_angle - 90)
                                second_angle = 360 - (second_angle - 90)

                                cos_factor = math.cos(math.radians(hour_angle))
                                sin_factor = math.sin(math.radians(hour_angle))

                                line_x_end = int(self.center_x + self.hour_length * cos_factor)
                                line_y_end = int(self.center_y - self.hour_length * sin_factor)

                                self.hour_points[1].x = line_x_end
                                self.hour_points[1].y = line_y_end
                                self.hour.set_points(self.hour_points, 2)

                                line_main_x_start = int(self.center_x + self.hour_main_offset * cos_factor)
                                line_main_y_start = int(self.center_y - self.hour_main_offset * sin_factor)
                                line_main_x_end = int(self.center_x + self.hour_main_length * cos_factor)
                                line_main_y_end = int(self.center_y - self.hour_main_length * sin_factor)

                                self.hour_main_points[0].x = line_main_x_start
                                self.hour_main_points[0].y = line_main_y_start
                                self.hour_main_points[1].x = line_main_x_end
                                self.hour_main_points[1].y = line_main_y_end
                                self.hour_main.set_points(self.hour_main_points, 2)

                                cos_factor = math.cos(math.radians(minute_angle))
                                sin_factor = math.sin(math.radians(minute_angle))

                                line_x_end = int(self.center_x + self.minute_length * cos_factor)
                                line_y_end = int(self.center_y - self.minute_length * sin_factor)

                                self.minute_points[1].x = line_x_end
                                self.minute_points[1].y = line_y_end
                                self.minute.set_points(self.minute_points, 2)

                                line_main_x_start = int(self.center_x + self.minute_main_offset * cos_factor)
                                line_main_y_start = int(self.center_y - self.minute_main_offset * sin_factor)
                                line_main_x_end = int(self.center_x + self.minute_main_length * cos_factor)
                                line_main_y_end = int(self.center_y - self.minute_main_length * sin_factor)

                                self.minute_main_points[0].x = line_main_x_start
                                self.minute_main_points[0].y = line_main_y_start
                                self.minute_main_points[1].x = line_main_x_end
                                self.minute_main_points[1].y = line_main_y_end
                                self.minute_main.set_points(self.minute_main_points, 2)

                                cos_factor = math.cos(math.radians(second_angle))
                                sin_factor = math.sin(math.radians(second_angle))

                                line_x_end = int(self.center_x - self.second_length * cos_factor)
                                line_y_end = int(self.center_y + self.second_length * sin_factor)

                                self.second_points[1].x = line_x_end
                                self.second_points[1].y = line_y_end
                                self.second.set_points(self.second_points, 2)

                                line_main_x_end = int(self.center_x + self.second_main_length * cos_factor)
                                line_main_y_end = int(self.center_y - self.second_main_length * sin_factor)

                                self.second_main_points[1].x = line_main_x_end
                                self.second_main_points[1].y = line_main_y_end
                                self.second_main.set_points(self.second_main_points, 2)

                        def __init__(self, show_conv, app_timer, hw_resources):
                            self.show_conv = show_conv
                            self.app_timer = app_timer
                            self.clock_manager = hw_resources.get("ClockManager")

                        def show(self):
                            self.app_timer.pause()
                            self.show_conv.clean()

                            self.app_timer.set_cb(self.app_timer_cb)
                            self.app_timer.set_period(1000)
                            self.app_timer.resume()

                            self.lv_font_app_clock_time_size80 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_clock_time_size80_bpp4.bin")
                            self.lv_font_normal_size28 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size28_bpp4.bin")

                            self.clock_dial = lv.obj(self.show_conv)
                            self.clock_dial.set_size(240, 240)
                            self.clock_dial.align(lv.ALIGN.CENTER, 0, -40)
                            self.clock_dial.set_style_pad_all(0, 0)
                            self.clock_dial.set_style_border_width(0, 0)
                            self.clock_dial.set_style_radius(120, 0)
                            self.clock_dial.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                            self.clock_dial.clear_flag(lv.obj.FLAG.SCROLLABLE)

                            self.time_label = lv.label(self.show_conv)
                            self.time_label.set_style_text_font(self.lv_font_app_clock_time_size80, 0)
                            self.time_label.set_text("00:00:00")
                            self.time_label.align_to(self.clock_dial, lv.ALIGN.OUT_BOTTOM_MID, 0, 20)
                            self.time_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                            center_x = 120
                            center_y = 120
                            radius = 95

                            for i in range(1, 13):
                                angle = i * 30
                                x = int(center_x + radius * math.sin(math.radians(angle)))
                                y = int(center_y - radius * math.cos(math.radians(angle)))

                                label = lv.label(self.clock_dial)
                                label.set_style_text_font(self.lv_font_normal_size28, 0)
                                label.set_text(str(i))
                                label.align(lv.ALIGN.CENTER, x - center_x, y - center_y)
                                label.set_style_text_color(lv.color_hex(0x000000), 0)

                            self.dial_hand = self.DialHand(self.clock_dial)

                            self.update()

                        def update(self):
                            time = self.clock_manager.get_time()
                            self.time_label.set_text(f"{time[4]:02d}" + ":" + f"{time[5]:02d}" + ":" + f"{time[6]:02d}")

                            if time[4] > 12:
                                self.dial_hand.set((time[4] - 12) / 12 * 360 + time[5] / 60 * 30 + time[6] / 60 * (360 / 43200), time[5] / 60 * 360 + time[6] / 60 * 6, time[6] / 60 * 360)
                            else:
                                self.dial_hand.set(time[4] / 12 * 360 + time[5] / 60 * 30 + time[6] / 60 * (360 / 43200), time[5] / 60 * 360 + time[6] / 60 * 6, time[6] / 60 * 360)

                        def app_timer_cb(self, timer):
                            self.update()

                    class Stopwatch():
                        def __init__(self, show_conv, app_timer, hw_resources):
                            self.show_conv = show_conv
                            self.app_timer = app_timer
                            self.time_minute = 0
                            self.time_second = 0
                            self.time_microsecond = 0
                            self.hw_resources = hw_resources

                        def show(self):
                            self.app_timer.pause()
                            self.show_conv.clean()

                            self.app_timer.set_cb(self.app_timer_cb)
                            self.app_timer.set_period(100)

                            self.lv_font_app_clock_time_size80 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_app_clock_time_size80_bpp4.bin")
                            self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                            self.time_label = lv.label(self.show_conv)
                            self.time_label.set_style_text_font(self.lv_font_app_clock_time_size80, 0)
                            self.time_label.set_text("00:00.0")
                            self.time_label.align(lv.ALIGN.TOP_MID, 0, 80)
                            self.time_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                            self.ctrl_conv = lv.obj(self.show_conv)
                            self.ctrl_conv.set_size(100, 100)
                            self.ctrl_conv.align(lv.ALIGN.BOTTOM_MID, 0, -60)
                            self.ctrl_conv.set_style_pad_all(0, 0)
                            self.ctrl_conv.set_style_border_width(0, 0)
                            self.ctrl_conv.set_style_radius(50, 0)
                            self.ctrl_conv.set_style_bg_color(lv.color_hex(0x092911), 0)
                            self.ctrl_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
                            self.ctrl_conv.add_flag(lv.obj.FLAG.CLICKABLE)
                            self.ctrl_conv.add_event(self.ctrl_conv_event_cb, lv.EVENT.CLICKED, None)

                            self.ctrl_label = lv.label(self.ctrl_conv)
                            self.ctrl_label.set_style_text_font(self.lv_font_normal_size20, 0)
                            self.ctrl_label.set_text("Start")
                            self.ctrl_label.center()
                            self.ctrl_label.set_style_text_color(lv.color_hex(0x43B677), 0)

                        def time_label_update(self):
                            self.time_label.set_text(f"{self.time_minute:02d}" + ":" + f"{self.time_second:02d}" + "." + f"{self.time_microsecond:1d}")

                        def app_timer_cb(self, timer):
                            self.time_microsecond = self.time_microsecond + 1
                            if self.time_microsecond == 10:
                                self.time_microsecond = 0
                                self.time_second = self.time_second + 1
                                if self.time_second == 60:
                                    self.time_second = 0
                                    self.time_minute = self.time_minute + 1

                            self.time_label_update()

                        def ctrl_conv_event_cb(self, event):
                            code = event.get_code()

                            if code == lv.EVENT.CLICKED:
                                self.ctrl_label.get_text()

                                if self.ctrl_label.get_text() == "Start":
                                    self.ctrl_conv.set_style_bg_color(lv.color_hex(0x350F0C), 0)
                                    self.ctrl_label.set_text("Stop")
                                    self.ctrl_label.set_style_text_color(lv.color_hex(0xDE465E), 0)

                                    self.time_minute = 0
                                    self.time_second = 0
                                    self.time_microsecond = 0
                                    self.app_timer.resume()
                                elif self.ctrl_label.get_text() == "Stop":
                                    self.ctrl_conv.set_style_bg_color(lv.color_hex(0x333333), 0)
                                    self.ctrl_label.set_text("Reset")
                                    self.ctrl_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                                    self.app_timer.pause()
                                elif self.ctrl_label.get_text() == "Reset":
                                    self.ctrl_conv.set_style_bg_color(lv.color_hex(0x092911), 0)
                                    self.ctrl_label.set_text("Start")
                                    self.ctrl_label.set_style_text_color(lv.color_hex(0x43B677), 0)

                                    self.time_minute = 0
                                    self.time_second = 0
                                    self.time_microsecond = 0
                                    self.time_label_update()

                    def __init__(self, conv, show_conv, app_timer, hw_resources):
                        self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                        self.item_conv_list = []
                        self.current_item_conv = None

                        self.local_clock_conv = lv.obj(conv)
                        self.local_clock_conv.set_size(180, lv.pct(80))
                        self.local_clock_conv.align(lv.ALIGN.LEFT_MID, 6, 0)
                        self.local_clock_conv.set_style_pad_all(0, 0)
                        self.local_clock_conv.set_style_border_width(0, 0)
                        self.local_clock_conv.set_style_radius(30, 0)
                        self.local_clock_conv.set_style_bg_color(lv.color_hex(0x444348), 0)
                        self.local_clock_conv.set_style_bg_opa(255, 0)
                        self.local_clock_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.local_clock_conv.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.local_clock_conv.add_event(self.conv_event_cb, lv.EVENT.CLICKED, None)

                        self.local_clock_label = lv.label(self.local_clock_conv)
                        self.local_clock_label.set_style_text_font(self.lv_font_normal_size20, 0)
                        self.local_clock_label.set_text("Local Clock")
                        self.local_clock_label.center()
                        self.local_clock_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                        self.stopwatch_conv = lv.obj(conv)
                        self.stopwatch_conv.set_size(160, lv.pct(80))
                        self.stopwatch_conv.align_to(self.local_clock_conv, lv.ALIGN.OUT_RIGHT_MID, 0, 0)
                        self.stopwatch_conv.set_style_pad_all(0, 0)
                        self.stopwatch_conv.set_style_border_width(0, 0)
                        self.stopwatch_conv.set_style_radius(30, 0)
                        self.stopwatch_conv.set_style_bg_color(lv.color_hex(0x444348), 0)
                        self.stopwatch_conv.set_style_bg_opa(0, 0)
                        self.stopwatch_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.stopwatch_conv.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.stopwatch_conv.add_event(self.conv_event_cb, lv.EVENT.CLICKED, None)

                        self.stopwatch_label = lv.label(self.stopwatch_conv)
                        self.stopwatch_label.set_style_text_font(self.lv_font_normal_size20, 0)
                        self.stopwatch_label.set_text("Stopwatch")
                        self.stopwatch_label.center()
                        self.stopwatch_label.set_style_text_color(lv.color_hex(0xA6A5AA), 0)

                        self.item_conv_list.append(self.local_clock_conv)
                        self.item_conv_list.append(self.stopwatch_conv)
                        self.current_item_conv = self.local_clock_conv

                        self.local_clock = self.LocalClock(show_conv, app_timer, hw_resources)
                        self.stopwatch = self.Stopwatch(show_conv, app_timer, hw_resources)

                        self.local_clock.show()

                    def conv_event_cb(self, event):
                        code = event.get_code()
                        item_conv = lv.obj.__cast__(event.get_target())
                        item_label = lv.label.__cast__(item_conv.get_child(0))

                        if code == lv.EVENT.CLICKED:
                            if item_conv != self.current_item_conv:
                                self.current_item_conv = item_conv
                                for conv in self.item_conv_list:
                                    label = conv.get_child(0)
                                    conv.set_style_bg_opa(0, 0)
                                    label.set_style_text_color(lv.color_hex(0xA6A5AA), 0)
                                item_conv.set_style_bg_opa(255, 0)
                                item_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)
                                item_label_text = item_label.get_text()
                                if item_label_text == "Local Clock":
                                    self.local_clock.show()
                                elif item_label_text == "Stopwatch":
                                    self.stopwatch.show()

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)
                    self.conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.status_bar.dark_mode()

                    self.app_timer = lv.timer_create(self.app_timer_cb, 1000, None)
                    self.app_timer.pause()
                    self.timer_list.append(self.app_timer)

                    self.top_bar_conv = lv.obj(self.conv)
                    self.top_bar_conv.set_size(352, 60)
                    self.top_bar_conv.align(lv.ALIGN.TOP_MID, 0, 30)
                    self.top_bar_conv.set_style_pad_all(0, 0)
                    self.top_bar_conv.set_style_border_width(0, 0)
                    self.top_bar_conv.set_style_radius(30, 0)
                    self.top_bar_conv.set_style_clip_corner(True, 0)
                    self.top_bar_conv.set_style_bg_color(lv.color_hex(0x28272C), 0)
                    self.top_bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.show_conv = lv.obj(self.conv)
                    self.show_conv.set_size(lv.pct(100), 368)
                    self.show_conv.align_to(self.top_bar_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 0)
                    self.show_conv.set_style_pad_all(0, 0)
                    self.show_conv.set_style_border_width(0, 0)
                    self.show_conv.set_style_radius(0, 0)
                    self.show_conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.show_conv.set_style_bg_opa(0, 0)
                    self.show_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.top_bar = self.TopBar(self.top_bar_conv, self.show_conv, self.app_timer, self.hw_resources)

                    self.set_home_bar_color(lv.color_hex(0xFFFFFF))
                    self.set_home_bar_top()

                def app_timer_cb(self, timer):
                    pass

            class AppFreeform(AppBase):
                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    self.lv_font_normal_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size25_bpp4.bin")

                    super().__init__(icon_area, masker, screen, status_bar, hw_resources)

                    canvas_width, canvas_height = screen.get_width(), screen.get_height()
                    canvas_buffer = bytearray(4 * canvas_width * canvas_height)
                    self.board_previous_point = None
                    self.board_current_point = None
                    self.settings_handle_start_x = None
                    self.is_settings_opened = False
                    self.pen_color = [0xFF, 0x00, 0x00]

                    self.line_dsc = lv.draw_line_dsc_t()
                    self.line_dsc.init()
                    self.line_dsc.color = lv.color_make(self.pen_color[0], self.pen_color[1], self.pen_color[2])
                    self.line_dsc.width = 30
                    self.line_dsc.round_end = 1
                    self.line_dsc.round_start = 1

                    self.board = lv.canvas(self.conv)
                    self.board.set_buffer(canvas_buffer, canvas_width, canvas_height, lv.COLOR_FORMAT.NATIVE)
                    self.board.fill_bg(lv.color_hex3(0xFFF), lv.OPA.COVER)
                    self.board.center()
                    self.board.clear_flag(lv.obj.FLAG.SCROLLABLE)
                    self.board.add_flag(lv.obj.FLAG.CLICKABLE)
                    self.board.add_event(self.board_event_cb, lv.EVENT.PRESSED, None)
                    self.board.add_event(self.board_event_cb, lv.EVENT.PRESSING, None)
                    self.board.add_event(self.board_event_cb, lv.EVENT.RELEASED, None)

                    self.settings_conv = lv.obj(self.conv)
                    self.settings_conv.set_size(260, lv.pct(100))
                    self.settings_conv.align(lv.ALIGN.LEFT_MID, -260, 0)
                    self.settings_conv.set_style_pad_all(0, 0)
                    self.settings_conv.set_style_border_width(0, 0)
                    self.settings_conv.set_style_radius(20, 0)
                    self.settings_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.settings_conv.set_style_bg_opa(180, 0)
                    self.settings_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.settings_handle = lv.obj(self.conv)
                    self.settings_handle.set_size(50, lv.pct(30))
                    self.settings_handle.align_to(self.settings_conv, lv.ALIGN.OUT_RIGHT_MID, 0, 0)
                    self.settings_handle.set_style_pad_all(0, 0)
                    self.settings_handle.set_style_border_width(0, 0)
                    self.settings_handle.set_style_radius(0, 0)
                    self.settings_handle.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.settings_handle.set_style_bg_opa(0, 0)
                    self.settings_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                    self.settings_handle.add_flag(lv.obj.FLAG.CLICKABLE)
                    self.settings_handle.add_event(self.settings_handle_event_cb, lv.EVENT.PRESSING, None)
                    self.settings_handle.add_event(self.settings_handle_event_cb, lv.EVENT.RELEASED, None)

                    self.settings_handle_bar = lv.obj(self.settings_handle)
                    self.settings_handle_bar.set_size(12, lv.pct(50))
                    self.settings_handle_bar.align(lv.ALIGN.LEFT_MID, 10, 0)
                    self.settings_handle_bar.set_style_pad_all(0, 0)
                    self.settings_handle_bar.set_style_border_width(0, 0)
                    self.settings_handle_bar.set_style_radius(6, 0)
                    self.settings_handle_bar.set_style_bg_color(lv.color_hex(0x1F1F1F), 0)
                    self.settings_handle_bar.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.settings_conv_x_anim = lv.anim_t()
                    self.settings_conv_x_anim.init()
                    self.settings_conv_x_anim.set_var(self.settings_conv)
                    self.settings_conv_x_anim.set_repeat_count(1)
                    self.settings_conv_x_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.settings_conv_x_anim.set_custom_exec_cb(lambda anim, val: self.settings_conv_x_anim_cb(self.settings_conv, val))

                    self.settings_pen_show_conv = lv.obj(self.settings_conv)
                    self.settings_pen_show_conv.set_size(lv.pct(100), 100)
                    self.settings_pen_show_conv.align(lv.ALIGN.TOP_MID, 0, 40)
                    self.settings_pen_show_conv.set_style_pad_all(0, 0)
                    self.settings_pen_show_conv.set_style_border_width(0, 0)
                    self.settings_pen_show_conv.set_style_radius(0, 0)
                    self.settings_pen_show_conv.set_style_bg_opa(0, 0)
                    self.settings_pen_show_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.settings_pen_show = lv.obj(self.settings_pen_show_conv)
                    self.settings_pen_show.set_size(self.line_dsc.width, self.line_dsc.width)
                    self.settings_pen_show.center()
                    self.settings_pen_show.set_style_pad_all(0, 0)
                    self.settings_pen_show.set_style_border_width(0, 0)
                    self.settings_pen_show.set_style_radius(1000, 0)
                    self.settings_pen_show.set_style_bg_color(self.line_dsc.color, 0)
                    self.settings_pen_show.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.settings_red_slider = lv.slider(self.settings_conv)
                    self.settings_red_slider.set_size(lv.pct(75), 20)
                    self.settings_red_slider.align_to(self.settings_pen_show_conv, lv.ALIGN.OUT_BOTTOM_MID, 0, 10)
                    self.settings_red_slider.set_style_bg_color(lv.color_hex(0xFF0000), lv.PART.MAIN)
                    self.settings_red_slider.set_style_bg_color(lv.color_hex(0xFF0000), lv.PART.INDICATOR)
                    self.settings_red_slider.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.KNOB)
                    self.settings_red_slider.set_range(0, 0xFF)
                    self.settings_red_slider.set_value(self.pen_color[0], lv.ANIM.OFF)
                    self.settings_red_slider.add_event(self.settings_color_slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

                    self.settings_green_slider = lv.slider(self.settings_conv)
                    self.settings_green_slider.set_size(lv.pct(75), 20)
                    self.settings_green_slider.align_to(self.settings_red_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 25)
                    self.settings_green_slider.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.MAIN)
                    self.settings_green_slider.set_style_bg_color(lv.color_hex(0x00FF00), lv.PART.INDICATOR)
                    self.settings_green_slider.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.KNOB)
                    self.settings_green_slider.set_range(0, 0xFF)
                    self.settings_green_slider.set_value(self.pen_color[1], lv.ANIM.OFF)
                    self.settings_green_slider.add_event(self.settings_color_slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

                    self.settings_blue_slider = lv.slider(self.settings_conv)
                    self.settings_blue_slider.set_size(lv.pct(75), 20)
                    self.settings_blue_slider.align_to(self.settings_green_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 25)
                    self.settings_blue_slider.set_style_bg_color(lv.color_hex(0x0000FF), lv.PART.MAIN)
                    self.settings_blue_slider.set_style_bg_color(lv.color_hex(0x0000FF), lv.PART.INDICATOR)
                    self.settings_blue_slider.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.KNOB)
                    self.settings_blue_slider.set_range(0, 0xFF)
                    self.settings_blue_slider.set_value(self.pen_color[2], lv.ANIM.OFF)
                    self.settings_blue_slider.add_event(self.settings_color_slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

                    self.settings_size_slider = lv.slider(self.settings_conv)
                    self.settings_size_slider.set_size(lv.pct(75), 20)
                    self.settings_size_slider.align_to(self.settings_blue_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 25)
                    self.settings_size_slider.set_style_bg_color(lv.color_hex(0x7F7F7F), lv.PART.MAIN)
                    self.settings_size_slider.set_style_bg_color(lv.color_hex(0x7F7F7F), lv.PART.INDICATOR)
                    self.settings_size_slider.set_style_bg_color(lv.color_hex(0xFFFFFF), lv.PART.KNOB)
                    self.settings_size_slider.set_range(8, 100)
                    self.settings_size_slider.set_value(self.line_dsc.width, lv.ANIM.OFF)
                    self.settings_size_slider.add_event(self.settings_size_slider_event_cb, lv.EVENT.VALUE_CHANGED, None)

                    self.settings_clean_btn = lv.btn(self.settings_conv)
                    self.settings_clean_btn.set_size(lv.pct(75), lv.pct(16))
                    self.settings_clean_btn.align_to(self.settings_size_slider, lv.ALIGN.OUT_BOTTOM_MID, 0, 40)
                    self.settings_clean_btn.set_style_radius(12, 0)
                    self.settings_clean_btn.add_event(self.settings_clean_btn_event_cb, lv.EVENT.CLICKED, None)

                    self.settings_clean_btn_label = lv.label(self.settings_clean_btn)
                    self.settings_clean_btn_label.set_style_text_font(self.lv_font_normal_size25, 0)
                    self.settings_clean_btn_label.set_text("Clean")
                    self.settings_clean_btn_label.center()
                    self.settings_clean_btn_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                    self.set_home_bar_color(lv.color_hex(0x000000))
                    self.set_home_bar_top()

                def settings_clean_btn_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.CLICKED:
                        self.board.fill_bg(lv.color_hex3(0xFFF), lv.OPA.COVER)

                def settings_color_slider_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.VALUE_CHANGED:
                        self.pen_color[0] = self.settings_red_slider.get_value()
                        self.pen_color[1] = self.settings_green_slider.get_value()
                        self.pen_color[2] = self.settings_blue_slider.get_value()
                        color = lv.color_make(self.pen_color[0], self.pen_color[1], self.pen_color[2])

                        self.settings_pen_show.set_style_bg_color(color, 0)
                        self.line_dsc.color = color

                def settings_size_slider_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.VALUE_CHANGED:
                        size = self.settings_size_slider.get_value()
                        self.settings_pen_show.set_size(size, size)
                        self.line_dsc.width = size

                def settings_conv_x_anim_cb(self, settings_handle, x):
                    self.settings_conv.set_x(x)
                    self.settings_handle.set_x(x + 260)

                def settings_handle_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.PRESSING:
                        point = lv.point_t()
                        indev = lv.indev_get_act()
                        indev.get_point(point)

                        if self.settings_handle_start_x is None:
                            self.settings_handle_start_x = point.x
                        else:
                            delta_x = point.x - self.settings_handle_start_x
                            settings_conv_x = self.settings_conv.get_x()
                            settings_handle_x = self.settings_handle.get_x()
                            settings_conv_x_dest = settings_conv_x + delta_x
                            settings_handle_x_dest = settings_handle_x + delta_x
                            if settings_conv_x_dest >= -260 and settings_conv_x_dest <= 0:
                                self.settings_conv.set_x(settings_conv_x_dest)
                                self.settings_handle.set_x(settings_handle_x_dest)

                            self.settings_handle_start_x = point.x
                    elif code == lv.EVENT.RELEASED:
                        self.settings_handle_start_x = None
                        self.settings_conv_x_anim.set_time(200)
                        settings_conv_x = self.settings_conv.get_x()
                        if self.is_settings_opened == False:
                            if settings_conv_x > -200:
                                self.is_settings_opened = True
                                self.settings_conv_x_anim.set_values(settings_conv_x, 0)
                            else:
                                self.settings_conv_x_anim.set_values(settings_conv_x, -260)
                        else:
                            if settings_conv_x < -60:
                                self.is_settings_opened = False
                                self.settings_conv_x_anim.set_values(settings_conv_x, -260)
                            else:
                                self.settings_conv_x_anim.set_values(settings_conv_x, 0)

                        lv.anim_t.start(self.settings_conv_x_anim)

                def board_event_cb(self, event):
                    code = event.get_code()

                    if code == lv.EVENT.PRESSED:
                        self.board_previous_point = lv.point_t()
                        indev = lv.indev_get_act()
                        indev.get_point(self.board_previous_point)

                        if self.is_settings_opened == True:
                            self.is_settings_opened = False
                            self.settings_conv_x_anim.set_time(500)
                            settings_conv_x = self.settings_conv.get_x()
                            self.settings_conv_x_anim.set_values(settings_conv_x, -260)
                            lv.anim_t.start(self.settings_conv_x_anim)
                    elif code == lv.EVENT.PRESSING:
                        self.board_current_point = lv.point_t()
                        indev = lv.indev_get_act()
                        indev.get_point(self.board_current_point)

                        self.board.draw_line([self.board_previous_point, self.board_current_point], 2, self.line_dsc)

                        self.board_previous_point = lv.point_t({'x': self.board_current_point.x, 'y': self.board_current_point.y})
                    elif code == lv.EVENT.RELEASED:
                        self.board_previous_point = None
                        self.board_current_point = None

            class AppTester(AppBase):
                class LEDRCtrl():
                    def __init__(self, slot, led_hw, default_percent=50):
                        self.led_hw = led_hw

                        self.bar_handle_main_start_y = None

                        self.bar_conv = lv.obj(slot)
                        self.bar_conv.set_size(lv.pct(100), lv.pct(60))
                        self.bar_conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                        self.bar_conv.set_style_pad_all(0, 0)
                        self.bar_conv.set_style_border_width(0, 0)
                        self.bar_conv.set_style_radius(40, 0)
                        self.bar_conv.set_style_clip_corner(True, 0)
                        self.bar_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.bar_conv.set_style_bg_opa(120, 0)
                        self.bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle_main = lv.obj(self.bar_conv)
                        self.bar_handle_main.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle_main.align(lv.ALIGN.TOP_MID, 0, lv.pct(100 - default_percent))
                        self.bar_handle_main.set_style_pad_all(0, 0)
                        self.bar_handle_main.set_style_border_width(0, 0)
                        self.bar_handle_main.set_style_radius(0, 0)
                        self.bar_handle_main.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.bar_handle_main.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle = lv.obj(self.bar_conv)
                        self.bar_handle.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle.center()
                        self.bar_handle.set_style_pad_all(0, 0)
                        self.bar_handle.set_style_border_width(0, 0)
                        self.bar_handle.set_style_radius(0, 0)
                        self.bar_handle.set_style_bg_opa(0, 0)
                        self.bar_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.bar_handle.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.PRESSING, None)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.RELEASED, None)

                        self.led_icon = lv.obj(slot)
                        self.led_icon.set_size(40, 40)
                        self.led_icon.align_to(self.bar_conv, lv.ALIGN.OUT_TOP_MID, 0, -18)
                        self.led_icon.set_style_pad_all(0, 0)
                        self.led_icon.set_style_border_width(0, 0)
                        self.led_icon.set_style_radius(20, 0)
                        self.led_icon.set_style_bg_color(lv.color_hex(0xFF0000), 0)
                        self.led_icon.set_style_shadow_color(lv.color_hex(0xFF0000), 0)
                        self.led_icon.set_style_shadow_width(30, 0)
                        self.led_icon.set_style_shadow_spread(3, 0)
                        self.led_icon.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.percent_cb(default_percent)

                    def bar_handle_event_cb(self, event):
                        code = event.get_code()

                        if code == lv.EVENT.PRESSING:
                            point = lv.point_t()
                            indev = lv.indev_get_act()
                            indev.get_point(point)

                            if self.bar_handle_main_start_y is None:
                                self.bar_handle_main_start_y = point.y
                            else:
                                delta_y = point.y - self.bar_handle_main_start_y
                                bar_handle_main_y = self.bar_handle_main.get_y()
                                bar_handle_main_y_dest = bar_handle_main_y + delta_y
                                if bar_handle_main_y_dest < 0:
                                    bar_handle_main_y_dest = 0
                                elif bar_handle_main_y_dest > self.bar_handle_main.get_height():
                                    bar_handle_main_y_dest = self.bar_handle_main.get_height()
                                self.bar_handle_main.set_y(bar_handle_main_y_dest)
                                self.bar_handle_main_start_y = point.y
                                self.percent_cb(100 - round(bar_handle_main_y_dest / (self.bar_handle_main.get_height() / 100)))
                        elif code == lv.EVENT.RELEASED:
                            self.bar_handle_main_start_y = None

                    def percent_cb(self, percent):
                        if percent == 0:
                            self.led_icon.set_style_bg_color(lv.color_hex(0x7F0000), 0)
                            self.led_icon.set_style_shadow_width(0, 0)
                            self.led_icon.set_style_shadow_spread(0, 0)
                            self.led_hw.off()
                        else:
                            self.led_icon.set_style_bg_color(lv.color_hex(0xFF0000), 0)
                            self.led_icon.set_style_shadow_width(int(percent * 0.45), 0)
                            self.led_icon.set_style_shadow_spread(int(percent * 0.45 // 10), 0)
                            self.led_hw.set_brightness(percent)

                class LEDBCtrl():
                    def __init__(self, slot, led_hw, default_percent=50):
                        self.led_hw = led_hw

                        self.bar_handle_main_start_y = None

                        self.bar_conv = lv.obj(slot)
                        self.bar_conv.set_size(lv.pct(100), lv.pct(60))
                        self.bar_conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                        self.bar_conv.set_style_pad_all(0, 0)
                        self.bar_conv.set_style_border_width(0, 0)
                        self.bar_conv.set_style_radius(40, 0)
                        self.bar_conv.set_style_clip_corner(True, 0)
                        self.bar_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.bar_conv.set_style_bg_opa(120, 0)
                        self.bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle_main = lv.obj(self.bar_conv)
                        self.bar_handle_main.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle_main.align(lv.ALIGN.TOP_MID, 0, lv.pct(100 - default_percent))
                        self.bar_handle_main.set_style_pad_all(0, 0)
                        self.bar_handle_main.set_style_border_width(0, 0)
                        self.bar_handle_main.set_style_radius(0, 0)
                        self.bar_handle_main.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.bar_handle_main.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle = lv.obj(self.bar_conv)
                        self.bar_handle.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle.center()
                        self.bar_handle.set_style_pad_all(0, 0)
                        self.bar_handle.set_style_border_width(0, 0)
                        self.bar_handle.set_style_radius(0, 0)
                        self.bar_handle.set_style_bg_opa(0, 0)
                        self.bar_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.bar_handle.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.PRESSING, None)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.RELEASED, None)

                        self.led_icon = lv.obj(slot)
                        self.led_icon.set_size(40, 40)
                        self.led_icon.align_to(self.bar_conv, lv.ALIGN.OUT_TOP_MID, 0, -18)
                        self.led_icon.set_style_pad_all(0, 0)
                        self.led_icon.set_style_border_width(0, 0)
                        self.led_icon.set_style_radius(20, 0)
                        self.led_icon.set_style_bg_color(lv.color_hex(0x0000FF), 0)
                        self.led_icon.set_style_shadow_color(lv.color_hex(0x0000FF), 0)
                        self.led_icon.set_style_shadow_width(30, 0)
                        self.led_icon.set_style_shadow_spread(3, 0)
                        self.led_icon.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.percent_cb(default_percent)

                    def bar_handle_event_cb(self, event):
                        code = event.get_code()

                        if code == lv.EVENT.PRESSING:
                            point = lv.point_t()
                            indev = lv.indev_get_act()
                            indev.get_point(point)

                            if self.bar_handle_main_start_y is None:
                                self.bar_handle_main_start_y = point.y
                            else:
                                delta_y = point.y - self.bar_handle_main_start_y
                                bar_handle_main_y = self.bar_handle_main.get_y()
                                bar_handle_main_y_dest = bar_handle_main_y + delta_y
                                if bar_handle_main_y_dest < 0:
                                    bar_handle_main_y_dest = 0
                                elif bar_handle_main_y_dest > self.bar_handle_main.get_height():
                                    bar_handle_main_y_dest = self.bar_handle_main.get_height()
                                self.bar_handle_main.set_y(bar_handle_main_y_dest)
                                self.bar_handle_main_start_y = point.y
                                self.percent_cb(100 - round(bar_handle_main_y_dest / (self.bar_handle_main.get_height() / 100)))
                        elif code == lv.EVENT.RELEASED:
                            self.bar_handle_main_start_y = None

                    def percent_cb(self, percent):
                        if percent == 0:
                            self.led_icon.set_style_bg_color(lv.color_hex(0x00007F), 0)
                            self.led_icon.set_style_shadow_width(0, 0)
                            self.led_icon.set_style_shadow_spread(0, 0)
                            self.led_hw.off()
                        else:
                            self.led_icon.set_style_bg_color(lv.color_hex(0x0000FF), 0)
                            self.led_icon.set_style_shadow_width(int(percent * 0.45), 0)
                            self.led_icon.set_style_shadow_spread(int(percent * 0.45 // 10), 0)
                            self.led_hw.set_brightness(percent)

                class BuzzerLoudnessCtrl():
                    def __init__(self, slot, buzzer_hw, default_percent=50):
                        with open(RESOURCES_PATH + "APP/Tester/app_icon_64x64_volume_mute.png", 'rb') as f:
                            img_data = f.read()
                        self.img_volume_mute_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })
                        with open(RESOURCES_PATH + "APP/Tester/app_icon_64x64_volume_low.png", 'rb') as f:
                            img_data = f.read()
                        self.img_volume_low_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })
                        with open(RESOURCES_PATH + "APP/Tester/app_icon_64x64_volume_high.png", 'rb') as f:
                            img_data = f.read()
                        self.img_volume_high_dsc = lv.img_dsc_t({
                            'data_size': len(img_data),
                            'data': img_data
                        })

                        self.buzzer_hw = buzzer_hw

                        self.bar_handle_main_start_y = None

                        self.bar_conv = lv.obj(slot)
                        self.bar_conv.set_size(lv.pct(100), lv.pct(60))
                        self.bar_conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                        self.bar_conv.set_style_pad_all(0, 0)
                        self.bar_conv.set_style_border_width(0, 0)
                        self.bar_conv.set_style_radius(40, 0)
                        self.bar_conv.set_style_clip_corner(True, 0)
                        self.bar_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.bar_conv.set_style_bg_opa(120, 0)
                        self.bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle_main = lv.obj(self.bar_conv)
                        self.bar_handle_main.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle_main.align(lv.ALIGN.TOP_MID, 0, lv.pct(100 - default_percent))
                        self.bar_handle_main.set_style_pad_all(0, 0)
                        self.bar_handle_main.set_style_border_width(0, 0)
                        self.bar_handle_main.set_style_radius(0, 0)
                        self.bar_handle_main.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.bar_handle_main.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle = lv.obj(self.bar_conv)
                        self.bar_handle.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle.center()
                        self.bar_handle.set_style_pad_all(0, 0)
                        self.bar_handle.set_style_border_width(0, 0)
                        self.bar_handle.set_style_radius(0, 0)
                        self.bar_handle.set_style_bg_opa(0, 0)
                        self.bar_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.bar_handle.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.PRESSING, None)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.RELEASED, None)

                        self.buzzer_icon = lv.img(slot)
                        self.buzzer_icon.set_src(self.img_volume_mute_dsc)
                        self.buzzer_icon.align_to(self.bar_conv, lv.ALIGN.OUT_TOP_MID, 0, -10)

                        self.percent_cb(default_percent)

                    def bar_handle_event_cb(self, event):
                        code = event.get_code()

                        if code == lv.EVENT.PRESSING:
                            point = lv.point_t()
                            indev = lv.indev_get_act()
                            indev.get_point(point)

                            if self.bar_handle_main_start_y is None:
                                self.bar_handle_main_start_y = point.y
                            else:
                                delta_y = point.y - self.bar_handle_main_start_y
                                bar_handle_main_y = self.bar_handle_main.get_y()
                                bar_handle_main_y_dest = bar_handle_main_y + delta_y
                                if bar_handle_main_y_dest < 0:
                                    bar_handle_main_y_dest = 0
                                elif bar_handle_main_y_dest > self.bar_handle_main.get_height():
                                    bar_handle_main_y_dest = self.bar_handle_main.get_height()
                                self.bar_handle_main.set_y(bar_handle_main_y_dest)
                                self.bar_handle_main_start_y = point.y
                                self.percent_cb(100 - round(bar_handle_main_y_dest / (self.bar_handle_main.get_height() / 100)))
                        elif code == lv.EVENT.RELEASED:
                            self.bar_handle_main_start_y = None

                    def percent_cb(self, percent):
                        if percent == 0:
                            self.buzzer_icon.set_src(self.img_volume_mute_dsc)
                            self.buzzer_hw.off()
                        else:
                            self.buzzer_hw.set_loudness(percent // 10 + 1)
                            if percent > 50:
                                self.buzzer_icon.set_src(self.img_volume_high_dsc)
                            else:
                                self.buzzer_icon.set_src(self.img_volume_low_dsc)

                class BuzzerFrequencyCtrl():
                    def __init__(self, slot, buzzer_hw, default_percent=50):
                        self.lv_font_normal_size30 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size30_bpp4.bin")

                        self.buzzer_hw = buzzer_hw

                        self.bar_handle_main_start_y = None

                        self.bar_conv = lv.obj(slot)
                        self.bar_conv.set_size(lv.pct(100), lv.pct(60))
                        self.bar_conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                        self.bar_conv.set_style_pad_all(0, 0)
                        self.bar_conv.set_style_border_width(0, 0)
                        self.bar_conv.set_style_radius(40, 0)
                        self.bar_conv.set_style_clip_corner(True, 0)
                        self.bar_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                        self.bar_conv.set_style_bg_opa(120, 0)
                        self.bar_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle_main = lv.obj(self.bar_conv)
                        self.bar_handle_main.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle_main.align(lv.ALIGN.TOP_MID, 0, lv.pct(100 - default_percent))
                        self.bar_handle_main.set_style_pad_all(0, 0)
                        self.bar_handle_main.set_style_border_width(0, 0)
                        self.bar_handle_main.set_style_radius(0, 0)
                        self.bar_handle_main.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                        self.bar_handle_main.clear_flag(lv.obj.FLAG.SCROLLABLE)

                        self.bar_handle = lv.obj(self.bar_conv)
                        self.bar_handle.set_size(lv.pct(100), lv.pct(100))
                        self.bar_handle.center()
                        self.bar_handle.set_style_pad_all(0, 0)
                        self.bar_handle.set_style_border_width(0, 0)
                        self.bar_handle.set_style_radius(0, 0)
                        self.bar_handle.set_style_bg_opa(0, 0)
                        self.bar_handle.clear_flag(lv.obj.FLAG.SCROLLABLE)
                        self.bar_handle.add_flag(lv.obj.FLAG.CLICKABLE)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.PRESSING, None)
                        self.bar_handle.add_event(self.bar_handle_event_cb, lv.EVENT.RELEASED, None)

                        self.frequency = lv.label(slot)
                        self.frequency.set_style_text_font(self.lv_font_normal_size30, 0)
                        self.frequency.set_text("4000Hz")
                        self.frequency.align_to(self.bar_conv, lv.ALIGN.OUT_TOP_MID, 0, -20)
                        self.frequency.set_style_text_color(lv.color_hex(0x000000), 0)

                        self.percent_cb(default_percent)

                    def bar_handle_event_cb(self, event):
                        code = event.get_code()

                        if code == lv.EVENT.PRESSING:
                            point = lv.point_t()
                            indev = lv.indev_get_act()
                            indev.get_point(point)

                            if self.bar_handle_main_start_y is None:
                                self.bar_handle_main_start_y = point.y
                            else:
                                delta_y = point.y - self.bar_handle_main_start_y
                                bar_handle_main_y = self.bar_handle_main.get_y()
                                bar_handle_main_y_dest = bar_handle_main_y + delta_y
                                if bar_handle_main_y_dest < 0:
                                    bar_handle_main_y_dest = 0
                                elif bar_handle_main_y_dest > self.bar_handle_main.get_height():
                                    bar_handle_main_y_dest = self.bar_handle_main.get_height()
                                self.bar_handle_main.set_y(bar_handle_main_y_dest)
                                self.bar_handle_main_start_y = point.y
                                self.percent_cb(100 - round(bar_handle_main_y_dest / (self.bar_handle_main.get_height() / 100)))
                        elif code == lv.EVENT.RELEASED:
                            self.bar_handle_main_start_y = None

                    def percent_cb(self, percent):
                        frequency = int(4000 + ((percent - 50) * 10))
                        self.buzzer_hw.set_frequency(frequency)
                        self.frequency.set_text(str(frequency) + "Hz")

                def __init__(self, icon_area, masker, screen, status_bar, hw_resources):
                    super().__init__(icon_area, masker, screen, status_bar, hw_resources, self.base_close_cb)
                    self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.conv.set_style_bg_grad_color(lv.color_hex(0x000000), 0)
                    self.conv.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)

                    self.ledr = self.hw_resources.get("LEDR")
                    self.ledb = self.hw_resources.get("LEDB")
                    self.buzzer = self.hw_resources.get("Buzzer")

                    self.ledr_slot = lv.obj(self.conv)
                    self.ledr_slot.set_size(120, 400)
                    self.ledr_slot.align(lv.ALIGN.LEFT_MID, 40, -40)
                    self.ledr_slot.set_style_pad_all(0, 0)
                    self.ledr_slot.set_style_border_width(0, 0)
                    self.ledr_slot.set_style_radius(0, 0)
                    self.ledr_slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.ledr_slot.set_style_bg_opa(0, 0)
                    self.ledr_slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.ledb_slot = lv.obj(self.conv)
                    self.ledb_slot.set_size(120, 400)
                    self.ledb_slot.align_to(self.ledr_slot, lv.ALIGN.OUT_RIGHT_MID, 20, 0)
                    self.ledb_slot.set_style_pad_all(0, 0)
                    self.ledb_slot.set_style_border_width(0, 0)
                    self.ledb_slot.set_style_radius(0, 0)
                    self.ledb_slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.ledb_slot.set_style_bg_opa(0, 0)
                    self.ledb_slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.buzzer_loudness_slot = lv.obj(self.conv)
                    self.buzzer_loudness_slot.set_size(120, 400)
                    self.buzzer_loudness_slot.align_to(self.ledb_slot, lv.ALIGN.OUT_RIGHT_MID, 40, 0)
                    self.buzzer_loudness_slot.set_style_pad_all(0, 0)
                    self.buzzer_loudness_slot.set_style_border_width(0, 0)
                    self.buzzer_loudness_slot.set_style_radius(0, 0)
                    self.buzzer_loudness_slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.buzzer_loudness_slot.set_style_bg_opa(0, 0)
                    self.buzzer_loudness_slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.buzzer_frequency_slot = lv.obj(self.conv)
                    self.buzzer_frequency_slot.set_size(120, 400)
                    self.buzzer_frequency_slot.align_to(self.buzzer_loudness_slot, lv.ALIGN.OUT_RIGHT_MID, 20, 0)
                    self.buzzer_frequency_slot.set_style_pad_all(0, 0)
                    self.buzzer_frequency_slot.set_style_border_width(0, 0)
                    self.buzzer_frequency_slot.set_style_radius(0, 0)
                    self.buzzer_frequency_slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.buzzer_frequency_slot.set_style_bg_opa(0, 0)
                    self.buzzer_frequency_slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.ledr_ctrl = self.LEDRCtrl(self.ledr_slot, self.hw_resources.get("LEDR"), 0)
                    self.ledb_ctrl = self.LEDBCtrl(self.ledb_slot, self.hw_resources.get("LEDB"), 0)
                    self.buzzer_loudness_ctrl = self.BuzzerLoudnessCtrl(self.buzzer_loudness_slot, self.hw_resources.get("Buzzer"), 0)
                    self.buzzer_frequency_ctrl = self.BuzzerFrequencyCtrl(self.buzzer_frequency_slot, self.hw_resources.get("Buzzer"), 50)

                    self.set_home_bar_color(lv.color_hex(0xFFFFFF))
                    self.set_home_bar_top()

                def base_close_cb(self):
                    self.ledr.off()
                    self.ledb.off()
                    self.buzzer.off()

            class FullScreenMSG():
                def __init__(self, screen):
                    self.lv_font_normal_size25 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size25_bpp4.bin")
                    self.lv_font_normal_size20 = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                    self.masker = lv.obj(screen)
                    self.masker.set_size(lv.pct(100), lv.pct(100))
                    self.masker.center()
                    self.masker.set_style_pad_all(0, 0)
                    self.masker.set_style_border_width(0, 0)
                    self.masker.set_style_radius(0, 0)
                    self.masker.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.masker.set_style_bg_opa(50, 0)
                    self.masker.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.conv = lv.obj(self.masker)
                    self.conv.set_size(lv.pct(50), lv.pct(40))
                    self.conv.center()
                    self.conv.set_style_pad_all(0, 0)
                    self.conv.set_style_border_width(0, 0)
                    self.conv.set_style_radius(20, 0)
                    self.conv.set_style_clip_corner(True, 0)
                    self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                    self.conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.title_conv = lv.obj(self.conv)
                    self.title_conv.set_size(lv.pct(100), lv.pct(20))
                    self.title_conv.align(lv.ALIGN.TOP_MID, 0, 0)
                    self.title_conv.set_style_pad_all(0, 0)
                    self.title_conv.set_style_border_width(0, 0)
                    self.title_conv.set_style_radius(0, 0)
                    self.title_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.title_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.title = lv.label(self.title_conv)
                    self.title.set_style_text_font(self.lv_font_normal_size25, 0)
                    self.title.set_text("Title")
                    self.title.align(lv.ALIGN.LEFT_MID, 20, 0)
                    self.title.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                    self.msg_conv = lv.obj(self.conv)
                    self.msg_conv.set_size(lv.pct(100), lv.pct(55))
                    self.msg_conv.align_to(self.title_conv, lv.ALIGN.OUT_BOTTOM_LEFT, 0, 0)
                    self.msg_conv.set_style_pad_all(0, 0)
                    self.msg_conv.set_style_border_width(0, 0)
                    self.msg_conv.set_style_radius(0, 0)
                    self.msg_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.msg_conv.set_style_bg_opa(0, 0)
                    self.msg_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.msg = lv.label(self.msg_conv)
                    self.msg.set_style_text_font(self.lv_font_normal_size20, 0)
                    self.msg.set_width(lv.pct(90))
                    self.msg.set_text("Massage")
                    self.msg.align(lv.ALIGN.LEFT_MID, lv.pct(10), 0)
                    self.msg.set_style_text_color(lv.color_hex(0x000000), 0)

                    self.btn_conv = lv.obj(self.conv)
                    self.btn_conv.set_size(lv.pct(100), lv.pct(25))
                    self.btn_conv.align(lv.ALIGN.BOTTOM_MID, 0, 0)
                    self.btn_conv.set_style_pad_all(0, 0)
                    self.btn_conv.set_style_border_width(0, 0)
                    self.btn_conv.set_style_radius(0, 0)
                    self.btn_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.btn_conv.set_style_bg_opa(0, 0)
                    self.btn_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                    self.btn = lv.btn(self.btn_conv)
                    self.btn.set_size(lv.pct(40), lv.pct(80))
                    self.btn.align(lv.ALIGN.TOP_MID, 0, 0)
                    self.btn.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.btn.add_event(self.btn_event_cb, lv.EVENT.CLICKED, None)

                    self.btn_label = lv.label(self.btn)
                    self.btn_label.set_style_text_font(self.lv_font_normal_size25, 0)
                    self.btn_label.set_text("OK")
                    self.btn_label.center()
                    self.btn_label.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

                    self.hide()

                def show(self, title_text, msg_text, btn_text):
                    self.title.set_text(title_text)
                    self.msg.set_text(msg_text)
                    self.btn_label.set_text(btn_text)
                    self.masker.move_foreground()
                    self.masker.clear_flag(lv.obj.FLAG.HIDDEN)

                def hide(self):
                    self.masker.add_flag(lv.obj.FLAG.HIDDEN)

                def btn_event_cb(self, event):
                    code = event.get_code()
                    if code == lv.EVENT.CLICKED:
                        self.hide()

            class AppLoader():
                def __init__(self, screen, status_bar, hw_resources_dict):
                    self.screen = screen
                    self.status_bar = status_bar
                    self.hw_resources_dict = hw_resources_dict

                    self.masker = lv.obj(screen)
                    self.masker.align(lv.ALIGN.TOP_LEFT, 0, 0)
                    self.masker.set_style_pad_all(0, 0)
                    self.masker.set_style_border_width(0, 0)
                    self.masker.set_style_radius(20, 0)
                    self.masker.set_style_clip_corner(True, 0)
                    self.masker.set_style_bg_color(lv.color_hex(0x000000), 0)
                    self.masker.set_style_bg_opa(0, 0)
                    self.masker.clear_flag(lv.obj.FLAG.SCROLLABLE)
                    self.masker.move_background()
                    self.masker.add_flag(lv.obj.FLAG.HIDDEN)

                    self.masker_opa_anim = lv.anim_t()
                    self.masker_opa_anim.init()
                    self.masker_opa_anim.set_var(self.masker)
                    self.masker_opa_anim.set_values(0, 255)
                    self.masker_opa_anim.set_repeat_count(1)
                    self.masker_opa_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.masker_opa_anim.set_custom_exec_cb(lambda anim, val: self.masker_opa_anim_cb(self.masker, val))

                    self.masker_x_anim = lv.anim_t()
                    self.masker_x_anim.init()
                    self.masker_x_anim.set_var(self.masker)
                    self.masker_x_anim.set_repeat_count(1)
                    self.masker_x_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.masker_x_anim.set_custom_exec_cb(lambda anim, val: self.masker_x_anim_cb(self.masker, val))

                    self.masker_y_anim = lv.anim_t()
                    self.masker_y_anim.init()
                    self.masker_y_anim.set_var(self.masker)
                    self.masker_y_anim.set_repeat_count(1)
                    self.masker_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.masker_y_anim.set_custom_exec_cb(lambda anim, val: self.masker_y_anim_cb(self.masker, val))

                    self.masker_width_anim = lv.anim_t()
                    self.masker_width_anim.init()
                    self.masker_width_anim.set_var(self.masker)
                    self.masker_width_anim.set_values(0, screen.get_width())
                    self.masker_width_anim.set_repeat_count(1)
                    self.masker_width_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.masker_width_anim.set_custom_exec_cb(lambda anim, val: self.masker_width_anim_cb(self.masker, val))

                    self.masker_height_anim = lv.anim_t()
                    self.masker_height_anim.init()
                    self.masker_height_anim.set_var(self.masker)
                    self.masker_height_anim.set_values(0, screen.get_height())
                    self.masker_height_anim.set_repeat_count(1)
                    self.masker_height_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    self.masker_height_anim.set_custom_exec_cb(lambda anim, val: self.masker_height_anim_cb(self.masker, val))

                def masker_opa_anim_cb(self, masker, opa):
                    masker.set_style_opa(opa, 0)

                def masker_x_anim_cb(self, masker, x):
                    masker.set_x(x)

                def masker_y_anim_cb(self, masker, y):
                    masker.set_y(y)

                def masker_width_anim_cb(self, masker, width):
                    masker.set_width(width)

                def masker_height_anim_cb(self, masker, height):
                    masker.set_height(height)

                def load_app(self, app_class, icon_area, load_time=200):
                    self.app = app_class(icon_area, self.masker, self.screen, self.status_bar, self.hw_resources_dict)

                    self.masker_x_anim.set_values((icon_area.x1 + icon_area.x2) // 2, 1)
                    self.masker_y_anim.set_values((icon_area.y1 + icon_area.y2) // 2, 1)

                    self.masker.clear_flag(lv.obj.FLAG.HIDDEN)
                    self.masker.move_foreground()

                    self.masker_opa_anim.set_time(load_time // 2)
                    self.masker_x_anim.set_time(load_time)
                    self.masker_y_anim.set_time(load_time)
                    self.masker_width_anim.set_time(load_time)
                    self.masker_height_anim.set_time(load_time)

#                     lv.anim_t.start(self.masker_opa_anim)
                    lv.anim_t.start(self.masker_x_anim)
                    lv.anim_t.start(self.masker_y_anim)
                    lv.anim_t.start(self.masker_width_anim)
                    lv.anim_t.start(self.masker_height_anim)

            def __init__(self, screen, status_bar, hw_resources_dict):
                self.lv_font_normal = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")
                self.app_dict = {
                    "Template": self.AppTemplate,
                    "AI Hub": self.AppAIHub,
                    "Calculator": self.AppCalculator,
                    "Photos": self.AppPhotos,
                    "Settings": self.AppSettings,
                    "Clock": self.AppClock,
                    "Freeform": self.AppFreeform,
                    "Tester": self.AppTester,
                }
                self.full_screen_msg = self.FullScreenMSG(screen)
                self.app_loader = self.AppLoader(screen, status_bar, hw_resources_dict)

            def add_icon(self, slot, label_text, label_text_color, icon_path):
                label = lv.label(slot)
                label.set_style_text_font(self.lv_font_normal, 0)
                label.set_text(label_text)
                label.align(lv.ALIGN.CENTER, 0, 50)
                label.set_style_text_color(label_text_color, 0)

                icon_conv = lv.obj(slot)
                icon_conv.set_size(100, 100)
                icon_conv.align(lv.ALIGN.CENTER, 0, -10)
                icon_conv.set_style_pad_all(0, 0)
                icon_conv.set_style_border_width(0, 0)
                icon_conv.set_style_radius(25, 0)
                icon_conv.set_style_clip_corner(True, 0)
                icon_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                icon_conv.set_style_bg_opa(0, 0)
                icon_conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

                with open(icon_path, 'rb') as f:
                    icon_data = f.read()
                icon_dsc = lv.img_dsc_t({
                    'data_size': len(icon_data),
                    'data': icon_data
                })
                icon = lv.img(icon_conv)
                icon.set_src(icon_dsc)
                icon.center()
                icon.add_flag(lv.obj.FLAG.CLICKABLE)
                icon.set_user_data(label)
                icon.add_event(self.app_icon_event_cb, lv.EVENT.PRESSED, None)
                icon.add_event(self.app_icon_event_cb, lv.EVENT.RELEASED, None)
                icon.add_event(self.app_icon_event_cb, lv.EVENT.CLICKED, None)

            def app_icon_event_cb(self, event):
                code = event.get_code()
                icon = lv.img.__cast__(event.get_target())
                label = lv.label.__cast__(icon.get_user_data())

                if code == lv.EVENT.PRESSED or code == lv.EVENT.RELEASED:
                    icon_zoom_anim = lv.anim_t()
                    icon_zoom_anim.init()
                    icon_zoom_anim.set_var(icon)
                    icon_zoom_anim.set_time(100)
                    icon_zoom_anim.set_repeat_count(1)
                    icon_zoom_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                    icon_zoom_anim.set_custom_exec_cb(lambda anim, val: self.icon_zoom_anim_cb(icon, val))
                    if code == lv.EVENT.PRESSED:
                        icon_zoom_anim.set_values(256, 270)
                    elif code == lv.EVENT.RELEASED:
                        icon_zoom_anim.set_values(270, 256)
                    lv.anim_t.start(icon_zoom_anim)
                elif code == lv.EVENT.CLICKED:
                    area = lv.area_t()
                    icon.get_coords(area)
                    if self.has_app(label.get_text()):
                        self.load_app(label.get_text(), area)
                    else:
                        self.full_screen_msg.show("Message", "The app has not been implemented yet", "OK")

            def icon_zoom_anim_cb(self, icon, val):
                icon.set_zoom(val)

            def has_app(self, app_name):
                return app_name in self.app_dict

            def load_app(self, app_name, icon_area):
                self.app_loader.load_app(self.app_dict.get(app_name), icon_area)

        class StatusBar():
            class ClockTime():
                def __init__(self, screen, hour, minute):
                    self.lv_font_normal = lv.font_load("A:" + RESOURCES_PATH + "Fonts/lv_font_normal_size20_bpp4.bin")

                    self.clock_time = lv.label(screen)
                    self.clock_time.set_style_text_font(self.lv_font_normal, 0)
                    self.clock_time.set_text(f"{hour:02d}" + ":" + f"{minute:02d}")
                    self.clock_time.align(lv.ALIGN.LEFT_MID, 20, 0)
                    self.clock_time.set_style_text_color(lv.color_hex(0x000000), 0)

                def set_time(self, hour, minute):
                    self.clock_time.set_text(f"{hour:02d}" + ":" + f"{minute:02d}")

            def __init__(self, screen):
                self.status_bar = lv.obj(screen)
                self.status_bar.set_size(lv.pct(100), 40)
                self.status_bar.align(lv.ALIGN.TOP_MID, 0, 0)
                self.status_bar.set_style_pad_all(0, 0)
                self.status_bar.set_style_border_width(0, 0)
                self.status_bar.set_style_radius(0, 0)
                self.status_bar.set_style_bg_color(lv.color_hex(0x000000), 0)
                self.status_bar.set_style_bg_opa(0, 0)
                self.status_bar.clear_flag(lv.obj.FLAG.SCROLLABLE)

                self.status_bar_y_anim = lv.anim_t()
                self.status_bar_y_anim.init()
                self.status_bar_y_anim.set_var(self.status_bar)
                self.status_bar_y_anim.set_time(300)
                self.status_bar_y_anim.set_repeat_count(1)
                self.status_bar_y_anim.set_path_cb(lv.anim_t.path_ease_in_out)
                self.status_bar_y_anim.set_custom_exec_cb(lambda anim, val: self.status_bar_y_anim_cb(self.status_bar, val))

                self.clock_time = self.ClockTime(self.status_bar, 0, 0)

            def light_mode(self):
                self.clock_time.clock_time.set_style_text_color(lv.color_hex(0x000000), 0)

            def dark_mode(self):
                self.clock_time.clock_time.set_style_text_color(lv.color_hex(0xFFFFFF), 0)

            def enter_full_screen(self):
                self.status_bar_y_anim.set_values(0, -40)
                lv.anim_t.start(self.status_bar_y_anim)

            def exit_full_screen(self):
                self.status_bar_y_anim.set_values(-40, 0)
                lv.anim_t.start(self.status_bar_y_anim)

            def status_bar_y_anim_cb(self, status_bar, y):
                status_bar.set_y(y)

        class Dock():
            def __init__(self, screen, app_manager):
                self.dock = lv.obj(screen)
                self.dock.set_size(lv.pct(90), 130)
                self.dock.align(lv.ALIGN.BOTTOM_MID, 0, -15)
                self.dock.set_style_pad_all(0, 0)
                self.dock.set_style_border_width(0, 0)
                self.dock.set_style_radius(25, 0)
                self.dock.set_style_clip_corner(True, 0)
                self.dock.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
                self.dock.set_style_bg_opa(120, 0)
                self.dock.clear_flag(lv.obj.FLAG.SCROLLABLE)

                self.app_manager = app_manager
                self.app_slot_list = []

                self.update_width()

            def update_width(self):
                if len(self.app_slot_list) == 0:
                    self.dock.set_width(0)
                else:
                    self.dock.set_width(len(self.app_slot_list) * (125 + 10) + 10)

            def add_app(self, icon_path, label_text, label_text_color):
                slot = lv.obj(self.dock)
                slot.set_size(125, lv.pct(100))
                if len(self.app_slot_list) == 0:
                    slot.align(lv.ALIGN.LEFT_MID, 10, 0)
                else:
                    slot_prev = self.app_slot_list[-1]
                    slot.align_to(slot_prev, lv.ALIGN.OUT_RIGHT_TOP, 10, 0)
                slot.set_style_pad_all(0, 0)
                slot.set_style_border_width(0, 0)
                slot.set_style_radius(0, 0)
                slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                slot.set_style_bg_opa(0, 0)
                slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                self.app_slot_list.append(slot)

                self.update_width()

                self.app_manager.add_icon(slot, label_text, label_text_color, icon_path)

        class AppConv():
            def __init__(self, screen, app_manager):
                self.app_conv = lv.obj(screen)
                self.app_conv.set_size(lv.pct(100), 280)
                self.app_conv.align(lv.ALIGN.CENTER, 0, -60)
                self.app_conv.set_style_pad_all(0, 0)
                self.app_conv.set_style_border_width(0, 0)
                self.app_conv.set_style_radius(0, 0)
                self.app_conv.set_style_bg_color(lv.color_hex(0x000000), 0)
                self.app_conv.set_style_bg_opa(0, 0)
                self.app_conv.add_flag(lv.obj.FLAG.SCROLLABLE)
                self.app_conv.set_scroll_dir(lv.DIR.HOR)
                self.app_conv.set_scroll_snap_x(lv.SCROLL_SNAP.CENTER)
                self.app_conv.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

                self.app_manager = app_manager
                self.app_page_list = []
                self.app_page_app_list_list = []

            def add_page(self):
                app_page = lv.obj(self.app_conv)
                app_page.set_size(lv.pct(100), 280)
                if len(self.app_page_list) == 0:
                    app_page.align(lv.ALIGN.LEFT_MID, 0, 0)
                else:
                    app_page_prev = self.app_page_list[-1]
                    app_page.align_to(app_page_prev, lv.ALIGN.OUT_RIGHT_TOP, 0, 0)
                app_page.set_style_pad_all(0, 0)
                app_page.set_style_border_width(0, 0)
                app_page.set_style_radius(0, 0)
                app_page.set_style_bg_color(lv.color_hex(0x000000), 0)
                app_page.set_style_bg_opa(0, 0)
                app_page.clear_flag(lv.obj.FLAG.SCROLLABLE)

                app_page_app_list = []

                self.app_page_list.append(app_page)
                self.app_page_app_list_list.append(app_page_app_list)

            def add_app(self, app_page_num, icon_path, label_text, label_text_color):
                slot = lv.obj(self.app_page_list[app_page_num])
                slot.set_size(125, lv.pct(50))
                if len(self.app_page_app_list_list[app_page_num]) == 0:
                    slot.align(lv.ALIGN.TOP_LEFT, 56, 0)
                elif len(self.app_page_app_list_list[app_page_num]) == 4:
                    slot.align(lv.ALIGN.BOTTOM_LEFT, 56, 0)
                else:
                    slot_prev = self.app_page_app_list_list[app_page_num][-1]
                    slot.align_to(slot_prev, lv.ALIGN.OUT_RIGHT_TOP, 10, 0)
                slot.set_style_pad_all(0, 0)
                slot.set_style_border_width(0, 0)
                slot.set_style_radius(0, 0)
                slot.set_style_bg_color(lv.color_hex(0x000000), 0)
                slot.set_style_bg_opa(0, 0)
                slot.clear_flag(lv.obj.FLAG.SCROLLABLE)

                self.app_page_app_list_list[app_page_num].append(slot)

                self.app_manager.add_icon(slot, label_text, label_text_color, icon_path)

        class Wallpaper():
            def __init__(self, screen, path):
                with open(path, 'rb') as f:
                    wallpaper_data = f.read()
                wallpaper_dsc = lv.img_dsc_t({
                    'data_size': len(wallpaper_data),
                    'data': wallpaper_data
                })
                wallpaper = lv.img(screen)
                wallpaper.set_src(wallpaper_dsc)
                wallpaper.center()
                wallpaper.move_background()

        def __init__(self, screen, hw_resources_dict):
            self.conv = lv.obj(screen)
            self.conv.set_size(lv.pct(100), lv.pct(100))
            self.conv.center()
            self.conv.set_style_pad_all(0, 0)
            self.conv.set_style_border_width(0, 0)
            self.conv.set_style_radius(0, 0)
            self.conv.set_style_bg_color(lv.color_hex(0xFFFFFF), 0)
            self.conv.set_style_bg_grad_color(lv.color_hex(0x000000), 0)
            self.conv.set_style_bg_grad_dir(lv.GRAD_DIR.VER, 0)
            self.conv.clear_flag(lv.obj.FLAG.SCROLLABLE)

            self.status_bar = self.StatusBar(screen)
            self.app_manager = self.AppManager(self.conv, self.status_bar, hw_resources_dict)
            self.app_conv = self.AppConv(self.conv, self.app_manager)
            self.dock = self.Dock(self.conv, self.app_manager)
#            self.wallpaper = self.Wallpaper(self.conv, RESOURCES_PATH + "Wallpapers/home_screen_wallpaper.png")

    def __init__(self, hw_resources_dict):
        self.hw_resources_dict = hw_resources_dict

        scr = lv.scr_act()
        scr.set_style_bg_color(lv.color_hex(0x000000), 0)

        self.screen = lv.obj(scr)
        self.screen.set_size(lv.pct(100), lv.pct(100))
        self.screen.center()
        self.screen.set_style_pad_all(0, 0)
        self.screen.set_style_border_width(-1, 0)
        self.screen.set_style_radius(20, 0)
        self.screen.set_style_clip_corner(True, 0)
        self.screen.set_style_bg_color(lv.color_hex(0x000000), 0)
        self.screen.clear_flag(lv.obj.FLAG.SCROLLABLE)

        self.home_screen = self.HomeScreen(self.screen, self.hw_resources_dict)
        self.lock_screen = self.LockScreen(self.screen)

        self.update_time()

        self.clock_updater = lv.timer_create(self.clock_updater_cb, 1000, None)

#        self.lock_screen.hide()
#        area = lv.area_t()
#        area.x1, area.y1, area.x2, area.y2 = 1, 1, 101, 101
#        self.home_screen.app_manager.app_loader.load_app(self.home_screen.app_manager.app_dict.get("Freeform"), area)

    def clock_updater_cb(self, timer):
        self.update_time()

    def update_time(self):
        time = self.hw_resources_dict.get("ClockManager").get_time()
        hour = time[4]
        minute = time[5]
        self.lock_screen.clock_time.set_time(hour, minute)
        self.home_screen.status_bar.clock_time.set_time(hour, minute)

    def lock(self):
        self.lock_screen.show()

def main():
    os.exitpoint(os.EXITPOINT_ENABLE)
    try:
        fpioa = FPIOA()
        lcd = LCD(640, 480, True, fpioa, 5, 1)
        touch = Touch()
        lvgl_init(lcd, touch)
        ledr = LED(fpioa, 61, 0, 1)
        ledb = LED(fpioa, 59, 0, 5)
        button0 = Button(fpioa, 34, 0)
        button1 = Button(fpioa, 35, 0)
        button2 = Button(fpioa, 0, 1)
        buzzer = Buzzer(fpioa, 60, 0, 0)
        clock_manager = ClockManager(2024, 12, 12, 8, 0, 0, 0)
        hw_resources_dict = {
            "LCD": lcd,
            "LEDR": ledr,
            "LEDB": ledb,
            "Button0": button0,
            "Button1": button1,
            "Button2": button2,
            "Buzzer": buzzer,
            "ClockManager": clock_manager,
            "ClockManager": clock_manager,
        }
        gui = GUI(hw_resources_dict)

        gui.home_screen.dock.add_app(RESOURCES_PATH + "APP/icons/app_icon_90x90_settings.png", "Settings", lv.color_hex(0xFFFFFF))
        gui.home_screen.dock.add_app(RESOURCES_PATH + "APP/icons/app_icon_90x90_clock.png", "Clock", lv.color_hex(0xFFFFFF))
        gui.home_screen.dock.add_app(RESOURCES_PATH + "APP/icons/app_icon_90x90_calculator.png", "Calculator", lv.color_hex(0xFFFFFF))
        gui.home_screen.dock.add_app(RESOURCES_PATH + "APP/icons/app_icon_90x90_intelligence.png", "AI Hub", lv.color_hex(0xFFFFFF))

        gui.home_screen.app_conv.add_page()
        gui.home_screen.app_conv.add_page()

        gui.home_screen.app_conv.add_app(0, RESOURCES_PATH + "APP/icons/app_icon_90x90_photos.png", "Photos", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(0, RESOURCES_PATH + "APP/icons/app_icon_90x90_freeform.png", "Freeform", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(0, RESOURCES_PATH + "APP/icons/app_icon_90x90_test_flight.png", "Tester", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(0, RESOURCES_PATH + "APP/icons/app_icon_90x90_template.png", "Template", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_books.png", "Books", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_files.png", "Files", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_calendar.png", "Calendar", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_health.png", "Health", lv.color_hex(0x000000))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_home.png", "Home", lv.color_hex(0xFFFFFF))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_music.png", "Music", lv.color_hex(0xFFFFFF))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_notes.png", "Notes", lv.color_hex(0xFFFFFF))
        gui.home_screen.app_conv.add_app(1, RESOURCES_PATH + "APP/icons/app_icon_90x90_weather.png", "Weather", lv.color_hex(0xFFFFFF))

        while True:
            lv.task_handler()
            gc.collect()
            if button0.is_pressing():
                gui.lock()
    except BaseException as e:
        import sys
        sys.print_exception(e)

    lvgl_deinit(lcd, touch)
    del clock_manager
    del lcd
    del touch

    gc.collect()

if __name__ == "__main__":
    main()
