# 视频水印工具箱

集视频水印去除，视频高清化，视频Logo添加于一体的工具箱。

## 功能介绍

### 1. 水印去除
自动检测并去除视频中的静态水印。通过分析多个关键帧的梯度差异来定位水印区域，然后使用 FFmpeg 进行修复。

### 2. Logo添加
为视频添加Logo水印，支持指定位置、大小和透明度。

### 3. 图片高清化
使用 Upscayl 对图片进行超分辨率放大，支持 2x/3x/4x 放大倍数。

### 4. 视频高清化
使用 Upscayl 对视频进行逐帧超分辨率放大，生成高清视频（H.265 编码）。

---

## 示例视频
原始带logo的视频
[test_video.mp4](test_video.mp4)
去掉logo
[output.mp4](output.mp4)
高清化
[output_hd.mp4](output_hd.mp4)
加上logo
[output_hd_logo.mp4](output_hd_logo.mp4)

## 特性

- ✅ 自动水印检测（基于多帧图像分析）
- ✅ 支持多种 Logo 位置（左上/右上/左下/右下/居中）
- ✅ 可调节 Logo 大小和透明度
- ✅ 图片超分辨率放大（Upscayl）
- ✅ 视频超分辨率放大（Upscayl）
- ✅ CPU 友好，本地即可运行
- ✅ 支持本地部署和 Docker 部署

## 依赖

- Python 3.8+
- FFmpeg
- numpy
- scipy
- imageio

---

## 快速开始

### 环境准备

**macOS:**
```bash
brew install ffmpeg
```

**安装 Python 依赖:**
```bash
pip install numpy scipy imageio
```

---

## 用法说明

### 水印去除

```bash
# 基本用法（输出自动命名为 input_cleaned.mp4）
python remove_video_watermark.py input.mp4

# 指定输出文件
python remove_video_watermark.py input.mp4 output.mp4

# 指定提取的关键帧数量
python remove_video_watermark.py input.mp4 -k 100

# 显示详细输出
python remove_video_watermark.py input.mp4 -v
```

### Logo添加

```bash
# 基本用法（Logo默认添加在右下角）
python add_logo.py input.mp4 logo.png

# 指定输出文件
python add_logo.py input.mp4 logo.png output.mp4

# 指定位置
python add_logo.py input.mp4 logo.png -p top-left      # 左上角
python add_logo.py input.mp4 logo.png -p top-right     # 右上角
python add_logo.py input.mp4 logo.png -p bottom-left   # 左下角
python add_logo.py input.mp4 logo.png -p bottom-right  # 右下角（默认）
python add_logo.py input.mp4 logo.png -p center        # 居中

# 完整参数示例
python add_logo.py output.mp4 logo.png -p top-right -s 1.5 -o 1 -m 20
# 输出到
output_logo.mp4文件中
```

### 视频高清化

