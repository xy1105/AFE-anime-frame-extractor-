# utils/settings.py
import os
import json
import logging
import appdirs
from utils.constants import APP_NAME, APP_AUTHOR, ALGO_FRAME_DIFF # Import constants

class Settings:
    """Manages application settings persistence using JSON."""
    def __init__(self):
        self.app_dir = appdirs.user_data_dir(APP_NAME, APP_AUTHOR)
        os.makedirs(self.app_dir, exist_ok=True)
        # 使用新版本号的文件名，避免与旧版冲突
        self.filename = os.path.join(self.app_dir, "settings_v2.1.json")
        self.log_file = os.path.join(self.app_dir, 'frame_extractor_debug.log')

        self.default_settings = {
            # --- General ---
            "reverse_video": False,
            "preview_frame_index": 100,
            "last_input_dir": "",
            "last_output_dir": "",
            # --- Algorithm Choice ---
            "selected_algorithm": ALGO_FRAME_DIFF, # 默认算法
            # --- Frame Difference Params ---
            "f_diff_threshold": 15,
            "f_diff_min_area": 500,
            "f_diff_blur_size": 5,
            # --- SSIM Params ---
            "ssim_threshold": 0.98,
            "ssim_blur_size": 5,
            # --- Optical Flow Params ---
            "flow_threshold": 1.0, # 值越小越容易保留帧 (与界面标签反向，标签是敏感度)
            "flow_blur_size": 7,
        }
        self.settings = {} # Initialize empty
        self.load()
        logging.info(f"Settings loaded from: {self.filename}")
        logging.info(f"Log file location: {self.log_file}")

    def get_log_file_path(self):
        """Returns the path to the log file."""
        return self.log_file

    def load(self):
        """Loads settings from the JSON file, ensuring all keys exist."""
        loaded_settings = {}
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                loaded_settings = json.load(f)
        except FileNotFoundError:
            logging.warning(f"Settings file not found at {self.filename}. Using defaults.")
            # Don't set self.settings here yet, let the merging logic handle it
        except json.JSONDecodeError:
            logging.error(f"Error decoding settings file {self.filename}. Using defaults and attempting to backup.")
            try:
                os.rename(self.filename, self.filename + ".corrupted")
            except OSError:
                logging.error(f"Could not backup corrupted settings file.")
            # Continue with empty loaded_settings, defaults will be used
        except Exception as e:
            logging.error(f"Unexpected error loading settings: {e}. Using defaults.")
            # Continue with empty loaded_settings

        # --- Merge logic: Start with defaults, update with loaded ---
        self.settings = self.default_settings.copy()
        if loaded_settings: # Only update if something was successfully loaded
             # Filter loaded settings to only include keys present in defaults? (Optional stricter loading)
             # valid_loaded = {k: v for k, v in loaded_settings.items() if k in self.default_settings}
             # self.settings.update(valid_loaded)
             self.settings.update(loaded_settings) # Simpler: allow extra keys but defaults ensure minimum set

        # --- Verification and saving ---
        # Check if all default keys are present *after* merging. This handles cases
        # where the loaded file might be from an older version missing new keys.
        needs_save = False
        for key, default_value in self.default_settings.items():
            if key not in self.settings:
                logging.warning(f"Settings file missing key '{key}'. Adding default value: {default_value}")
                self.settings[key] = default_value
                needs_save = True

        # If the file was missing or keys were added, save the complete current settings.
        if needs_save or not os.path.exists(self.filename):
             self.save()


    def save(self):
        """Saves current settings to the JSON file."""
        try:
            with open(self.filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=4)
            logging.debug("Settings saved.")
        except IOError as e:
            logging.error(f"Could not save settings to {self.filename}: {e}")
        except Exception as e:
            logging.error(f"Unexpected error saving settings: {e}")

    # --- 修改 get 方法 ---
    def get(self, key):
        """Gets a setting value by key, falling back to default_settings if necessary."""
        # Try to get from self.settings first.
        # If the key doesn't exist in self.settings (shouldn't happen with current load logic, but safe),
        # fall back to getting the value from self.default_settings.
        # The second .get() on default_settings is a final safety net, returning None if somehow
        # the key is missing even in defaults (which would be a coding error).
        return self.settings.get(key, self.default_settings.get(key))
    # --- 修改结束 ---

    def set(self, key, value):
        """Sets a setting value by key and saves the settings."""
        self.settings[key] = value
        self.save()