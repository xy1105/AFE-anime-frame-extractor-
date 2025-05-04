# utils/watermark.py
import hashlib
import time
import random
import sys
from cryptography.fernet import Fernet
import logging

class WatermarkProtection:
    """Handles encryption and integrity check for a watermark."""
    def __init__(self, watermark_text):
        self.watermark = watermark_text
        try:
            self.key = Fernet.generate_key()
            self.cipher_suite = Fernet(self.key)
            self.encrypted_watermark = self._encrypt_watermark()
            self.checksum = self._generate_checksum()
            logging.info("Watermark protection initialized.")
        except Exception as e:
            logging.error(f"Failed to initialize WatermarkProtection: {e}")
            # Handle initialization failure gracefully, maybe disable watermark
            self.key = None
            self.cipher_suite = None
            self.encrypted_watermark = None
            self.checksum = None


    def _encrypt_watermark(self):
        if not self.cipher_suite: return None
        return self.cipher_suite.encrypt(self.watermark.encode('utf-8'))

    def _decrypt_watermark(self, encrypted):
        if not self.cipher_suite: return None
        try:
            return self.cipher_suite.decrypt(encrypted).decode('utf-8')
        except Exception as e:
            logging.error(f"Failed to decrypt watermark: {e}")
            return None # Or handle error differently

    def _generate_checksum(self):
        if not self.encrypted_watermark: return None
        return hashlib.sha256(self.encrypted_watermark).hexdigest()

    def verify_integrity(self):
        """Checks if the watermark data has been tampered with."""
        if not self.checksum or not self.encrypted_watermark:
            logging.warning("Integrity check skipped: Watermark not initialized properly.")
            # Depending on security needs, you might return False here
            return True # Allow execution if initialization failed but wasn't critical
        is_valid = self.checksum == hashlib.sha256(self.encrypted_watermark).hexdigest()
        if not is_valid:
            logging.warning("Watermark integrity check failed!")
        return is_valid

    def get_watermark(self):
        """Returns the decrypted watermark if integrity check passes."""
        if self.verify_integrity() and self.encrypted_watermark:
            return self._decrypt_watermark(self.encrypted_watermark)
        logging.warning("Could not retrieve watermark due to integrity check failure or initialization error.")
        return "[Integrity Check Failed]" # Provide feedback instead of None

# --- Obfuscated Check ---
# Keep this if it's a specific requirement, but be aware it's not standard practice.
# Consider if standard code signing or licensing is more appropriate.
def validate_watermark_integrity(protector_instance):
    """Performs the integrity check and exits if failed."""
    if not protector_instance.verify_integrity():
        print("程序完整性检查失败. Program integrity check failed.")
        logging.critical("Application integrity check failed. Exiting.")
        time.sleep(random.random() * 2) # Short random delay
        sys.exit(1) # Exit with an error code

def run_obfuscated_check(func_to_run):
    """Simple obfuscation by calling the function indirectly."""
    # This function name `a1b2c3d4e5f6g7h8i9j0` is intentionally obscure.
    # Renaming it slightly for clarity within the refactor, but keeping the concept.
    return func_to_run()

# --- Instance ---
# Create a single instance for the application to use
watermark_protection = WatermarkProtection("by笑颜") # Or load from constants