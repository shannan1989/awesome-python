# coding=utf-8

import os
import subprocess


def get_video_resolution(input_path):
    command = [
        'ffprobe',
        '-v', 'error',
        '-select_streams', 'v:0',
        '-show_entries', 'stream=width,height',
        '-of', 'csv=p=0',
        input_path
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        width, height = map(int, result.stdout.strip().split(','))
        return width, height
    except (subprocess.CalledProcessError, ValueError):
        print(f"无法获取视频分辨率: {input_path}")
        return 0, 0


def adjust_video_resolution_720p(input_path):
    width, height = get_video_resolution(input_path)
    # 检查视频分辨率是否不低于 720P
    if height <= 720:
        print(f"跳过视频 (分辨率{height}P): {input_path}")
        return


    input_dir, input_filename = os.path.split(input_path)
    name, ext = os.path.splitext(input_filename)
    output_filename = f"{name}_720P.mp4"
    output_path = os.path.join(input_dir, output_filename)

    # 定义 ffmpeg 命令，将视频转换为 MP4 格式且分辨率为 720P
    command = [
        'ffmpeg',
        '-loglevel', 'warning',
        '-i', input_path,
        '-s', '1280x720',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        output_path
    ]
    try:
        subprocess.run(command, check=True)
        print(f"转换成功: {input_path}")
    except subprocess.CalledProcessError as e:
        print(f"转换失败: {input_path}, 错误信息: {e}")


def batch_adjust_video_resolution(root_folder):
    # 遍历根文件夹及其所有子文件夹
    for root, dirs, files in os.walk(root_folder):
        for file in files:
            # 检查文件扩展名是否为常见视频格式
            if file.lower().endswith(('.mp4', '.mkv', '.avi', '.mov')):
                input_path = os.path.join(root, file)
                adjust_video_resolution_720p(input_path)


if __name__ == "__main__":
    root_folder = 'path/to/your/root/folder'
    batch_adjust_video_resolution(root_folder)
