# utils/constants.py

# --- App Info ---
APP_NAME = "动漫抽帧 V2.1" # 版本号更新
APP_AUTHOR = "YourCompanyName" # Or keep "笑颜" if preferred

# --- Processing Defaults ---
DEFAULT_FRAME_FOR_PREVIEW = 100

# --- Algorithm Identifiers ---
ALGO_FRAME_DIFF = "帧差法 (Frame Difference)"
ALGO_SSIM = "结构相似性 (SSIM)"
ALGO_OPTICAL_FLOW = "光流法 (Optical Flow)"

# --- Parameter Presets ---
# 格式: 'Preset Name': {'algorithm': ALGO_*, param1: value1, ...}
# 注意: SSIM 的阈值是越接近1表示越相似，所以保留条件是 ssim < threshold
# 光流法的阈值是运动幅度，保留条件是 flow > threshold
PRESETS = {
    "默认 (Default)": {
        'algorithm': ALGO_FRAME_DIFF,
        'threshold': 15,
        'min_area': 500,
        'blur_size': 5,
    },
    "高速动作 (High Action)": {
        'algorithm': ALGO_FRAME_DIFF,
        'threshold': 10, # 更敏感
        'min_area': 200, # 捕捉更小变化
        'blur_size': 3,
    },
    "缓慢场景 (Slow Scene)": {
        'algorithm': ALGO_SSIM,
        'ssim_threshold': 0.985, # 允许非常细微的变化通过
        'blur_size': 7, # 模糊多一点，忽略噪点
    },
    "运镜优化 (Pan/Zoom Optimize)": {
        'algorithm': ALGO_OPTICAL_FLOW,
        'flow_sensitivity': 1.5, # 较高的敏感度，只有明显运动才保留
        'blur_size': 9,
    },
     "视觉相似 (Visual Similarity - SSIM)": {
        'algorithm': ALGO_SSIM,
        'ssim_threshold': 0.97, # 比较宽松，丢弃更多相似帧
        'blur_size': 5,
    },
}