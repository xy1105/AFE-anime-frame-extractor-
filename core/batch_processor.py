# core/batch_processor.py
import os
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from core.video_processor import VideoProcessor # Absolute import

class BatchProcessor(QThread):
    """Handles processing multiple video files sequentially."""
    # Signals remain mostly the same, but file_finished now includes output_path
    overall_progress = pyqtSignal(int)
    current_file_progress = pyqtSignal(int, str, int, int) # Propagate detailed progress
    file_started = pyqtSignal(str)
    file_finished = pyqtSignal(str, str, float, int, str) # Added output_path
    file_error = pyqtSignal(str, str)
    batch_finished = pyqtSignal()
    error = pyqtSignal(str)

    # Accept algorithm choice and the full parameter dictionary
    def __init__(self, video_list, output_dir, algorithm, params, reverse_video, parent=None):
        super().__init__(parent)
        self.video_list = list(video_list)
        self.output_dir = output_dir
        self.algorithm = algorithm # Store selected algorithm
        self.params = params       # Store all parameters
        self.reverse_video = reverse_video
        self._is_running = True
        self.current_processor = None
        logging.info(f"BatchProcessor initialized for {len(video_list)} files. Output dir: {output_dir}")
        logging.info(f"Batch using Algorithm: {self.algorithm}, Params: {self.params}")

    def stop(self):
        """Requests the batch processing and any current video processing to stop."""
        self._is_running = False
        if self.current_processor and self.current_processor.isRunning():
            self.current_processor.stop()
        logging.info("Batch processing stop requested.")

    def run(self):
        """Executes the batch processing loop."""
        self._is_running = True
        total_files = len(self.video_list)
        if total_files == 0:
            logging.warning("Batch run called with empty video list.")
            self.batch_finished.emit()
            return

        files_processed_info = [] # Store results for each file

        try:
            if not os.path.isdir(self.output_dir):
                 os.makedirs(self.output_dir)
                 logging.info(f"Created batch output directory: {self.output_dir}")

            for i, video_path in enumerate(self.video_list):
                if not self._is_running:
                    logging.info("Batch processing stopped externally.")
                    break

                base_filename = os.path.basename(video_path)
                output_filename = f"processed_{os.path.splitext(base_filename)[0]}.mp4"
                output_path = os.path.join(self.output_dir, output_filename)

                logging.info(f"Batch: Starting file {i+1}/{total_files}: {base_filename}")
                self.file_started.emit(base_filename)

                # --- Run single video processor ---
                processor = VideoProcessor(
                    video_path,
                    output_path,
                    self.algorithm, # Pass algorithm choice
                    self.params,    # Pass all parameters
                    self.reverse_video
                )
                self.current_processor = processor

                # --- Connect signals ---
                # Use lambda to capture filename and output path
                # Propagate detailed progress
                processor.progress.connect(self.current_file_progress.emit)
                # Connect file_finished to store result and emit batch signal
                processor.finished.connect(
                    lambda msg, speed, frames, out_path, fn=base_filename:
                        self.handle_file_finish(fn, msg, speed, frames, out_path, files_processed_info)
                )
                # Connect file_error
                processor.error.connect(
                    lambda err_msg, fn=base_filename:
                        self.handle_file_error(fn, err_msg, files_processed_info)
                )

                if not self._is_running:
                    logging.info("Batch processing stopped before running next file.")
                    self.current_processor = None
                    break

                processor.run() # Run synchronously

                # --- Disconnect signals (optional but good practice) ---
                try:
                     processor.progress.disconnect()
                     processor.finished.disconnect()
                     processor.error.disconnect()
                except TypeError: pass # Ignore errors if already disconnected


                self.current_processor = None # Clear reference

                # Update overall progress *after* file is processed (success or error)
                overall_p = int(((i + 1) / total_files) * 100)
                self.overall_progress.emit(overall_p)

            # --- Batch finished ---
            if self._is_running:
                logging.info("Batch processing completed.")
            else:
                logging.info("Batch processing cancelled before completion.")

        except OSError as e:
             error_msg = f"批量处理时发生文件/目录错误: {e}"
             logging.exception(error_msg)
             self.error.emit(error_msg)
        except Exception as e:
            error_msg = f"批量处理时发生意外错误: {e}"
            logging.exception(error_msg)
            self.error.emit(error_msg)
        finally:
             self.current_processor = None
             self.batch_finished.emit() # Signal completion/cancellation

    # Helper methods to handle signals and update shared state
    def handle_file_finish(self, filename, message, tw_speed, kept_frames, output_path, results_list):
        results_list.append({'filename': filename, 'status': 'success', 'kept': kept_frames, 'speed': tw_speed, 'output': output_path})
        self.file_finished.emit(filename, message, tw_speed, kept_frames, output_path)

    def handle_file_error(self, filename, error_message, results_list):
         results_list.append({'filename': filename, 'status': 'error', 'message': error_message})
         self.file_error.emit(filename, error_message)