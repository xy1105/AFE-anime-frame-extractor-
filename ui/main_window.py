# ui/main_window.py
import os
import sys
import random
import logging
import subprocess # <--- 新增导入 subprocess
import time       # <--- 新增导入 time
try:
    import pygetwindow as gw # <--- 新增导入 pygetwindow (虽然最终可能不用，先保留)
    PYGETWINDOW_AVAILABLE = True
except ImportError:
    gw = None
    PYGETWINDOW_AVAILABLE = False
    logging.warning("pygetwindow not found. Automatic window arrangement disabled.")

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                             QFileDialog, QSlider, QCheckBox, QGroupBox, QGridLayout,
                             QMessageBox, QDialog, QTextBrowser, QComboBox,
                             QLineEdit, QListWidget, QAbstractItemView, QToolTip,
                             QApplication, QStyle, QSizePolicy, QDoubleSpinBox,
                             QFrame, QSpinBox) # 确保 QSpinBox 在这里
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QRect, QTimer, QSize
from PyQt5.QtGui import QFont, QColor, QPainter, QIcon

# Import refactored components
from ui.widgets import AEStyleSlider, AnimatedProgressBar
# 不再需要从这里导入 PreviewContrastDialog
from ui.dialogs import SettingsDialog, HelpDialog, PreviewDialog #, PreviewContrastDialog
# 导入重写后的 PreviewContrastDialog (确保 dialogs.py 中定义了它)
from ui.dialogs import PreviewContrastDialog as VLCPreviewDialog # 重命名导入以区分

from core.video_processor import VideoProcessor
from core.batch_processor import BatchProcessor
from utils.settings import Settings
from utils.watermark import watermark_protection
# Import constants including presets and algorithms
from utils.constants import (APP_NAME, APP_AUTHOR, PRESETS,
                            ALGO_FRAME_DIFF, ALGO_SSIM, ALGO_OPTICAL_FLOW)

