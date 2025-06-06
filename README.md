# 动漫抽帧工具 v2.1 - 智能、高效、多选择

这是一个专为动漫视频优化和剪辑设计的**高级**抽帧工具。本工具结合多种图像处理与分析算法，能够智能地识别并去除冗余或相似的视频帧，显著优化动画的动态效果，或为动漫 AMV/MAD 创作者提供更高效的补帧与素材处理方案。

**软件截图:**
![image](https://github.com/user-attachments/assets/fd6b7795-4cfc-4300-aabf-cec9c4828a9f)






## 目录

1.  [功能特点](#功能特点)
2.  [新增亮点 (v2.1)](#新增亮点)
3.  [安装指南](#安装指南)
4.  [使用说明](#使用说明)
5.  [算法与参数设置](#算法与参数设置)
6.  [视频对比预览](#视频对比预览)
7.  [批量处理](#批量处理)
8.  [常见问题](#常见问题)
9.  [注意事项](#注意事项)
10. [声明与联系方式](#使用权限与声明)
11. [开源许可](#开源许可)
12. [开发者唠叨](#开发者唠叨)

## 功能特点

*   **多种智能抽帧算法:** 提供帧差法、SSIM（结构相似性）、光流法等多种核心算法，应对不同视频特性。
*   **参数高度可定制:** 每种算法均提供关键参数（如阈值、最小区域、模糊度、相似度、运动敏感度等）供用户精细调整。
*   **VLC 内核预览:** 内置强大的 VLC 引擎，实现**稳定、兼容性极高**的并排视频对比预览，直观比较处理前后效果。
*   **参数效果预览:** （当前支持帧差法）可预览参数设置对单帧判断的影响。
*   **参数预设:** 内置多种场景预设，方便快速上手。
*   **批量处理:** 支持同时处理多个视频文件，提高效率。
*   **视频倒放:** 可选择在抽帧后将视频帧顺序倒放。
*   **实时进度反馈:** 提供详细的总体进度和单文件处理进度（包括帧数）。
*   **Twixtor 速度建议:** 自动计算处理后视频在 AE/PR 等软件中使用 Twixtor 插件恢复原始时长的建议速度百分比。
*   **纯视频输出:** 处理后输出不含音频轨道的 MP4 文件，避免音画不同步问题。
*   **跨平台潜力:** 基于 Python 和 PyQt，核心功能可在多平台运行（VLC 依赖需对应平台）。

## 新增亮点

*   **核心重构:** 代码结构全面优化，更稳定、易扩展。
*   **VLC 预览引擎:** 彻底解决视频预览的解码器兼容性问题。
*   **新增算法:** SSIM 和光流法为处理不同类型视频提供更多选择。
*   **参数预设:** 一键应用推荐参数。
*   **体验优化:** 界面布局、控件交互、进度反馈、错误处理等多方面改进。
*   **输出优化:** 优先使用 H.264 编码，去除音频。
*   **打包支持:** 改进了打包方式，包含 VLC 依赖，力求开箱即用。

## 安装指南

### 1. 安装 Python

确保你的系统已安装 Python 3.8 或更高版本，并在安装时勾选 "Add Python to PATH"。访问 [Python 官网](https://www.python.org/downloads/) 下载。

### 2. 安装必要的库

本程序依赖以下 Python 库：

*   `PyQt5`: 图形用户界面框架。
*   `opencv-python`: 核心视频/图像处理库。
*   `numpy`: 数值计算基础库。
*   `cryptography`: 用于内部加密功能。
*   `appdirs`: 处理应用程序数据目录。
*   `scikit-image`: 用于 SSIM 算法。
*   `python-vlc`: 用于内嵌视频对比预览。

**安装方式：**

1.  **自动安装 (如果提供):** 程序首次运行时可能会尝试自动检查并安装缺失库（这依赖于开发者的打包方式）。
2.  **手动安装 (推荐):**
    *   打开命令提示符 (CMD) 或终端。
    *   （可选但推荐）创建一个虚拟环境 (`python -m venv venv`, `source venv/bin/activate` 或 `venv\Scripts\activate`)。
    *   进入程序 **根目录** (包含 `requirements.txt` 的目录)。
    *   运行以下命令（使用清华镜像加速下载）：
        ```bash
        pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
        ```
        如果在海外，可以去掉 `-i ...` 部分：
        ```bash
        pip install -r requirements.txt
        ```
        等待所有库安装完成。

## 使用说明

1.  **启动程序:** 运行 `main.py` 。
2.  **选择输入视频:** 点击 "选择视频 (Select Video)" 按钮选择单个视频文件。
3.  **设置输出路径:**
    *   **自动生成:** 程序会在输入视频同目录下生成 `[原文件名]_[算法缩写].mp4` 文件。
    *   **手动选择:** 点击 "选择路径 (Select Path)" 指定输出文件名和位置。
4.  **选择算法与调整参数:**
    *   在 "算法 (Algorithm)" 下拉菜单中选择 `帧差法`, `SSIM` 或 `光流法`。
    *   对应的参数设置区域会自动显示。
    *   使用滑块或输入框调整参数。点击 `?` 查看参数说明。
    *   或者，在 "选择预设..." 下拉菜单中选择一个预设方案。
5.  **参数效果预览:** （可选，目前仅帧差法有效）点击 "参数效果预览" 按钮查看当前设置对示例帧的影响。
6.  **其他选项:** 根据需要勾选 "倒放视频 (Reverse Video)"。
7.  **开始处理:**
    *   **单个视频:** 点击 "处理当前视频" 按钮。
    *   **批量处理:** 查看 [批量处理](#批量处理) 部分。
8.  **查看结果:**
    *   处理过程中，进度条和状态栏会显示进度。
    *   完成后，状态栏会显示结果、保留帧数，以及建议的 Twixtor 速度。输出文件保存在指定位置。
9.  **视频对比预览:** 单个视频处理成功后，"对比预览 (VLC)" 按钮会启用。点击即可打开内置预览窗口，对比处理前后的效果。

## 算法与参数设置

### 1. 帧差法 (Frame Difference)

*   **原理:** 计算相邻帧像素差异，通过差异大小和区域面积判断是否保留。速度快，适合检测明显运动。
*   **参数:**
    *   **阈值 (Threshold):** 像素差异的敏感度 (0-100+)。值越低越敏感。建议 10-30。
    *   **最小区域 (Min Area):** 变化区域的最小像素数 (0-10000+)。值越小越能捕捉细微动作。建议 100-2000。
    *   **模糊 (Blur - odd):** 高斯模糊核大小 (1-51+，奇数)。用于降噪。值越大越模糊。建议 5-11。

### 2. 结构相似性 (SSIM)

*   **原理:** 比较相邻帧的亮度、对比度和结构相似性。更能模拟人眼感知，适合去除视觉上极度相似的静止帧。计算速度中等。
*   **参数:**
    *   **相似度阈值 (<) (SSIM Threshold):** 两帧的 SSIM 值 (0.9-0.9999)。如果实际相似度**低于**此阈值，则保留该帧。值越低，抽帧越“狠”（允许更大差异）；值越高，抽帧越保守。建议 0.97-0.99。
    *   **模糊 (Blur - odd):** 同帧差法，用于预处理降噪。建议 5-9。

### 3. 光流法 (Optical Flow)

*   **原理:** 计算相邻帧之间像素的运动矢量，通过平均运动幅度判断画面是否“动了”。对光照变化不敏感，适合处理镜头移动或需要精确捕捉运动感的场景。计算速度较慢。
*   **参数:**
    *   **运动阈值 (>) (Motion Threshold):** 平均运动幅度的阈值 (0.1-10.0+)。如果实际运动幅度**大于**此阈值，则保留该帧。值越低，越容易保留帧（对微小运动敏感）；值越高，只保留大幅度运动。建议 0.5-2.0。
    *   **模糊 (Blur - odd):** 同帧差法，用于预处理降噪。建议 7-15。

**参数建议仅供参考，最佳设置取决于具体视频内容和个人需求，请结合预览功能进行调整。**

## 视频对比预览

当处理**单个视频**成功后，"对比预览 (VLC)" 按钮将自动启用。

*   点击此按钮，会弹出一个新窗口。
*   窗口左侧播放**原始视频片段**，右侧播放**处理后的视频片段**。
*   窗口打开后会自动开始播放。
*   您可以使用底部的播放/暂停按钮和进度条来控制两个视频的播放，它们会**同步**进行。
*   **注意:** 此功能依赖于内置的 VLC 引擎和项目自带的 VLC 依赖文件 (`vlc_dependencies` 文件夹)。

## 批量处理

1.  在 "批量处理" 区域，点击 "添加视频 (Add)" 选择多个文件，或直接将视频文件**拖拽**到列表框中。
2.  使用 "移除选中 (Remove Selected)" 或 "清空列表 (Clear All)" 管理列表。
3.  在 "参数设置" 区域选择好**本次批量处理要使用的算法和参数**。
4.  点击 "处理列表视频 (Process Batch List)" 按钮。
5.  在弹出的对话框中选择一个**输出目录**，所有处理后的视频将保存在该目录下，文件名会自动添加 `processed_` 前缀和算法后缀。
6.  程序将依次处理列表中的视频，状态栏显示总体进度和当前文件进度。
7.  处理完成后，列表项会显示处理结果 (✔/❌)、保留帧数和建议速度。将鼠标悬停在成功的列表项上可查看输出文件路径。

## 常见问题

1.  **Q: 启动时提示缺少 'python-vlc' 或 'skimage' (scikit-image)?**
    A: 这说明相应的库没有安装成功。请返回 [安装指南](#安装指南) 部分，使用 `pip install -r requirements.txt ...` 命令重新安装。
2.  **Q: 对比预览窗口弹出但黑屏或报错？**
    A:
    *   请确保项目根目录下的 `vlc_dependencies` 文件夹及其内容（特别是 `plugins` 文件夹）完整且未被移动或删除。
    *   尝试更新显卡驱动程序。
    *   查看日志文件 (`frame_extractor_debug.log`) 获取更详细的 VLC 错误信息。
    *   作为临时方案，可以尝试在 `dialogs.py` 中取消注释禁用硬件加速的行（搜索 `--avcodec-hw=none`）。
3.  **Q: 处理视频时报错 "无法创建输出/临时文件"？**
    A: 这通常是**文件写入权限**问题。请尝试：
    *   **以管理员身份运行**本程序。
    *   选择**非系统盘符或非桌面**的目录作为输出路径。
    *   检查 Windows 的 "受控制文件夹访问" 设置或杀毒软件是否阻止了写入。
4.  **Q: 处理后的视频感觉跳跃/卡顿？**
    A: 这说明抽帧可能过于激进了。请尝试：
    *   **帧差法:** 降低阈值，减小最小区域。
    *   **SSIM 法:** 提高相似度阈值。
    *   **光流法:** 降低运动阈值。
    *   尝试使用不同的算法。
5.  **Q: 处理速度很慢？**
    A: 光流法本身计算量较大。帧差法和 SSIM 法相对较快。处理速度也受视频分辨率、时长和电脑 CPU 性能影响。可以尝试适当调整参数以减少计算量（例如增大帧差法的阈值/最小区域）。

## 注意事项

*   处理视频，特别是使用光流法，可能会消耗较多 CPU 资源。
*   请确保输出目录有足够的磁盘空间。
*   建议在处理前备份重要原始视频。
*   处理后的视频不包含音频。需要在视频编辑软件中重新匹配或添加音频。
*   请遵守相关版权法律，勿将工具用于非法用途。

## 使用权限与声明

本工具由笑颜（XiaoYan）借助 AI 及参考开源社区知识进行开发。

1.  本工具主要供学习交流和个人非盈利用途。
2.  用于商业目的前请联系作者。
3.  引用、修改或分发本工具时，请保留原作者信息。
4.  使用本工具产生的任何结果或风险由使用者自行承担。
5.  欢迎提出改进建议或参与贡献。

联系方式：
*   Discord：xy4402
*   电子邮件：3162172880@qq.com

## 开源许可

本项目（指代码部分）基于 GPLv3 许可证开源。这意味着您可以自由使用、修改和分发，但衍生作品需遵循相同许可证。详情请参阅项目中的 LICENSE 文件。

## 开发者唠叨

我是笑颜，一个刚上高一的学生，平时学习挺忙的。这个小工具是我课余与AI一起搞出来的，纯粹是为了好玩,因为我对编程比较感兴趣

要是你觉得这玩小意儿有用的话，那我会很开心的！不过，因为学习考试啥的，我可能没太多时间经常更新。但如果真有不少人在用，我看到大家的建议和反馈，肯定会想办法挤时间来修修补补的。

希望这个小玩意能给喜欢做动漫和看动漫的你们带来一点方便！

-- 笑颜
