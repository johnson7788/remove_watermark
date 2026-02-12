#!/usr/bin/env python3
"""
视频高清化工具

使用 upscayl CLI 对视频逐帧进行超分辨率放大，然后重新合成视频。
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


UPSCAYL_BIN = "upscayl"
MODEL_PATH = os.path.expanduser("~/.upscayl-cli/resources/models")
DEFAULT_MODEL = "upscayl-standard-4x"


def get_video_info(video_path: str) -> dict:
    """获取视频的帧率、分辨率、时长等信息"""
    cmd = [
        "ffprobe", "-hide_banner", "-loglevel", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,nb_frames",
        "-show_entries", "format=duration",
        "-of", "csv=p=0:s=,",
        video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    lines = [l.strip() for l in result.stdout.strip().split("\n") if l.strip()]

    # 第一行: width,height,r_frame_rate,nb_frames
    stream_parts = lines[0].split(",")
    width = int(stream_parts[0])
    height = int(stream_parts[1])
    fps_str = stream_parts[2]
    nb_frames_str = stream_parts[3] if len(stream_parts) > 3 else "N/A"

    # 解析帧率
    if "/" in fps_str:
        num, den = fps_str.split("/")
        fps = float(num) / float(den)
    else:
        fps = float(fps_str)

    # 时长
    duration = float(lines[1]) if len(lines) > 1 else 0.0

    # 总帧数
    if nb_frames_str != "N/A" and nb_frames_str.isdigit():
        total_frames = int(nb_frames_str)
    else:
        total_frames = int(fps * duration)

    return {
        "width": width,
        "height": height,
        "fps": fps,
        "fps_str": fps_str,
        "duration": duration,
        "total_frames": total_frames,
    }


def has_audio(video_path: str) -> bool:
    """检查视频是否包含音频流"""
    cmd = [
        "ffprobe", "-hide_banner", "-loglevel", "error",
        "-select_streams", "a", "-show_entries", "stream=index",
        "-of", "csv=p=0", video_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return bool(result.stdout.strip())


def extract_frames(video_path: str, frames_dir: Path, verbose: bool = False):
    """使用 ffmpeg 将视频拆分为逐帧 PNG 图片"""
    output_pattern = str(frames_dir / "frame_%08d.png")
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error",
        "-i", video_path,
        "-vsync", "cfr",
        output_pattern
    ]
    if verbose:
        print(f"  命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def upscale_frame(frame_path: Path, output_path: Path, scale: int,
                  model_name: str, model_path: str, fmt: str = "png") -> bool:
    """使用 upscayl 放大单帧图片"""
    cmd = [
        UPSCAYL_BIN, "run",
        "-i", str(frame_path),
        "-o", str(output_path),
        "-m", model_path,
        "-n", model_name,
        "-s", str(scale),
        "-f", fmt,
    ]
    try:
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n  放大失败: {frame_path.name} - {e.stderr.decode() if e.stderr else e}")
        return False


def upscale_frames(input_dir: Path, output_dir: Path, scale: int,
                   model_name: str, model_path: str,
                   workers: int = 1, verbose: bool = False):
    """批量放大所有帧"""
    frames = sorted(input_dir.glob("frame_*.png"))
    total = len(frames)

    if total == 0:
        raise ValueError("没有找到可处理的帧图片")

    print(f"  共 {total} 帧，放大倍数: {scale}x，并发数: {workers}")

    completed = 0
    failed = 0

    def process(frame_path):
        out_path = output_dir / frame_path.name
        return frame_path.name, upscale_frame(
            frame_path, out_path, scale, model_name, model_path
        )

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(process, f): f for f in frames}
        for future in as_completed(futures):
            name, success = future.result()
            if success:
                completed += 1
            else:
                failed += 1
            # 进度显示
            pct = (completed + failed) * 100 // total
            print(f"\r  进度: {completed + failed}/{total} ({pct}%)"
                  f" - 成功: {completed}, 失败: {failed}", end="", flush=True)

    print()  # 换行

    if failed > 0:
        print(f"  警告: {failed} 帧处理失败")
    if completed == 0:
        raise RuntimeError("所有帧都处理失败")


def reassemble_video(frames_dir: Path, audio_source: str, output_path: str,
                     fps_str: str, has_audio_stream: bool, verbose: bool = False):
    """将放大后的帧合成视频"""
    input_pattern = str(frames_dir / "frame_%08d.png")

    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "warning",
        "-y", "-stats",
        "-framerate", fps_str,
        "-i", input_pattern,
    ]

    # 如果原视频有音频，加入音频
    if has_audio_stream:
        cmd.extend(["-i", audio_source, "-map", "0:v", "-map", "1:a",
                     "-c:a", "copy"])

    cmd.extend([
        "-c:v", "libx265",
        "-crf", "18",
        "-preset", "slow",
        "-tag:v", "hvc1",
        "-pix_fmt", "yuv420p",
        output_path
    ])

    if verbose:
        print(f"  命令: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser(
        description="视频高清化工具 - 使用 upscayl 超分辨率放大视频",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python upscale_video.py input.mp4                    # 默认 4x 放大
  python upscale_video.py input.mp4 -s 2               # 2x 放大
  python upscale_video.py input.mp4 -s 4 -o output.mp4 # 4x 放大，指定输出
  python upscale_video.py input.mp4 -w 4 -v            # 4线程并发，详细输出
        """
    )
    parser.add_argument("input", help="输入视频文件路径")
    parser.add_argument("-o", "--output", default=None,
                        help="输出视频文件路径（默认: 输入文件_upscaled.mp4）")
    parser.add_argument("-s", "--scale", type=int, default=4, choices=[2, 3, 4],
                        help="放大倍数（2/3/4，默认: 4）")
    parser.add_argument("-n", "--model-name", default=DEFAULT_MODEL,
                        help=f"模型名称（默认: {DEFAULT_MODEL}）")
    parser.add_argument("-m", "--model-path", default=MODEL_PATH,
                        help=f"模型文件夹路径（默认: {MODEL_PATH}）")
    parser.add_argument("-w", "--workers", type=int, default=1,
                        help="并发处理线程数（默认: 1）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="显示详细输出")
    parser.add_argument("--keep-frames", action="store_true",
                        help="保留提取的帧图片（调试用）")

    args = parser.parse_args()

    # 验证输入
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    # 检查 upscayl 是否可用
    if not shutil.which(UPSCAYL_BIN):
        print(f"错误: 未找到 {UPSCAYL_BIN}，请确认已安装 upscayl-cli")
        sys.exit(1)

    # 检查模型路径
    if not Path(args.model_path).exists():
        print(f"错误: 模型路径不存在: {args.model_path}")
        sys.exit(1)

    # 生成输出文件名
    if args.output:
        output_path = args.output
    else:
        stem = input_path.stem
        output_path = str(input_path.parent / f"{stem}_upscaled.mp4")

    # 获取视频信息
    print(f"[1/4] 分析视频...")
    info = get_video_info(str(input_path))
    audio = has_audio(str(input_path))
    print(f"  分辨率: {info['width']}x{info['height']}")
    print(f"  帧率: {info['fps']:.2f} fps")
    print(f"  时长: {info['duration']:.1f} 秒")
    print(f"  总帧数: {info['total_frames']}")
    print(f"  有音频: {'是' if audio else '否'}")
    print(f"  目标分辨率: {info['width'] * args.scale}x{info['height'] * args.scale}")

    # 创建临时目录
    tmpdir = Path(tempfile.mkdtemp(prefix="upscale_video_"))
    frames_dir = tmpdir / "frames"
    upscaled_dir = tmpdir / "upscaled"
    frames_dir.mkdir()
    upscaled_dir.mkdir()

    try:
        # 提取帧
        print(f"\n[2/4] 提取视频帧...")
        extract_frames(str(input_path), frames_dir, args.verbose)
        actual_frames = len(list(frames_dir.glob("frame_*.png")))
        print(f"  提取了 {actual_frames} 帧")

        # 放大帧
        print(f"\n[3/4] 使用 upscayl 放大帧 ({args.scale}x)...")
        upscale_frames(
            frames_dir, upscaled_dir, args.scale,
            args.model_name, args.model_path,
            workers=args.workers, verbose=args.verbose
        )

        # 合成视频
        print(f"\n[4/4] 合成高清视频...")
        reassemble_video(
            upscaled_dir, str(input_path), output_path,
            info["fps_str"], audio, args.verbose
        )

        # 输出结果信息
        output_size = os.path.getsize(output_path) / (1024 * 1024)
        input_size = os.path.getsize(str(input_path)) / (1024 * 1024)
        print(f"\n完成！")
        print(f"  输入: {input_path} ({input_size:.1f} MB)")
        print(f"  输出: {output_path} ({output_size:.1f} MB)")
        print(f"  放大: {args.scale}x ({info['width']}x{info['height']}"
              f" -> {info['width'] * args.scale}x{info['height'] * args.scale})")

    except Exception as e:
        print(f"\n错误: {e}")
        sys.exit(1)
    finally:
        if args.keep_frames:
            print(f"  帧图片保留在: {tmpdir}")
        else:
            shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
