#!/usr/bin/env python3
"""
视频Logo添加工具

为视频添加Logo水印，支持指定位置、大小和透明度。
"""

import argparse
import subprocess
import sys
from pathlib import Path


POSITIONS = {
    "top-left":     "10:10",
    "top-right":    "W-w-10:10",
    "bottom-left":  "10:H-h-10",
    "bottom-right": "W-w-10:H-h-10",
    "center":       "(W-w)/2:(H-h)/2",
}


def add_logo(
    video_path: str,
    logo_path: str,
    output_path: str,
    position: str = "bottom-right",
    scale: float = 0.15,
    opacity: float = 1.0,
    margin: int = 10,
):
    """使用ffmpeg为视频添加Logo水印

    Args:
        video_path: 输入视频路径
        logo_path: Logo图片路径（支持PNG透明背景）
        output_path: 输出视频路径
        position: Logo位置 (top-left, top-right, bottom-left, bottom-right, center)
        scale: Logo相对于视频宽度的缩放比例（默认0.15，即15%）
        opacity: Logo透明度 0.0~1.0（默认1.0，完全不透明）
        margin: Logo距离边缘的像素间距（默认10）
    """
    # 构建位置表达式（替换默认margin）
    pos_map = {
        "top-left":     f"{margin}:{margin}",
        "top-right":    f"W-w-{margin}:{margin}",
        "bottom-left":  f"{margin}:H-h-{margin}",
        "bottom-right": f"W-w-{margin}:H-h-{margin}",
        "center":       "(W-w)/2:(H-h)/2",
    }

    overlay_pos = pos_map[position]

    # 构建滤镜链：缩放Logo -> 设置透明度 -> 叠加到视频
    # [1:v] 是Logo输入流，iw*scale 按视频宽度比例缩放
    filter_parts = [
        f"[1:v]scale=iw*{scale}:-1",  # 按比例缩放Logo，高度自适应
    ]

    if opacity < 1.0:
        filter_parts.append(f"format=rgba,colorchannelmixer=aa={opacity}")

    filter_parts.append(f"[logo];[0:v][logo]overlay={overlay_pos}")

    filter_complex = ",".join(filter_parts[:-1]) + filter_parts[-1]

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-y", "-stats",
        "-i", video_path,
        "-i", logo_path,
        "-filter_complex", filter_complex,
        "-acodec", "copy",
        "-c:v", "libx265",
        "-crf", "18",
        "-preset", "slow",
        "-tag:v", "hvc1",
        output_path,
    ]

    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="视频Logo添加工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python add_logo.py input.mp4 logo.png
  python add_logo.py input.mp4 logo.png -p top-left
  python add_logo.py input.mp4 logo.png -p bottom-right -s 0.2 -o 0.8
  python add_logo.py input.mp4 logo.png output.mp4 -p center -m 20

位置参数:
  top-left      左上角
  top-right     右上角
  bottom-left   左下角
  bottom-right  右下角（默认）
  center        居中
        """,
    )
    parser.add_argument("input", help="输入视频文件路径")
    parser.add_argument("logo", help="Logo图片路径（推荐使用PNG透明背景）")
    parser.add_argument("output", nargs="?", default=None,
                        help="输出视频文件路径（默认: 输入文件_logo.mp4）")
    parser.add_argument("-p", "--position", default="bottom-right",
                        choices=POSITIONS.keys(),
                        help="Logo位置（默认: bottom-right）")
    parser.add_argument("-s", "--scale", type=float, default=0.15,
                        help="Logo相对于原始尺寸的缩放比例（默认: 0.15）")
    parser.add_argument("-o", "--opacity", type=float, default=1.0,
                        help="Logo透明度 0.0~1.0（默认: 1.0）")
    parser.add_argument("-m", "--margin", type=int, default=10,
                        help="Logo距离边缘的像素间距（默认: 10）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细输出")

    args = parser.parse_args()

    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入视频不存在: {input_path}")
        sys.exit(1)

    logo_path = Path(args.logo)
    if not logo_path.exists():
        print(f"错误: Logo文件不存在: {logo_path}")
        sys.exit(1)

    if not 0.0 <= args.opacity <= 1.0:
        print(f"错误: 透明度必须在 0.0~1.0 之间，当前值: {args.opacity}")
        sys.exit(1)

    if args.scale <= 0:
        print(f"错误: 缩放比例必须大于0，当前值: {args.scale}")
        sys.exit(1)

    # 生成输出文件名
    if args.output:
        output_path = args.output
    else:
        stem = input_path.stem
        suffix = input_path.suffix
        output_path = str(input_path.parent / f"{stem}_logo{suffix}")

    if args.verbose:
        print(f"输入视频: {input_path}")
        print(f"Logo文件: {logo_path}")
        print(f"输出文件: {output_path}")
        print(f"位置: {args.position}")
        print(f"缩放: {args.scale}")
        print(f"透明度: {args.opacity}")
        print(f"边距: {args.margin}px")

    try:
        add_logo(
            str(input_path),
            str(logo_path),
            output_path,
            position=args.position,
            scale=args.scale,
            opacity=args.opacity,
            margin=args.margin,
        )
        print(f"完成: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"错误: ffmpeg处理失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
