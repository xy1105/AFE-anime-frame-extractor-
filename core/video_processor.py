# core/video_processor.py
import os
import cv2
import numpy as np
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from skimage.metrics import structural_similarity as ssim # 导入SSIM

from utils.constants import ALGO_FRAME_DIFF, ALGO_SSIM, ALGO_OPTICAL_FLOW # 导入算法常量

class VideoProcessor(QThread):
    """Handles processing a single video file to extract significant frames using different algorithms."""
    # Signals: progress(int percentage, str current_file_basename, int current_frame, int total_frames), finished(str message, float tw_speed, int kept_frames, str output_path), error(str message)
    progress = pyqtSignal(int, str, int, int) # 添加了当前帧和总帧数
    finished = pyqtSignal(str, float, int, str) # 添加了输出路径，方便预览
    error = pyqtSignal(str)

    def __init__(self, input_path, output_path, algorithm, params, reverse_video, parent=None):
        super().__init__(parent)
        self.input_path = input_path
        self.output_path = output_path
        self.algorithm = algorithm
        self.params = params # 传入包含所有可能参数的字典
        self.reverse_video = reverse_video
        self._is_running = True

        # 根据算法提取和验证所需参数
        self.threshold = params.get('f_diff_threshold', 15)
        self.min_area = params.get('f_diff_min_area', 500)
        self.ssim_threshold = params.get('ssim_threshold', 0.98)
        # 注意：flow_sensitivity 在界面上是“敏感度”（越高越敏感，即越容易保留帧）
        # 但在算法实现里，通常是比较“平均运动幅度”，幅度越大越保留
        # 所以这里需要做一个转换或者调整逻辑。我们设定一个基础值，敏感度越高，实际判断的运动幅度阈值越低
        # flow_sensitivity 值范围假设为 0-10 (界面控制), 0最不敏感，10最敏感
        # 实际运动阈值 = 基础最大运动阈值 * (1 - flow_sensitivity / 10)
        # 或者更简单：直接使用一个运动幅度阈值，界面上的“敏感度”越高，这个阈值越低
        # 假设界面 flow_sensitivity 范围 0.1 - 5.0, 值越低越敏感 (容易保留)
        self.flow_threshold = params.get('flow_threshold', 1.0) # 值越小越敏感
        # 模糊程度根据所选算法获取
        if self.algorithm == ALGO_SSIM:
             self.blur_size = params.get('ssim_blur_size', 5)
        elif self.algorithm == ALGO_OPTICAL_FLOW:
             self.blur_size = params.get('flow_blur_size', 7)
        else: # ALGO_FRAME_DIFF
             self.blur_size = params.get('f_diff_blur_size', 5)

        # Ensure blur size is always odd and positive
        self.blur_size = max(1, self.blur_size if self.blur_size % 2 == 1 else self.blur_size + 1)

        logging.info(f"VideoProcessor initialized for {os.path.basename(input_path)}")
        logging.info(f"Algorithm: {self.algorithm}, Params: {self.params}, Blur: {self.blur_size}, Reverse: {reverse_video}")


    def stop(self):
        """Requests the processing thread to stop."""
        self._is_running = False
        logging.info("Video processing stop requested.")

    def run(self):
        """The core video processing logic executed in a separate thread."""
        self._is_running = True
        cap = None
        out = None
        try:
            base_filename = os.path.basename(self.input_path)
            logging.info(f"Starting video processing for: {self.input_path}")
            self.progress.emit(0, base_filename, 0, 1) # Initial progress (frame 0 / 1)

            cap = cv2.VideoCapture(self.input_path)
            if not cap.isOpened():
                raise IOError(f"无法打开输入视频文件: {self.input_path}")

            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            if fps <= 0:
                fps = 30 # Assume a default FPS
                logging.warning(f"Invalid FPS detected for {self.input_path}. Assuming {fps} FPS.")
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

            if total_frames <= 0 or width <= 0 or height <= 0:
                 raise ValueError(f"视频元数据无效: 帧={total_frames}, 宽={width}, 高={height}")

            logging.info(f"Video Info: Frames={total_frames}, FPS={fps:.2f}, Res={width}x{height}")

            # Ensure output directory exists
            output_dir = os.path.dirname(self.output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                logging.info(f"Created output directory: {output_dir}")

            # Use appropriate fourcc for mp4. Crucially, set isColor=True.
            fourcc = cv2.VideoWriter_fourcc(*'mp4v') # or 'avc1'
            # OpenCV VideoWriter does NOT handle audio. This inherently removes audio.
            out = cv2.VideoWriter(self.output_path, fourcc, fps, (width, height), isColor=True)
            if not out.isOpened():
                 raise IOError(f"无法创建输出视频文件: {self.output_path}")

            frames_to_keep = []
            prev_frame_gray_blurred = None # Used by all algorithms
            processed_frames_count = 0

            # --- Frame Processing Loop ---
            for i in range(total_frames):
                if not self._is_running:
                    logging.info("Processing stopped externally.")
                    self.error.emit("处理已取消")
                    # Clean up potentially incomplete output file
                    if out is not None: out.release()
                    if cap is not None: cap.release()
                    # It's generally safer NOT to delete the partially written file automatically
                    # if os.path.exists(self.output_path): os.remove(self.output_path)
                    return # Exit thread cleanly

                ret, frame = cap.read()
                if not ret:
                    logging.warning(f"Frame read failed at index {i}/{total_frames}. End of stream or error.")
                    break # End of video or error

                keep_this_frame = False

                # --- Initial/Final Frames ---
                # Always keep first frame, prepare for comparison
                if i == 0:
                    keep_this_frame = True
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    prev_frame_gray_blurred = cv2.GaussianBlur(gray, (self.blur_size, self.blur_size), 0)
                # Always keep last frame (check i == total_frames - 1)
                elif i == total_frames - 1:
                    keep_this_frame = True
                # --- Algorithm-based Comparison ---
                else:
                    current_frame_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    current_frame_gray_blurred = cv2.GaussianBlur(current_frame_gray, (self.blur_size, self.blur_size), 0)

                    if prev_frame_gray_blurred is not None:
                        # --- Frame Difference Logic ---
                        if self.algorithm == ALGO_FRAME_DIFF:
                            diff = cv2.absdiff(current_frame_gray_blurred, prev_frame_gray_blurred)
                            _, thresh_img = cv2.threshold(diff, self.threshold, 255, cv2.THRESH_BINARY)
                            contours, _ = cv2.findContours(thresh_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                            if any(cv2.contourArea(contour) > self.min_area for contour in contours):
                                keep_this_frame = True

                        # --- SSIM Logic ---
                        elif self.algorithm == ALGO_SSIM:
                             # Ensure frames have same dimensions for SSIM
                            if current_frame_gray_blurred.shape == prev_frame_gray_blurred.shape:
                                # win_size should be odd and <= min(height, width), typically small (e.g., 7)
                                win_size = min(7, self.blur_size, current_frame_gray_blurred.shape[0], current_frame_gray_blurred.shape[1])
                                if win_size % 2 == 0: win_size -= 1 # Ensure odd
                                if win_size >=3: # SSIM needs window size >= 3
                                     similarity_index = ssim(prev_frame_gray_blurred, current_frame_gray_blurred, win_size=win_size)
                                     # Keep frame if NOT similar enough
                                     if similarity_index < self.ssim_threshold:
                                         keep_this_frame = True
                                else:
                                     # Fallback or warning if window size too small
                                     logging.warning(f"SSIM window size too small ({win_size}) at frame {i}. Keeping frame as precaution.")
                                     keep_this_frame = True # Or compare differently?
                            else:
                                logging.warning(f"Frame shape mismatch at frame {i}. Keeping frame.")
                                keep_this_frame = True # Keep if shapes mismatch (unlikely but possible)


                        # --- Optical Flow Logic ---
                        elif self.algorithm == ALGO_OPTICAL_FLOW:
                            # Calculate dense optical flow (Farneback)
                            # Parameters can be tuned: pyr_scale, levels, winsize, iterations, poly_n, poly_sigma, flags
                            flow = cv2.calcOpticalFlowFarneback(prev_frame_gray_blurred, current_frame_gray_blurred,
                                                                None, 0.5, 3, 15, 3, 5, 1.2, 0)
                            # Calculate magnitude of flow vectors
                            magnitude, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                            # Calculate average magnitude (or median, or percentile for robustness)
                            avg_magnitude = np.mean(magnitude)
                            # Keep frame if average motion is significant enough
                            if avg_magnitude > self.flow_threshold:
                                keep_this_frame = True


                    # Update previous frame for the next iteration
                    prev_frame_gray_blurred = current_frame_gray_blurred

                # --- Add frame if marked for keeping ---
                if keep_this_frame:
                    frames_to_keep.append(frame)

                processed_frames_count += 1
                # --- Update Progress ---
                # Update more frequently for better feedback, e.g., every frame or every N frames
                # if processed_frames_count % 1 == 0 or keep_this_frame:
                progress_percent = int((processed_frames_count / total_frames) * 100)
                self.progress.emit(progress_percent, base_filename, processed_frames_count, total_frames)

            logging.info(f"Analysis complete. Kept {len(frames_to_keep)} out of {total_frames} frames.")
            self.progress.emit(100, base_filename, total_frames, total_frames) # Ensure 100% on analysis finish

            # --- Write Output ---
            if not self._is_running:
                logging.info("Writing output cancelled before start.")
                self.error.emit("处理已取消")
                # Clean up necessary? out might not be fully initialized
                if out is not None: out.release()
                if cap is not None: cap.release()
                return

            if self.reverse_video:
                frames_to_keep.reverse()
                logging.info("Reversing frame order for output.")

            logging.info(f"Writing {len(frames_to_keep)} frames to {self.output_path}...")
            write_progress_update_interval = max(1, len(frames_to_keep) // 20) # Update ~20 times during write
            for idx, frame_to_write in enumerate(frames_to_keep):
                 if not self._is_running:
                     logging.info("Writing output cancelled during process.")
                     self.error.emit("处理已取消")
                     # Clean up partially written file
                     if out is not None: out.release() # Release writer first
                     if cap is not None: cap.release()
                     # if os.path.exists(self.output_path): os.remove(self.output_path) # Be cautious with auto-delete
                     return
                 out.write(frame_to_write)
                 # Optional: Progress update during writing (can slow down slightly)
                 if (idx + 1) % write_progress_update_interval == 0:
                     # Can emit a different signal or update main progress bar if desired
                     logging.debug(f"Written {idx+1}/{len(frames_to_keep)} frames.")

            # --- Final Calculations ---
            original_duration = total_frames / fps if fps > 0 else 0
            new_duration = len(frames_to_keep) / fps if fps > 0 else 0
            tw_speed = (new_duration / original_duration) * 100 if original_duration > 0 else 0 # Avoid division by zero

            logging.info(f"Processing finished successfully for {self.input_path}.")
            logging.info(f"Original Duration: {original_duration:.2f}s, New Duration: {new_duration:.2f}s")
            logging.info(f"Suggested Twixtor Speed: {tw_speed:.2f}%")

            # Emit finished signal with output path
            self.finished.emit(f"处理成功完成!", tw_speed, len(frames_to_keep), self.output_path)

        except (IOError, ValueError, cv2.error, ImportError) as e: # Added ImportError for scikit-image
            error_msg = f"处理视频 '{os.path.basename(self.input_path)}' 时发生错误: {e}"
            logging.exception(error_msg) # Log full traceback
            self.error.emit(error_msg)
            # Ensure resources are released in case of error during loop/write
            if out is not None: out.release()
            if cap is not None: cap.release()
        except Exception as e:
            error_msg = f"处理视频时发生意外错误: {e}"
            logging.exception(error_msg)
            self.error.emit(error_msg)
            if out is not None: out.release()
            if cap is not None: cap.release()
        finally:
            # Release resources if they haven't been already
            if cap is not None and cap.isOpened():
                cap.release()
            if out is not None and out.isOpened(): # Check if writer is opened before releasing
                 out.release()
            logging.debug(f"Resources potentially released for {self.input_path}.")