```bash
# 默认 4x 放大
python upscale_video.py input.mp4

# 2x 放大
python upscale_video.py input.mp4 -s 2

# 指定输出路径
python upscale_video.py input.mp4 -s 4 -o output_hd.mp4

# 4 线程并发加速
python upscale_video.py input.mp4 -w 4 -v
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| **水印去除** |
| `input` | 输入视频文件路径 | 必填 |
| `output` | 输出视频文件路径 | `{输入名}_cleaned.{后缀}` |
| `-k, --keyframes` | 提取的关键帧数量 | 50 |
| `-v, --verbose` | 显示详细输出 | False |
| **Logo添加** |
| `input` | 输入视频文件路径 | 必填 |
| `logo` | Logo图片路径 | 必填 |
| `output` | 输出视频文件路径 | `{输入名}_logo.{后缀}` |
| `-p, --position` | Logo位置 | bottom-right |
| `-s, --scale` | Logo缩放比例 | 0.15 |
| `-o, --opacity` | 透明度 (0.0~1.0) | 1.0 |
| `-m, --margin` | 距边缘像素间距 | 10 |
| `-v, --verbose` | 显示详细输出 | False |
| **图片高清化** |
| `-i, --input` | 输入图片路径 | 必填 |
| `-o, --output` | 输出图片路径 | 必填 |
| `-n, --model` | Upscayl 模型名称 | upscayl-standard-4x |
| `-s, --scale` | 放大倍数：2/3/4 | 4 |
| `-f, --format` | 输出格式 | png |
| **视频高清化** |
| `-s` | 放大倍数：2/3/4（默认 4） | 4 |
| `-o` | 输出路径（默认 输入文件_upscaled.mp4） | `{输入名}_upscaled.{后缀}` |
| `-w` | 并发线程数（默认 1，可提高加速） | 1 |
| `-n` | upscayl 模型名称 | upscayl-standard-4x |
| `-v` | 显示详细信息 | False |
| `--keep-frames` | 保留中间帧文件（调试用） | False |

---

## 图片高清化 (Upscayl)

### 安装 Upscayl

```bash
cd upscayl-cli
go mod download
make local
```

编译成功后，可执行文件会生成在：`release/build/local`

```bash
# 安装到系统路径
mv release/build/local/upscayl /usr/local/bin

# 验证安装
upscayl --version
upscayl run --help
```

### 使用方法

```bash
# 基本用法（4x 放大）
upscayl run -i logo.png -o logo_upscaled.png -n upscayl-standard-4x -s 4 -f png

# 2x 放大
upscayl run -i input.png -o output.png -n upscayl-standard-2x -s 2 -f png
```

### 可用模型

| 模型名称 | 放大倍数 | 适用场景 |
|----------|----------|----------|
| `upscayl-standard-2x` | 2x | 通用图片 |
| `upscayl-standard-3x` | 3x | 通用图片 |
| `upscayl-standard-4x` | 4x | 通用图片 |
| `upscayl-photo-4x` | 4x | 照片优化 |
| `upscayl-anime-4x` | 4x | 动漫/插画 |

---

## Docker 部署

### 构建镜像
```bash
docker build -t watermark-remover .
```

### 运行容器

```bash
# 水印去除
docker run --rm -v $(pwd):/app watermark-remover test_video.mp4

# Logo添加
docker run --rm -v $(pwd):/app watermark-remover add_logo.py test_video.mp4 logo.png
```

---

## 工作原理

### 水印检测流程
1. **关键帧提取**：从视频中随机提取 N 个关键帧
2. **水印检测**：通过计算多帧图像的梯度差异，识别水印区域（水印位置在所有帧中保持不变）
3. **蒙版生成**：生成二值蒙版标记水印位置
4. **水印去除**：使用 FFmpeg 的 `removelogo` 滤镜对水印区域进行修复

### Logo添加原理
使用 FFmpeg 的 `overlay` 滤镜将 Logo 叠加到视频指定位置，支持缩放和透明度调整。

### 视频高清化原理
1. **分析视频** - 获取分辨率、帧率、时长等信息
2. **提取帧** - 用 ffmpeg 将视频拆为逐帧 PNG
3. **逐帧放大** - 调用 upscayl CLI 对每帧进行超分辨率放大
4. **合成视频** - 将放大后的帧 + 原始音频合成为高清视频（H.265 编码）

---

## 常见问题

### 水印检测不准确？
- 增加关键帧数量（`-k 100` 或更多）
- 确保水印在视频中是静态的
- 确保水印有足够的梯度差异

### 处理速度慢？
- 减少关键帧数量
- 使用 GPU 加速（需要 FFmpeg 编译时支持）

### Logo 推荐？
推荐使用 PNG 透明背景图片效果最佳。

---

## 测试环境

- macOS 10.14+
- Ubuntu 20.04+
- Python 3.8+

---

## 联系作者

如有问题，请联系作者：

![weichat.png](weichat.png)

---

## 许可证

MIT
