# utils/helpers.py
import sys
import subprocess
import importlib
import logging

def check_and_install_libraries():
    """Checks for required libraries and installs them if missing."""
    required_libraries = [
        'PyQt5',
        'opencv-python',
        'numpy',
        'cryptography',
        'appdirs'
    ]
    installed_all = True
    for library in required_libraries:
        try:
            # Module name might differ from package name (e.g., opencv-python -> cv2)
            module_name = library.replace('-', '_')
            if library == 'opencv-python':
                module_name = 'cv2'
            elif library == 'PyQt5':
                 # Check for a core module like QtCore
                 importlib.import_module('PyQt5.QtCore')
            else:
                importlib.import_module(module_name)
            logging.info(f"Library '{library}' is already installed.")
            print(f"{library} 已安装")
        except ImportError:
            installed_all = False
            print(f"{library} 未安装，正在安装...")
            logging.info(f"Library '{library}' not found. Attempting installation.")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", library])
                print(f"{library} 安装完成")
                logging.info(f"Library '{library}' installed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"无法安装 {library}. 请手动安装: pip install {library}")
                logging.error(f"Failed to install {library}: {e}")
                # Depending on how critical the lib is, you might want to exit
                # sys.exit(f"Error: Could not install required library {library}")
            except Exception as e:
                print(f"安装 {library} 时发生未知错误: {e}")
                logging.error(f"Unknown error installing {library}: {e}")

    return installed_all

def setup_logging(log_file_path):
    """Configures logging for the application."""
    logging.basicConfig(filename=log_file_path, level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
                        encoding='utf-8') # Specify encoding for wider compatibility
    print(f"日志文件位于: {log_file_path}")

def custom_exception_hook(exctype, value, traceback):
    """Custom exception handler to log unhandled exceptions."""
    logging.error("Unhandled exception caught by hook:", exc_info=(exctype, value, traceback))
    # Call the default excepthook to print to stderr
    sys.__excepthook__(exctype, value, traceback)