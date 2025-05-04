# main.py
import sys
import os
import logging
from datetime import datetime # For timestamp in log start/end

# --- Early Setup ---
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import QApplication, QMessageBox
from utils.helpers import check_and_install_libraries, setup_logging, custom_exception_hook
from utils.settings import Settings
from utils.watermark import watermark_protection, validate_watermark_integrity, run_obfuscated_check
from ui.main_window import MainWindow
from utils.constants import APP_NAME # Get app name for log


def main():
    # 1. Initialize Settings
    try:
        settings = Settings()
    except Exception as e:
        print(f"FATAL: Could not initialize settings: {e}")
        try:
            app_temp = QApplication.instance() or QApplication([]) # Use empty list if argv not needed yet
            QMessageBox.critical(None, "初始化错误", f"无法初始化设置或日志系统: {e}\n程序将退出。")
        except Exception: pass
        sys.exit(1)

    # 2. Setup Logging
    try:
        log_file_path = settings.get_log_file_path()
        setup_logging(log_file_path)
    except Exception as e:
        print(f"FATAL: Could not set up logging: {e}")
        try:
            app_temp = QApplication.instance() or QApplication([])
            QMessageBox.critical(None, "日志错误", f"无法设置日志文件: {e}\n程序将继续，但可能缺少日志。")
        except Exception: pass

    # 3. Set Global Exception Hook
    sys.excepthook = custom_exception_hook
    start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"--- {APP_NAME} Application Start --- ({start_time})")


    # 4. Check and Install Libraries
    logging.info("Checking required libraries...")
    print("正在检查必需的库...")
    try:
        libraries_ok = check_and_install_libraries()
        if not libraries_ok:
             logging.warning("Some libraries might have failed to install automatically.")
             # Decide if you want to show a warning or exit
             # msg = "部分必需的库未能自动安装。请检查控制台输出并尝试手动安装 (`pip install ...`)。程序将尝试继续运行，但可能会出错。"
             # app_temp = QApplication.instance() or QApplication(sys.argv) # Need argv here
             # QMessageBox.warning(None, "库安装问题", msg)
    except Exception as e:
        logging.error(f"Error during library check/install: {e}")
        print(f"检查/安装库时出错: {e}")
        # Decide whether to continue or exit


    # 5. Validate Watermark/Integrity Check
    try:
         run_obfuscated_check(lambda: validate_watermark_integrity(watermark_protection))
         logging.info("Integrity check passed.")
    except SystemExit:
         logging.critical("Integrity check failed via obfuscated call. Exiting.")
         sys.exit(1)
    except Exception as e:
         logging.critical(f"Error during integrity check: {e}")
         try: # Try to show message box
             app_temp = QApplication.instance() or QApplication(sys.argv)
             QMessageBox.critical(None, "安全错误", f"程序完整性检查时发生错误: {e}")
         except: pass
         sys.exit(1)


    # 6. Initialize QApplication
    try:
        # It's generally safer to pass sys.argv here
        app = QApplication(sys.argv)
    except Exception as e:
        logging.critical(f"Failed to create QApplication: {e}")
        print(f"FATAL: Could not initialize Qt Application: {e}")
        sys.exit(1)


    # 7. Create and Show Main Window
    try:
        main_window = MainWindow(settings)
        main_window.show()
    except ImportError as e:
         # Catch specific import errors related to missing modules like QtMultimedia
         logging.critical(f"Failed to create main window due to missing dependency: {e}", exc_info=True)
         QMessageBox.critical(None, "依赖错误", f"无法创建主窗口: 缺少必要的组件。\n请确保所有依赖项已安装 (特别是 PyQt5 相关模块)。\n错误: {e}")
         sys.exit(1)
    except Exception as e:
        logging.critical("Failed to create or show the main window.", exc_info=True)
        QMessageBox.critical(None, "严重错误", f"无法创建主窗口: {e}\n请查看日志文件。")
        sys.exit(1)


    # 8. Start Event Loop
    exit_code = app.exec_()
    end_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    logging.info(f"Application exited with code {exit_code}. ({end_time})")
    logging.info(f"--- {APP_NAME} Application End ---")
    sys.exit(exit_code)


if __name__ == '__main__':
    main()
