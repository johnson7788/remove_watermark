#!/usr/bin/env python3
"""
视频水印去除工具

通过提取多个关键帧并分析其梯度差异来自动检测和去除静态水印。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

import imageio
import numpy as np
from scipy.ndimage import gaussian_filter


def normalize(x: np.ndarray) -> np.ndarray:
    """归一化数组到[0, 1]范围"""
    _min = np.min(x)
    _max = np.max(x)
    if _max - _min == 0:
        return np.zeros_like(x)
    return (x - _min) / (_max - _min)


def extract_keyframes(video_path: str, max_frames: int = 50) -> list:
    """提取视频的关键帧"""
    # 获取关键帧时间戳
    cmd = [
        "ffprobe", "-hide_banner", "-loglevel", "warning",
        "-select_streams", "v", "-skip_frame", "nokey",
        "-show_frames", "-show_entries", "frame=pkt_dts_time",
        video_path
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        keyframes_time = [
            line.split("=")[1].strip()
            for line in result.stdout.split("\n")
            if line.startswith("pkt_dts_time=") and "N/A" not in line
        ]
        keyframes_time = sorted(set(keyframes_time))
        # 如果没有找到关键帧，降级到时间间隔提取
        if not keyframes_time:
            raise ValueError("No keyframes found")
        # 随机打乱并取max_frames个
        np.random.seed(42)  # 可复现的结果
        np.random.shuffle(keyframes_time)
        keyframes_time = keyframes_time[:max_frames]
    except (subprocess.CalledProcessError, ValueError):
        # 如果ffprobe失败或没有关键帧，使用时间间隔提取
        cmd = [
            "ffprobe", "-hide_banner", "-loglevel", "warning",
            "-show_entries", "format=duration", "-of", "csv=p=0",
            video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        duration = float(result.stdout.strip().split(",")[0])
        interval = duration / max_frames
        keyframes_time = [f"{i * interval:.4f}" for i in range(1, max_frames + 1)]

    return keyframes_time


def extract_frames(video_path: str, keyframes_time: list, tmpdir: Path) -> int:
    """从视频中提取帧图片"""
    counter = 0
    for ts in keyframes_time:
        try:
            ts_str = str(float(ts))
        except ValueError:
            continue

        output_path = tmpdir / f"output_{counter}.png"
        cmd = [
            "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
            "-ss", ts_str, "-i", video_path, "-vframes", "1",
            str(output_path)
        ]
        subprocess.run(cmd, capture_output=True)
        counter += 1

    return counter


def extract_watermark_mask(tmpdir: Path) -> Path:
    """通过分析多帧图像提取水印蒙版"""
    buff = []
    for p in sorted(tmpdir.glob("output_*.png")):
        buff.append(imageio.imread(p))

    if len(buff) < 2:
        raise ValueError(f"需要至少2帧图像来提取水印，实际获取了 {len(buff)} 帧")

    images = np.array(buff)

    # 计算梯度
    dx = np.gradient(images, axis=1).mean(axis=3)
    dy = np.gradient(images, axis=2).mean(axis=3)
    mean_dx = np.abs(np.mean(dx, axis=0))
    mean_dy = np.abs(np.mean(dy, axis=0))

    # 阈值过滤
    threshold = 10
    salient = ((mean_dx > threshold) | (mean_dy > threshold)).astype(float)
    salient = normalize(gaussian_filter(salient, sigma=3))
    mask = ((salient > 0.2) * 255).astype(np.uint8)

    mask_path = tmpdir / "mask.png"
    imageio.imsave(str(mask_path), mask)
    return mask_path


def remove_watermark(video_path: str, mask_path: Path, output_path: str):
    """使用ffmpeg的removelogo滤镜去除水印"""
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-y", "-stats", "-i", video_path,
        "-acodec", "copy",
        "-vf", f"removelogo={str(mask_path)}",
        output_path
    ]
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="视频水印去除工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python remove_watermark.py input.mp4
  python remove_watermark.py input.mp4 output_cleaned.mp4
  python remove_watermark.py input.mp4 -k 100
        """
    )
    parser.add_argument("input", help="输入视频文件路径")
    parser.add_argument("output", nargs="?", default=None,
                        help="输出视频文件路径（默认: 输入文件_cleaned.mp4）")
    parser.add_argument("-k", "--keyframes", type=int, default=50,
                        help="提取的关键帧数量（默认: 50）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细输出")

    args = parser.parse_args()

    # 验证输入文件
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    # 生成输出文件名
    if args.output:
        output_path = args.output
    else:
        stem = input_path.stem
        suffix = input_path.suffix
        output_path = str(input_path.parent / f"{stem}_cleaned{suffix}")

    # 创建临时目录
    tmpdir = Path(tempfile.mkdtemp(prefix="watermark_remove_"))

    try:
        if args.verbose:
            print(f"处理视频: {input_path}")
            print(f"输出文件: {output_path}")
            print(f"关键帧数量: {args.keyframes}")

        # 提取关键帧
        if args.verbose:
            print("提取关键帧...")
        keyframes_time = extract_keyframes(str(input_path), args.keyframes)
        if args.verbose:
            print(f"找到 {len(keyframes_time)} 个关键帧")

        # 提取帧图片
        if args.verbose:
            print("提取帧图片...")
        frame_count = extract_frames(str(input_path), keyframes_time, tmpdir)
        if args.verbose:
            print(f"提取了 {frame_count} 帧")

        if frame_count < 2:
            print(f"错误: 提取了 {frame_count} 帧，需要至少2帧")
            sys.exit(1)

        # 提取水印蒙版
        if args.verbose:
            print("提取水印蒙版...")
        mask_path = extract_watermark_mask(tmpdir)
        if args.verbose:
            print(f"蒙版保存至: {mask_path}")

        # 去除水印
        if args.verbose:
            print("去除水印中...")
        remove_watermark(str(input_path), mask_path, output_path)
        if args.verbose:
            print(f"完成！输出文件: {output_path}")
        else:
            print(f"完成: {output_path}")

    except Exception as e:
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        # 清理临时目录
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
