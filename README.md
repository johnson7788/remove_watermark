# 视频水印去除工具

自动检测并去除视频中的静态水印。通过分析多个关键帧的梯度差异来定位水印区域，然后使用 FFmpeg 进行修复。

## 特性

- **自动水印检测**：基于多帧图像分析，无需手动标注位置
- **CPU 友好**：可在普通笔记本上运行
- **简单易用**：一行命令即可完成水印去除
- **灵活部署**：支持本地部署和 Docker 部署

- ✅ 白色的水印
- ✅ 黑色或其他颜色的水印
- ✅ 半透明水印
- ✅ LOGO 类水印

## 依赖

- Python 3.8+
- FFmpeg
- numpy
- scipy
- imageio

## 部署方式

### 方式一：本地部署

#### 1. 安装 FFmpeg

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install ffmpeg
```

**Windows:**
下载并安装 [FFmpeg](https://ffmpeg.org/download.html)，添加到系统 PATH。

#### 2. 安装 Python 依赖

```bash
pip install numpy scipy imageio
```

#### 3. 运行程序

```bash
# 基本用法（输出自动命名为 input_cleaned.mp4）
python remove_watermark.py input.mp4

# 指定输出文件
python remove_watermark.py input.mp4 output.mp4

# 指定提取的关键帧数量
python remove_watermark.py input.mp4 -k 100

# 显示详细输出
python remove_watermark.py input.mp4 -v
```

### 方式二：Docker 部署

#### 1. 构建镜像

```bash
docker build -t watermark-remover .
```

#### 2. 运行容器

```bash
# 基本用法
docker run --rm -v $(pwd):/app watermark-remover test_video.mp4

# 指定输出文件
docker run --rm -v $(pwd):/app watermark-remover test_video.mp4 output.mp4

# 指定关键帧数量
docker run --rm -v $(pwd):/app watermark-remover test_video.mp4 -k 100
```

#### 3. 使用 Docker Compose（可选）

```bash
docker-compose run watermark test_video.mp4
```

## 工作原理

1. **关键帧提取**：从视频中随机提取 N 个关键帧
2. **水印检测**：通过计算多帧图像的梯度差异，识别水印区域（水印位置在所有帧中保持不变）
3. **蒙版生成**：生成二值蒙版标记水印位置
4. **水印去除**：使用 FFmpeg 的 `removelogo` 滤镜对水印区域进行修复

## 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `input` | 输入视频文件路径 | 必填 |
| `output` | 输出视频文件路径 | `{输入名}_cleaned.{后缀}` |
| `-k, --keyframes` | 提取的关键帧数量 | 50 |
| `-v, --verbose` | 显示详细输出 | False |

## 常见问题

### 提取不到关键帧？

程序会自动降级为时间间隔提取。如果仍然失败，请检查：
- FFmpeg 是否正确安装
- 输入视频是否有效

### 水印检测不准确？

- 增加关键帧数量（`-k 100` 或更多）
- 确保水印在视频中是静态的
- 确保水印有足够的梯度差异（明显的文字或图案）

### 处理速度慢？

- 减少关键帧数量
- 使用 GPU 加速（需要 FFmpeg 编译时支持）

## 测试环境

- macOS 10.14+
- Ubuntu 20.04+
- Python 3.8+

## 许可证

MIT