# resource_path function remains the same
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class MainWindow(QWidget):
    """Main application window with enhanced features."""
    def __init__(self, settings: Settings):
        super().__init__()
        self.settings = settings
        self.input_path = None
        self.output_path = None
        self.last_processed_output_path = None # Store path for contrast preview
        self.current_processor = None
        self.initUI()
        self.load_settings_to_ui() # Load saved settings into UI elements
        self.update_parameter_visibility() # Initial UI state based on loaded algo
        self.connect_param_signals() # Connect signals *after* loading defaults

        # Watermark check timer setup
        self.watermark_check_timer = QTimer(self)
        self.watermark_check_timer.timeout.connect(self.check_watermark_integrity)
        self.watermark_check_timer.start(random.randint(15000, 45000))
        logging.info("Main window initialized.")


    def initUI(self):
        """Sets up the main user interface layout and widgets."""
        self.setWindowTitle(f"{APP_NAME} - {APP_AUTHOR}")
        self.setMinimumSize(750, 750) # Increased height for more params
        self.setFont(QFont("Microsoft YaHei", 10))

        main_layout = QVBoxLayout(self)

        # --- File Selection Group ---
        file_group = QGroupBox("文件选择 (File Selection)")
        # --- 添加 objectName ---
        file_group.setObjectName("FileSelectionGroup")
        # --- 修改结束 ---
        file_layout = QGridLayout()
        self.input_label = QLabel('输入视频 (Input): 未选择')
        self.input_label.setWordWrap(True)
        file_layout.addWidget(self.input_label, 0, 0, 1, 3)
        input_button = QPushButton('选择视频 (Select Video)')
        input_button.clicked.connect(self.select_input)
        file_layout.addWidget(input_button, 0, 3)
        settings_button = QPushButton('默认设置 (Defaults)')
        settings_button.setToolTip("配置处理参数的默认值")
        settings_button.clicked.connect(self.open_settings)
        file_layout.addWidget(settings_button, 0, 4)
        self.output_label = QLabel('输出路径 (Output): 未设置')
        self.output_label.setWordWrap(True)
        file_layout.addWidget(self.output_label, 1, 0, 1, 2)
        self.output_mode_combo = QComboBox()
        self.output_mode_combo.addItems(['自动生成文件名 (Auto-generate)', '手动选择路径 (Manual Select)'])
        self.output_mode_combo.currentIndexChanged.connect(self.update_output_state)
        self.output_mode_combo.setToolTip("选择输出文件是自动命名还是手动指定")
        file_layout.addWidget(self.output_mode_combo, 1, 2)
        self.output_button = QPushButton('选择路径 (Select Path)')
        self.output_button.clicked.connect(self.select_output)
        self.output_button.setEnabled(False)
        file_layout.addWidget(self.output_button, 1, 3, 1, 2)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)


        # --- Parameter Settings Group ---
        param_group = QGroupBox("参数设置 (Parameters)")
        # --- 添加 objectName ---
        param_group.setObjectName("ParameterSettingsGroup") # 使用英文或简单的标识符
        # --- 修改结束 ---
        param_layout = QGridLayout()
        param_group.setLayout(param_layout) # Set layout early

        # Row 0: Algorithm Selection and Presets
        param_layout.addWidget(QLabel("算法 (Algorithm):"), 0, 0)
        self.algo_combo = QComboBox()
        self.algo_combo.addItems([ALGO_FRAME_DIFF, ALGO_SSIM, ALGO_OPTICAL_FLOW])
        self.algo_combo.setToolTip("选择用于比较帧的算法")
        param_layout.addWidget(self.algo_combo, 0, 1, 1, 2) # Span 2 columns

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("选择预设...") # Placeholder item
        self.preset_combo.addItems(PRESETS.keys())
        self.preset_combo.setToolTip("加载预定义的参数组合")
        self.preset_combo.activated[str].connect(self.apply_preset) # Use activated for selection
        param_layout.addWidget(self.preset_combo, 0, 3, 1, 2) # Span 2 columns

        # Row 1: Separator
        line1 = QFrame()
        line1.setFrameShape(QFrame.HLine)
        line1.setFrameShadow(QFrame.Sunken)
        param_layout.addWidget(line1, 1, 0, 1, 5)

        # Row 2-4: Frame Difference Parameters (Initially Visible)
        self.f_diff_threshold_label = QLabel('帧差-阈值:')
        self.f_diff_threshold_slider, self.f_diff_threshold_edit = self.create_parameter_controls(
             0, 100, self.settings.get("f_diff_threshold"), step=1
        )
        self.f_diff_threshold_help = self.create_help_button(self.show_threshold_help)
        param_layout.addWidget(self.f_diff_threshold_label, 2, 0)
        param_layout.addWidget(self.f_diff_threshold_slider, 2, 1)
        param_layout.addWidget(self.f_diff_threshold_edit, 2, 2)
        param_layout.addWidget(self.f_diff_threshold_help, 2, 3)

        self.f_diff_min_area_label = QLabel('帧差-最小区域:')
        self.f_diff_min_area_slider, self.f_diff_min_area_edit = self.create_parameter_controls(
             0, 10000, self.settings.get("f_diff_min_area"), step=50
        )
        self.f_diff_min_area_help = self.create_help_button(self.show_min_area_help)
        param_layout.addWidget(self.f_diff_min_area_label, 3, 0)
        param_layout.addWidget(self.f_diff_min_area_slider, 3, 1)
        param_layout.addWidget(self.f_diff_min_area_edit, 3, 2)
        param_layout.addWidget(self.f_diff_min_area_help, 3, 3)

        self.f_diff_blur_label = QLabel('帧差-模糊 (奇数):')
        self.f_diff_blur_slider, self.f_diff_blur_edit = self.create_parameter_controls(
             1, 51, self.settings.get("f_diff_blur_size"), step=2
        )
        self.f_diff_blur_help = self.create_help_button(self.show_blur_help)
        param_layout.addWidget(self.f_diff_blur_label, 4, 0)
        param_layout.addWidget(self.f_diff_blur_slider, 4, 1)
        param_layout.addWidget(self.f_diff_blur_edit, 4, 2)
        param_layout.addWidget(self.f_diff_blur_help, 4, 3)


        # Row 5-6: SSIM Parameters (Initially Hidden)
        self.ssim_threshold_label = QLabel('SSIM-相似阈值 (<):')
        # SSIM Threshold uses QDoubleSpinBox for precision
        self.ssim_threshold_spin = QDoubleSpinBox(self)
        self.ssim_threshold_spin.setRange(0.90, 0.9999)
        self.ssim_threshold_spin.setDecimals(4)
        self.ssim_threshold_spin.setSingleStep(0.001)
        self.ssim_threshold_spin.setValue(self.settings.get("ssim_threshold"))
        self.ssim_threshold_spin.setToolTip("值越低，允许的差异越大 (保留帧越少)")
        self.ssim_threshold_help = self.create_help_button(self.show_ssim_threshold_help)
        param_layout.addWidget(self.ssim_threshold_label, 5, 0)
        param_layout.addWidget(self.ssim_threshold_spin, 5, 1, 1, 2) # Span 2
        param_layout.addWidget(self.ssim_threshold_help, 5, 3)


        self.ssim_blur_label = QLabel('SSIM-模糊 (奇数):')
        self.ssim_blur_slider, self.ssim_blur_edit = self.create_parameter_controls(
             1, 51, self.settings.get("ssim_blur_size"), step=2
        )
        self.ssim_blur_help = self.create_help_button(self.show_blur_help) # Reuse blur help
        param_layout.addWidget(self.ssim_blur_label, 6, 0)
        param_layout.addWidget(self.ssim_blur_slider, 6, 1)
        param_layout.addWidget(self.ssim_blur_edit, 6, 2)
        param_layout.addWidget(self.ssim_blur_help, 6, 3)


        # Row 7-8: Optical Flow Parameters (Initially Hidden)
        self.flow_sensitivity_label = QLabel('光流-运动阈值 (>):')
        # Flow sensitivity uses QDoubleSpinBox
        self.flow_threshold_spin = QDoubleSpinBox(self)
        self.flow_threshold_spin.setRange(0.1, 10.0) # Lower value = more sensitive = keeps more
        self.flow_threshold_spin.setDecimals(2)
        self.flow_threshold_spin.setSingleStep(0.1)
        self.flow_threshold_spin.setValue(self.settings.get("flow_threshold"))
        self.flow_threshold_spin.setToolTip("平均运动幅度需大于此值才保留帧 (值越小越容易保留)")
        self.flow_sensitivity_help = self.create_help_button(self.show_flow_sensitivity_help)
        param_layout.addWidget(self.flow_sensitivity_label, 7, 0)
        param_layout.addWidget(self.flow_threshold_spin, 7, 1, 1, 2) # Span 2
        param_layout.addWidget(self.flow_sensitivity_help, 7, 3)


        self.flow_blur_label = QLabel('光流-模糊 (奇数):')
        self.flow_blur_slider, self.flow_blur_edit = self.create_parameter_controls(
             1, 51, self.settings.get("flow_blur_size"), step=2
        )
        self.flow_blur_help = self.create_help_button(self.show_blur_help) # Reuse blur help
        param_layout.addWidget(self.flow_blur_label, 8, 0)
        param_layout.addWidget(self.flow_blur_slider, 8, 1)
        param_layout.addWidget(self.flow_blur_edit, 8, 2)
        param_layout.addWidget(self.flow_blur_help, 8, 3)


        # Row 9: Separator
        line2 = QFrame()
        line2.setFrameShape(QFrame.HLine)
        line2.setFrameShadow(QFrame.Sunken)
        param_layout.addWidget(line2, 9, 0, 1, 5)

        # Row 10: Common Options (Preview and Reverse)
        self.preview_button = QPushButton("参数效果预览 (Preview Effect)")
        self.preview_button.setToolTip("在示例帧上预览当前选中算法的效果\n(注意: 当前仅帧差法预览有效)")
        self.preview_button.clicked.connect(self.show_parameter_preview) # Renamed handler
        param_layout.addWidget(self.preview_button, 10, 0, 1, 2)

        self.reverse_video_check = QCheckBox('倒放视频 (Reverse Video)')
        self.reverse_video_check.setChecked(self.settings.get("reverse_video"))
        self.reverse_video_check.setToolTip("处理后是否将帧顺序倒放")
        param_layout.addWidget(self.reverse_video_check, 10, 2, 1, 3)


        main_layout.addWidget(param_group)

        # --- Batch Processing Group ---
        batch_group = QGroupBox("批量处理 (Batch Processing)")
        # --- 添加 objectName ---
        batch_group.setObjectName("BatchProcessingGroup")
        # --- 修改结束 ---
        batch_layout = QVBoxLayout()
        self.video_list_widget = QListWidget()
        self.video_list_widget.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.video_list_widget.setToolTip("要进行批量处理的视频文件列表")
        # Allow dropping files onto the list widget
        self.video_list_widget.setAcceptDrops(True)
        self.video_list_widget.dragEnterEvent = self.list_dragEnterEvent
        self.video_list_widget.dragMoveEvent = self.list_dragMoveEvent
        self.video_list_widget.dropEvent = self.list_dropEvent
        batch_layout.addWidget(self.video_list_widget)
        batch_buttons_layout = QHBoxLayout()
        add_videos_button = QPushButton("添加视频 (Add)")
        add_videos_button.clicked.connect(self.add_videos)
        batch_buttons_layout.addWidget(add_videos_button)
        remove_videos_button = QPushButton("移除选中 (Remove Selected)")
        remove_videos_button.clicked.connect(self.remove_videos)
        batch_buttons_layout.addWidget(remove_videos_button)
        clear_videos_button = QPushButton("清空列表 (Clear All)")
        clear_videos_button.clicked.connect(self.clear_videos)
        batch_buttons_layout.addWidget(clear_videos_button)
        batch_layout.addLayout(batch_buttons_layout)
        batch_group.setLayout(batch_layout)
        main_layout.addWidget(batch_group)

        # --- Processing & Progress Group ---
        process_group = QGroupBox("处理与进度 (Process & Progress)")
        # --- 添加 objectName ---
        process_group.setObjectName("ProcessProgressGroup")
        # --- 修改结束 ---
        process_layout = QVBoxLayout()

        process_buttons_layout = QHBoxLayout()
        self.process_button = QPushButton('处理当前视频') # Text shortened
        self.process_button.setStyleSheet("QPushButton { padding: 8px; }")
        self.process_button.clicked.connect(self.process_single_video)
        self.process_button.setToolTip("处理上面选定的单个输入视频")
        process_buttons_layout.addWidget(self.process_button)

        self.process_button = QPushButton('处理当前视频')
        self.process_button.setStyleSheet("QPushButton { padding: 8px; }")
        self.process_button.clicked.connect(self.process_single_video)
        self.process_button.setToolTip("处理上面选定的单个输入视频")
        process_buttons_layout.addWidget(self.process_button)

        self.batch_process_button = QPushButton('处理列表视频')
        self.batch_process_button.setStyleSheet("QPushButton { padding: 8px; }")
        self.batch_process_button.clicked.connect(self.process_batch_videos)
        self.batch_process_button.setToolTip("处理下面列表中的所有视频")
        process_buttons_layout.addWidget(self.batch_process_button)

        # --- 修改对比预览按钮设置 ---
        self.contrast_preview_button = QPushButton("对比预览 (VLC)") # 更新按钮文本
        self.contrast_preview_button.setStyleSheet("QPushButton { padding: 8px; }")
        self.contrast_preview_button.setToolTip("使用内置VLC引擎并排播放原视频和处理后视频") # 更新 Tooltip
        self.contrast_preview_button.clicked.connect(self.show_contrast_preview) # <--- 连接到 show_contrast_preview
        self.contrast_preview_button.setEnabled(False)
        process_buttons_layout.addWidget(self.contrast_preview_button)


        self.cancel_button = QPushButton('取消处理') # Text shortened
        self.cancel_button.setStyleSheet("QPushButton { padding: 8px; background-color: #f44336; color: white;}")
        self.cancel_button.clicked.connect(self.cancel_processing)
        self.cancel_button.setToolTip("停止当前正在进行的处理")
        self.cancel_button.setEnabled(False)
        process_buttons_layout.addWidget(self.cancel_button)

        process_layout.addLayout(process_buttons_layout)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("等待中...")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        process_layout.addWidget(self.progress_bar)

        self.status_label = QLabel('状态: 空闲') # Text shortened
        self.status_label.setWordWrap(True)
        process_layout.addWidget(self.status_label)

        self.tw_speed_label = QLabel('')
        self.tw_speed_label.setWordWrap(True)
        process_layout.addWidget(self.tw_speed_label)

        process_group.setLayout(process_layout)
        main_layout.addWidget(process_group)

        # --- Watermark ---
        self.watermark_label = QLabel(watermark_protection.get_watermark(), self)
        self.watermark_label.setStyleSheet("color: rgba(0, 0, 0, 100); font-size: 8pt;")
        self.watermark_label.setAlignment(Qt.AlignRight | Qt.AlignBottom)
        # Positioned using resizeEvent

        self.setLayout(main_layout)
        self.update_button_states()


    # --- Drag and Drop for List Widget ---
    def list_dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            # Check if urls are video files (basic check by extension)
            valid_urls = False
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    _, ext = os.path.splitext(path)
                    if ext.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                         valid_urls = True
                         break
            if valid_urls:
                event.acceptProposedAction()
        else:
            event.ignore()

    def list_dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def list_dropEvent(self, event):
        if event.mimeData().hasUrls():
            files_added = []
            current_items = [self.video_list_widget.item(i).text().split(" (")[0] for i in range(self.video_list_widget.count())]
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    path = url.toLocalFile()
                    _, ext = os.path.splitext(path)
                    if ext.lower() in ['.mp4', '.avi', '.mov', '.mkv']:
                         if path not in current_items and path not in files_added:
                            files_added.append(path)

            if files_added:
                self.video_list_widget.addItems(files_added)
                logging.info(f"Added {len(files_added)} videos via drag & drop.")
                self.update_button_states()
            event.acceptProposedAction()
        else:
            event.ignore()

    # --- Parameter Control Creation Helpers ---
    def create_parameter_controls(self, min_val, max_val, default_val, step=1):
        """Creates a slider and a line edit for a parameter."""
        slider = AEStyleSlider(Qt.Horizontal, self)
        slider.setRange(min_val, max_val)
        slider.setValue(int(default_val)) # Ensure integer for slider
        slider.setSingleStep(step)
        slider.setPageStep(step * 10)
        # slider.setTickPosition(QSlider.TicksBelow) # Ticks can make it look cluttered
        # slider.setTickInterval(max(step, (max_val - min_val) // 10))

        value_edit = QLineEdit(str(int(default_val)))
        value_edit.setFixedWidth(60)

        # Connect signals within this helper (will be overridden later by connect_param_signals if needed)
        slider.valueChanged.connect(lambda v, edit=value_edit: edit.setText(str(v)))
        value_edit.editingFinished.connect(lambda s=slider, edit=value_edit, minv=min_val, maxv=max_val:
                                           self.update_slider_from_edit(s, edit, minv, maxv))

        return slider, value_edit

    def create_help_button(self, help_func):
        """Creates a standard help button."""
        help_button = QPushButton('?')
        help_button.setFixedSize(25, 25)
        help_button.setStyleSheet("""
            QPushButton { font-weight: bold; border-radius: 12px; border: 1px solid #bbb; background-color: #f0f0f0; }
            QPushButton:hover { background-color: #e0e0e0; }
        """)
        help_button.setToolTip("显示此参数的详细说明 (Show help)")
        help_button.clicked.connect(lambda: self.show_help_dialog("参数说明", help_func())) # Use generic title
        # --- Add a flag to identify help buttons ---
        setattr(help_button, '_is_help_button', True)
        # --- Modification End ---
        return help_button


    def connect_param_signals(self):
         """Connect signals for parameter controls after initial loading."""
         # Disconnect any previous connections first to prevent duplicates if called multiple times
         try: self.algo_combo.currentIndexChanged.disconnect()
         except TypeError: pass
         try: self.preset_combo.activated[str].disconnect()
         except TypeError: pass
         # Disconnect sliders/edits/spins... (or be careful only to connect once)

         # Algorithm selection changes visibility
         self.algo_combo.currentIndexChanged.connect(self.update_parameter_visibility)

         # Presets
         self.preset_combo.activated[str].connect(self.apply_preset)

         # Frame Diff Controls
         self.f_diff_threshold_slider.valueChanged.connect(lambda v: self.f_diff_threshold_edit.setText(str(v)))
         self.f_diff_threshold_edit.editingFinished.connect(lambda: self.update_slider_from_edit(self.f_diff_threshold_slider, self.f_diff_threshold_edit, 0, 100))
         self.f_diff_min_area_slider.valueChanged.connect(lambda v: self.f_diff_min_area_edit.setText(str(v)))
         self.f_diff_min_area_edit.editingFinished.connect(lambda: self.update_slider_from_edit(self.f_diff_min_area_slider, self.f_diff_min_area_edit, 0, 10000))
         self.f_diff_blur_slider.valueChanged.connect(lambda v: self.f_diff_blur_edit.setText(str(v)))
         self.f_diff_blur_edit.editingFinished.connect(lambda: self.update_slider_from_edit(self.f_diff_blur_slider, self.f_diff_blur_edit, 1, 51, ensure_odd=True)) # Ensure odd

         # SSIM Controls
         self.ssim_blur_slider.valueChanged.connect(lambda v: self.ssim_blur_edit.setText(str(v)))
         self.ssim_blur_edit.editingFinished.connect(lambda: self.update_slider_from_edit(self.ssim_blur_slider, self.ssim_blur_edit, 1, 51, ensure_odd=True)) # Ensure odd
         # No slider for SSIM threshold, just SpinBox

         # Optical Flow Controls
         self.flow_blur_slider.valueChanged.connect(lambda v: self.flow_blur_edit.setText(str(v)))
         self.flow_blur_edit.editingFinished.connect(lambda: self.update_slider_from_edit(self.flow_blur_slider, self.flow_blur_edit, 1, 51, ensure_odd=True)) # Ensure odd
          # No slider for Flow threshold, just SpinBox


    def update_slider_from_edit(self, slider, edit, min_value, max_value, ensure_odd=False):
        """Updates slider value based on QLineEdit input, validating the range and oddness."""
        try:
            value = int(edit.text())
            if ensure_odd and value % 2 == 0:
                value = max(min_value, min(max_value, value + 1)) # Make odd, clamp
            else:
                value = max(min_value, min(max_value, value)) # Clamp

            if str(value) != edit.text(): # Correct edit if value changed
                edit.setText(str(value))
            slider.setValue(value) # Set potentially corrected value

        except ValueError:
            # If text is not a valid integer, revert edit to slider's current value
            edit.setText(str(slider.value()))


    def update_parameter_visibility(self):
        """Shows/hides parameter controls based on selected algorithm."""
        selected_algo = self.algo_combo.currentText()
        logging.debug(f"Algorithm changed to: {selected_algo}. Updating UI visibility.")

        is_f_diff = (selected_algo == ALGO_FRAME_DIFF)
        is_ssim = (selected_algo == ALGO_SSIM)
        is_flow = (selected_algo == ALGO_OPTICAL_FLOW)

        # Frame Diff Widgets
        self.f_diff_threshold_label.setVisible(is_f_diff)
        self.f_diff_threshold_slider.setVisible(is_f_diff)
        self.f_diff_threshold_edit.setVisible(is_f_diff)
        self.f_diff_threshold_help.setVisible(is_f_diff)
        self.f_diff_min_area_label.setVisible(is_f_diff)
        self.f_diff_min_area_slider.setVisible(is_f_diff)
        self.f_diff_min_area_edit.setVisible(is_f_diff)
        self.f_diff_min_area_help.setVisible(is_f_diff)
        self.f_diff_blur_label.setVisible(is_f_diff)
        self.f_diff_blur_slider.setVisible(is_f_diff)
        self.f_diff_blur_edit.setVisible(is_f_diff)
        self.f_diff_blur_help.setVisible(is_f_diff)

        # SSIM Widgets
        self.ssim_threshold_label.setVisible(is_ssim)
        self.ssim_threshold_spin.setVisible(is_ssim)
        self.ssim_threshold_help.setVisible(is_ssim)
        self.ssim_blur_label.setVisible(is_ssim)
        self.ssim_blur_slider.setVisible(is_ssim)
        self.ssim_blur_edit.setVisible(is_ssim)
        self.ssim_blur_help.setVisible(is_ssim)

        # Optical Flow Widgets
        self.flow_sensitivity_label.setVisible(is_flow)
        self.flow_threshold_spin.setVisible(is_flow)
        self.flow_sensitivity_help.setVisible(is_flow)
        self.flow_blur_label.setVisible(is_flow)
        self.flow_blur_slider.setVisible(is_flow)
        self.flow_blur_edit.setVisible(is_flow)
        self.flow_blur_help.setVisible(is_flow)

        # Adjust window layout (optional, might cause resize jumps)
        # self.adjustSize()


    # --- Presets ---
    def apply_preset(self, preset_name):
        """Applies the selected parameter preset."""
        if preset_name == "选择预设...":
            return # Ignore placeholder

        preset = PRESETS.get(preset_name)
        if not preset:
            logging.warning(f"Preset '{preset_name}' not found.")
            return

        logging.info(f"Applying preset: {preset_name}")

        # 1. Set Algorithm ComboBox
        algo_text = preset.get('algorithm', ALGO_FRAME_DIFF)
        index = self.algo_combo.findText(algo_text)
        if index != -1:
             # Temporarily block signals to prevent recursive updates or visibility flicker
             self.algo_combo.blockSignals(True)
             self.algo_combo.setCurrentIndex(index)
             self.algo_combo.blockSignals(False)
        else:
             logging.warning(f"Preset algorithm '{algo_text}' not found in ComboBox.")
             return # Don't apply if algorithm is invalid

        # 2. Update relevant parameter controls based on the *preset's* algorithm
        if algo_text == ALGO_FRAME_DIFF:
            self.f_diff_threshold_slider.setValue(preset.get('threshold', 15))
            self.f_diff_min_area_slider.setValue(preset.get('min_area', 500))
            self.f_diff_blur_slider.setValue(preset.get('blur_size', 5))
            # Sync edits
            self.f_diff_threshold_edit.setText(str(self.f_diff_threshold_slider.value()))
            self.f_diff_min_area_edit.setText(str(self.f_diff_min_area_slider.value()))
            self.f_diff_blur_edit.setText(str(self.f_diff_blur_slider.value()))
        elif algo_text == ALGO_SSIM:
            self.ssim_threshold_spin.setValue(preset.get('ssim_threshold', 0.98))
            self.ssim_blur_slider.setValue(preset.get('blur_size', 5))
            # Sync edit
            self.ssim_blur_edit.setText(str(self.ssim_blur_slider.value()))
        elif algo_text == ALGO_OPTICAL_FLOW:
             # Presets might use 'flow_sensitivity', map to 'flow_threshold' if needed, or use direct 'flow_threshold' in presets
             flow_thresh_val = preset.get('flow_threshold', preset.get('flow_sensitivity', 1.0)) # Allow either key
             self.flow_threshold_spin.setValue(flow_thresh_val)
             self.flow_blur_slider.setValue(preset.get('blur_size', 7))
             # Sync edit
             self.flow_blur_edit.setText(str(self.flow_blur_slider.value()))

        # 3. Update UI Visibility *after* setting values
        self.update_parameter_visibility()

        # 4. Reset preset combo selection to placeholder
        self.preset_combo.setCurrentIndex(0)

        QMessageBox.information(self, "预设已应用", f"已应用预设: {preset_name}")


    # --- Help Dialog Launchers ---
    def show_help_dialog(self, title, content):
        """Displays the help dialog."""
        dialog = HelpDialog(title, content, self)
        dialog.exec_()

    # Help content for Frame Diff params (threshold, min_area, blur) remain the same
    def show_threshold_help(self):
        return """
        <h3>帧差-阈值 (FrameDiff - Threshold)</h3>
        <p>比较相邻帧时，像素颜色值的最小差异。只有差异大于此值的像素才会被考虑。</p>
        <ul>
            <li>范围: 0 - 100+</li>
            <li><b>较低值:</b> 对微小变化更敏感。</li>
            <li><b>较高值:</b> 只考虑显著的颜色/亮度变化。</li>
        </ul>
        <p><b>建议:</b> 10-30。从15开始调整。</p>
        """

    def show_min_area_help(self):
        return """
        <h3>帧差-最小区域 (FrameDiff - Min Area)</h3>
        <p>变化像素组成的区域（轮廓）的总面积必须大于此值，才认为发生了显著变化。</p>
        <ul>
            <li>范围: 0 - 10000+ (像素)</li>
            <li><b>较小值:</b> 捕捉微小动作（如眨眼）。</li>
            <li><b>较大值:</b> 只关注大范围运动。</li>
        </ul>
        <p><b>建议:</b> 100-2000。从500开始调整。</p>
        """

    def show_blur_help(self):
        return """
        <h3>模糊程度 (Blur Size - odd number)</h3>
        <p>在比较帧之前应用的高斯模糊核大小。有助于减少噪点影响。</p>
        <ul>
            <li>范围: 1 - 51+ (必须是奇数)</li>
            <li><b>较小值 (e.g., 3, 5):</b> 保留更多细节，适用于清晰视频。</li>
            <li><b>较大值 (e.g., 11, 21):</b> 平滑噪点和细微纹理，适用于有噪点视频或忽略精细纹理。值为 1 不模糊。</li>
        </ul>
        <p><b>建议:</b> 5 或 7。根据视频质量调整。</p>
        """

    def show_ssim_threshold_help(self):
         return """
        <h3>SSIM-相似度阈值 (SSIM - Similarity Threshold)</h3>
        <p>结构相似性指数 (SSIM) 用于衡量两帧图像的相似程度 (值范围-1到1，1为完全相同)。</p>
        <p>如果计算出的 SSIM 值 <b>小于</b> 此阈值，则认为两帧差异足够大，<b>保留</b>当前帧。</p>
        <ul>
            <li>范围: 0.9 - 0.9999</li>
            <li><b>较低值 (e.g., 0.95):</b> 允许较大的视觉差异，会丢弃更多看起来“比较像”的帧 (抽帧更狠)。</li>
            <li><b>较高值 (e.g., 0.99):</b> 只允许非常小的视觉差异，会保留更多帧 (抽帧更保守)。</li>
        </ul>
        <p><b>建议:</b> 从 0.98 开始。如果丢帧太多，增加此值；如果保留太多，降低此值。</p>
        """

    def show_flow_sensitivity_help(self):
        return """
        <h3>光流-运动阈值 (Optical Flow - Motion Threshold)</h3>
        <p>计算相邻帧之间像素的平均运动幅度。如果平均运动幅度 <b>大于</b> 此阈值，则认为画面有足够运动，<b>保留</b>当前帧。</p>
        <p>此方法对全局亮度变化不敏感，更能检测实际运动，有助于处理缓慢运镜。</p>
        <ul>
            <li>范围: 0.1 - 10.0+</li>
            <li><b>较低值 (e.g., 0.5):</b> 对微小的平均运动也敏感，会保留更多帧 (更敏感)。</li>
            <li><b>较高值 (e.g., 2.0):</b> 只有较大的平均运动才会保留帧 (更不敏感)。</li>
        </ul>
        <p><b>建议:</b> 从 1.0 开始。如果保留太多运镜或微小抖动，增加此值；如果丢失了需要的慢速运动，降低此值。计算较慢。</p>
        """


    # --- File Handling (select_input, update_output_state, generate_output_path, select_output) ---
    # (No changes needed, use code from previous response)
    def select_input(self):
        """Opens dialog to select input video file."""
        last_dir = self.settings.get("last_input_dir") or os.path.expanduser("~")
        fname, _ = QFileDialog.getOpenFileName(self, '选择输入视频 (Select Input Video)', last_dir, '视频文件 (Video Files) (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)')
        if fname:
            self.input_path = fname
            self.input_label.setText(f'输入 (Input): {os.path.basename(fname)}')
            self.input_label.setToolTip(fname)
            self.settings.set("last_input_dir", os.path.dirname(fname))
            logging.info(f"Input video selected: {fname}")
            if self.output_mode_combo.currentIndex() == 0:
                self.generate_output_path()
            self.update_button_states()
            self.last_processed_output_path = None # Reset processed path on new input
            self.contrast_preview_button.setEnabled(False)

    def update_output_state(self):
        """Enables/disables manual output selection based on combo box."""
        is_manual = (self.output_mode_combo.currentIndex() == 1)
        self.output_button.setEnabled(is_manual)
        if not is_manual and self.input_path:
            self.generate_output_path()
        elif not is_manual:
             self.output_label.setText('输出路径 (Output): 未设置 (自动)')
             self.output_label.setToolTip('')
             self.output_path = None
        self.update_button_states()

    def generate_output_path(self):
        """Generates an output path based on the input path."""
        if not self.input_path: return
        try:
            input_dir = os.path.dirname(self.input_path)
            input_name = os.path.splitext(os.path.basename(self.input_path))[0]
            algo_suffix = {ALGO_FRAME_DIFF: "fd", ALGO_SSIM: "ssim", ALGO_OPTICAL_FLOW: "flow"}.get(self.algo_combo.currentText(), "proc")
            self.output_path = os.path.join(input_dir, f"{input_name}_{algo_suffix}.mp4") # Add algo suffix
            self.output_label.setText(f'输出 (Output): {os.path.basename(self.output_path)} (自动)')
            self.output_label.setToolTip(self.output_path)
            logging.debug(f"Auto-generated output path: {self.output_path}")
            self.update_button_states()
        except Exception as e:
            logging.error(f"Error generating output path: {e}")
            self.output_label.setText('输出 (Output): 自动生成错误')
            self.output_path = None

    def select_output(self):
        """Opens dialog to select output video file path."""
        if not self.input_path:
            start_dir = self.settings.get("last_output_dir") or os.path.expanduser("~")
            default_name = "output_processed.mp4"
        else:
            start_dir = os.path.dirname(self.input_path)
            input_name = os.path.splitext(os.path.basename(self.input_path))[0]
            algo_suffix = {ALGO_FRAME_DIFF: "fd", ALGO_SSIM: "ssim", ALGO_OPTICAL_FLOW: "flow"}.get(self.algo_combo.currentText(), "proc")
            default_name = f"{input_name}_{algo_suffix}.mp4"
        start_path = os.path.join(start_dir, default_name)

        fname, _ = QFileDialog.getSaveFileName(self, '选择输出视频路径 (Select Output Path)', start_path, 'MP4 视频文件 (*.mp4);;所有文件 (*.*)')
        if fname:
            if not fname.lower().endswith('.mp4'): fname += '.mp4'
            self.output_path = fname
            self.output_label.setText(f'输出 (Output): {os.path.basename(fname)}')
            self.output_label.setToolTip(fname)
            self.settings.set("last_output_dir", os.path.dirname(fname))
            logging.info(f"Manual output path selected: {fname}")
            self.update_button_states()


    # --- Batch List Handling (add_videos, remove_videos, clear_videos) ---
    # (No changes needed, use code from previous response)
    def add_videos(self):
        """Adds videos to the batch processing list."""
        last_dir = self.settings.get("last_input_dir") or os.path.expanduser("~")
        files, _ = QFileDialog.getOpenFileNames(self, "选择要批量处理的视频 (Select Videos for Batch)", last_dir, "视频文件 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*.*)")
        if files:
            current_items = [self.video_list_widget.item(i).text().split(" (")[0] for i in range(self.video_list_widget.count())]
            added_count = 0
            files_to_add = []
            for f in files:
                 if f not in current_items and f not in files_to_add:
                     files_to_add.append(f)
                     added_count += 1
            if files_to_add:
                self.video_list_widget.addItems(files_to_add)
            logging.info(f"Added {added_count} videos to batch list.")
            if added_count > 0:
                 self.settings.set("last_input_dir", os.path.dirname(files[0]))
            self.update_button_states()

    def remove_videos(self):
        """Removes selected videos from the batch list."""
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items: return
        # Iterate backwards when removing multiple items
        for item in reversed(selected_items):
            self.video_list_widget.takeItem(self.video_list_widget.row(item))
        logging.info(f"Removed {len(selected_items)} videos from batch list.")
        self.update_button_states()

    def clear_videos(self):
        """Clears the entire batch list."""
        if self.video_list_widget.count() > 0:
            self.video_list_widget.clear()
            logging.info("Cleared batch list.")
            self.update_button_states()


    # --- Settings ---
    def open_settings(self):
        """Opens the settings dialog."""
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec_():
            self.load_settings_to_ui() # Reload potentially changed defaults
            self.update_parameter_visibility() # Update UI based on potentially changed default algo
            self.connect_param_signals() # Reconnect signals
            QMessageBox.information(self, "设置已保存", "默认设置已更新。")
        else:
             logging.debug("Settings dialog cancelled.")


    def load_settings_to_ui(self):
        """Loads values from settings into the UI controls."""
        # Algorithm
        saved_algo = self.settings.get("selected_algorithm")
        index = self.algo_combo.findText(saved_algo)
        if index != -1:
             self.algo_combo.blockSignals(True)
             self.algo_combo.setCurrentIndex(index)
             self.algo_combo.blockSignals(False)
        else: # Fallback to default if saved algo is invalid
             self.algo_combo.setCurrentIndex(self.algo_combo.findText(ALGO_FRAME_DIFF))


        # Frame Diff Params
        self.f_diff_threshold_slider.setValue(self.settings.get("f_diff_threshold"))
        self.f_diff_min_area_slider.setValue(self.settings.get("f_diff_min_area"))
        self.f_diff_blur_slider.setValue(self.settings.get("f_diff_blur_size"))
        self.f_diff_threshold_edit.setText(str(self.f_diff_threshold_slider.value()))
        self.f_diff_min_area_edit.setText(str(self.f_diff_min_area_slider.value()))
        self.f_diff_blur_edit.setText(str(self.f_diff_blur_slider.value()))

        # SSIM Params
        self.ssim_threshold_spin.setValue(self.settings.get("ssim_threshold"))
        self.ssim_blur_slider.setValue(self.settings.get("ssim_blur_size"))
        self.ssim_blur_edit.setText(str(self.ssim_blur_slider.value()))

        # Optical Flow Params
        self.flow_threshold_spin.setValue(self.settings.get("flow_threshold"))
        self.flow_blur_slider.setValue(self.settings.get("flow_blur_size"))
        self.flow_blur_edit.setText(str(self.flow_blur_slider.value()))

        # General
        self.reverse_video_check.setChecked(self.settings.get("reverse_video"))

        logging.debug("Loaded settings into UI controls.")
        # Visibility update is handled separately by update_parameter_visibility()


    # --- Previews ---
    def show_parameter_preview(self):
        """Shows the parameter preview dialog (currently Frame Diff only)."""
        if not self.input_path or not os.path.exists(self.input_path):
            QMessageBox.warning(self, "无输入视频", "请先选择一个有效的输入视频文件以进行预览。")
            return

        # TODO: Make this preview context-aware based on self.algo_combo.currentText()
        # For now, it only previews Frame Difference parameters.
        selected_algo = self.algo_combo.currentText()
        if selected_algo == ALGO_FRAME_DIFF:
            try:
                params = self.get_current_parameters() # Get current UI vals
                dialog = PreviewDialog(self.input_path,
                                       params['f_diff_threshold'],
                                       params['f_diff_min_area'],
                                       params['f_diff_blur_size'], self)
                dialog.exec_()
            except Exception as e:
                error_msg = f"无法显示帧差法预览: {e}"
                logging.exception(error_msg)
                QMessageBox.critical(self, "预览错误", error_msg)
        else:
             QMessageBox.information(self, "预览限制", f"参数效果预览当前仅支持“帧差法”。\n({selected_algo} 算法的预览功能尚未实现)")


    def show_contrast_preview(self):
         """显示使用 python-vlc 的并排视频对比对话框"""
         if not self.input_path or not os.path.exists(self.input_path):
              QMessageBox.warning(self, "无原始视频", "找不到用于对比的原始视频文件。")
              return
         if not self.last_processed_output_path or not os.path.exists(self.last_processed_output_path):
              QMessageBox.warning(self, "无处理后视频", "找不到用于对比的处理后视频文件。\n请先成功处理一个视频。")
              return

         # --- 检查 VLC 库是否真的在运行时可用 ---
         # 注意：VLC_AVAILABLE 需要在 ui.dialogs 中定义并在此处可用
         # 如果没有把它设为全局可访问，可以在这里再次尝试导入 vlc
         try:
             import vlc # 再次检查导入
             if vlc is None: raise ImportError # 如果之前导入失败
         except ImportError:
             QMessageBox.critical(self, "错误", "缺少 'python-vlc' 库或初始化失败。\n无法使用 VLC 预览功能。\n请安装： pip install python-vlc")
             return
         # ---

         try:
              logging.info("Opening VLC contrast preview dialog...")
              # 创建并执行 VLC 预览对话框实例
              # 使用我们重命名导入的 VLCPreviewDialog
              dialog = VLCPreviewDialog(self.input_path, self.last_processed_output_path, self)
              dialog.exec_() # 显示为模态对话框
              logging.info("VLC contrast preview dialog closed.")
         except Exception as e:
              error_msg = f"无法显示 VLC 对比预览: {e}"
              logging.exception(error_msg)
              QMessageBox.critical(self, "预览错误", error_msg)


    # --- Processing ---
    def get_current_parameters(self):
         """Collects current parameter values from the UI based on selected algorithm."""
         params = {
             # Frame Diff
             'f_diff_threshold': self.f_diff_threshold_slider.value(),
             'f_diff_min_area': self.f_diff_min_area_slider.value(),
             'f_diff_blur_size': self.f_diff_blur_slider.value(),
             # SSIM
             'ssim_threshold': self.ssim_threshold_spin.value(),
             'ssim_blur_size': self.ssim_blur_slider.value(),
             # Optical Flow
             'flow_threshold': self.flow_threshold_spin.value(), # Use the direct threshold value
             'flow_blur_size': self.flow_blur_slider.value(),
         }
         return params


    def update_button_states(self, processing=False):
        """Enable/disable buttons based on current state."""
        single_ready = bool(self.input_path and self.output_path and os.path.exists(self.input_path))
        self.process_button.setEnabled(single_ready and not processing)

        batch_ready = self.video_list_widget.count() > 0
        self.batch_process_button.setEnabled(batch_ready and not processing)

        # Contrast preview enabled only if single input & processed output exist and not processing
        contrast_ready = bool(self.input_path and self.last_processed_output_path and
                              os.path.exists(self.input_path) and os.path.exists(self.last_processed_output_path))
        self.contrast_preview_button.setEnabled(contrast_ready and not processing)


        self.cancel_button.setEnabled(processing)

        # Disable parameter changes and file selections during processing
        self.algo_combo.setEnabled(not processing)
        self.preset_combo.setEnabled(not processing)

        # --- 更健壮地查找和禁用控件 ---
        param_group = self.findChild(QGroupBox, "ParameterSettingsGroup") # 使用 objectName
        if param_group:
            # 遍历 group 内的所有子控件
            for child_widget in param_group.findChildren(QWidget):
                # 禁用 Slider, LineEdit, CheckBox, ComboBox, PushButton (除了Help?), SpinBox
                 if isinstance(child_widget, (QSlider, QLineEdit, QCheckBox, QComboBox, QPushButton, QSpinBox, QDoubleSpinBox)):
                    # 不要禁用算法和预设下拉框 (它们已经在上面单独处理)
                    if child_widget != self.algo_combo and child_widget != self.preset_combo:
                         # 不要禁用帮助按钮 (通过检查我们添加的标志)
                         if not getattr(child_widget, '_is_help_button', False):
                              child_widget.setEnabled(not processing)
        else:
             logging.warning("Could not find ParameterSettingsGroup to disable controls.")

        # Disable file group buttons
        file_group = self.findChild(QGroupBox, "FileSelectionGroup") # 使用 objectName
        if file_group:
             for button in file_group.findChildren(QPushButton): button.setEnabled(not processing)
             for combo in file_group.findChildren(QComboBox): combo.setEnabled(not processing)
        else:
             logging.warning("Could not find FileSelectionGroup to disable controls.")


        # Disable batch group buttons
        batch_group = self.findChild(QGroupBox, "BatchProcessingGroup") # 使用 objectName
        if batch_group:
             for button in batch_group.findChildren(QPushButton): button.setEnabled(not processing)
             self.video_list_widget.setEnabled(not processing)
        else:
             logging.warning("Could not find BatchProcessingGroup to disable controls.")
        # --- 修改结束 ---


    def start_processing_state(self):
        """UI changes when processing starts."""
        self.update_button_states(processing=True)
        self.status_label.setText("状态: 处理中...")
        self.tw_speed_label.setText("")
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("处理中... %p%")
        self.last_processed_output_path = None # Reset on new process start
        self.contrast_preview_button.setEnabled(False)

    def end_processing_state(self):
        """UI changes when processing ends."""
        self.update_button_states(processing=False)
        self.current_processor = None

    def process_single_video(self):
        """Starts processing the currently selected single video."""
        if not self.input_path or not self.output_path:
             QMessageBox.critical(self, "缺少文件", "请确保已选择有效的输入视频和输出路径。")
             return
        if not os.path.exists(self.input_path):
             QMessageBox.critical(self, "文件未找到", f"输入文件不存在:\n{self.input_path}")
             return

        if os.path.exists(self.output_path):
            reply = QMessageBox.question(self, '确认覆盖', f"输出文件已存在:\n{os.path.basename(self.output_path)}\n\n是否覆盖?",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.status_label.setText("状态: 操作取消")
                return

        try:
            logging.info("Starting single video processing.")
            self.start_processing_state()

            selected_algorithm = self.algo_combo.currentText()
            current_params = self.get_current_parameters()
            # Save chosen algorithm and params to settings for next launch?
            self.settings.set('selected_algorithm', selected_algorithm)
            self.settings.set('f_diff_threshold', current_params['f_diff_threshold'])
            self.settings.set('f_diff_min_area', current_params['f_diff_min_area'])
            self.settings.set('f_diff_blur_size', current_params['f_diff_blur_size'])
            self.settings.set('ssim_threshold', current_params['ssim_threshold'])
            self.settings.set('ssim_blur_size', current_params['ssim_blur_size'])
            self.settings.set('flow_threshold', current_params['flow_threshold'])
            self.settings.set('flow_blur_size', current_params['flow_blur_size'])

            self.current_processor = VideoProcessor(
                self.input_path,
                self.output_path,
                selected_algorithm,
                current_params,
                self.reverse_video_check.isChecked()
            )
            # Connect signals
            self.current_processor.progress.connect(self.update_progress)
            self.current_processor.finished.connect(self.on_single_process_finished)
            self.current_processor.error.connect(self.on_process_error)

            self.current_processor.start()

        except ImportError as e:
             error_msg = f"无法启动处理: 缺少必要的库 (可能与 {self.algo_combo.currentText()} 相关)。\n错误: {e}\n请检查 requirements.txt 并安装。"
             logging.exception(error_msg)
             QMessageBox.critical(self, "依赖错误", error_msg)
             self.end_processing_state()
             self.status_label.setText(f"状态: 错误!")
        except Exception as e:
            error_msg = f"启动视频处理时出错: {e}"
            logging.exception(error_msg)
            QMessageBox.critical(self, "启动错误", error_msg)
            self.end_processing_state()
            self.status_label.setText(f"状态: 错误!")


    def process_batch_videos(self):
        """Starts processing videos in the batch list."""
        if self.video_list_widget.count() == 0:
            QMessageBox.warning(self, "列表为空", "请先向批量处理列表中添加视频。")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "选择批量输出目录", self.settings.get("last_output_dir") or os.path.expanduser("~"))
        if not output_dir:
            self.status_label.setText("状态: 批量处理取消")
            return
        self.settings.set("last_output_dir", output_dir)

        video_paths = [self.video_list_widget.item(i).text().split(" (")[0] for i in range(self.video_list_widget.count())]
        # Reset batch list item states
        for i in range(self.video_list_widget.count()):
            item = self.video_list_widget.item(i)
            item.setText(video_paths[i]) # Restore original text
            item.setForeground(QColor("black"))
            item.setToolTip("")


        try:
            logging.info(f"Starting batch processing for {len(video_paths)} files to {output_dir}.")
            self.start_processing_state()

            selected_algorithm = self.algo_combo.currentText()
            current_params = self.get_current_parameters()
            # Save chosen algorithm and params to settings
            self.settings.set('selected_algorithm', selected_algorithm)
            # ... (save other params as in single process) ...
            self.settings.set('f_diff_threshold', current_params['f_diff_threshold'])
            self.settings.set('f_diff_min_area', current_params['f_diff_min_area'])
            self.settings.set('f_diff_blur_size', current_params['f_diff_blur_size'])
            self.settings.set('ssim_threshold', current_params['ssim_threshold'])
            self.settings.set('ssim_blur_size', current_params['ssim_blur_size'])
            self.settings.set('flow_threshold', current_params['flow_threshold'])
            self.settings.set('flow_blur_size', current_params['flow_blur_size'])


            self.current_processor = BatchProcessor(
                video_paths,
                output_dir,
                selected_algorithm,
                current_params,
                self.reverse_video_check.isChecked()
            )
            # Connect batch-specific signals
            self.current_processor.overall_progress.connect(self.update_overall_progress)
            self.current_processor.current_file_progress.connect(self.update_current_file_progress)
            self.current_processor.file_started.connect(self.on_batch_file_started)
            self.current_processor.file_finished.connect(self.on_batch_file_finished)
            self.current_processor.file_error.connect(self.on_batch_file_error)
            self.current_processor.batch_finished.connect(self.on_batch_process_finished)
            self.current_processor.error.connect(self.on_process_error) # General batch errors

            self.current_processor.start()

        except ImportError as e:
             error_msg = f"无法启动批量处理: 缺少必要的库 (可能与 {self.algo_combo.currentText()} 相关)。\n错误: {e}\n请检查 requirements.txt 并安装。"
             logging.exception(error_msg)
             QMessageBox.critical(self, "依赖错误", error_msg)
             self.end_processing_state()
             self.status_label.setText(f"状态: 错误!")
        except Exception as e:
            error_msg = f"启动批量处理时出错: {e}"
            logging.exception(error_msg)
            QMessageBox.critical(self, "启动错误", error_msg)
            self.end_processing_state()
            self.status_label.setText(f"状态: 错误!")


    def cancel_processing(self):
        """Stops the currently running processor thread."""
        if self.current_processor and self.current_processor.isRunning():
            logging.info("Cancel button clicked. Requesting process stop.")
            self.current_processor.stop()
            self.status_label.setText("状态: 取消中...")
            self.cancel_button.setEnabled(False)
        else:
            logging.warning("Cancel called but no process seemed to be running.")


    # --- Signal Handlers ---
    def update_progress(self, value, filename, current_frame, total_frames):
        """Updates progress bar for single video processing, showing frame count."""
        if isinstance(self.current_processor, VideoProcessor):
             self.progress_bar.setValue(value)
             self.progress_bar.setFormat(f"{filename} ({current_frame}/{total_frames}) - %p%")

    # Add output_path parameter to handler
    def on_single_process_finished(self, message, tw_speed, kept_frames, output_path):
        """Handles successful completion of single video processing."""
        if isinstance(self.current_processor, VideoProcessor):
            logging.info(f"Single process finished: {message}. Output: {output_path}")
            self.end_processing_state()
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat("完成!")

            result_color = "#008000"; kept_frames_color = "#FF6347"; speed_color = "#4682B4"
            self.status_label.setText(f"状态: <font color='{result_color}'>{message}</font> 保留了 <font color='{kept_frames_color}'>{kept_frames}</font> 帧。")
            self.tw_speed_label.setText(f"建议 Twixtor 速度: <font color='{speed_color}'><b>{tw_speed:.2f}%</b></font> (恢复原时长)")

            # Store the path for contrast preview and enable the button
            self.last_processed_output_path = output_path
            self.update_button_states() # Re-evaluates button states

            QMessageBox.information(self, "处理完成", f"{message}\n保留了 {kept_frames} 帧。\n输出文件: {output_path}\n\n建议 Twixtor 速度: {tw_speed:.2f}%")

    # (on_process_error remains the same)
    def on_process_error(self, error_message):
        """Handles errors during video processing (single or batch setup)."""
        logging.error(f"Processing error reported: {error_message}")
        self.end_processing_state()
        self.progress_bar.setValue(0) # Reset progress on error
        self.progress_bar.setFormat("错误!")
        self.status_label.setText(f"<font color='red'>错误: {error_message}</font>")
        self.tw_speed_label.setText("")

        if "处理已取消" in error_message or "cancelled" in error_message.lower():
             self.status_label.setText("状态: 处理已取消")
             QMessageBox.warning(self, "处理取消", "视频处理已被用户取消。")
        else:
             QMessageBox.critical(self, "处理错误", error_message)


    # --- Batch Signal Handlers ---
    def update_overall_progress(self, value):
        """Updates the main progress bar for overall batch progress."""
        if isinstance(self.current_processor, BatchProcessor):
            self.progress_bar.setValue(value)
            self.progress_bar.setFormat(f"总进度: %p%")

    def update_current_file_progress(self, value, filename, current_frame, total_frames):
        """Updates status label for the current file's progress in batch."""
        if isinstance(self.current_processor, BatchProcessor):
            self.status_label.setText(f"状态: 正在处理 {filename} ({current_frame}/{total_frames}) - {value}%")

    def on_batch_file_started(self, filename):
        """Highlights the file being processed in the list."""
        if isinstance(self.current_processor, BatchProcessor):
            self.status_label.setText(f"状态: 开始处理 {filename}...")
            logging.info(f"Batch: Started processing {filename}")
            for i in range(self.video_list_widget.count()):
                item = self.video_list_widget.item(i)
                item_text = item.text().split(" (")[0]
                if os.path.basename(item_text) == filename:
                     item.setForeground(QColor("blue"))
                     self.video_list_widget.scrollToItem(item)
                elif item.foreground().color() == QColor("blue"): # Reset previous blue
                     item.setForeground(QColor("black"))


    # Add output_path parameter to handler
    def on_batch_file_finished(self, filename, message, tw_speed, kept_frames, output_path):
        """Handles successful completion of one file within a batch."""
        if isinstance(self.current_processor, BatchProcessor):
            logging.info(f"Batch: Finished {filename}. Kept {kept_frames} frames. TW Speed: {tw_speed:.2f}%. Output: {output_path}")
            for i in range(self.video_list_widget.count()):
                item = self.video_list_widget.item(i)
                item_text = item.text().split(" (")[0]
                if os.path.basename(item_text) == filename:
                    item.setForeground(QColor("green"))
                    # Show more info in the list item
                    item.setText(f"{item_text} (完成 ✔ | {kept_frames} 帧 | TW: {tw_speed:.1f}%)")
                    item.setToolTip(f"输出: {output_path}") # Show output path on hover
                    break
            self.status_label.setText(f"状态: {filename} 处理完成 ({kept_frames} 帧).")

    def on_batch_file_error(self, filename, error_message):
        """Handles error for one file within a batch."""
        if isinstance(self.current_processor, BatchProcessor):
            logging.error(f"Batch: Error processing {filename}: {error_message}")
            for i in range(self.video_list_widget.count()):
                item = self.video_list_widget.item(i)
                item_text = item.text().split(" (")[0]
                if os.path.basename(item_text) == filename:
                    item.setForeground(QColor("red"))
                    item.setText(f"{item_text} (错误 ❌)")
                    item.setToolTip(error_message)
                    break
            self.status_label.setText(f"<font color='red'>错误处理 {filename}: {error_message}</font>")

    def on_batch_process_finished(self):
        """Handles completion of the entire batch process."""
        if isinstance(self.current_processor, BatchProcessor):
            logging.info("Batch processing finished signal received.")
            was_cancelled = not self.cancel_button.isEnabled()
            self.end_processing_state()

            # Count successes and failures
            success_count = sum(1 for item_idx in range(self.video_list_widget.count()) if "✔" in self.video_list_widget.item(item_idx).text())
            error_count = sum(1 for item_idx in range(self.video_list_widget.count()) if "❌" in self.video_list_widget.item(item_idx).text())
            total_count = self.video_list_widget.count()

            if not was_cancelled:
                 self.progress_bar.setValue(100)
                 self.progress_bar.setFormat("批量完成!")
                 final_msg = f"状态: 批量处理完毕 ({success_count}/{total_count} 成功, {error_count} 失败)"
                 self.status_label.setText(final_msg)
                 QMessageBox.information(self, "批量处理完成", f"所有视频已处理完毕。\n成功: {success_count}\n失败: {error_count}\n请检查列表和输出目录。")
            else:
                 self.status_label.setText("状态: 批量处理已取消")


    # --- Watermark & Closing ---
    # (check_watermark_integrity and closeEvent remain the same)
    def check_watermark_integrity(self):
        """Periodically checks watermark integrity."""
        if not watermark_protection.verify_integrity():
            logging.critical("Watermark integrity check failed during runtime. Closing application.")
            QMessageBox.critical(self, "错误", "应用程序完整性验证失败，将关闭。")
            self.close()
        else:
            self.watermark_check_timer.start(random.randint(15000, 45000))
            logging.debug("Periodic watermark check passed.")

    def closeEvent(self, event):
        """Handles window close event."""
        logging.info("Close event triggered.")
        if self.current_processor and self.current_processor.isRunning():
            logging.warning("Attempting to close while processing. Stopping thread...")
            reply = QMessageBox.question(self, '确认退出', "处理仍在进行中。是否取消处理并退出？",
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.cancel_processing()
                logging.info("Processing stop requested on close.")
                # Don't wait here, let the app close. The thread should stop eventually.
            else:
                event.ignore()
                return

        logging.info("Application closing.")
        super().closeEvent(event)

    # resizeEvent remains the same for watermark positioning
    def resizeEvent(self, event):
        """Adjust watermark position on window resize."""
        super().resizeEvent(event)
        label_size = self.watermark_label.sizeHint()
        margin = 5
        self.watermark_label.setGeometry(
            self.width() - label_size.width() - margin,
            self.height() - label_size.height() - margin,
            label_size.width(),
            label_size.height()
        )
        self.watermark_label.raise_()