# ui/dialogs.py
import os
import sys
import cv2 # 保留用于 PreviewDialog
import numpy as np # 保留用于 PreviewDialog
import logging
import time # 需要 time.sleep
# --- 导入必要的 PyQt5 控件 ---
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QLineEdit, QMessageBox, QTextBrowser, QDialogButtonBox,
                             QFileDialog, QSizePolicy, QSlider, QStyle,
                             QGroupBox, QGridLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QWidget, QFrame) # QWidget/QFrame 用于VLC显示
from PyQt5.QtGui import QImage, QPixmap, QPainter, QColor, QPen, QIcon
from PyQt5.QtCore import Qt, QSize, QUrl, QTimer

# 导入 vlc (如果未安装或找不到会报错，添加错误处理)
try:
    import vlc
    VLC_AVAILABLE = True
except ImportError:
    vlc = None
    VLC_AVAILABLE = False
    logging.error("DEPENDENCY ERROR: python-vlc library not found. Please install it (`pip install python-vlc`).")
except Exception as e: # 捕捉其他可能的导入错误 (例如找不到libvlc)
    vlc = None
    VLC_AVAILABLE = False
    logging.error(f"Error importing vlc module: {e}. VLC features disabled.")
# ---

from utils.settings import Settings # Absolute import
from utils.constants import DEFAULT_FRAME_FOR_PREVIEW # Absolute import

# 帮助函数：用于查找打包后的资源路径 (也需要放在 main_window.py 或 helpers.py 中以便共用)
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    return os.path.join(base_path, relative_path)


class SettingsDialog(QDialog):
    """Dialog for configuring application default settings."""
    def __init__(self, settings: Settings, parent=None):
        super().__init__(parent)
        self.settings = settings
        self.setWindowTitle("默认设置")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Frame Diff Params
        fd_group = QGroupBox(f"帧差法默认参数")
        fd_layout = QGridLayout(fd_group)
        self.f_diff_threshold_spin = QSpinBox()
        self.f_diff_threshold_spin.setRange(0, 100)
        self.f_diff_threshold_spin.setValue(settings.get("f_diff_threshold"))
        fd_layout.addWidget(QLabel("阈值:"), 0, 0)
        fd_layout.addWidget(self.f_diff_threshold_spin, 0, 1)

        self.f_diff_min_area_spin = QSpinBox()
        self.f_diff_min_area_spin.setRange(0, 10000)
        self.f_diff_min_area_spin.setValue(settings.get("f_diff_min_area"))
        fd_layout.addWidget(QLabel("最小区域:"), 1, 0)
        fd_layout.addWidget(self.f_diff_min_area_spin, 1, 1)

        self.f_diff_blur_spin = QSpinBox()
        self.f_diff_blur_spin.setRange(1, 51)
        self.f_diff_blur_spin.setSingleStep(2)
        self.f_diff_blur_spin.setValue(settings.get("f_diff_blur_size"))
        fd_layout.addWidget(QLabel("模糊 (奇数):"), 2, 0)
        fd_layout.addWidget(self.f_diff_blur_spin, 2, 1)
        layout.addWidget(fd_group)

        # SSIM Params
        ssim_group = QGroupBox(f"SSIM法默认参数")
        ssim_layout = QGridLayout(ssim_group)
        self.ssim_thresh_spin = QDoubleSpinBox()
        self.ssim_thresh_spin.setRange(0.9, 0.9999)
        self.ssim_thresh_spin.setDecimals(4)
        self.ssim_thresh_spin.setSingleStep(0.001)
        self.ssim_thresh_spin.setValue(settings.get("ssim_threshold"))
        ssim_layout.addWidget(QLabel("相似度阈值 (<):"), 0, 0)
        ssim_layout.addWidget(self.ssim_thresh_spin, 0, 1)

        self.ssim_blur_spin = QSpinBox()
        self.ssim_blur_spin.setRange(1, 51)
        self.ssim_blur_spin.setSingleStep(2)
        self.ssim_blur_spin.setValue(settings.get("ssim_blur_size"))
        ssim_layout.addWidget(QLabel("模糊 (奇数):"), 1, 0)
        ssim_layout.addWidget(self.ssim_blur_spin, 1, 1)
        layout.addWidget(ssim_group)

        # Optical Flow Params
        flow_group = QGroupBox(f"光流法默认参数")
        flow_layout = QGridLayout(flow_group)
        self.flow_thresh_spin = QDoubleSpinBox()
        self.flow_thresh_spin.setRange(0.1, 10.0)
        self.flow_thresh_spin.setDecimals(2)
        self.flow_thresh_spin.setSingleStep(0.1)
        self.flow_thresh_spin.setValue(settings.get("flow_threshold"))
        flow_layout.addWidget(QLabel("运动阈值 (>):"), 0, 0)
        flow_layout.addWidget(self.flow_thresh_spin, 0, 1)

        self.flow_blur_spin = QSpinBox()
        self.flow_blur_spin.setRange(1, 51)
        self.flow_blur_spin.setSingleStep(2)
        self.flow_blur_spin.setValue(settings.get("flow_blur_size"))
        flow_layout.addWidget(QLabel("模糊 (奇数):"), 1, 0)
        flow_layout.addWidget(self.flow_blur_spin, 1, 1)
        layout.addWidget(flow_group)

        # General setting
        self.reverse_video_check = QCheckBox("默认倒放视频 (Reverse Video)")
        self.reverse_video_check.setChecked(settings.get("reverse_video"))
        layout.addWidget(self.reverse_video_check)

        # Standard buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


    def accept(self):
        """Saves the settings when OK is clicked."""
        def make_odd_and_clamp(value, min_val=1, max_val=51):
             try: value = int(value)
             except (ValueError, TypeError): value = min_val
             min_val=int(min_val); max_val=int(max_val)
             if value % 2 == 0:
                 if value + 1 <= max_val: value += 1
                 elif value - 1 >= min_val: value -= 1
                 else: value = min_val
             return max(min_val, min(max_val, value))

        self.settings.set("f_diff_threshold", self.f_diff_threshold_spin.value())
        self.settings.set("f_diff_min_area", self.f_diff_min_area_spin.value())
        self.settings.set("f_diff_blur_size", make_odd_and_clamp(self.f_diff_blur_spin.value()))
        self.settings.set("ssim_threshold", self.ssim_thresh_spin.value())
        self.settings.set("ssim_blur_size", make_odd_and_clamp(self.ssim_blur_spin.value()))
        self.settings.set("flow_threshold", self.flow_thresh_spin.value())
        self.settings.set("flow_blur_size", make_odd_and_clamp(self.flow_blur_spin.value()))
        self.settings.set("reverse_video", self.reverse_video_check.isChecked())
        logging.info("Default settings updated.")
        super().accept()

    def reject(self):
        logging.debug("Settings dialog cancelled.")
        super().reject()


class HelpDialog(QDialog):
    """Simple dialog to display HTML help content."""
    def __init__(self, title, content, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)
        text_browser = QTextBrowser()
        text_browser.setHtml(content)
        text_browser.setOpenExternalLinks(True)
        layout.addWidget(text_browser)
        button_box = QDialogButtonBox(QDialogButtonBox.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


class PreviewDialog(QDialog):
    """Dialog to show parameter preview on sample frames (currently FrameDiff only)."""
    def __init__(self, video_path, threshold, min_area, blur_size, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.threshold = threshold
        self.min_area = min_area
        self.blur_size = blur_size if blur_size % 2 == 1 else blur_size + 1
        self.frame_index = DEFAULT_FRAME_FOR_PREVIEW
        self.setWindowTitle(f"参数预览 [帧差法] (帧 {self.frame_index} vs {self.frame_index+1})")
        self.setMinimumSize(800, 500)
        self.layout = QVBoxLayout(self)
        self.image_layout = QHBoxLayout()
        self.frame1_label = QLabel("加载中...")
        self.frame1_label.setAlignment(Qt.AlignCenter); self.frame1_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.diff_label = QLabel("加载中...")
        self.diff_label.setAlignment(Qt.AlignCenter); self.diff_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.image_layout.addWidget(self.frame1_label); self.image_layout.addWidget(self.diff_label)
        self.layout.addLayout(self.image_layout)
        self.info_label = QLabel("处理中...")
        self.info_label.setAlignment(Qt.AlignCenter); self.layout.addWidget(self.info_label)
        button_box = QDialogButtonBox(QDialogButtonBox.Close); button_box.rejected.connect(self.reject)
        self.layout.addWidget(button_box)
        self.generate_preview()

    def generate_preview(self):
        cap = cv2.VideoCapture(self.video_path); ok = cap.isOpened()
        if not ok: self.info_label.setText(f"<font color='red'>错误: 无法打开视频文件</font>"); return
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); max_index = total_frames - 2
        if max_index < 0 : self.info_label.setText(f"<font color='red'>错误: 视频帧数不足无法预览</font>"); cap.release(); return
        if self.frame_index > max_index: self.frame_index = max_index; self.info_label.setText(f"<font color='orange'>警告: 预览帧索引调整为 {self.frame_index}.</font>")
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_index); ret1, frame1 = cap.read(); ret2, frame2 = cap.read(); cap.release()
        if not ret1 or not ret2: self.info_label.setText(f"<font color='red'>错误: 无法读取预览帧</font>"); return
        try:
            prev_frame_gray = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY); prev_frame_gray = cv2.GaussianBlur(prev_frame_gray, (self.blur_size, self.blur_size), 0)
            current_frame_gray = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY); current_frame_gray = cv2.GaussianBlur(current_frame_gray, (self.blur_size, self.blur_size), 0)
            diff = cv2.absdiff(current_frame_gray, prev_frame_gray); _, thresh_img = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
            contours, _ = cv2.findContours(thresh_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            significant_change_found = any(cv2.contourArea(c) > self.min_area for c in contours)
            frame2_with_contours = frame2.copy(); cv2.drawContours(frame2_with_contours, [c for c in contours if cv2.contourArea(c) > self.min_area], -1, (0, 0, 255), 2)
            pixmap1 = self.convert_cv_qt(frame2_with_contours, self.frame1_label.size())
            pixmap_diff = self.convert_cv_qt(cv2.cvtColor(thresh_img, cv2.COLOR_GRAY2BGR), self.diff_label.size())
            self.frame1_label.setPixmap(pixmap1); self.frame1_label.setToolTip("Frame N+1 with significant contours (if any) in red")
            self.diff_label.setPixmap(pixmap_diff); self.diff_label.setToolTip(f"Thresholded difference (Threshold={self.threshold})")
            status_color = "green" if significant_change_found else "orange"; status_text = "保留 (KEEP)" if significant_change_found else "丢弃 (DISCARD)"
            self.info_label.setText(f"[帧差法] 参数: 阈值={self.threshold}, 最小区域={self.min_area}, 模糊={self.blur_size}<br>帧 {self.frame_index+1} vs {self.frame_index}: <font color='{status_color}'><b>{status_text}</b></font>")
        except Exception as e: self.info_label.setText(f"<font color='red'>预览处理错误: {e}</font>")

    def convert_cv_qt(self, cv_img, target_size: QSize):
        if cv_img is None or target_size.width() <= 0 or target_size.height() <= 0: return QPixmap()
        if len(cv_img.shape) == 2: cv_img = cv2.cvtColor(cv_img, cv2.COLOR_GRAY2BGR)
        try:
            rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB); h, w, ch = rgb_image.shape; bytes_per_line = ch * w
            convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(convert_to_Qt_format); return pixmap.scaled(target_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        except Exception as e: logging.error(f"Error converting CV image to QPixmap: {e}"); return QPixmap()


class PreviewContrastDialog(QDialog):
    """Dialog to play original and processed videos side-by-side using VLC."""
    def __init__(self, original_path, processed_path, parent=None):
        super().__init__(parent)
        self.original_path = original_path
        self.processed_path = processed_path
        self.is_playing = False
        self.vlc_instance = None
        self.player1 = None
        self.player2 = None
        self._position_update_timer = QTimer(self)
        self._slider_pressed = False
        self._error_occurred = False
        self._media_loaded = False

        if not VLC_AVAILABLE:
             self._error_occurred = True
             QMessageBox.critical(self, "错误", "缺少 'python-vlc' 库。\n无法使用 VLC 预览功能。\n请安装： pip install python-vlc")
             QTimer.singleShot(0, self.reject); return

        self.setWindowTitle("预览对比 (VLC)"); self.setMinimumSize(1000, 600)

        # --- UI Setup ---
        main_layout = QVBoxLayout(self); video_layout = QHBoxLayout()
        self.video_frame1 = QFrame(); self.video_frame1.setFrameShape(QFrame.Box); self.video_frame1.setStyleSheet("background-color: black;"); self.video_frame1.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_frame2 = QFrame(); self.video_frame2.setFrameShape(QFrame.Box); self.video_frame2.setStyleSheet("background-color: black;"); self.video_frame2.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        video_layout.addWidget(self.video_frame1); video_layout.addWidget(self.video_frame2); main_layout.addLayout(video_layout, 1)
        label_layout = QHBoxLayout()
        self.label1 = QLabel(f"原始视频: {os.path.basename(original_path)}"); self.label1.setAlignment(Qt.AlignCenter)
        self.label2 = QLabel(f"处理后视频: {os.path.basename(processed_path)}"); self.label2.setAlignment(Qt.AlignCenter)
        label_layout.addWidget(self.label1); label_layout.addWidget(self.label2); main_layout.addLayout(label_layout)
        controls_layout = QHBoxLayout()
        self.play_pause_button = QPushButton(); self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay)); self.play_pause_button.clicked.connect(self.toggle_play_pause)
        controls_layout.addWidget(self.play_pause_button)
        self.position_slider = QSlider(Qt.Horizontal); self.position_slider.setRange(0, 1000); self.position_slider.sliderPressed.connect(self.slider_pressed); self.position_slider.sliderReleased.connect(self.slider_released_and_seek)
        controls_layout.addWidget(self.position_slider)
        self.time_label = QLabel("00:00 / 00:00"); self.time_label.setFixedWidth(100)
        controls_layout.addWidget(self.time_label); main_layout.addLayout(controls_layout)

        # --- VLC Player Setup ---
        try:
            vlc_dir = resource_path("vlc_dependencies"); plugin_path = os.path.join(vlc_dir, 'plugins')
            if os.path.isdir(vlc_dir):
                logging.info(f"Found vlc_dependencies directory: {vlc_dir}")
                if os.path.isdir(plugin_path): os.environ['VLC_PLUGIN_PATH'] = plugin_path; logging.info(f"Set VLC_PLUGIN_PATH to: {plugin_path}")
                else: logging.warning(f"VLC plugins directory not found at: {plugin_path}")
                if sys.platform.startswith('win'):
                    libvlc_dll = os.path.join(vlc_dir, 'libvlc.dll'); libvlccore_dll = os.path.join(vlc_dir, 'libvlccore.dll')
                    if os.path.exists(libvlc_dll) and os.path.exists(libvlccore_dll):
                        logging.debug("Found libvlc.dll and libvlccore.dll.")
                        if hasattr(os, 'add_dll_directory'):
                            try: os.add_dll_directory(vlc_dir); logging.info(f"Added VLC directory to DLL search path: {vlc_dir}")
                            except Exception as e: logging.error(f"Failed to add VLC directory to DLL path: {e}")
            vlc_args = ["--no-video-title-show", "--no-stats"]
            # vlc_args.append("--avcodec-hw=none"); logging.info("Hardware decoding disabled.")
            try: self.vlc_instance = vlc.Instance(vlc_args)
            except NameError: raise RuntimeError("VLC library (python-vlc) not available.")
            except Exception as instance_error: raise instance_error
            if not self.vlc_instance: raise RuntimeError("无法创建 VLC 实例。")
            logging.info("VLC Instance created.")

            self.player1 = self.vlc_instance.media_player_new(); self.player2 = self.vlc_instance.media_player_new()
            if not self.player1 or not self.player2: raise RuntimeError("无法创建 VLC MediaPlayer 实例")
            logging.info("VLC MediaPlayers created.")

            media1_ok = self.load_vlc_media(self.player1, self.original_path)
            media2_ok = self.load_vlc_media(self.player2, self.processed_path)

            if not media1_ok or not media2_ok:
                 self._error_occurred = True; self.play_pause_button.setEnabled(False); self.position_slider.setEnabled(False)
                 logging.error("Failed to load one or both media files into VLC.")
                 if self.vlc_instance: QMessageBox.warning(self, "加载错误", "无法加载一个或两个视频文件进行预览。")
                 return
            else:
                 self._media_loaded = True
                 try:
                     hwnd1 = int(self.video_frame1.winId()); hwnd2 = int(self.video_frame2.winId())
                     logging.debug(f"Widget HWNDs: Frame1={hwnd1}, Frame2={hwnd2}")
                     if sys.platform.startswith('win'): self.player1.set_hwnd(hwnd1); self.player2.set_hwnd(hwnd2)
                     elif sys.platform.startswith('linux'): self.player1.set_xwindow(hwnd1); self.player2.set_xwindow(hwnd2)
                     elif sys.platform == 'darwin': self.player1.set_nsobject(hwnd1); self.player2.set_nsobject(hwnd2)
                     logging.info("VLC output successfully set to QWidgets.")
                 except Exception as e:
                     logging.exception("Error setting VLC HWND/XWindow/NSObject:"); self._error_occurred = True
                     QMessageBox.critical(self, "嵌入错误", f"无法将VLC视频嵌入窗口: {e}"); return

                 # --- 设置 Timer (间隔改为 50ms) ---
                 self._position_update_timer.setInterval(50)
                 self._position_update_timer.timeout.connect(self.update_ui_from_player)

                 # --- 添加 VLC 错误事件处理 ---
                 self.vlc_event_manager1 = self.player1.event_manager()
                 self.vlc_event_manager2 = self.player2.event_manager()
                 self.vlc_event_manager1.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda event: self.handle_vlc_error(event, 1))
                 self.vlc_event_manager2.event_attach(vlc.EventType.MediaPlayerEncounteredError, lambda event: self.handle_vlc_error(event, 2))
                 logging.debug("Attached VLC error event handlers.")
                 # ---

                 # --- 对话框显示后自动开始播放 ---
                 QTimer.singleShot(200, self.start_playback_if_ready) # 延迟稍长一点确保窗口渲染
                 # ---

        except Exception as e:
            self._error_occurred = True; logging.exception("初始化 VLC 预览时发生严重错误:")
            QMessageBox.critical(self, "VLC 初始化错误", f"无法初始化 VLC 播放器:\n{e}\n\n请检查依赖项和路径。")
            QTimer.singleShot(0, self.reject); return

        logging.info("PreviewContrastDialog initialized successfully with VLC.")

    def load_vlc_media(self, player, file_path):
        """Loads a media file into the VLC player instance."""
        if not player: return False
        try:
            abs_path = os.path.abspath(file_path)
            if not os.path.exists(abs_path): logging.error(f"Media file does not exist: {abs_path}"); return False
            uri = f'file:///{abs_path.replace(os.path.sep, "/")}'
            logging.debug(f"Creating VLC media with URI: {uri}")
            media = self.vlc_instance.media_new(uri)
        except Exception as e:
             logging.error(f"Error creating VLC media URI for {file_path}: {e}"); media = None
        if not media:
             try:
                  logging.warning("Retrying media creation with direct path."); media = self.vlc_instance.media_new(file_path)
             except Exception as e2: logging.error(f"Fallback media creation failed: {e2}"); media = None
        if not media: logging.error(f"VLC failed to create media object for: {file_path}"); return False
        player.set_media(media)
        # --- 解析媒体信息 ---
        # 解析媒体以尝试获取元数据（包括时长），可以异步或同步
        # 同步解析可能会短暂阻塞，但能更快获取信息
        media.parse()
        # 你也可以在这里尝试获取一次时长，但可能仍然是0或-1
        # initial_duration = media.get_duration()
        # logging.debug(f"Initial duration after parse for {file_path}: {initial_duration} ms")
        media.release()
        logging.debug(f"VLC media loaded for player: {file_path}")
        return True

    def start_playback_if_ready(self):
        """Starts playback if no errors occurred during init and media loaded."""
        if not self._error_occurred and self._media_loaded and not self.is_playing:
            logging.debug("Attempting to auto-start playback...")
            # 直接调用 play()
            play1_ok = self.player1.play() == 0
            play2_ok = self.player2.play() == 0
            if play1_ok and play2_ok:
                self.is_playing = True
                self._position_update_timer.start()
                logging.debug("VLC players auto-started.")
            else:
                logging.error("Auto-start playback failed for one or both players.")
            # 无论是否成功，都更新按钮图标
            self.update_play_button_icon()

    def toggle_play_pause(self):
        """Toggles play/pause state for both players using VLC API."""
        if not self.player1 or not self.player2 or self._error_occurred: return

        state1 = self.player1.get_state()

        # 如果当前是播放状态，则暂停
        if state1 == vlc.State.Playing:
            self.player1.set_pause(1) # 1 to pause
            self.player2.set_pause(1)
            self.is_playing = False
            self._position_update_timer.stop()
            logging.debug("VLC players paused.")
        # 如果是其他状态 (Paused, Stopped, Ended)，则尝试播放
        else:
            # --- 修改：处理从 Ended/Stopped 状态重启 ---
            if state1 == vlc.State.Ended or state1 == vlc.State.Stopped:
                logging.debug("Player was stopped or ended. Stopping both and restarting...")
                try: # Stop 可能会在某些状态下失败
                    self.player1.stop()
                    self.player2.stop()
                    # 等待短暂时间让 stop 生效？ (可选)
                    # time.sleep(0.05)
                except Exception as stop_err:
                     logging.warning(f"Error stopping players before restart: {stop_err}")
            # ---
            play1_ok = self.player1.play() == 0
            play2_ok = self.player2.play() == 0
            if not play1_ok or not play2_ok:
                 error_msg = "无法开始播放。"
                 if not play1_ok: error_msg += " (Player 1 失败)"
                 if not play2_ok: error_msg += " (Player 2 失败)"
                 logging.error(error_msg)
                 QMessageBox.warning(self, "播放错误", error_msg)
                 try: self.player1.stop(); self.player2.stop()
                 except Exception: pass
                 self.is_playing = False; self._position_update_timer.stop()
            else:
                 self.is_playing = True
                 self._position_update_timer.start()
                 logging.debug("VLC players playing/resumed.")
        self.update_play_button_icon()

    def update_play_button_icon(self):
        """Changes the play/pause button icon based on player state."""
        if not self.player1 or self._error_occurred:
             self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
             self.play_pause_button.setEnabled(False); return
        if not self._media_loaded:
             self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))
             self.play_pause_button.setEnabled(False); return

        self.play_pause_button.setEnabled(True)
        state = self.player1.get_state()
        if state == vlc.State.Playing:
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPause))
        else: # Paused, Stopped, Ended, Error etc.
            self.play_pause_button.setIcon(self.style().standardIcon(QStyle.SP_MediaPlay))

    def slider_pressed(self):
        if self._error_occurred: return
        self._slider_pressed = True

    def slider_released_and_seek(self):
        """Called when the slider is released by the user."""
        if not self.player1 or not self.player2 or self._error_occurred: return
        slider_value = self.position_slider.value()
        target_position = slider_value / 1000.0

        # --- 修改：处理从 Ended/Stopped 状态 seek ---
        state1 = self.player1.get_state()
        play_after_seek = False
        if state1 == vlc.State.Ended or state1 == vlc.State.Stopped:
             logging.debug("Seeking from Ended/Stopped state. Will play after seek.")
             # 需要在设置位置后调用 play
             play_after_seek = True
             # 也许需要先 stop 一下？VLC 文档不明确，先不加
             # self.player1.stop()
             # self.player2.stop()
        # ---

        if self.player1.is_seekable() and self.player2.is_seekable():
            logging.debug(f"VLC seek triggered by slider release to position: {target_position:.3f}")
            self.player1.set_position(target_position)
            self.player2.set_position(target_position) # Seek both to maintain sync

            # --- 修改：如果需要，在 seek 后播放 ---
            if play_after_seek:
                 # 短暂延迟后播放，确保 set_position 生效
                 QTimer.singleShot(50, self.play_if_needed)
            # ---

            # Update UI shortly after seeking
            QTimer.singleShot(50, self.update_ui_from_player)
        else: logging.warning("One or both players are not seekable.")
        self._slider_pressed = False

    # --- 新增：用于 seek 后播放的辅助方法 ---
    def play_if_needed(self):
        """Plays the media if it's not currently playing (used after seek from stopped/ended)."""
        if not self.player1 or self._error_occurred: return
        state = self.player1.get_state()
        if state != vlc.State.Playing:
             logging.debug("Calling play() after seeking from non-playing state.")
             self.toggle_play_pause() # Use toggle to handle state correctly
    # ---

    def update_ui_from_player(self):
        """Updates the slider and time label based on player1's state (called by timer)."""
        if not self.player1 or self._slider_pressed or self._error_occurred:
            return

        # 更新滑块位置
        if self.player1.is_seekable():
            position = self.player1.get_position() # 0.0 to 1.0
            if 0.0 <= position <= 1.0:
                slider_value = int(position * 1000)
                if self.position_slider.value() != slider_value:
                    # 仅当用户未按下时更新滑块
                    if not self._slider_pressed:
                         self.position_slider.setValue(slider_value)
            else:
                 current_state = self.player1.get_state()
                 if current_state == vlc.State.Ended:
                      if self.position_slider.value() != 1000: self.position_slider.setValue(1000)

        # 更新时间标签
        time_ms = self.player1.get_time()
        duration_ms = self.player1.get_length()
        self.update_time_label(time_ms, duration_ms)

        # 检查播放状态是否改变
        current_state = self.player1.get_state()
        if self.is_playing and current_state not in [vlc.State.Playing, vlc.State.Buffering]:
             logging.debug(f"VLC player 1 state changed to {current_state}. Stopping UI updates.")
             self.is_playing = False
             self.update_play_button_icon() # 更新按钮为 "Play"
             self._position_update_timer.stop()
             if current_state == vlc.State.Ended:
                  self.update_time_label(duration_ms, duration_ms)
                  if self.position_slider.value() != 1000: self.position_slider.setValue(1000)
             elif current_state == vlc.State.Error:
                  self.update_time_label(0, duration_ms)
                  if self.position_slider.value() != 0: self.position_slider.setValue(0)

    def update_time_label(self, position_ms, duration_ms):
        """Updates the time label (e.g., 01:23 / 05:40). Handles negative values."""
        pos_ms = max(0, position_ms)
        dur_ms = max(0, duration_ms)

        pos_seconds = pos_ms // 1000
        pos_str = f"{pos_seconds // 60:02d}:{pos_seconds % 60:02d}"

        if dur_ms > 0:
             dur_seconds = dur_ms // 1000
             dur_str = f"{dur_seconds // 60:02d}:{dur_seconds % 60:02d}"
             # --- 修改：只有在 duration > 0 时才更新总时长部分 ---
             current_text = self.time_label.text()
             new_text = f"{pos_str} / {dur_str}"
             if current_text != new_text: # 避免不必要的更新
                 self.time_label.setText(new_text)
        else:
             # 如果总时长无效，保持显示 "--:--"
             current_text = self.time_label.text().split(" / ")[0]
             if current_text != pos_str: # 只更新当前时间部分
                 self.time_label.setText(f"{pos_str} / --:--")
             # ---

    def handle_vlc_error(self, event, player_id):
        """Callback function for VLC MediaPlayerEncounteredError event."""
        if self._error_occurred: return
        self._error_occurred = True
        logging.error(f"VLC MediaPlayer Error encountered on Player {player_id}!")
        self.is_playing = False
        self._position_update_timer.stop()
        self.update_play_button_icon() # 会禁用按钮
        self.position_slider.setEnabled(False)
        QMessageBox.warning(self, "VLC 播放错误", f"播放器 {player_id} 遇到错误。\n播放可能已停止或出现问题。")

    def closeEvent(self, event):
        """Stop players, detach events, and release resources when dialog closes."""
        logging.debug("Closing PreviewContrastDialog with VLC.")
        self._position_update_timer.stop()
        if hasattr(self, 'vlc_event_manager1') and self.vlc_event_manager1:
             try: self.vlc_event_manager1.event_detach(vlc.EventType.MediaPlayerEncounteredError)
             except Exception as e: logging.error(f"Error detaching event manager 1: {e}")
        if hasattr(self, 'vlc_event_manager2') and self.vlc_event_manager2:
             try: self.vlc_event_manager2.event_detach(vlc.EventType.MediaPlayerEncounteredError)
             except Exception as e: logging.error(f"Error detaching event manager 2: {e}")
        if hasattr(self, 'player1') and self.player1:
            try:
                if self.player1.is_playing(): self.player1.stop()
                self.player1.release(); logging.debug("Player 1 released.")
            except Exception as e: logging.error(f"Error releasing player 1: {e}")
        if hasattr(self, 'player2') and self.player2:
            try:
                if self.player2.is_playing(): self.player2.stop()
                self.player2.release(); logging.debug("Player 2 released.")
            except Exception as e: logging.error(f"Error releasing player 2: {e}")
        if hasattr(self, 'vlc_instance') and self.vlc_instance:
            try:
                self.vlc_instance.release(); logging.debug("VLC instance released.")
            except Exception as e: logging.error(f"Error releasing VLC instance: {e}")
        super().closeEvent(event)